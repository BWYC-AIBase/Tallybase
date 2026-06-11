# TallyBase

Raspberry Pi Gateway for ATEM LoRa Tally。

## 1. 系統內容概要

TallyBase 是 ATEM LoRa Tally 系統的樹莓派端 Gateway，負責：

- 連接 ATEM 切換台，讀取 Tally 狀態與攝影機名稱
- 透過 REYAX RYLR998 LoRa 模組廣播狀態給 Tally 燈
- 提供 Web UI 進行裝置配對與 Gateway 設定

Tally 燈韌體位於另一個 `tallylight` repo，不需要部署到樹莓派。

| 目錄 / 檔案 | 說明 |
|-------------|------|
| `gateway/` | Python Gateway 主程式 |
| `gateway/web/` | 配對與設定 Web UI |
| `Dockerfile` | Docker image 建置 |
| `docker-compose.yml` | 容器啟動設定 |
| `data/` | 配對資料與設定持久化目錄 |
| `.env.example` | Web UI port 設定範本 |

## 2. 接線對應（RYLR998）

啟用樹莓派 UART：`raspi-config` → `Interface Options` → `Serial Port` → Login shell over serial：**No**、Serial hardware：**Yes**

| RYLR998 腳位 | Raspberry Pi 4 實體腳位 | 說明 |
|---|---|---|
| VDD | Pin 1（3.3V） | 模組工作電壓 3.3V，勿接 5V |
| GND | Pin 9（GND） | 與 TXD/RXD 同排，接線最短；Pin 6 若已被風扇佔用可改接任一 GND 腳（Pin 14 / 20 / 25 / 30 / 34 / 39） |
| RXD | Pin 8（GPIO14 / TXD） | Pi 的 TX → 模組的 RX |
| TXD | Pin 10（GPIO15 / RXD） | 模組的 TX → Pi 的 RX |
| RST | 不需接線 | 內部已有 100kΩ 上拉，保持高電位 |

Gateway 預設使用 `/dev/serial0`、115200 baud rate。

## 3. 安裝方式

在樹莓派上進入 repo 目錄後執行：

```bash
cd ~/tallybase
sudo docker compose build
sudo docker compose up -d
```

若要修改 Web UI port，複製 `.env.example` 為 `.env` 後再啟動：

```bash
cp .env.example .env
```

```env
FLASK_PORT=5000
```

查看 log：

```bash
sudo docker compose logs -f
```

停止服務：

```bash
sudo docker compose down
```

## 4. Web UI 開啟方式

瀏覽器開啟：

```
http://<pi-ip>:5000
```

若已修改 `.env` 中的 `FLASK_PORT`，請改用對應 port。

在 Web UI 的「Gateway 設定」中設定 ATEM IP，並完成 Tally 燈配對。
