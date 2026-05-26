# Parcer

Bu repo `eTender` IT tender monitoru da daxil olmaqla müxtəlif scraping və export alətlərini saxlayır.

## eTender IT monitor

Skript: `parcer/etender_it_telegram_monitor.py`

### Lokal run

```powershell
C:/Users/user/AppData/Local/Programs/Python/Python312/python.exe -m pip install -r requirements.txt
C:/Users/user/AppData/Local/Programs/Python/Python312/python.exe parcer/etender_it_telegram_monitor.py --once --dry-run --pages 1
```

### Telegram secrets

GitHub Actions üçün repository secrets əlavə et:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Ətraflı addımlar: [GITHUB_SECRETS.md](GITHUB_SECRETS.md)

### GitHub Actions

Workflow faylı: `.github/workflows/etender-it-monitor.yml`

- Hər 30 dəqiqədən bir işə düşür
- `parcer/.etender_it_state.json` faylını yeniləyir
- Köhnə tenderləri yenidən göndərməmək üçün state saxlayır

### Qısa qeyd

Repo GitHub-a push olunandan sonra monitor avtomatik işləyir. Kompın açıq qalmasına ehtiyac yoxdur.