"""LoRa packet encode/decode for ATEM Tally system v3."""

from __future__ import annotations

from .constants import (
    IDENTIFY_CMD_START,
    IDENTIFY_CMD_STOP,
    IDENTIFY_PACKET_LEN,
    MAC_BROADCAST_PACKET_LEN,
    MAGIC,
    MAX_CHANNELS,
    MAX_LABEL_BYTES,
    PKT_IDENTIFY,
    PKT_MAC_BROADCAST,
    PKT_PAIR_NAME,
    PKT_TALLY_STATUS,
    TALLY_OFF,
    TALLY_PGM,
    TALLY_PVW,
    TALLY_STATUS_PACKET_LEN,
)


class ProtocolError(ValueError):
    pass


def normalize_mac(mac: str) -> str:
    parts = mac.strip().upper().split(":")
    if len(parts) != 6:
        raise ProtocolError(f"Invalid MAC address: {mac}")
    return ":".join(f"{int(part, 16):02X}" for part in parts)


def mac_to_bytes(mac: str) -> bytes:
    return bytes(int(part, 16) for part in normalize_mac(mac).split(":"))


def mac_to_str(mac_bytes: bytes) -> str:
    if len(mac_bytes) != 6:
        raise ProtocolError("MAC must be 6 bytes")
    return ":".join(f"{b:02X}" for b in mac_bytes)


def mac_match_id(mac: bytes) -> bytes:
    """Last 4 bytes used in identify/pair packets (indices 2..5)."""
    if len(mac) != 6:
        raise ProtocolError("MAC must be 6 bytes")
    return mac[2:6]


def mac_match_id_from_str(mac: str) -> bytes:
    return mac_match_id(mac_to_bytes(mac))


def encode_tally_status(seq: int, states: list[int]) -> bytes:
    if len(states) != MAX_CHANNELS:
        raise ProtocolError(f"Expected {MAX_CHANNELS} channel states")
    packet = bytearray([MAGIC, PKT_TALLY_STATUS, seq & 0xFF, 0x00])
    for group in range(8):
        value = 0
        for offset in range(4):
            channel = group * 4 + offset
            state = states[channel] & 0x03
            value |= state << (offset * 2)
        packet.append(value)
    if len(packet) != TALLY_STATUS_PACKET_LEN:
        raise ProtocolError("Tally status packet length mismatch")
    return bytes(packet)


def decode_tally_status(data: bytes) -> tuple[int, list[int]]:
    if len(data) != TALLY_STATUS_PACKET_LEN:
        raise ProtocolError("Invalid tally status packet length")
    if data[0] != MAGIC or data[1] != PKT_TALLY_STATUS:
        raise ProtocolError("Invalid tally status packet header")
    seq = data[2]
    states: list[int] = []
    for group in range(8):
        value = data[4 + group]
        for offset in range(4):
            states.append((value >> (offset * 2)) & 0x03)
    return seq, states


def get_channel_state(states: list[int], tally_id: int) -> int:
    if not 1 <= tally_id <= MAX_CHANNELS:
        raise ProtocolError("TALLY_ID out of range")
    return states[tally_id - 1]


def encode_identify(mac: str, start: bool = True) -> bytes:
    """Deprecated: firmware no longer handles identify packets."""
    match_id = mac_match_id_from_str(mac)
    cmd = IDENTIFY_CMD_START if start else IDENTIFY_CMD_STOP
    packet = bytes([MAGIC, PKT_IDENTIFY]) + match_id + bytes([cmd, 0x00])
    if len(packet) != IDENTIFY_PACKET_LEN:
        raise ProtocolError("Identify packet length mismatch")
    return packet


def decode_identify(data: bytes) -> tuple[bytes, int]:
    if len(data) != IDENTIFY_PACKET_LEN:
        raise ProtocolError("Invalid identify packet length")
    if data[0] != MAGIC or data[1] != PKT_IDENTIFY:
        raise ProtocolError("Invalid identify packet header")
    return data[2:6], data[6]


def encode_mac_broadcast(mac: str) -> bytes:
    mac_bytes = mac_to_bytes(mac)
    packet = bytes([MAGIC, PKT_MAC_BROADCAST]) + mac_bytes
    if len(packet) != MAC_BROADCAST_PACKET_LEN:
        raise ProtocolError("MAC broadcast packet length mismatch")
    return packet


def decode_mac_broadcast(data: bytes) -> str:
    if len(data) != MAC_BROADCAST_PACKET_LEN:
        raise ProtocolError("Invalid MAC broadcast packet length")
    if data[0] != MAGIC or data[1] != PKT_MAC_BROADCAST:
        raise ProtocolError("Invalid MAC broadcast packet header")
    return mac_to_str(data[2:8])


def encode_pair_name(mac: str, tally_id: int, label: str) -> bytes:
    if not 1 <= tally_id <= MAX_CHANNELS:
        raise ProtocolError("TALLY_ID out of range")
    match_id = mac_match_id_from_str(mac)
    label_bytes = label.encode("utf-8")[:MAX_LABEL_BYTES]
    return bytes([MAGIC, PKT_PAIR_NAME]) + match_id + bytes([tally_id, len(label_bytes)]) + label_bytes


def decode_pair_name(data: bytes) -> tuple[bytes, int, str]:
    if len(data) < 8:
        raise ProtocolError("Pair/name packet too short")
    if data[0] != MAGIC or data[1] != PKT_PAIR_NAME:
        raise ProtocolError("Invalid pair/name packet header")
    match_id = data[2:6]
    tally_id = data[6]
    label_len = data[7]
    if len(data) < 8 + label_len:
        raise ProtocolError("Pair/name label truncated")
    label = data[8 : 8 + label_len].decode("utf-8", errors="replace")
    return match_id, tally_id, label


def parse_packet(data: bytes) -> tuple[int, dict]:
    if len(data) < 2 or data[0] != MAGIC:
        raise ProtocolError("Unknown packet")
    packet_type = data[1]
    if packet_type == PKT_TALLY_STATUS:
        seq, states = decode_tally_status(data)
        return packet_type, {"seq": seq, "states": states}
    if packet_type == PKT_IDENTIFY:
        match_id, cmd = decode_identify(data)
        return packet_type, {"match_id": match_id, "cmd": cmd}
    if packet_type == PKT_MAC_BROADCAST:
        return packet_type, {"mac": decode_mac_broadcast(data)}
    if packet_type == PKT_PAIR_NAME:
        match_id, tally_id, label = decode_pair_name(data)
        return packet_type, {"match_id": match_id, "tally_id": tally_id, "label": label}
    raise ProtocolError(f"Unsupported packet type: 0x{packet_type:02X}")


def tally_state_name(state: int) -> str:
    if state == TALLY_PGM:
        return "PGM"
    if state == TALLY_PVW:
        return "PVW"
    return "OFF"
