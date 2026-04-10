# Telegram Delivery Bot for Chisinau

Бот для приёма заказов на доставку по Кишинёву. Поддерживает русский, румынский и английский языки.

## Развёртывание на Railway

1. Загрузите репозиторий на GitHub.
2. Подключите Railway к этому репозиторию.
3. В разделе **Variables** добавьте:
   - `BOT_TOKEN` = ваш токен от BotFather
   - `ADMIN_ID` = ваш Telegram ID (число)
4. Railway автоматически определит `runtime.txt` и `nixpacks.toml`.

Бот запустится и будет работать 24/7.
