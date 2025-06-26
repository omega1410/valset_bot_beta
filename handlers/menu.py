
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from db.database import is_user_allowed

def register_menu_handlers(app: Client):
    @app.on_message(filters.text & filters.private)
    async def show_menu(client: Client, message: Message):
        if not is_user_allowed(message.from_user.id):
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 разделы", callback_data="sections")],
            [InlineKeyboardButton("🧪 пройти тест", callback_data="test")],
            [InlineKeyboardButton("📅 график смен", callback_data="schedule")],
            [InlineKeyboardButton("🔍 поиск", callback_data="search")]
        ])

        await message.reply("выбери нужный раздел:", reply_markup=keyboard)
