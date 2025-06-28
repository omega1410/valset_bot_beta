from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu():
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📚  Разделы", callback_data="sections_1")],
            [InlineKeyboardButton("🧪  Пройти тест", callback_data="test")],
            [InlineKeyboardButton("📅  График смен", callback_data="schedule")],
            [InlineKeyboardButton("🔍  Поиск", callback_data="search")],
        ]
    )
    text = "Используй кнопки ниже для навигации."
    return text, keyboard
