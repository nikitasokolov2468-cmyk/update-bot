import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
import gspread

from config import BOT_TOKEN, ADMIN_ID, PHONE_NUMBER, SPREADSHEET_NAME

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Подключение к Google Таблицам через credentials.json
try:
    gc = gspread.service_account(filename="credentials.json")
    sheet = gc.open(SPREADSHEET_NAME).sheet1
except Exception as e:
    logging.error(f"Ошибка подключения к Google Таблицам: {e}")
    sheet = None


# Описываем шаги состояний (FSM)
class Registration(StatesGroup):
    full_name = State()
    city = State()
    vibe = State()
    payment_screenshot = State()


# 1. Команда /start (Главное меню с кнопками)
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Зарегистрироваться", callback_data="start_reg")
    builder.button(text="ℹ️ О нас", callback_data="about_us")
    builder.adjust(1)

    await message.answer(
        "Привет! Добро пожаловать в официальный бот конференции **Update**.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )


# Обработка кнопки "О нас"
@dp.callback_query(F.data == "about_us")
async def about_us_callback(callback: types.CallbackQuery):
    about_text = (
        "🚀 **Update** — конференция для специалистов ИТ!\n\n"
        "Здесь встречаются разработчики, инженеры и архитекторы, чтобы обсудить "
        "передовые технологии, поделиться опытом и найти единомышленников."
    )
    await callback.message.answer(about_text, parse_mode="Markdown")
    await callback.answer()


# Обработка нажатия "Зарегистрироваться"
@dp.callback_query(F.data == "start_reg")
async def start_reg_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Отлично! Как тебя зовут? (Введите ФИО полностью):")
    await state.set_state(Registration.full_name)
    await callback.answer()


# 2. Получение ФИО
@dp.message(Registration.full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Из какого ты города?")
    await state.set_state(Registration.city)


# 3. Получение города
@dp.message(Registration.city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Опиши свой «вайб» или с каким настроем идёшь на конференцию?")
    await state.set_state(Registration.vibe)


# 4. Получение вайба и запрос оплаты
@dp.message(Registration.vibe)
async def process_vibe(message: types.Message, state: FSMContext):
    await state.update_data(vibe=message.text)

    payment_text = (
        "Почти готово! Осталось оплатить оргвзнос **100 рублей**.\n\n"
        f"Перевод можно сделать по номеру телефона: `{PHONE_NUMBER}` (Сбербанк / Т-Банк).\n\n"
        "После оплаты отправь в этот чат **скриншот чека**."
    )
    await message.answer(payment_text, parse_mode="Markdown")
    await state.set_state(Registration.payment_screenshot)


# 5. Получение скриншота чека, сохранение в таблицу и уведомление админа с кнопками
@dp.message(Registration.payment_screenshot, F.photo)
async def process_payment_screenshot(message: types.Message, state: FSMContext):
    user_data = await state.get_data()

    full_name = user_data.get("full_name")
    city = user_data.get("city")
    vibe = user_data.get("vibe")
    username = f"@{message.from_user.username}" if message.from_user.username else "нет username"
    user_id = message.from_user.id

    photo_file_id = message.photo[-1].file_id

    # Сохраняем данные в Google Таблицу (без file_id)
    if sheet:
        try:
            sheet.append_row([
                str(user_id),
                username,
                full_name,
                city,
                vibe,
                "Оплачено (ожидает проверки)"
            ])
        except Exception as e:
            logging.error(f"Ошибка записи в таблицу: {e}")

    # Благодарим участника
    await message.answer(
        "Спасибо! Твоя заявка и чек отправлены на проверку администратору.\n"
        "Скоро мы с тобой свяжемся!"
    )

    # Текст уведомления для администратора
    admin_notification = (
        "⚡ Новая заявка на конференцию Update!\n\n"
        f"От: {full_name} ({username})\n"
        f"ID: {user_id}\n"
        f"Город: {city}\n"
        f"Вайб: {vibe}"
    )

    # Создаем инлайн-кнопки для админа
    admin_kb = InlineKeyboardBuilder()
    admin_kb.button(text="✅ Подтвердить", callback_data=f"confirm_{user_id}")
    admin_kb.button(text="❌ Отклонить", callback_data=f"reject_{user_id}")
    admin_kb.adjust(2)

    try:
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_file_id,
            caption=admin_notification,
            reply_markup=admin_kb.as_markup()
        )
    except Exception as e:
        logging.error(f"НЕ УДАЛОСЬ ОТПРАВИТЬ АДМИНУ: {e}")

    await state.clear()


# Защита от отправки текста вместо скриншота
@dp.message(Registration.payment_screenshot)
async def not_a_photo(message: types.Message):
    await message.answer("Пожалуйста, отправь именно **скриншот (фотографию)** чека об оплате.")


# Обработка нажатий кнопок администратором (Подтвердить / Отклонить)
@dp.callback_query(F.data.startswith("confirm_") | F.data.startswith("reject_"))
async def process_admin_decision(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет прав для этого действия.", show_alert=True)
        return

    action, user_id_str = callback.data.split("_")
    target_user_id = int(user_id_str)

    status_text = "Подтверждено ✅" if action == "confirm" else "Отклонено ❌"

    # Обновляем статус в Google Таблице (ищем среди всех строк с этим ID)
    if sheet:
        try:
            cells = sheet.findall(str(target_user_id))
            target_cell = None

            for cell in cells:
                current_status = sheet.cell(cell.row, 6).value
                if current_status and "ожидает проверки" in current_status:
                    target_cell = cell
                    break

            if not target_cell and cells:
                target_cell = cells[-1]

            if target_cell:
                sheet.update_cell(target_cell.row, 6, status_text)
                logging.info(f"Статус в таблице успешно обновлен для строки {target_cell.row}")
            else:
                logging.error(f"НЕ НАЙДЕНА строка с user_id {target_user_id} в таблице!")
        except Exception as e:
            logging.error(f"Ошибка обновления статуса в таблице: {e}")

    # Уведомляем пользователя о результате
    try:
        if action == "confirm":
            await bot.send_message(
                chat_id=target_user_id,
                text="🎉 Поздравляем! Ваша оплата подтверждена. Ждем вас на конференции **Update**!",
                parse_mode="Markdown"
            )
        else:
            await bot.send_message(
                chat_id=target_user_id,
                text="❌ К сожалению, ваша оплата/заявка была отклонена. Обратитесь к администратору для уточнения деталей."
            )
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление пользователю: {e}")

    # Обновляем подпись к фото у администратора
    new_caption = callback.message.caption + f"\n\n**Решение:** {status_text}"
    try:
        await callback.message.edit_caption(
            caption=new_caption,
            reply_markup=None  # Убираем кнопки после выбора
        )
    except Exception:
        pass

    await callback.answer(f"Статус изменен: {status_text}")


# Точка входа
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())