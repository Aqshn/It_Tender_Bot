# GitHub Secrets

`eTender` monitoru GitHub Actions-da işlətmək üçün repository secrets əlavə et:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Addımlar

1. GitHub repo səhifəsinə gir.
2. `Settings` aç.
3. `Secrets and variables` → `Actions` seç.
4. `New repository secret` bas.
5. Ad və dəyəri daxil et:
   - Name: `TELEGRAM_BOT_TOKEN`
   - Value: Telegram bot token
6. Eyni qayda ilə `TELEGRAM_CHAT_ID` əlavə et.
7. Workflow-u `Actions` bölməsində `Run workflow` ilə test et.

## Qeyd

Bu dəyərləri repoya düz yazmaq olmaz; yalnız GitHub Secrets kimi saxlanmalıdır.