# 🚚 Богдан — Telegram бот курьерской службы

ИИ-диспетчер для курьерской службы Кишинёва. Поддерживает русский, румынский и английский языки.

---

## 🚀 Деплой на Railway (рекомендуется, бесплатно)

### 1. Получи токены

**Telegram Bot Token:**
1. Открой [@BotFather](https://t.me/BotFather) в Telegram
2. Отправь `/newbot`
3. Следуй инструкциям, получи токен вида `7123456789:AAF...`

**Anthropic API Key:**
1. Зайди на [console.anthropic.com](https://console.anthropic.com)
2. API Keys → Create Key
3. Скопируй ключ вида `sk-ant-...`

---

### 2. Деплой на Railway

1. Зайди на [railway.app](https://railway.app) и войди через GitHub
2. Нажми **New Project → Deploy from GitHub repo**
3. Загрузи файлы этого проекта в новый GitHub репозиторий
4. В Railway перейди в **Variables** и добавь:
   ```
   BOT_TOKEN=твой_токен_бота
   ANTHROPIC_API_KEY=твой_ключ_anthropic
   ```
5. Railway автоматически установит зависимости из `requirements.txt` и запустит `bot.py`

---

### 3. Деплой на Render

1. Зайди на [render.com](https://render.com)
2. New → **Web Service** → подключи GitHub репозиторий
3. Настройки:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
4. В Environment Variables добавь `BOT_TOKEN` и `ANTHROPIC_API_KEY`

---

## 💻 Локальный запуск (для тестирования)

```bash
# Установи зависимости
pip install -r requirements.txt

# Создай файл .env
cp .env.example .env
# Отредактируй .env — вставь свои токены

# Запусти
python bot.py
```

---

## 📋 Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Начать диалог, выбрать язык |
| `/reset` | Сбросить историю диалога |

---

## 🌐 Языки

Бот поддерживает переключение языка кнопками:
- 🇷🇺 Русский
- 🇷🇴 Română  
- 🇬🇧 English

История диалога сбрасывается при смене языка.
