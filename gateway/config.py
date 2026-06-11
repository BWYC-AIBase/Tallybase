"""Gateway configuration."""
import os

# ATEM switcher
ATEM_DEFAULT_IP = os.environ.get("ATEM_DEFAULT_IP", "")
ATEM_PORT = 9910
MIX_EFFECT = 0

# REYAX RYLR998 UART LoRa module
# Wiring: RYLR998 TXD -> Pi RXD, RYLR998 RXD -> Pi TXD, plus 3.3V/GND.
RYLR_SERIAL_PORT = os.environ.get("RYLR_SERIAL_PORT", "/dev/serial0")
RYLR_BAUDRATE = int(os.environ.get("RYLR_BAUDRATE", "115200"))
RYLR_ADDRESS = int(os.environ.get("RYLR_ADDRESS", "1"))
RYLR_TARGET_ADDRESS = int(os.environ.get("RYLR_TARGET_ADDRESS", "0"))  # 0 = broadcast
RYLR_NETWORK_ID = int(os.environ.get("RYLR_NETWORK_ID", "18"))
RYLR_BAND_HZ = int(os.environ.get("RYLR_BAND_HZ", "920000000"))
RYLR_SPREADING_FACTOR = int(os.environ.get("RYLR_SPREADING_FACTOR", "9"))
RYLR_BANDWIDTH_CODE = int(os.environ.get("RYLR_BANDWIDTH_CODE", "7"))  # 7=125kHz, 8=250kHz, 9=500kHz
RYLR_CODING_RATE = int(os.environ.get("RYLR_CODING_RATE", "1"))  # 1 = 4/5
RYLR_PREAMBLE_LENGTH = int(os.environ.get("RYLR_PREAMBLE_LENGTH", "8"))
RYLR_RF_POWER_DBM = int(os.environ.get("RYLR_RF_POWER_DBM", "14"))

# Timing
TALLY_BROADCAST_INTERVAL_S = 0.5
MAC_BROADCAST_INTERVAL_S = 2.0
SIGNAL_TIMEOUT_S = 10.0

# Web server
FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.environ.get("FLASK_PORT", "5000"))

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("TALLY_DATA_DIR", BASE_DIR)
PAIRED_DEVICES_FILE = os.path.join(DATA_DIR, "paired_devices.json")
GATEWAY_SETTINGS_FILE = os.path.join(DATA_DIR, "gateway_settings.json")

