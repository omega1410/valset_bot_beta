import os
import logging
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)


def register_schedule_handler(app: Client):
    @app.on_callback_query(filters.regex("^show_schedule$"))
    async def handle_schedule_callback(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id

        try:
            await callback_query.answer()
            await callback_query.message.delete()

            # путь к файлу
            photo_path = os.path.abspath("schedule.jpeg")

            # проверка существования файла
            if not os.path.exists(photo_path):
                await client.send_message(
                    chat_id=callback_query.message.chat.id,
                    text="Файл графика не найден.",
                )
                logger.error(f"[schedule] файл {photo_path} не найден")
                return

            logger.info(f"[schedule] отправка графика пользователю {user_id}")

            await client.send_photo(
                chat_id=callback_query.message.chat.id,
                photo=photo_path,
                caption="🗓 График смен",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
                ),
            )

        except Exception as e:
            logger.error(f"[schedule] ошибка у пользователя {user_id}: {e}")
            try:
                await client.send_message(
                    chat_id=callback_query.message.chat.id,
                    text="⚠️ Не удалось отправить график. Попробуйте позже.",
                )
            except:
                pass  # если и это упадёт — ничего не делаем
