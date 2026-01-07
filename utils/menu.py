from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu():
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📚  Разделы", callback_data="sections_1")],
            [InlineKeyboardButton("📋  Чек-листы", callback_data="open_checklists")],
            [InlineKeyboardButton("📔  Логбук (бета)", callback_data="open_logbook")],
            # Две кнопки AI в одном ряду
            [
                InlineKeyboardButton("🤖 AI по БД", callback_data="start_ai"),
                InlineKeyboardButton("🧠 Общий AI", callback_data="free_ai_menu"),
            ],
            [InlineKeyboardButton("📆 График смен", callback_data="show_schedule")],
            [InlineKeyboardButton("🔍  Поиск", callback_data="start_search")],
        ]
    )
    text = "Используй кнопки ниже для навигации."
    return text, keyboard
