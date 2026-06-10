#!/usr/bin/env python3
"""ATEM LoRa Tally Gateway main entry point."""

from __future__ import annotations

import logging
import os
import sys
import threading
import time

# Ensure gateway package root is on sys.path
GATEWAY_DIR = os.path.dirname(os.path.abspath(__file__))
if GATEWAY_DIR not in sys.path:
    sys.path.insert(0, GATEWAY_DIR)

import config
from atem.client import ATEMService, create_atem_client
from lora.radio import create_lora_radio
from persistence import load_gateway_settings, load_paired_devices, save_paired_devices
from protocol.constants import PKT_MAC_BROADCAST
from protocol.packets import decode_mac_broadcast, encode_pair_name, encode_tally_status, normalize_mac, parse_packet
from state import GatewayState
from web.app import create_app, run_web_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("tally-gateway")


class TallyGateway:
    def __init__(self) -> None:
        settings = load_gateway_settings()
        self.state = GatewayState()
        self.atem = create_atem_client(str(settings.get("atem_ip", config.ATEM_DEFAULT_IP)))
        self.lora = create_lora_radio()
        self.atem_service = ATEMService(self.atem)
        self._seq = 0
        self._broadcast_now = threading.Event()
        self._stop = threading.Event()
        self._atem_was_connected = False

    def start(self) -> None:
        paired = load_paired_devices()
        self.state.set_paired_devices(paired)
        logger.info("Loaded %d paired devices", len(paired))

        self.atem.on_tally_change = self._request_broadcast
        self.atem.on_label_change = self._on_label_change
        self.atem_service.start()

        self.lora.start(on_receive=self._on_lora_receive)

        app = create_app(self.state, self.atem, self.lora)
        web_thread = threading.Thread(
            target=run_web_server,
            args=(app,),
            daemon=True,
            name="flask-web",
        )
        web_thread.start()
        logger.info("Web UI at http://%s:%s", config.FLASK_HOST, config.FLASK_PORT)

        self._main_loop()

    def stop(self) -> None:
        self._stop.set()
        self.lora.stop()
        self.atem_service.stop()

    def _request_broadcast(self) -> None:
        self._broadcast_now.set()

    def _on_label_change(self, channel: int, _old: str, new_label: str) -> None:
        mac = self.state.find_mac_by_tally_id(channel)
        if not mac:
            return
        paired = self.state.get_paired()
        info = paired.get(mac)
        if info:
            info["label"] = new_label
            self.state.pair_device(mac, info)
            save_paired_devices(self.state.get_paired())
        packet = encode_pair_name(mac, channel, new_label)
        self.lora.transmit(packet)
        logger.info("Pushed label update CAM%d -> %s", channel, new_label)

    def _push_all_labels(self) -> None:
        if not self.atem.connected:
            return
        for mac, info in self.state.get_paired().items():
            tally_id = info["tally_id"]
            label = self.atem.get_label(tally_id)
            info["label"] = label
            self.state.pair_device(mac, info)
            self.lora.transmit(encode_pair_name(mac, tally_id, label))
        save_paired_devices(self.state.get_paired())

    def _on_lora_receive(self, data: bytes) -> None:
        try:
            packet_type, payload = parse_packet(data)
        except Exception:
            return
        if packet_type == PKT_MAC_BROADCAST:
            mac = normalize_mac(payload["mac"])
            self.state.add_unpaired(mac)

    def _broadcast_tally(self) -> None:
        if not self.atem.connected:
            return
        states = self.atem.get_tally_states()
        packet = encode_tally_status(self._seq, states)
        self.lora.transmit(packet)
        self._seq = (self._seq + 1) & 0xFF
        self.state.last_broadcast_seq = self._seq

    def _main_loop(self) -> None:
        next_broadcast = time.monotonic()
        while not self._stop.is_set():
            if self.atem.connected and not self._atem_was_connected:
                self._atem_was_connected = True
                self._push_all_labels()
            elif not self.atem.connected:
                self._atem_was_connected = False

            now = time.monotonic()
            if self._broadcast_now.is_set() or now >= next_broadcast:
                self._broadcast_now.clear()
                self._broadcast_tally()
                next_broadcast = now + config.TALLY_BROADCAST_INTERVAL_S
            time.sleep(0.01)


def main() -> None:
    gateway = TallyGateway()
    try:
        gateway.start()
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        gateway.stop()


if __name__ == "__main__":
    main()
