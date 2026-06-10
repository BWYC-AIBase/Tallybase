# TallyBase

Raspberry Pi Gateway for ATEM LoRa Tally。

這個 repo 只包含樹莓派端程式：ATEM 連線、REYAX RYLR998 LoRa Gateway、Flask Web UI、systemd 自動安裝腳本。Tally 燈韌體請放在另一個 `tallylight` repo，不需要複製到樹莓派。

## 內容

- `gateway/`：Python Gateway 主程式
- `gateway/web/`：配對與設定 Web UI
- `gateway/scripts/setup_pi.sh`：Pi 安裝腳本

## 安裝到 Pi

### 方式 A：從 GitHub clone 到 Pi

```bash
cd ~
git clone <你的 tallybase repo URL> tallybase
cd ~/tallybase/gateway/scripts
chmod +x setup_pi.sh
./setup_pi.sh
```

### 方式 B：從開發機用 scp 複製

在這個 repo 根目錄執行：

```powershell
scp -r .\* <pi-user>@<pi-ip>:/home/<pi-user>/tallybase/
```

範例：

```powershell
scp -r .\* tallybase@192.168.1.50:/home/tallybase/tallybase/
```

然後在 Pi 上執行：

```bash
cd ~/tallybase/gateway/scripts
chmod +x setup_pi.sh
./setup_pi.sh
sudo systemctl enable tally-gateway
sudo systemctl restart tally-gateway
```

`setup_pi.sh` 會自動建立 `.venv`，避免 Raspberry Pi OS Bookworm 的 `externally-managed-environment` pip 限制。

## Web UI

配對 UI：`http://<pi-ip>:5000`

ATEM IP 在 Web UI 的「Gateway 設定」中設定。

## RYLR998

預設使用 `/dev/serial0`、`115200` baud rate。

Pi 上請先啟用 UART：

```bash
sudo raspi-config
```

選 `Interface Options` → `Serial Port`：

- Login shell over serial：No
- Serial hardware：Yes

接線：

| RYLR998 | Raspberry Pi |
|---------|--------------|
| VCC | 3.3V |
| GND | GND |
| TXD | RXD / GPIO15 / Pin 10 |
| RXD | TXD / GPIO14 / Pin 8 |

## Runtime 檔案

以下檔案會在 Pi 上自動產生，不要提交到 GitHub：

- `gateway/paired_devices.json`
- `gateway/gateway_settings.json`
- `gateway/__pycache__/`
