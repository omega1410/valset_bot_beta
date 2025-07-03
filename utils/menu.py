from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu():
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📚  Разделы", callback_data="sections_1")],
            [InlineKeyboardButton("🧪  Пройти тест", callback_data="start_test_1")],
            [InlineKeyboardButton("📅  График смен", callback_data="show_schedule")],
        ]
    )
    text = "Используй кнопки ниже для навигации."
    return text, keyboard
