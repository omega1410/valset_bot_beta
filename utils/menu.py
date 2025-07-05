from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu():
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📚  Разделы", callback_data="sections_1")],
            [InlineKeyboardButton("📋  Чек-листы", callback_data="open_checklists")],
        ]
    )
    text = "Используй кнопки ниже для навигации."
    return text, keyboard
