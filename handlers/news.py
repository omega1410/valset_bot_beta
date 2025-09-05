from pyrogram import Client, filters
from pyrogram.types import Message
from config import ADMIN_IDS
from utils import news_state
import sqlite3
import logging
import asyncio

logger = logging.getLogger(__name__)


def register_news_handlers(app: Client):
    """
    Регистрирует обработчики команды рассылки новостей.
    
    Обрабатывает:
    - /news для запуска режима ввода текста
    - Отправку сообщений всем пользователям из белого списка
    """
    
    @app.on_message(filters.command("news") & filters.private, group=20)
    async def start_news(client: Client, message: Message):
        """
        Запускает режим ввода текста для рассылки.
        
        Args:
            client: Клиент Pyrogram
            message: Сообщение пользователя
        """
        if message.from_user.id not in ADMIN_IDS:
            await message.reply("⛔️ Доступ запрещён.")
            return

        await message.reply(f"✍️ Введите текст рассылки:")
        news_state.add(message.from_user.id)

    @app.on_message(filters.text & filters.private, group=20)
    async def handle_news_text(client: Client, message: Message):
        """
        Обрабатывает текст рассылки и отправляет его всем подписчикам.
        
        Args:
            client: Клиент Pyrogram
            message: Сообщение с текстом рассылки
        """
        user_id = message.from_user.id
        if not news_state.has(user_id):
            return

        news_text = message.text.strip()
        news_state.discard(user_id)

        try:
            with sqlite3.connect("data.db", timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Проверяем существование таблицы
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='whitelist'")
                if not cursor.fetchone():
                    await message.reply("⚠️ Таблица белого списка не найдена")
                    return

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
        for idx, user in enumerate(users, 1):
            try:
                await client.send_message(
                    user["user_id"], 
                    f"🔔 Рассылка:\n\n{news_text}"
                )
                count += 1
                
                # Анти-рейтлимит задержка (Telegram позволяет ~30 сообщений/сек)
                if idx % 10 == 0:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                errors.append(f"{user['user_id']}: {str(e)}")
                logger.warning(f"Не удалось отправить {user['user_id']}: {e}")

        result_msg = f"📬 Рассылка завершена\nУспешно: {count}\nОшибки: {len(errors)}"
        if errors:
            result_msg += f"\n\nОшибки:\n" + "\n".join(errors[:5])
        await message.reply(result_msg)
