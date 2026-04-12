import asyncio
import logging
import os
import sys
import re
import aiohttp
from urllib.parse import quote

from aiogram import Bot, Dispatcher, types, BaseMiddleware
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_STR = os.getenv("ADMIN_ID")
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")

if not BOT_TOKEN or not ADMIN_ID_STR:
    raise ValueError("❌ BOT_TOKEN или ADMIN_ID не заданы!")
if not GEOAPIFY_API_KEY:
    raise ValueError("❌ GEOAPIFY_API_KEY не задан!")

ADMIN_ID = int(ADMIN_ID_STR)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding='utf-8')
    ]
)

# Инициализация бота и диспетчера с MemoryStorage
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# --- Middleware напоминания (однократное) ---
reminded_users = set()
user_lang = {}   # временное хранилище языка пользователя

class StateReminderMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        state: FSMContext = data.get('state')
        user_id = event.from_user.id

        if state and user_id not in reminded_users:
            current_state = await state.get_state()
            if current_state is not None:
                lang = user_lang.get(user_id, 'ru')
                t = LANGUAGES[lang]

                reminder_map = {
                    OrderForm.waiting_for_cargo.state: (t['lang_set'], get_cargo_keyboard(lang)),
                    OrderForm.waiting_for_weight.state: (t['ask_weight'], ReplyKeyboardRemove()),
                    OrderForm.waiting_for_dimensions.state: (t['ask_dimensions'], ReplyKeyboardRemove()),
                    OrderForm.waiting_for_pickup.state: (t['ask_pickup'], ReplyKeyboardRemove()),
                    OrderForm.waiting_for_confirm.state: (t['cargo_prompt'], ReplyKeyboardRemove()),
                    OrderForm.waiting_for_name.state: (t['confirm_cargo'], get_confirm_keyboard(lang)),
                    OrderForm.waiting_for_phone.state: (t['enter_name'], ReplyKeyboardRemove()),
                    OrderForm.waiting_for_address.state: (t['enter_phone'], ReplyKeyboardRemove()),
                    OrderForm.waiting_for_comment.state: (t['enter_address'], ReplyKeyboardRemove()),
                    "final": (t['enter_comment'], get_skip_keyboard(lang)),
                }

                if current_state in reminder_map:
                    reminder_text, reply_markup = reminder_map[current_state]
                    if not (event.text and event.text.startswith('/start')):
                        await event.answer(
                            f"🔔 Бот был перезапущен. Продолжим:\n\n{reminder_text}",
                            reply_markup=reply_markup
                        )
                        reminded_users.add(user_id)

        return await handler(event, data)

dp.message.middleware(StateReminderMiddleware())

# --- Состояния ---
class OrderForm(StatesGroup):
    waiting_for_cargo = State()
    waiting_for_weight = State()
    waiting_for_dimensions = State()
    waiting_for_pickup = State()
    waiting_for_confirm = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_comment = State()

# --- Многоязычные тексты (без изменений, как в предыдущей полной версии) ---
LANGUAGES = {
    'ru': {
        'select_lang': "🇷🇺 Выберите язык / Select language:",
        'lang_set': "✅ Язык установлен: Русский. Выберите, что нужно доставить:",
        'docs': "📄 Документы",
        'food': "🍕 Еда",
        'large': "📦 Крупногабарит",
        'flowers': "🌸 Цветы",
        'back': "🔙 Назад",
        'confirm': "✅ Подтвердить",
        'cancel': "❌ Отмена",
        'ask_weight': "⚖️ Укажите примерный вес груза в килограммах (например, 2.5):",
        'ask_dimensions': "📐 Укажите габариты груза в сантиметрах (Длина x Ширина x Высота), например: 30x20x10:",
        'invalid_weight': "⚠️ Пожалуйста, введите число (можно дробное через точку).",
        'invalid_dimensions': "⚠️ Пожалуйста, введите габариты в формате ДxШxВ, например: 30x20x10.",
        'ask_pickup': "📍 Укажите пожалуйста адрес, откуда забрать доставку (улица, дом):",
        'cargo_prompt': "📦 Пожалуйста, опишите груз подробнее: хрупкость, особенности, количество мест.",
        'confirm_cargo': "📋 Ваш заказ:\n<b>Тип:</b> {cargo_type}\n<b>Описание:</b> {cargo_details}\n\n<b>Примерная стоимость доставки:</b> {delivery_price}\n\nВсё верно?",
        'price_free': "Бесплатно (при заказе от 500 MDL)",
        'price_fixed': "50 MDL (базовый тариф)",
        'enter_name': "👤 Введите ваше имя:",
        'enter_phone': "📞 Введите ваш номер телефона:",
        'enter_address': "📍 Введите адрес доставки (улица, дом, подъезд, квартира):",
        'enter_comment': "💬 Оставьте комментарий к заказу (или нажмите 'Пропустить'):",
        'skip': "⏭ Пропустить",
        'order_sent': "✅ Ваш заказ №{order_id} отправлен!",
        'error': "⚠️ Произошла ошибка. Попробуйте позже или начните заново: /start",
        'cancel_text': "🚫 Действие отменено. Чтобы начать заново, нажмите /start.",
        'cargo_types': ["📄 Документы", "🍕 Еда", "📦 Крупногабарит", "🌸 Цветы"]
    },
    'ro': {
        'select_lang': "🇷🇴 Selectați limba / Выберите язык:",
        'lang_set': "✅ Limba setată: Română. Selectați ce trebuie livrat:",
        'docs': "📄 Documente",
        'food': "🍕 Mâncare",
        'large': "📦 Obiecte voluminoase",
        'flowers': "🌸 Flori",
        'back': "🔙 Înapoi",
        'confirm': "✅ Confirmă",
        'cancel': "❌ Anulare",
        'ask_weight': "⚖️ Indicați greutatea aproximativă în kg (ex: 2.5):",
        'ask_dimensions': "📐 Indicați dimensiunile în cm (Lungime x Lățime x Înălțime), ex: 30x20x10:",
        'invalid_weight': "⚠️ Introduceți un număr valid (zecimal cu punct).",
        'invalid_dimensions': "⚠️ Introduceți dimensiunile în format LxLxÎ, ex: 30x20x10.",
        'ask_pickup': "📍 Vă rugăm să furnizați adresa de unde doriți să ridicați livrarea. (stradă, număr):",
        'cargo_prompt': "📦 Descrieți coletul: fragilitate, particularități, număr de locuri.",
        'confirm_cargo': "📋 Comanda dvs.:\n<b>Tip:</b> {cargo_type}\n<b>Descriere:</b> {cargo_details}\n\n<b>Cost livrare estimat:</b> {delivery_price}\n\nEste corect?",
        'price_free': "Gratuit (pentru comenzi peste 500 MDL)",
        'price_fixed': "50 MDL (tarif de bază)",
        'enter_name': "👤 Introduceți numele dvs.:",
        'enter_phone': "📞 Introduceți numărul de telefon:",
        'enter_address': "📍 Introduceți adresa de livrare (stradă, număr, scară, apartament):",
        'enter_comment': "💬 Lăsați un comentariu (sau apăsați 'Săriți'):",
        'skip': "⏭ Săriți",
        'order_sent': "✅ Comanda nr. {order_id} a fost trimisă!",
        'error': "⚠️ A apărut o eroare. Încercați din nou sau începeți cu /start.",
        'cancel_text': "🚫 Acțiune anulată. Începeți din nou: /start.",
        'cargo_types': ["📄 Documente", "🍕 Mâncare", "📦 Obiecte voluminoase", "🌸 Flori"]
    },
    'en': {
        'select_lang': "🇬🇧 Select language / Выберите язык:",
        'lang_set': "✅ Language set: English. Select what needs to be delivered:",
        'docs': "📄 Documents",
        'food': "🍕 Food",
        'large': "📦 Large parcels",
        'flowers': "🌸 Flowers",
        'back': "🔙 Back",
        'confirm': "✅ Confirm",
        'cancel': "❌ Cancel",
        'ask_weight': "⚖️ Enter approximate weight in kg (e.g., 2.5):",
        'ask_dimensions': "📐 Enter dimensions in cm (Length x Width x Height), e.g.: 30x20x10:",
        'invalid_weight': "⚠️ Please enter a valid number (decimal point allowed).",
        'invalid_dimensions': "⚠️ Please enter dimensions in LxWxH format, e.g.: 30x20x10.",
        'ask_pickup': "📍 Please provide the address where you would like to pick up the delivery. (street, building):",
        'cargo_prompt': "📦 Describe the cargo: fragility, special notes, number of pieces.",
        'confirm_cargo': "📋 Your order:\n<b>Type:</b> {cargo_type}\n<b>Description:</b> {cargo_details}\n\n<b>Estimated delivery cost:</b> {delivery_price}\n\nIs everything correct?",
        'price_free': "Free (for orders over 500 MDL)",
        'price_fixed': "50 MDL (base rate)",
        'enter_name': "👤 Enter your name:",
        'enter_phone': "📞 Enter your phone number:",
        'enter_address': "📍 Enter delivery address (street, building, entrance, apartment):",
        'enter_comment': "💬 Leave a comment (or press 'Skip'):",
        'skip': "⏭ Skip",
        'order_sent': "✅ Your order #{order_id} has been sent!",
        'error': "⚠️ An error occurred. Please try again or start over: /start.",
        'cancel_text': "🚫 Action canceled. To start over, press /start.",
        'cargo_types': ["📄 Documents", "🍕 Food", "📦 Large parcels", "🌸 Flowers"]
    }
}

# --- Клавиатуры ---
def get_lang_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🇷🇺 Русский")],
                  [KeyboardButton(text="🇷🇴 Română")],
                  [KeyboardButton(text="🇬🇧 English")]],
        resize_keyboard=True, one_time_keyboard=True
    )

def get_cargo_keyboard(lang):
    t = LANGUAGES[lang]
    buttons = [
        [KeyboardButton(text=t['docs']), KeyboardButton(text=t['food'])],
        [KeyboardButton(text=t['large']), KeyboardButton(text=t['flowers'])],
        [KeyboardButton(text=t['cancel'])]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

def get_confirm_keyboard(lang):
    t = LANGUAGES[lang]
    buttons = [[KeyboardButton(text=t['confirm']), KeyboardButton(text=t['cancel'])]]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

def get_skip_keyboard(lang):
    t = LANGUAGES[lang]
    buttons = [[KeyboardButton(text=t['skip']), KeyboardButton(text=t['cancel'])]]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

# --- Функция расчёта расстояния через Geoapify ---
async def get_distance_km(origin: str, destination: str) -> float:
    if not GEOAPIFY_API_KEY:
        return 0.0
    base_url = "https://api.geoapify.com/v1/routing"
    params = {
        "waypoints": f"{quote(origin)}|{quote(destination)}",
        "mode": "drive",
        "apiKey": GEOAPIFY_API_KEY
    }
    url = f"{base_url}?waypoints={params['waypoints']}&mode={params['mode']}&apiKey={params['apiKey']}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return 0.0
                data = await resp.json()
                distance_m = data["features"][0]["properties"]["distance"]
                return distance_m / 1000.0
    except Exception as e:
        logging.error(f"Geoapify error: {e}")
        return 0.0

# --- Обработчики команд и сообщений ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(LANGUAGES['ru']['select_lang'], reply_markup=get_lang_keyboard())

@dp.message(lambda message: message.text in ["🇷🇺 Русский", "🇷🇴 Română", "🇬🇧 English"])
async def process_lang_selection(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if message.text == "🇷🇺 Русский":
        user_lang[user_id] = 'ru'
    elif message.text == "🇷🇴 Română":
        user_lang[user_id] = 'ro'
    else:
        user_lang[user_id] = 'en'
    lang = user_lang[user_id]
    t = LANGUAGES[lang]
    await message.answer(t['lang_set'], reply_markup=get_cargo_keyboard(lang))
    await state.set_state(OrderForm.waiting_for_cargo)

@dp.message(OrderForm.waiting_for_cargo)
async def process_cargo_selection(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_lang.get(user_id, 'ru')
    t = LANGUAGES[lang]
    if message.text == t['cancel']:
        await state.clear()
        await message.answer(t['cancel_text'], reply_markup=get_lang_keyboard())
        return
    if message.text not in t['cargo_types']:
        await message.answer(t['lang_set'], reply_markup=get_cargo_keyboard(lang))
        return
    cargo_type = message.text
    await state.update_data(cargo_type=cargo_type)
    if cargo_type in [t['food'], t['flowers'], t['docs']]:
        await state.update_data(weight=1.0, volume=0.01)
        await message.answer(t['ask_pickup'], reply_markup=ReplyKeyboardRemove())
        await state.set_state(OrderForm.waiting_for_pickup)
    else:
        await message.answer(t['ask_weight'], reply_markup=ReplyKeyboardRemove())
        await state.set_state(OrderForm.waiting_for_weight)

@dp.message(OrderForm.waiting_for_weight)
async def process_weight(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_lang.get(user_id, 'ru')
    t = LANGUAGES[lang]
    if message.text == t['cancel']:
        await state.clear()
        await message.answer(t['cancel_text'], reply_markup=get_lang_keyboard())
        return
    try:
        weight = float(message.text.replace(',', '.'))
        if weight <= 0:
            raise ValueError
    except ValueError:
        await message.answer(t['invalid_weight'])
        return
    await state.update_data(weight=weight)
    await message.answer(t['ask_dimensions'], reply_markup=ReplyKeyboardRemove())
    await state.set_state(OrderForm.waiting_for_dimensions)

@dp.message(OrderForm.waiting_for_dimensions)
async def process_dimensions(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_lang.get(user_id, 'ru')
    t = LANGUAGES[lang]
    if message.text == t['cancel']:
        await state.clear()
        await message.answer(t['cancel_text'], reply_markup=get_lang_keyboard())
        return
    pattern = r'^(\d+)\s*[xх×*XХ]\s*(\d+)\s*[xх×*XХ]\s*(\d+)$'
    match = re.match(pattern, message.text.strip(), re.IGNORECASE)
    if not match:
        await message.answer(t['invalid_dimensions'])
        return
    length, width, height = map(int, match.groups())
    volume = (length * width * height) / 1_000_000
    await state.update_data(dimensions=f"{length}x{width}x{height}", volume=volume)
    await message.answer(t['ask_pickup'], reply_markup=ReplyKeyboardRemove())
    await state.set_state(OrderForm.waiting_for_pickup)

@dp.message(OrderForm.waiting_for_pickup)
async def process_pickup(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_lang.get(user_id, 'ru')
    t = LANGUAGES[lang]
    if message.text == t['cancel']:
        await state.clear()
        await message.answer(t['cancel_text'], reply_markup=get_lang_keyboard())
        return
    await state.update_data(pickup_address=message.text)
    await message.answer(t['cargo_prompt'], reply_markup=ReplyKeyboardRemove())
    await state.set_state(OrderForm.waiting_for_confirm)

@dp.message(OrderForm.waiting_for_confirm)
async def process_cargo_details(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_lang.get(user_id, 'ru')
    t = LANGUAGES[lang]
    if message.text == t['cancel']:
        await state.clear()
        await message.answer(t['cancel_text'], reply_markup=get_lang_keyboard())
        return
    cargo_details = message.text
    await state.update_data(cargo_details=cargo_details)
    data = await state.get_data()
    cargo_type = data.get('cargo_type')
    weight = data.get('weight', 0)
    volume = data.get('volume', 0)
    # Временная цена (без расстояния)
    base_price = 50.0
    weight_surcharge = max(0, (weight - 5) * 5)
    volume_surcharge = max(0, (volume - 0.1) * 20)
    total_price = base_price + weight_surcharge + volume_surcharge
    delivery_price = f"{total_price:.2f} MDL"
    confirm_text = t['confirm_cargo'].format(
        cargo_type=cargo_type,
        cargo_details=cargo_details,
        delivery_price=delivery_price
    )
    await message.answer(confirm_text, reply_markup=get_confirm_keyboard(lang))
    await state.set_state(OrderForm.waiting_for_name)

@dp.message(OrderForm.waiting_for_name)
async def process_cargo_confirmation(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_lang.get(user_id, 'ru')
    t = LANGUAGES[lang]
    if message.text == t['cancel']:
        await state.clear()
        await message.answer(t['cancel_text'], reply_markup=get_lang_keyboard())
        return
    if message.text != t['confirm']:
        await message.answer(t['confirm_cargo'], reply_markup=get_confirm_keyboard(lang))
        return
    await message.answer(t['enter_name'], reply_markup=ReplyKeyboardRemove())
    await state.set_state(OrderForm.waiting_for_phone)

@dp.message(OrderForm.waiting_for_phone)
async def process_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_lang.get(user_id, 'ru')
    t = LANGUAGES[lang]
    if message.text == t['cancel']:
        await state.clear()
        await message.answer(t['cancel_text'], reply_markup=get_lang_keyboard())
        return
    await state.update_data(customer_name=message.text)
    await message.answer(t['enter_phone'])
    await state.set_state(OrderForm.waiting_for_address)

@dp.message(OrderForm.waiting_for_address)
async def process_phone(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_lang.get(user_id, 'ru')
    t = LANGUAGES[lang]
    if message.text == t['cancel']:
        await state.clear()
        await message.answer(t['cancel_text'], reply_markup=get_lang_keyboard())
        return
    await state.update_data(customer_phone=message.text)
    await message.answer(t['enter_address'])
    await state.set_state(OrderForm.waiting_for_comment)

@dp.message(OrderForm.waiting_for_comment)
async def process_address(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_lang.get(user_id, 'ru')
    t = LANGUAGES[lang]
    if message.text == t['cancel']:
        await state.clear()
        await message.answer(t['cancel_text'], reply_markup=get_lang_keyboard())
        return
    await state.update_data(delivery_address=message.text)
    await message.answer(t['enter_comment'], reply_markup=get_skip_keyboard(lang))
    await state.set_state("final")

@dp.message(lambda message: message.text in ["⏭ Пропустить", "⏭ Săriți", "⏭ Skip"])
async def skip_comment(message: types.Message, state: FSMContext):
    await state.update_data(comment="-")
    await finalize_order(message, state)

@dp.message(lambda message: True)
async def process_comment(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_lang.get(user_id, 'ru')
    t = LANGUAGES[lang]
    if message.text == t['cancel']:
        await state.clear()
        await message.answer(t['cancel_text'], reply_markup=get_lang_keyboard())
        return
    await state.update_data(comment=message.text)
    await finalize_order(message, state)

async def finalize_order(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_lang.get(user_id, 'ru')
    t = LANGUAGES[lang]
    data = await state.get_data()
    order_id = f"#{user_id}{int(asyncio.get_event_loop().time())}"
    pickup = data.get('pickup_address', 'Не указан')
    delivery = data.get('delivery_address', 'Не указан')
    distance = 0.0
    if pickup and delivery:
        distance = await get_distance_km(pickup, delivery)
    weight = data.get('weight', 0)
    volume = data.get('volume', 0)
    base_price = 50.0
    weight_surcharge = max(0, (weight - 5) * 5)
    volume_surcharge = max(0, (volume - 0.1) * 20)
    distance_surcharge = max(0, distance - 5) * 5 if distance > 5 else 0
    total_price = base_price + weight_surcharge + volume_surcharge + distance_surcharge
    delivery_price = f"{total_price:.2f} MDL"
    admin_text = (
        f"🆕 <b>Новый заказ {order_id}</b>\n\n"
        f"👤 <b>Клиент:</b> {data.get('customer_name')}\n"
        f"📞 <b>Телефон:</b> {data.get('customer_phone')}\n"
        f"📍 <b>Адрес забора:</b> {pickup}\n"
        f"📍 <b>Адрес доставки:</b> {delivery}\n"
        f"📏 <b>Расстояние:</b> {round(distance, 2)} км\n"
        f"📦 <b>Тип груза:</b> {data.get('cargo_type')}\n"
        f"⚖️ <b>Вес:</b> {weight} кг\n"
        f"📐 <b>Габариты:</b> {data.get('dimensions', '-')} см\n"
        f"📝 <b>Детали:</b> {data.get('cargo_details')}\n"
        f"💬 <b>Комментарий:</b> {data.get('comment')}\n"
        f"💰 <b>Итоговая цена:</b> {delivery_price}\n"
        f"🌐 <b>Язык:</b> {lang}"
    )
    await bot.send_message(ADMIN_ID, admin_text)
    client_msg = t['order_sent'].format(order_id=order_id) + f"\n💰 Стоимость доставки: {delivery_price}"
    await message.answer(client_msg, reply_markup=get_lang_keyboard())
    await state.clear()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Webhook deleted, pending updates dropped")
    logging.info("Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
