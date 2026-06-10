"""ATEM switcher client using PyATEMMax."""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

import config
from protocol.constants import MAX_CHANNELS, TALLY_OFF

logger = logging.getLogger(__name__)


class ATEMClient:
    def __init__(self, ip: str = config.ATEM_DEFAULT_IP) -> None:
        self.ip = ip
        self.switcher = None
        self._connected = False
        self._last_states: list[int] = [TALLY_OFF] * MAX_CHANNELS
        self._last_labels: dict[int, str] = {}
        self._lock = threading.Lock()
        self.on_tally_change: Optional[Callable[[], None]] = None
        self.on_label_change: Optional[Callable[[int, str, str], None]] = None

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        if not self.ip:
            return
        from PyATEMMax import ATEMMax

        self.switcher = ATEMMax()
        logger.info("Connecting to ATEM at %s", self.ip)
        self.switcher.connect(self.ip)
        if not self.switcher.waitForConnection(timeout=10.0):
            raise TimeoutError(f"Could not connect to ATEM at {self.ip}")
        self._connected = True
        self._last_states = self.get_tally_states()
        self._last_labels = {i: self.get_label(i) for i in range(1, MAX_CHANNELS + 1)}
        logger.info("Connected to ATEM")

    def set_ip(self, ip: str) -> None:
        ip = ip.strip()
        with self._lock:
            if ip == self.ip:
                return
            self.ip = ip
            self.disconnect()
        logger.info("ATEM IP updated to %s", ip or "(empty)")

    def disconnect(self) -> None:
        self._connected = False
        if self.switcher is not None:
            try:
                self.switcher.disconnect()
            except Exception:
                pass
        self.switcher = None

    def _video_source(self, channel: int):
        return getattr(self.switcher.atem.videoSources, f"input{channel}")

    def get_tally_states(self) -> list[int]:
        if not self._connected or self.switcher is None:
            return [TALLY_OFF] * MAX_CHANNELS
        states: list[int] = []
        for channel in range(1, MAX_CHANNELS + 1):
            source = self._video_source(channel)
            flags = self.switcher.tally.bySource.flags[source]
            if flags.program:
                states.append(TALLY_PGM)
            elif flags.preview:
                states.append(TALLY_PVW)
            else:
                states.append(TALLY_OFF)
        return states

    def get_label(self, channel: int) -> str:
        if not self._connected or self.switcher is None:
            return f"CAM{channel}"
        props = self.switcher.inputProperties[self._video_source(channel)]
        label = props.longName
        return label if label else f"CAM{channel}"

    def get_camera_labels(self) -> list[dict]:
        return [{"id": i, "label": self.get_label(i)} for i in range(1, MAX_CHANNELS + 1)]

    def poll(self) -> bool:
        if not self._connected:
            return False
        changed = False
        states = self.get_tally_states()
        if states != self._last_states:
            self._last_states = states
            changed = True
            if self.on_tally_change:
                self.on_tally_change()

        for channel in range(1, MAX_CHANNELS + 1):
            label = self.get_label(channel)
            old = self._last_labels.get(channel)
            if old != label:
                self._last_labels[channel] = label
                changed = True
                if self.on_label_change:
                    self.on_label_change(channel, old or "", label)
        return changed


def create_atem_client(ip: str = config.ATEM_DEFAULT_IP) -> ATEMClient:
    return ATEMClient(ip)


class ATEMService:
    """Maintains ATEM connection with automatic reconnect."""

    def __init__(self, client: ATEMClient) -> None:
        self.client = client
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="atem-service")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        if hasattr(self.client, "disconnect"):
            self.client.disconnect()

    def _run(self) -> None:
        backoff = 1.0
        while not self._stop.is_set():
            try:
                if not self.client.connected:
                    self.client.connect()
                    backoff = 1.0
                self.client.poll()
                time.sleep(0.05)
            except Exception as exc:
                logger.warning("ATEM error: %s", exc)
                if hasattr(self.client, "disconnect"):
                    self.client.disconnect()
                time.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
