from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu():
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📚  Разделы", callback_data="sections_1")],
            [InlineKeyboardButton("📋  Чек-листы", callback_data="open_checklists")],
            [InlineKeyboardButton("🔍  Поиск", callback_data="start_search")],
            [InlineKeyboardButton("📆 График смен", callback_data="show_schedule")],
        ]
    )
    text = "Используй кнопки ниже для навигации."
    return text, keyboard
