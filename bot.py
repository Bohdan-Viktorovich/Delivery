import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# Загружаем переменные окружения из Railway Variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_STR = os.getenv("ADMIN_ID")
REDIS_URL = os.getenv("REDIS_URL")  # Railway добавит эту переменную автоматически

if not BOT_TOKEN or not ADMIN_ID_STR:
    raise ValueError("❌ BOT_TOKEN или ADMIN_ID не заданы в переменных окружения!")

ADMIN_ID = int(ADMIN_ID_STR)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера (с использованием DefaultBotProperties)
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode='HTML')
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# --- Состояния диалога (должны быть объявлены до хэндлеров) ---
class OrderForm(StatesGroup):
    waiting_for_cargo = State()
    waiting_for_confirm = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_comment = State()

# --- Многоязычные тексты ---
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
        'cargo_prompt': "📦 Пожалуйста, опишите груз подробнее: вес, габариты, хрупкость, количество мест.",
        'confirm_cargo': "📋 Ваш заказ:\n<b>Тип:</b> {cargo_type}\n<b>Описание:</b> {cargo_details}\n\n<b>Стоимость доставки:</b> {delivery_price}\n\nВсё верно?",
        'price_free': "Бесплатно (при заказе от 500 MDL)",
        'price_fixed': "50 MDL (базовый тариф)",
        'enter_name': "👤 Введите ваше имя:",
        'enter_phone': "📞 Введите ваш номер телефона:",
        'enter_address': "📍 Введите адрес доставки (улица, дом, подъезд, квартира):",
        'enter_comment': "💬 Оставьте комментарий к заказу (или нажмите 'Пропустить'):",
        'skip': "⏭ Пропустить",
        'order_sent': "✅ Ваш заказ №{order_id} отправлен! Мы свяжемся с вами в ближайшее время для подтверждения.",
        'error': "⚠️ Произошла ошибка. Пожалуйста, попробуйте позже или начните заново с команды /start.",
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
        'cargo_prompt': "📦 Vă rugăm să descrieți coletul mai detaliat: greutate, dimensiuni, fragilitate, numărul de locuri.",
        'confirm_cargo': "📋 Comanda dvs.:\n<b>Tip:</b> {cargo_type}\n<b>Descriere:</b> {cargo_details}\n\n<b>Cost livrare:</b> {delivery_price}\n\nEste corect?",
        'price_free': "Gratuit (pentru comenzi peste 500 MDL)",
        'price_fixed': "50 MDL (tarif de bază)",
        'enter_name': "👤 Introduceți numele dvs.:",
        'enter_phone': "📞 Introduceți numărul de telefon:",
        'enter_address': "📍 Introduceți adresa de livrare (stradă, număr, scară, apartament):",
        'enter_comment': "💬 Lăsați un comentariu la comandă (sau apăsați 'Săriți'):",
        'skip': "⏭ Săriți",
        'order_sent': "✅ Comanda dvs. nr. {order_id} a fost trimisă! Vă vom contacta în scurt timp pentru confirmare.",
        'error': "⚠️ A apărut o eroare. Vă rugăm să încercați din nou sau să începeți din nou cu comanda /start.",
        'cancel_text': "🚫 Acțiune anulată. Pentru a începe din nou, apăsați /start.",
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
        'cargo_prompt': "📦 Please describe the cargo in more detail: weight, dimensions, fragility, number of pieces.",
        'confirm_cargo': "📋 Your order:\n<b>Type:</b> {cargo_type}\n<b>Description:</b> {cargo_details}\n\n<b>Delivery cost:</b> {delivery_price}\n\nIs everything correct?",
        'price_free': "Free (for orders over 500 MDL)",
        'price_fixed': "50 MDL (base rate)",
        'enter_name': "👤 Enter your name:",
        'enter_phone': "📞 Enter your phone number:",
        'enter_address': "📍 Enter the delivery address (street, building, entrance, apartment):",
        'enter_comment': "💬 Leave a comment for the order (or press 'Skip'):",
        'skip': "⏭ Skip",
        'order_sent': "✅ Your order #{order_id} has been sent! We will contact you shortly for confirmation.",
        'error': "⚠️ An error occurred. Please try again later or start over with /start.",
        'cancel_text': "🚫 Action canceled. To start over, press /start.",
        'cargo_types': ["📄 Documents", "🍕 Food", "📦 Large parcels", "🌸 Flowers"]
    }
}

# Хранилище языка пользователя
user_lang = {}

# --- Клавиатуры ---
def get_lang_keyboard():
    buttons = [
        [KeyboardButton(text="🇷🇺 Русский")],
        [KeyboardButton(text="🇷🇴 Română")],
        [KeyboardButton(text="🇬🇧 English")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

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
    buttons = [
        [KeyboardButton(text=t['confirm']), KeyboardButton(text=t['cancel'])]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

def get_skip_keyboard(lang):
    t = LANGUAGES[lang]
    buttons = [
        [KeyboardButton(text=t['skip']), KeyboardButton(text=t['cancel'])]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

# --- Обработчики ---
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
    
    await state.update_data(cargo_type=message.text)
    await message.answer(t['cargo_prompt'], reply_markup=types.ReplyKeyboardRemove())
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
    
    delivery_price = t['price_fixed']
    
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
    elif message.text != t['confirm']:
        await message.answer(t['confirm_cargo'], reply_markup=get_confirm_keyboard(lang))
        return
    
    await message.answer(t['enter_name'], reply_markup=types.ReplyKeyboardRemove())
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
    
    admin_text = (
        f"🆕 <b>Новый заказ {order_id}</b>\n\n"
        f"👤 <b>Клиент:</b> {data.get('customer_name')}\n"
        f"📞 <b>Телефон:</b> {data.get('customer_phone')}\n"
        f"📍 <b>Адрес:</b> {data.get('delivery_address')}\n"
        f"📦 <b>Тип груза:</b> {data.get('cargo_type')}\n"
        f"📝 <b>Детали груза:</b> {data.get('cargo_details')}\n"
        f"💬 <b>Комментарий:</b> {data.get('comment')}\n"
        f"🌐 <b>Язык:</b> {lang}"
    )
    await bot.send_message(ADMIN_ID, admin_text)
    
    await message.answer(t['order_sent'].format(order_id=order_id), reply_markup=get_lang_keyboard())
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
