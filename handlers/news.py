from pyrogram import Client, filters
from pyrogram.types import Message
from config import ADMIN_IDS
from utils import news_state
import sqlite3
import logging

logger = logging.getLogger(__name__)


def register_news_handlers(app: Client):
    @app.on_message(filters.command("news") & filters.private, group=20)
    async def start_news(client: Client, message: Message):
        if message.from_user.id not in ADMIN_IDS:
            await message.reply("⛔️ Доступ запрещён.")
            return

        await message.reply(f"✍️ Введите текст рассылки:")
        news_state.add(message.from_user.id)

    @app.on_message(filters.text & filters.private, group=20)
    async def handle_news_text(client: Client, message: Message):
        user_id = message.from_user.id
        if not news_state.has(user_id):
            return

        news_text = message.text.strip()
        news_state.discard(user_id)

        try:
            with sqlite3.connect("data.db", timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("SELECT user_id FROM whitelist")
                users = cursor.fetchall()

                if not users:
                    await message.reply("ℹ️ В белом списке пока нет пользователей")
                    return

                logger.info(f"Найдено пользователей для рассылки: {len(users)}")

        except Exception as e:
            logger.error(f"Ошибка БД: {e}", exc_info=True)
            await message.reply("⚠️ Критическая ошибка при чтении БД")
            return

        count = 0
        errors = []
        for user in users:
            try:
                await client.send_message(
                    user["user_id"], f"🔔 Рассылка:\n\n{news_text}"
                )
                count += 1
            except Exception as e:
                errors.append(f"{user['user_id']}: {str(e)}")
                logger.warning(f"Не удалось отправить {user['user_id']}: {e}")

        result_msg = f"📬 Рассылка завершена\nУспешно: {count}\nОшибки: {len(errors)}"
        if errors:
            result_msg += f"\n\nОшибки:\n" + "\n".join(errors[:5])
        await message.reply(result_msg)
