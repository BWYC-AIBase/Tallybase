"""Shared gateway runtime state."""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional


class GatewayState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.unpaired_devices: set[str] = set()
        self.paired_devices: dict[str, dict[str, Any]] = {}
        self.atem_connected = False
        self.last_broadcast_seq = 0
        self.on_tally_change: Optional[Callable[[], None]] = None
        self.on_label_change: Optional[Callable[[int, str, str], None]] = None

    def add_unpaired(self, mac: str) -> None:
        with self._lock:
            if mac not in self.paired_devices:
                self.unpaired_devices.add(mac)

    def remove_unpaired(self, mac: str) -> None:
        with self._lock:
            self.unpaired_devices.discard(mac)

    def get_unpaired(self) -> list[str]:
        with self._lock:
            return sorted(self.unpaired_devices)

    def get_paired(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return dict(self.paired_devices)

    def set_paired_devices(self, devices: dict[str, dict[str, Any]]) -> None:
        with self._lock:
            self.paired_devices = devices
            self.unpaired_devices -= set(devices.keys())

    def pair_device(self, mac: str, info: dict[str, Any]) -> None:
        with self._lock:
            tally_id = info["tally_id"]
            for existing_mac, existing in list(self.paired_devices.items()):
                if existing_mac != mac and existing.get("tally_id") == tally_id:
                    del self.paired_devices[existing_mac]
            self.paired_devices[mac] = info
            self.unpaired_devices.discard(mac)

    def find_mac_by_tally_id(self, tally_id: int) -> Optional[str]:
        with self._lock:
            for mac, info in self.paired_devices.items():
                if info.get("tally_id") == tally_id:
                    return mac
        return None
