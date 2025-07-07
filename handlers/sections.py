from pyrogram import Client, filters
from pyrogram.types import Message
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_IDS = [5669245603]

# словари для хранения состояния ожидания ввода
pending_titles = {}
pending_contents = {}


def validate_input(text: str, max_length: int = 1000) -> bool:
    if not text.strip():
        return False
    if len(text) > max_length:
        return False
    return True


def register_section_handlers(app: Client):
    # команда /add_section - начинает процесс добавления раздела
    @app.on_message(filters.command("add_section") & filters.private)
    async def start_add_section(client: Client, message: Message):
        user_id = message.from_user.id
        if user_id not in ADMIN_IDS:
            await message.reply("У тебя нет доступа к этой команде")
            return
        pending_titles[user_id] = True  # ждем заголовок
        await message.reply("✅ Введи заголовок раздела:")

    # обработка ввода заголовка и содержания
    @app.on_message(filters.text & filters.private)
    async def handle_section_input(client: Client, message: Message):
        user_id = message.from_user.id
        if user_id not in ADMIN_IDS:
            logger.warning(f"Неавторизованный доступ: {user_id}")
            return

        try:
            # ожидаем заголовок
            if user_id in pending_titles and pending_titles[user_id] is True:
                title = message.text.strip()
                if not validate_input(title, 200):
                    await message.reply(
                        "Заголовок не должен быть пустым или слишком длинным (макс. 200 символов)"
                    )
                    return
                pending_titles[user_id] = title
                pending_contents[user_id] = True  # теперь ждём содержание
                await message.reply("Теперь введи содержание раздела:")
                logger.info(f"Пользователь {user_id} ввел заголовок: {title}")
                return

            # ожидаем содержание
            if user_id in pending_contents and pending_contents[user_id] is True:
                content = message.text.strip()
                if not validate_input(content, 5000):
                    await message.reply("Содержание не должно быть пустым")
                    return

                title = pending_titles.get(user_id)
                if not title:
                    await message.reply("Произошла ошибка, начни заново")
                    pending_titles.pop(user_id, None)
                    pending_contents.pop(user_id, None)
                    return

                # сохраняем в базу
                try:
                    conn = sqlite3.connect("data.db")
                    c = conn.cursor()
                    c.execute(
                        "INSERT INTO sections (title, content) VALUES (?, ?)",
                        (title, content),
                    )
                    conn.commit()
                    logger.info(f"Добавлен новый раздел: '{title}'")
                except sqlite3.Error as e:
                    logger.error(f"Ошибка БД: {e}")
                    await message.reply("⚠️ Ошибка при сохранении раздела")
                    return
                finally:
                    conn.close()

                # очистка состояний
                pending_titles.pop(user_id, None)
                pending_contents.pop(user_id, None)

                await message.reply("Раздел успешно сохранён ✅")
                return

        except Exception as e:
            logger.error(f"Ошибка в обработчике: {e}")
            pending_titles.pop(user_id, None)
            pending_contents.pop(user_id, None)
            await message.reply("⚠️ Произошла ошибка. Попробуйте снова.")
