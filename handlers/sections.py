from pyrogram import Client, filters
from pyrogram.types import Message
import sqlite3
import logging
from config import ADMIN_IDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pending_titles = {}
pending_contents = {}

# === состояния для редактирования ===
pending_edit_section = {}
pending_edit_title = {}


def validate_input(text: str, max_length: int = 1000) -> bool:
    if not text.strip():
        return False
    if len(text) > max_length:
        return False
    return True


def register_section_handlers(app: Client):
    # === /add_section ===
    @app.on_message(filters.command("add_section") & filters.private, group=1)
    async def start_add_section(client: Client, message: Message):
        user_id = message.from_user.id
        if user_id not in ADMIN_IDS:
            await message.reply("⛔️ Нет доступа")
            return
        pending_titles[user_id] = True
        await message.reply("✅ Введи заголовок раздела:")

    @app.on_message(filters.text & filters.private, group=1)
    async def handle_add_section(client: Client, message: Message):
        user_id = message.from_user.id
        if user_id not in ADMIN_IDS:
            return

        if user_id in pending_titles and pending_titles[user_id] is True:
            title = message.text.strip()
            if not validate_input(title, 200):
                await message.reply("❌ Заголовок пустой или слишком длинный")
                return
            pending_titles[user_id] = title
            pending_contents[user_id] = True
            await message.reply("Теперь введи содержание раздела:")
            return

        if user_id in pending_contents and pending_contents[user_id] is True:
            content = message.text.strip()
            if not validate_input(content, 5000):
                await message.reply("❌ Содержание пустое или слишком длинное")
                return

            title = pending_titles.get(user_id)
            if not title:
                await message.reply("Произошла ошибка, начни заново")
                pending_titles.pop(user_id, None)
                pending_contents.pop(user_id, None)
                return

            try:
                conn = sqlite3.connect("data.db")
                c = conn.cursor()
                c.execute(
                    "INSERT INTO sections (title, content) VALUES (?, ?)",
                    (title, content),
                )
                conn.commit()
                logger.info(f"[Добавлен раздел] {title}")
            except sqlite3.Error as e:
                logger.error(f"Ошибка БД: {e}")
                await message.reply("⚠️ Ошибка при сохранении")
                return
            finally:
                conn.close()

            pending_titles.pop(user_id, None)
            pending_contents.pop(user_id, None)
            await message.reply("✅ Раздел сохранён")
            return

    # === /edit_section ===
    @app.on_message(filters.command("edit_section") & filters.private, group=10)
    async def start_edit_section(client: Client, message: Message):
        user_id = message.from_user.id
        if user_id not in ADMIN_IDS:
            await message.reply("⛔️ Нет доступа")
            return

        conn = sqlite3.connect("data.db")
        c = conn.cursor()
        c.execute("SELECT id, title FROM sections")
        sections = c.fetchall()
        conn.close()

        if not sections:
            await message.reply("Разделы не найдены")
            return

        text = "🗂️ Список разделов:\n\n"
        for sec in sections:
            text += f"{sec[0]} — {sec[1]}\n"

        await message.reply(f"{text}\n\nВведи ID раздела для редактирования:")
        pending_edit_section[user_id] = True

    @app.on_message(filters.text & filters.private, group=10)
    async def handle_edit_section(client: Client, message: Message):
        user_id = message.from_user.id
        if user_id not in ADMIN_IDS:
            return

        # шаг 1: выбор ID
        if pending_edit_section.get(user_id) is True:
            try:
                section_id = int(message.text.strip())
                pending_edit_section[user_id] = section_id
                pending_edit_title[user_id] = True
                await message.reply("Введи новый заголовок раздела:")
            except ValueError:
                await message.reply("❌ ID должно быть числом")
            return

        # шаг 2: ввод нового заголовка
        if pending_edit_title.get(user_id) is True:
            title = message.text.strip()
            if not validate_input(title, 200):
                await message.reply("❌ Заголовок пустой или слишком длинный")
                return
            pending_edit_title[user_id] = title
            await message.reply("Теперь введи новое содержание:")
            return

        # шаг 3: ввод нового содержания
        if isinstance(pending_edit_title.get(user_id), str):
            content = message.text.strip()
            if not validate_input(content, 5000):
                await message.reply("❌ Содержание пустое или слишком длинное")
                return

            new_title = pending_edit_title[user_id]
            section_id = pending_edit_section[user_id]

            try:
                conn = sqlite3.connect("data.db")
                c = conn.cursor()
                c.execute(
                    "UPDATE sections SET title=?, content=? WHERE id=?",
                    (new_title, content, section_id)
                )
                conn.commit()
                logger.info(f"[Обновлён раздел] ID: {section_id}")
            except Exception as e:
                logger.error(f"Ошибка БД: {e}")
                await message.reply(f"⚠️ Ошибка при обновлении: {e}")
                return
            finally:
                conn.close()

            pending_edit_section.pop(user_id, None)
            pending_edit_title.pop(user_id, None)
            await message.reply("✅ Раздел обновлён")
