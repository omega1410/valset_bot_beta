from pyrogram import Client, filters
from pyrogram.types import Message
from whitelist import add_user_to_whitelist, is_user_allowed
from utils.menu import get_main_menu

ADMIN_IDS = [5669245603]


def register_access_handlers(app: Client):
    @app.on_message(filters.command("start"))
    async def start(client: Client, message: Message):
        user_id = message.from_user.id
        if not is_user_allowed(user_id):
            await message.reply(
                "Доступ к боту ограничен.\nОбратитесь к администратору."
            )
            return

        name = message.from_user.first_name
        text, keyboard = get_main_menu()
        await message.reply(f"Привет, {name}!\n\n{text}", reply_markup=keyboard)

    @app.on_message(filters.command("add") & filters.user(ADMIN_IDS))
    async def add(client: Client, message: Message):
        # пример парсинга аргумента: /add 123456789
        try:
            user_id_to_add = int(message.text.split()[1])
        except (IndexError, ValueError):
            await message.reply("Укажи id пользователя: /add <id>")
            return

        added = add_user_to_whitelist(user_id_to_add)
        if added:
            await message.reply(
                f"Пользователь {user_id_to_add} добавлен в белый список."
            )
        else:
            await message.reply("Ошибка при добавлении или пользователь уже в списке.")
