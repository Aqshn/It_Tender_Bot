# eTender IT Tender Telegram Monitor

Bu skript `https://etender.gov.az/main/competitions/1/2` səhifəsinin arxasındakı API-dən tenderləri yoxlayır və **IT mövzulu yeni tenderlər** çıxanda Telegram-a link göndərir.

## Fayl

- `parcer/etender_it_telegram_monitor.py`

## Quraşdırma

```powershell
C:/Users/user/AppData/Local/Programs/Python/Python312/python.exe -m pip install -r requirements.txt
```

## Telegram hazırlığı

1. `@BotFather` ilə bot yaradın və token alın.
2. Botu mesaj göndərəcəyiniz chat/qrupa əlavə edin.
3. Chat ID-ni alın (`@userinfobot` və ya Telegram API ilə).

PowerShell-də environment dəyişənlərini təyin edin:

```powershell
$env:TELEGRAM_BOT_TOKEN="your_bot_token"
$env:TELEGRAM_CHAT_ID="your_chat_id"
```

## İşlətmə

### 1) Test (mesaj göndərmədən)

```powershell
C:/Users/user/AppData/Local/Programs/Python/Python312/python.exe parcer/etender_it_telegram_monitor.py --once --dry-run
```

### 2) İlk real işə salınma (spam olmadan)

```powershell
C:/Users/user/AppData/Local/Programs/Python/Python312/python.exe parcer/etender_it_telegram_monitor.py --once
```

Qeyd: ilk run zamanı skript mövcud IT tenderlərini `state` fayla yazır, Telegram-a göndərmir.

### 3) Davamlı monitor (məs: hər 5 dəqiqə)

```powershell
C:/Users/user/AppData/Local/Programs/Python/Python312/python.exe parcer/etender_it_telegram_monitor.py --interval 300
```

## Faydalı parametrlər

- `--pages 3` : neçə səhifə yoxlansın (default `3`)
- `--state-file parcer/.etender_it_state.json` : state fayl yolu
- `--notify-existing` : ilk run-da mövcud tenderləri də göndər
- `--dry-run` : Telegram-a göndərmədən konsola çıxar

## Bildiriş formatı

Hər yeni uyğun tender üçün:

- tender adı
- qurum adı
- publish/end tarixləri
- `competition/detail/<id>` linki
