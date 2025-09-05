from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InputMediaPhoto,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
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

# Хранилище для отслеживания текущей позиции в карусели
carousel_state = {}  # {user_id: {section_id: current_photo_index}}


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

        # Показываем раздел с кнопкой для карусели вместо всех фото сразу
        await show_section_with_carousel_option(client, message, section_id)

    async def show_section_with_carousel_option(
        client: Client, message: Message, section_id: int
    ):
        """Показать раздел с опцией перехода в карусель"""
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
        photos = [p for p in photos if p]  # Убираем пустые значения

        # Создаем клавиатуру с кнопкой для карусели, если есть фото
        keyboard = []

        if photos:
            # Добавляем кнопку для перехода в режим карусели
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"🖼️ Просмотр фото ({len(photos)} шт.)",
                        callback_data=f"start_carousel_{section_id}",
                    )
                ]
            )

        # Кнопка "Назад" в список разделов
        keyboard.append(
            [
                InlineKeyboardButton(
                    "🔙 Назад к разделам", callback_data="back_to_sections"
                )
            ]
        )

        # Показываем только текст раздела
        full_text = f"<b>{title}</b>"
        if content.strip():
            full_text += f"\n\n{content}"

        if len(full_text) <= MSG_LIMIT:
            await message.reply(
                full_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            # Если текст слишком длинный, показываем краткое описание
            preview_text = f"<b>{title}</b>\n\n"
            content_preview = content[:500] + "..." if len(content) > 500 else content
            preview_text += content_preview
            if photos:
                preview_text += f"\n\n📷 Фото доступно: {len(photos)} шт."
            await message.reply(
                preview_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

    @app.on_callback_query(filters.regex(r"^start_carousel_(\d+)$"), group=15)
    async def start_carousel(client: Client, callback_query: CallbackQuery):
        """Начать просмотр фото в режиме карусели"""
        section_id = int(callback_query.matches[0].group(1))
        await show_carousel_photo(client, callback_query.message, section_id, 0)
        await callback_query.answer()

    @app.on_callback_query(filters.regex(r"^back_to_sections$"))
    async def back_to_sections(client: Client, callback_query: CallbackQuery):
        with sqlite3.connect("data.db") as conn:
            rows = conn.execute("SELECT id, title FROM sections").fetchall()

        if not rows:
            await callback_query.message.edit_text("⚠️ Разделов пока нет.")
            return

        text = "🗂️ Доступные разделы:\n\n" + "\n".join(
            f"{row[0]} — {row[1]}" for row in rows
        )
        await callback_query.message.edit_text(text)
        await callback_query.answer()

    # Функция для показа фото в карусели
    async def show_carousel_photo(
        client: Client, message: Message, section_id: int, photo_index: int
    ):
        """Показать фото из карусели с навигационными кнопками"""
        with sqlite3.connect("data.db") as conn:
            row = conn.execute(
                """
                SELECT title,
                    COALESCE(photo_id,  ''), COALESCE(photo_id2, ''), COALESCE(photo_id3, ''),
                    COALESCE(photo_id4, ''), COALESCE(photo_id5, ''), COALESCE(photo_id6, ''),
                    COALESCE(photo_id7, '')
                FROM sections
                WHERE id = ?
                """,
                (section_id,),
            ).fetchone()

        if row is None:
            await message.edit_text("⚠️ Раздел не найден.")
            return

        title, *photos = row
        photos = [p for p in photos if p]  # Убираем пустые значения

        if not photos:
            await message.edit_text("⚠️ В разделе нет фото.")
            return

        # Сохраняем текущую позицию пользователя
        user_id = message.from_user.id
        if user_id not in carousel_state:
            carousel_state[user_id] = {}
        carousel_state[user_id][section_id] = photo_index

        # Создаем навигационные кнопки
        keyboard = []
        nav_row = []

        # Кнопка "Назад" (если не первое фото)
        if photo_index > 0:
            nav_row.append(
                InlineKeyboardButton(
                    "⬅️ Назад", callback_data=f"carousel_prev_{section_id}_{photo_index}"
                )
            )

        # Индикатор текущей позиции
        nav_row.append(
            InlineKeyboardButton(
                f"{photo_index + 1}/{len(photos)}", callback_data="carousel_info"
            )
        )

        # Кнопка "Вперед" (если не последнее фото)
        if photo_index < len(photos) - 1:
            nav_row.append(
                InlineKeyboardButton(
                    "Вперед ➡️",
                    callback_data=f"carousel_next_{section_id}_{photo_index}",
                )
            )

        if nav_row:
            keyboard.append(nav_row)

        # Кнопка "Назад в раздел"
        keyboard.append(
            [
                InlineKeyboardButton(
                    "🔙 Назад в раздел", callback_data=f"back_to_section_{section_id}"
                )
            ]
        )

        # Отправляем фото с подписью и кнопками
        caption = f"<b>{title}</b>\n\nФото {photo_index + 1} из {len(photos)}"

        try:
            await message.edit_media(
                InputMediaPhoto(
                    photos[photo_index], caption=caption, parse_mode=ParseMode.HTML
                ),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except:
            # Если edit_media не работает, отправляем новое сообщение
            try:
                await message.delete()
            except:
                pass
            await message.reply_photo(
                photo=photos[photo_index],
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

    @app.on_callback_query(filters.regex(r"^carousel_prev_(\d+)_(\d+)$"))
    async def carousel_prev(client: Client, callback_query: CallbackQuery):
        match = callback_query.matches[0]
        section_id = int(match.group(1))
        current_index = int(match.group(2))

        if current_index > 0:
            new_index = current_index - 1
            await show_carousel_photo(
                client, callback_query.message, section_id, new_index
            )
        await callback_query.answer()

    @app.on_callback_query(filters.regex(r"^carousel_next_(\d+)_(\d+)$"))
    async def carousel_next(client: Client, callback_query: CallbackQuery):
        match = callback_query.matches[0]
        section_id = int(match.group(1))
        current_index = int(match.group(2))

        # Проверяем, есть ли следующее фото
        with sqlite3.connect("data.db") as conn:
            row = conn.execute(
                """
                SELECT COALESCE(photo_id,  ''), COALESCE(photo_id2, ''), COALESCE(photo_id3, ''),
                    COALESCE(photo_id4, ''), COALESCE(photo_id5, ''), COALESCE(photo_id6, ''),
                    COALESCE(photo_id7, '')
                FROM sections
                WHERE id = ?
                """,
                (section_id,),
            ).fetchone()

        if row:
            photos = [p for p in row if p]
            if current_index < len(photos) - 1:
                new_index = current_index + 1
                await show_carousel_photo(
                    client, callback_query.message, section_id, new_index
                )
        await callback_query.answer()

    @app.on_callback_query(filters.regex(r"^carousel_info$"))
    async def carousel_info(client: Client, callback_query: CallbackQuery):
        await callback_query.answer("📸 Карусель фото")

    @app.on_callback_query(filters.regex(r"^back_to_section_(\d+)$"))
    async def back_to_section(client: Client, callback_query: CallbackQuery):
        section_id = int(callback_query.matches[0].group(1))

        # Очищаем состояние карусели
        user_id = callback_query.from_user.id
        if user_id in carousel_state and section_id in carousel_state[user_id]:
            del carousel_state[user_id][section_id]

        # Показываем раздел обычным способом
        await show_section_with_carousel_option(
            client, callback_query.message, section_id
        )
        await callback_query.answer()
