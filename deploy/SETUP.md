# TallyBase（Raspberry Pi Gateway）部署指南

## Gateway（Raspberry Pi 4）

1. 安裝 Raspberry Pi OS Lite 64-bit Bookworm
2. 啟用 UART：`sudo raspi-config` → Interface Options → Serial Port
   - Login shell over serial：No
   - Serial hardware：Yes
3. 只將 `tallybase/` 複製到 Pi 的 `/home/pi/tallybase`
4. ATEM IP 不需改檔案；Gateway 啟動後在 Web UI 的「Gateway 設定」中輸入並儲存
5. 執行 setup：

```bash
cd /home/pi/tallybase/gateway/scripts
chmod +x setup_pi.sh
./setup_pi.sh
```

setup 會建立 `/home/<目前使用者>/tallybase/.venv`，Python 套件會安裝在這個 virtual environment，不會安裝到系統 Python。

6. 啟動服務：

```bash
sudo systemctl enable tally-gateway
sudo systemctl start tally-gateway
sudo systemctl status tally-gateway
```

7. 開啟配對 UI（見下方「無螢幕：如何開啟配對頁」）

### 無螢幕：如何開啟配對頁

Pi 通常沒有螢幕。Gateway 開機自啟後，在**筆電或手機**（與 Pi 同一 Wi‑Fi / 區網）用瀏覽器開：

**`http://<樹莓派區網 IP>:5000`**

例如：`http://192.168.1.50:5000`

**不要用筆電上的 `localhost`**——`localhost` 只代表你正在用的那台電腦，不是 Pi。

| 做法 | 說明 |
|------|------|
| **路由器固定 IP（建議）** | 在分享器 DHCP 保留中，依 Pi 的 MAC 綁定固定 IP（如 `192.168.1.50`），之後永遠用這個網址 |
| **Imager 寫卡** | Raspberry Pi Imager → 進階：啟用 SSH、設 hostname（如 `tally-gw`）、可選靜態 IP |
| **路由器管理頁** | 已連線裝置列表中找 `raspberrypi` 或你的 hostname |
| **mDNS** | 可試 `http://raspberrypi.local:5000`（視網路環境而定） |
| **SSH** | `ssh pi@raspberrypi.local` → `hostname -I` 看第一組 IP |

Gateway 已監聽 `0.0.0.0:5000`（見 `config.py`），區網內任一裝置皆可連線配對。

### ATEM IP 設定

ATEM IP 由配對網頁設定，不需要 SSH 進 Pi 修改 `gateway/config.py`。

1. 開啟 `http://<樹莓派區網 IP>:5000`
2. 在「Gateway 設定」輸入 ATEM IP（例如 `192.168.1.240`）
3. 按「儲存 ATEM IP」
4. Gateway 會保存到 `gateway/gateway_settings.json`，並自動重新連線 ATEM

### REYAX RYLR998 接線與設定

Pi Gateway 使用 **REYAX RYLR998 UART LoRa 模組**，不是 SPI LoRa HAT。

| RYLR998 | Raspberry Pi |
|---------|--------------|
| VCC | 3.3V |
| GND | GND |
| TXD | RXD / GPIO15 / Pin 10 |
| RXD | TXD / GPIO14 / Pin 8 |

預設序列埠：`/dev/serial0`，baud rate：`115200`。可在 [`gateway/config.py`](../gateway/config.py) 調整：

| 設定 | 預設 | 說明 |
|------|------|------|
| `RYLR_SERIAL_PORT` | `/dev/serial0` | RYLR998 UART 裝置 |
| `RYLR_ADDRESS` | `1` | Pi Gateway 的 REYAX address |
| `RYLR_TARGET_ADDRESS` | `0` | 0 = broadcast 給所有 Tally |
| `RYLR_NETWORK_ID` | `18` | REYAX network ID |
| `RYLR_BAND_HZ` | `920000000` | 台灣 920 MHz |
| `RYLR_SPREADING_FACTOR` | `9` | 需與 Tally 韌體一致 |
| `RYLR_BANDWIDTH_CODE` | `7` | 7 = 125 kHz |
| `RYLR_CODING_RATE` | `1` | 1 = 4/5 |
| `RYLR_PREAMBLE_LENGTH` | `8` | 需與 Tally 韌體一致 |

Gateway 會用 `AT+SEND` 傳送十六進位 ASCII payload；Tally 韌體會自動剝除 REYAX header 並還原原本二進位協定封包。

## 現場部署 Checklist

- [ ] Pi 與 ATEM 同一網段，有線連接
- [ ] 已知 Pi 固定 IP 或 hostname，可開 `http://<pi-ip>:5000`
- [ ] RYLR998 天線已接好，垂直放置
- [ ] 工作頻率 920 MHz，發射功率 +14 dBm
- [ ] 所有 Tally 燈已配對並顯示正確 cam label
- [ ] ATEM 切換 PGM/PVW 延遲 < 500 ms
- [ ] 無 tally 封包時維持黑底 + label（非黃屏）

