"""REYAX RYLR998 UART LoRa driver for Raspberry Pi Gateway."""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Callable, Optional

import config

logger = logging.getLogger(__name__)

# LoRa roles:
# - Downlink (tally / pair): RYLR998 TX via AT+SEND → tally light SX1262 RX
# - Uplink (MAC broadcast): tally light SX1262 TX → RYLR998 RX (+RCV)
# Uplink from lights uses a 5-byte SX1262 shim header before ASCII-hex payload.
_SX1262_UPLINK_HEADER_LEN = 5


def _unwrap_sx1262_frame(data: bytes) -> bytes:
    """Decode uplink frames from tally-light SX1262 (not RYLR998 downlink format)."""
    if len(data) >= 2 and data[0] == 0xAB:
        return data
    if len(data) >= 5:
        declared_len = data[4]
        hex_part = data[5 : 5 + declared_len]
        if declared_len > 0 and len(hex_part) == declared_len:
            try:
                return bytes.fromhex(hex_part.decode("ascii"))
            except (UnicodeDecodeError, ValueError):
                pass
    return data


class Rylr998Radio:
    def __init__(self) -> None:
        self._serial = None
        self._rx_callback: Optional[Callable[[bytes], None]] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._tx_lock = threading.Lock()
        self._responses: queue.Queue[str] = queue.Queue()

    def _configure(self) -> None:
        import serial

        self._serial = serial.Serial(
            config.RYLR_SERIAL_PORT,
            config.RYLR_BAUDRATE,
            timeout=0.1,
            write_timeout=1.0,
        )
        self._serial.reset_input_buffer()
        self._send_command_direct("AT")
        self._send_command_direct("AT+MODE=0")
        self._send_command_direct(f"AT+ADDRESS={config.RYLR_ADDRESS}")
        self._send_command_direct(f"AT+NETWORKID={config.RYLR_NETWORK_ID}")
        self._send_command_direct(f"AT+BAND={config.RYLR_BAND_HZ}")
        self._send_command_direct(
            "AT+PARAMETER="
            f"{config.RYLR_SPREADING_FACTOR},"
            f"{config.RYLR_BANDWIDTH_CODE},"
            f"{config.RYLR_CODING_RATE},"
            f"{config.RYLR_PREAMBLE_LENGTH}"
        )
        self._send_command_direct(f"AT+CRFOP={config.RYLR_RF_POWER_DBM}")
        logger.info(
            "RYLR998 initialized on %s at %.1f MHz",
            config.RYLR_SERIAL_PORT,
            config.RYLR_BAND_HZ / 1_000_000,
        )

    def start(self, on_receive: Optional[Callable[[bytes], None]] = None) -> None:
        self._rx_callback = on_receive
        self._configure()
        self._running = True
        self._thread = threading.Thread(target=self._rx_loop, daemon=True, name="lora-rx")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._serial:
            self._serial.close()

    def transmit(self, packet: bytes) -> None:
        """Send protocol packet via AT+SEND per RYLR998 manual.

        AT+SEND=<address>,<length>,<data>
        - address 0 = broadcast
        - length = ASCII character count of <data> (max 240)
        - <data> is literal ASCII (we send the packet as an uppercase hex string)

        RYLR998 is the downlink transmitter: the module prepends an 8-byte
        over-air header, then the ASCII-hex string. Tally lights decode that
        on receive (see tallylight lora_handler.cpp).
        """
        if self._serial is None:
            raise RuntimeError("LoRa radio not initialized")
        payload = packet.hex().upper()
        if len(payload) > 240:
            raise ValueError("RYLR998 payload exceeds 240 ASCII bytes")
        command = f"AT+SEND={config.RYLR_TARGET_ADDRESS},{len(payload)},{payload}"
        with self._tx_lock:
            self._send_command(command)
        logger.info("TX LoRa AT+SEND %s (%d ascii bytes)", payload, len(payload))

    def _rx_loop(self) -> None:
        while self._running:
            try:
                line = self._read_line()
                if not line:
                    continue
                if line.startswith("+RCV="):
                    data = self._parse_receive(line)
                    if self._rx_callback and data:
                        self._rx_callback(data)
                else:
                    self._responses.put(line)
            except Exception as exc:
                logger.warning("LoRa RX error: %s", exc)
                time.sleep(0.1)

    def _write_command(self, command: str) -> None:
        if self._serial is None:
            raise RuntimeError("RYLR998 serial port not initialized")
        self._serial.write((command + "\r\n").encode("ascii"))
        self._serial.flush()

    def _read_line(self) -> str:
        if self._serial is None:
            return ""
        raw = self._serial.readline()
        if not raw:
            return ""
        return raw.decode("ascii", errors="replace").strip()

    def _send_command_direct(self, command: str, timeout_s: float = 2.0) -> None:
        self._write_command(command)
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            line = self._read_line()
            if not line:
                continue
            if line == "+OK" or line.startswith(f"+{command[3:] if command.startswith('AT+') else 'OK'}"):
                return
            if line.startswith("+ERR"):
                raise RuntimeError(f"RYLR998 command failed: {command}: {line}")
            if line.startswith("+RCV="):
                logger.debug("Ignoring RX during config: %s", line)
        raise TimeoutError(f"RYLR998 command timed out: {command}")

    def _send_command(self, command: str, timeout_s: float = 2.0) -> None:
        while not self._responses.empty():
            self._responses.get_nowait()
        self._write_command(command)
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            try:
                line = self._responses.get(timeout=0.1)
            except queue.Empty:
                continue
            if line == "+OK":
                return
            if line.startswith("+ERR"):
                raise RuntimeError(f"RYLR998 command failed: {command}: {line}")
        raise TimeoutError(f"RYLR998 command timed out: {command}")

    def _parse_receive(self, line: str) -> bytes:
        # +RCV=<addr>,<len>,<hex-data>,<rssi>,<snr>
        parts = line[5:].split(",", 4)
        if len(parts) != 5:
            logger.warning("Malformed RYLR998 receive line: %s", line)
            return b""
        sender, length_text, payload, rssi, snr = parts
        payload = payload.strip()
        try:
            expected_len = int(length_text)
        except ValueError:
            logger.warning("Invalid RYLR998 receive length: %s", line)
            return b""
        if len(payload) != expected_len:
            logger.warning("RYLR998 receive length mismatch from %s: %s", sender, line)
            return b""
        try:
            packet = _unwrap_sx1262_frame(bytes.fromhex(payload))
        except ValueError:
            logger.warning("RYLR998 payload is not hex: %s", payload)
            return b""
        logger.debug("RX %s from addr=%s rssi=%s snr=%s", packet.hex(), sender, rssi, snr)
        return packet


def create_lora_radio() -> Rylr998Radio:
    return Rylr998Radio()
