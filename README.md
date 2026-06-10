# TallyBase

Raspberry Pi Gateway。這個資料夾是唯一需要放到樹莓派的內容。

## 安裝到 Pi

從開發機複製：

```powershell
scp -r .\tallybase pi@<pi-ip>:/home/pi/tallybase
```

在 Pi 上執行：

```bash
cd /home/pi/tallybase/gateway/scripts
chmod +x setup_pi.sh
./setup_pi.sh
sudo systemctl enable tally-gateway
sudo systemctl start tally-gateway
```

`setup_pi.sh` 會自動建立 `.venv`，避免 Raspberry Pi OS Bookworm 的 `externally-managed-environment` pip 限制。

配對 UI：`http://<pi-ip>:5000`

ATEM IP 在 Web UI 的「Gateway 設定」中設定。

詳細步驟見 [`deploy/SETUP.md`](deploy/SETUP.md)。
