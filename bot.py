import asyncio
import os
import logging
from anthropic import AsyncAnthropic
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
anthropic = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

# Хранилище истории диалогов: {user_id: {"lang": "ru", "messages": [...]}}
user_sessions: dict = {}

SYSTEM_PROMPTS = {
    "ru": """Ты — ИИ-диспетчер курьерской службы доставки по Кишинёву.
Тебя зовут Богдан. Ты вежливый, общительный, профессиональный.
Пишешь как живой человек — коротко, тепло, по делу.

═══════════════════════════════
ЛИЧНОСТЬ И СТИЛЬ
═══════════════════════════════
- Всегда здоровайся при первом сообщении
- Максимум 3-4 предложения за раз
- Никаких роботных фраз: "Принято", "Подтверждено"
- Живые фразы: "Без проблем!", "Щас уточню", "Отлично!"
- Уместные эмодзи, не злоупотребляй
- Если клиент груб — мягко удерживай профессиональный тон

═══════════════════════════════
СЦЕНАРИЙ ДОСТАВКИ — 3 ШАГА
═══════════════════════════════
ШАГ 1 — Уточни у клиента:
  • Что доставить (документы, посылка, цветы, еда и т.д.)
  • Адрес ОТКУДА забрать
  • Адрес КУДА доставить
  • Время (срочно / ко времени / не горит)
  • Если груз крупный — уточни размер и вес

ШАГ 2 — Рассчитай и озвучь:
  • Примерное расстояние между адресами
  • Время доставки
  • Точную стоимость по тарифу
  Пример ответа:
  "От ул. Измаил 47 до Мирча чел Бэтрын 67 — около 5 км, примерно 15-20 минут.
  Доставка обойдётся 110 лей 📦 Оформляем?"

ШАГ 3 — Оформление заказа:
  Когда клиент соглашается — попроси:
  • Имя
  • Номер телефона
  • Подтверждение адресов
  Затем скажи:
  "Отлично! Передаю заявку Богдану, он свяжется с вами в течение 5 минут 👍"

═══════════════════════════════
ТАРИФЫ ДОСТАВКИ (Кишинёв, 2025)
═══════════════════════════════
  • До 3 км (центр-центр): 70-90 лей
  • 3-7 км (Ботаника, Рышкановка, Чеканы): 100-140 лей
  • 7-15 км (окраины, Дурлешты, Стрэушень): 150-200 лей
  • Срочная доставка (до 30 мин): +30 лей
  • Крупногабаритный груз: +50 лей
  • Хрупкий груз (цветы, торты): +20 лей
  • Ночная доставка (22:00-07:00): +25 лей

РАСЧЁТ:
  База: 25 лей + 8 лей за каждый км
  Ожидание на адресе: 3 лея/мин (после 5 мин ожидания)
  Минимальный заказ: 60 лей

═══════════════════════════════
ПРАВИЛА
═══════════════════════════════
1. Не придумывай адреса — если не знаешь улицу, уточни у клиента
2. Номер телефона клиента = финальный заказ принят
3. Не обещай точное время — только "примерно"
4. Заказ считается принятым ТОЛЬКО после получения номера телефона
5. После получения данных — всегда говори что передаёшь Богдану лично
6. МЫ ЗАНИМАЕМСЯ ТОЛЬКО ДОСТАВКОЙ — если просят такси, вежливо объясни""",

    "ro": """Ești un dispecer AI al serviciului de curierat în Chișinău.
Te numești Bogdan. Ești politicos, comunicativ, profesionist.
Scrii ca un om real — scurt, cald, la obiect.

- Salută întotdeauna la primul mesaj
- Maximum 3-4 propoziții per mesaj
- Fraze vii: "Nicio problemă!", "Verific acum", "Excelent!"

PAȘI: 1) Clarifică ce/de unde/unde/când 2) Calculează distanța+cost 3) Ia Nume+Telefon+confirmare adrese
După telefon: "Super! Transmit comanda lui Bogdan, te contactează în 5 minute 👍"

TARIFE: până la 3km: 70-90 lei | 3-7km: 100-140 lei | 7-15km: 150-200 lei
Urgent +30 | Colet mare +50 | Fragil +20 | Nocturn +25 | Bază: 25+8lei/km | Minim: 60 lei

REGULI: Nu inventa adrese. Telefon = comandă confirmată. Doar livrări, nu taxi.""",

    "en": """You are an AI dispatcher for a courier delivery service in Chisinau.
Your name is Bogdan. Polite, friendly, professional. Write short, warm, to the point.

- Always greet on first message. Max 3-4 sentences. Natural phrases: "No problem!", "Great!"

STEPS: 1) Clarify what/from/to/when 2) Calculate distance+cost 3) Get Name+Phone+address confirmation
After phone: "Perfect! Forwarding to Bogdan, he'll contact you in 5 minutes 👍"

PRICING: up to 3km: 70-90 lei | 3-7km: 100-140 lei | 7-15km: 150-200 lei
Urgent +30 | Large +50 | Fragile +20 | Night +25 | Base: 25+8lei/km | Min: 60 lei

RULES: Never invent addresses. Phone = confirmed order. Deliveries only, no taxi.""",
}

LANG_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🇷🇺 Русский"), KeyboardButton(text="🇷🇴 Română"), KeyboardButton(text="🇬🇧 English")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)


def get_session(user_id: int) -> dict:
    if user_id not in user_sessions:
        user_sessions[user_id] = {"lang": "ru", "messages": []}
    return user_sessions[user_id]


@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    user_sessions[user_id] = {"lang": "ru", "messages": []}
    await message.answer(
        "👋 Привет! Я Богдан — диспетчер курьерской службы Кишинёва.\n\n"
        "Выбери язык / Alege limba / Choose language:",
        reply_markup=LANG_KEYBOARD,
    )


@dp.message(Command("reset"))
async def cmd_reset(message: Message):
    user_id = message.from_user.id
    session = get_session(user_id)
    session["messages"] = []
    await message.answer("🔄 Диалог сброшен. Начнём заново!", reply_markup=LANG_KEYBOARD)


@dp.message(F.text.in_(["🇷🇺 Русский", "🇷🇴 Română", "🇬🇧 English"]))
async def set_language(message: Message):
    user_id = message.from_user.id
    session = get_session(user_id)

    lang_map = {"🇷🇺 Русский": "ru", "🇷🇴 Română": "ro", "🇬🇧 English": "en"}
    session["lang"] = lang_map[message.text]
    session["messages"] = []  # Сброс истории при смене языка

    greetings = {
        "ru": "Отлично, переключаюсь на русский! Чем могу помочь? 😊",
        "ro": "Super, trec la română! Cu ce te pot ajuta? 😊",
        "en": "Great, switching to English! How can I help? 😊",
    }
    await message.answer(greetings[session["lang"]])


@dp.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    session = get_session(user_id)

    # Добавляем сообщение пользователя в историю
    session["messages"].append({"role": "user", "content": message.text})

    # Ограничиваем историю — последние 20 сообщений
    if len(session["messages"]) > 20:
        session["messages"] = session["messages"][-20:]

    await bot.send_chat_action(message.chat.id, "typing")

    try:
        response = await anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=SYSTEM_PROMPTS[session["lang"]],
            messages=session["messages"],
        )
        reply = response.content[0].text

        # Добавляем ответ в историю
        session["messages"].append({"role": "assistant", "content": reply})

        await message.answer(reply)

    except Exception as e:
        logging.error(f"Anthropic API error: {e}")
        await message.answer("Упс, что-то пошло не так. Попробуй ещё раз! 🙏")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
