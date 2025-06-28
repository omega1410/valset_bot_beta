from pyrogram import Client, filters
from pyrogram.types import Message
import sqlite3

from db.database import is_user_allowed

ADMIN_IDS = [5669245603]  # замени на актуальные ID

# временное хранилище для стадий ввода
pending_titles = {}
pending_contents = {}

def register_section_handlers(app: Client):
    @app.on_message(filters.command("add_section") & filters.user(ADMIN_IDS))
    async def add_section(client: Client, message: Message):
        await message.reply("Введи заголовок нового раздела:")
        pending_titles[message.from_user.id] = True

    @app.on_message(filters.text & filters.private)
    async def handle_section_input(client: Client, message: Message):
        user_id = message.from_user.id

        # этап 1: ожидаем заголовок
        if user_id in pending_titles and pending_titles[user_id] is True:
            pending_titles[user_id] = message.text
            await message.reply("Теперь введи содержание раздела:")
            return

        # этап 2: ожидаем текст
        if user_id in pending_titles and user_id not in pending_contents:
            title = pending_titles[user_id]
            content = message.text

            # сохраняем в базу
            conn = sqlite3.connect("data.db")
            c = conn.cursor()
            c.execute("INSERT INTO sections (title, content) VALUES (?, ?)", (title, content))
            conn.commit()
            conn.close()

            # очистка
            del pending_titles[user_id]
            await message.reply("Раздел успешно сохранён ✅")
