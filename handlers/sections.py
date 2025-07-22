from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto
import sqlite3
import logging
from config import ADMIN_IDS
from utils.whitelist import is_admin
from pyrogram.enums import ParseMode

admin_filter = filters.create(lambda _, __, m: is_admin(m.from_user.id))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pending_titles = {}
pending_contents = {}
pending_edit_section = {}
pending_edit_title = {}

MAX_SLOT = 7
MSG_LIMIT = 4096
CAPTION_LIMIT = 1024


def split_text(text: str, size: int = MSG_LIMIT):
    return [text[i : i + size] for i in range(0, len(text), size)]


def validate_input(text: str, max_length: int = 1000) -> bool:
    if not text.strip():
        return False
    if len(text) > max_length:
        return False
    return True


def register_section_handlers(app: Client):
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
            if not validate_input(content, 8000):
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

        if pending_edit_section.get(user_id) is True:
            try:
                section_id = int(message.text.strip())
                pending_edit_section[user_id] = section_id
                pending_edit_title[user_id] = True
                await message.reply("Введи новый заголовок раздела:")
            except ValueError:
                await message.reply("❌ ID должно быть числом")
            return

        if pending_edit_title.get(user_id) is True:
            title = message.text.strip()
            if not validate_input(title, 200):
                await message.reply("❌ Заголовок пустой или слишком длинный")
                return
            pending_edit_title[user_id] = title
            await message.reply("Теперь введи новое содержание:")
            return

        if isinstance(pending_edit_title.get(user_id), str):
            content = message.text.strip()
            if not validate_input(content, 8000):
                await message.reply("❌ Содержание пустое или слишком длинное")
                return

            new_title = pending_edit_title[user_id]
            section_id = pending_edit_section[user_id]

            try:
                conn = sqlite3.connect("data.db")
                c = conn.cursor()
                c.execute(
                    "UPDATE sections SET title=?, content=? WHERE id=?",
                    (new_title, content, section_id),
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

    @app.on_message(filters.command("set_photo") & admin_filter, group=0)
    async def cmd_set_photo(client, message):
        try:
            section_id = int(message.command[1])
            slot = int(message.command[2]) if len(message.command) > 2 else 1
            if not (1 <= slot <= MAX_SLOT):
                raise ValueError
        except (IndexError, ValueError):
            await message.reply(
                "ℹ️ Использование:\n"
                "1) пришлите фото\n"
                "2) ответом: /set_photo <ID_раздела> [<1-7>]"
            )
            return

        column = "photo_id" if slot == 1 else f"photo_id{slot}"

        photo = (
            message.reply_to_message.photo
            if message.reply_to_message and message.reply_to_message.photo
            else message.photo
        )
        if not photo:
            await message.reply(
                "❗️Команда должна быть в ответ на фото " "или в подписи к фото."
            )
            return

        file_id = photo.file_id
        column = "photo_id" if slot == 1 else f"photo_id{slot}"

        with sqlite3.connect("data.db") as conn:
            conn.execute(
                f"UPDATE sections SET {column}=? WHERE id=?", (file_id, section_id)
            )
        await message.reply(f"✅ Фото сохранено в слот {slot} для раздела {section_id}")

    @app.on_message(filters.command("remove_photo") & admin_filter, group=0)
    async def cmd_remove_photo(client, message):
        try:
            section_id = int(message.command[1])
            slot = int(message.command[2]) if len(message.command) > 2 else 1
            if not (1 <= slot <= MAX_SLOT):
                raise ValueError
        except (IndexError, ValueError):
            await message.reply("ℹ️ Использование: /remove_photo <ID_раздела> [<1-7>]")
            return
        column = "photo_id" if slot == 1 else f"photo_id{slot}"
        with sqlite3.connect("data.db") as conn:
            cur = conn.execute(
                f"UPDATE sections SET {column}=NULL WHERE id=?", (section_id,)
            )
            ok = cur.rowcount
        await message.reply("✅ Фото удалено" if ok else "⚠️ Раздел не найден")

    @app.on_message(filters.command("view_section") & filters.private, group=5)
    async def view_section(client: Client, message: Message):
        args = message.command

        if len(args) == 1:
            with sqlite3.connect("data.db") as conn:
                rows = conn.execute("SELECT id, title FROM sections").fetchall()

            if not rows:
                await message.reply("⚠️ Разделов пока нет.")
                return

            text = "🗂️ Доступные разделы:\n\n" + "\n".join(
                f"{row[0]} — {row[1]}" for row in rows
            )
            await message.reply(text)
            return

        try:
            section_id = int(args[1])
        except ValueError:
            await message.reply("❌ ID должно быть числом")
            return

        with sqlite3.connect("data.db") as conn:
            row = conn.execute(
                """
                SELECT title, content,
                       COALESCE(photo_id,  ''), COALESCE(photo_id2, ''), COALESCE(photo_id3, ''),
                       COALESCE(photo_id4, ''), COALESCE(photo_id5, ''), COALESCE(photo_id6, ''),
                       COALESCE(photo_id7, '')
                FROM sections
                WHERE id = ?
                """,
                (section_id,),
            ).fetchone()

        if row is None:
            await message.reply("⚠️ Раздел не найден.")
            return

        title, content, *photos = row
        photos = [p for p in photos if p]

        chat_id = message.chat.id

        if photos:
            caption = f"<b>{title}</b>"
            media = [
                InputMediaPhoto(photos[0], caption=caption, parse_mode=ParseMode.HTML)
            ]
            media += [InputMediaPhoto(p) for p in photos[1:]]
            await client.send_media_group(chat_id, media)

            if content.strip():
                for chunk in split_text(content):
                    await client.send_message(chat_id, chunk, parse_mode=ParseMode.HTML)
            return

        full_text = f"<b>{title}</b>\n\n{content}"
        if len(full_text) <= MSG_LIMIT:
            await message.reply(full_text, parse_mode=ParseMode.HTML)
        else:
            parts = split_text(full_text)
            await message.reply(parts[0], parse_mode=ParseMode.HTML)
            for part in parts[1:]:
                await client.send_message(chat_id, part, parse_mode=ParseMode.HTML)
