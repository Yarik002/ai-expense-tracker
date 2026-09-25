from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

def main_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Расход"), KeyboardButton(text="📸 Чек")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="🏠 Главное меню"), KeyboardButton(text="ℹ️ О боте")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
