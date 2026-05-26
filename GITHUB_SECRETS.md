# GitHub Secrets

`eTender` monitoru GitHub Actions-da işlətmək üçün repository secrets əlavə et:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID` (və ya `TELEGRAM_CHAT_IDS` — vergüllə ayrılmış chat id-lər)

## Addımlar

1. GitHub repo səhifəsinə gir.
2. `Settings` aç.
3. `Secrets and variables` → `Actions` seç.
4. `New repository secret` bas.
5. Ad və dəyəri daxil et:
   - Name: `TELEGRAM_BOT_TOKEN`
   - Value: Telegram bot token
6. Eyni qayda ilə `TELEGRAM_CHAT_ID` əlavə et. Əgər bir neçə chat-a göndərmək istəyirsənsə, `TELEGRAM_CHAT_IDS` adlı secret yaradıb dəyərləri vergül ilə ayır.
7. Workflow-u `Actions` bölməsində `Run workflow` ilə test et.

## Qeyd

Bu dəyərləri repoya düz yazmaq olmaz; yalnız GitHub Secrets kimi saxlanmalıdır.