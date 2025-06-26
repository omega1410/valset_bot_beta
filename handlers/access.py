from pyrogram import Client, filters
from pyrogram.types import Message
from db.database import is_user_allowed, add_user

# замени на свой ID
ADMIN_ID = 5669245603

def register_access_handlers(app: Client):
    @app.on_message(filters.command("start"))
    async def start(client: Client, message: Message):
        user_id = message.from_user.id
        name = message.from_user.first_name

        if not is_user_allowed(user_id):
            await message.reply("доступ к боту ограничен.\nобратитесь к администратору.")
            return

        await message.reply(f"привет, {name}!\nиспользуй кнопки ниже для навигации.")

    @app.on_message(filters.command("add") & filters.user(ADMIN_ID))
    async def add(client: Client, message: Message):
        try:
            _, uid = message.text.split()
            uid = int(uid)
            add_user(uid, "неизвестно")
            await message.reply(f"пользователь {uid} добавлен в белый список")
        except Exception:
            await message.reply("используй: /add <user_id>")
