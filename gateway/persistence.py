"""Persist paired device mapping."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import config

logger = logging.getLogger(__name__)


def _ensure_parent_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def load_paired_devices() -> dict[str, dict[str, Any]]:
    path = config.PAIRED_DEVICES_FILE
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Failed to load paired devices: %s", exc)
    return {}


def save_paired_devices(devices: dict[str, dict[str, Any]]) -> None:
    path = config.PAIRED_DEVICES_FILE
    _ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(devices, handle, indent=2, ensure_ascii=False)


def load_gateway_settings() -> dict[str, Any]:
    path = config.GATEWAY_SETTINGS_FILE
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Failed to load gateway settings: %s", exc)
    return {}


def save_gateway_settings(settings: dict[str, Any]) -> None:
    path = config.GATEWAY_SETTINGS_FILE
    _ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(settings, handle, indent=2, ensure_ascii=False)
