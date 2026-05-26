VPS Deployment for eTender monitor
=================================

Quick steps to run the monitor on an Ubuntu VPS (20.04+):

1. Push repo to the VPS or rsync from your machine. Then on VPS:

```bash
# as a regular user
sudo apt update && sudo apt install -y python3-venv python3-pip rsync
cd ~
git clone https://github.com/Aqshn/It_Tender_Bot.git etender-monitor
cd etender-monitor
./parcer/deploy_vps.sh
```

2. Edit `/opt/etender-monitor/.env` and add:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_IDS=1601481679,8248109069
```

3. Start/enable timer (if not already enabled):

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now etender-monitor.timer
sudo systemctl status etender-monitor.timer
```

Logs:
- Service logs: `sudo journalctl -u etender-monitor.service -f`
- Timer logs: `sudo journalctl -u etender-monitor.timer -f`

Notes:
- The timer runs the service every 5 minutes. Adjust `parcer/etender_monitor.timer` as needed.
- Service runs the script once per invocation. Modify ExecStart if you prefer continuous loop.
