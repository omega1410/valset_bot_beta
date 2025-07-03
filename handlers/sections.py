from pyrogram import Client, filters
from pyrogram.types import Message
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_IDS = [5669245603]


pending_titles = {}
pending_contents = {}


def validate_input(text: str, max_length: int = 1000) -> bool:
    if not text.strip():
        return False
    if len(text) > max_length:
        return False
    return True


def register_section_handlers(app: Client):
    @app.on_message(filters.text & filters.private)
    async def handle_section_input(client: Client, message: Message):
        user_id = message.from_user.id

        if user_id not in ADMIN_IDS:
            logger.warning(f"Неавторизованный доступ: {user_id}")
            return

        try:
            if user_id in pending_titles and pending_titles[user_id] is True:
                if not validate_input(message.text, 200):
                    await message.reply(
                        "Заголовок не должен быть пустым или слишком длинным (макс. 200 символов)"
                    )
                    return

                pending_titles[user_id] = message.text.strip()
                await message.reply("Теперь введи содержание раздела:")
                logger.info(f"Пользователь {user_id} ввел заголовок: {message.text}")
                return

            if user_id in pending_titles and user_id not in pending_contents:
                if not validate_input(message.text):
                    await message.reply("Содержание не должно быть пустым")
                    return

                title = pending_titles[user_id]
                content = message.text.strip()

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
                    raise
                finally:
                    conn.close()

                del pending_titles[user_id]
                await message.reply("Раздел успешно сохранён ✅")

        except Exception as e:
            logger.error(f"Ошибка в обработчике: {e}")
            pending_titles.pop(user_id, None)
            pending_contents.pop(user_id, None)
            await message.reply("⚠️ Произошла ошибка. Попробуйте снова.")
