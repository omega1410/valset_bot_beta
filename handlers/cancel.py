# handlers/cancel.py
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import logging
from utils.states import user_states
from handlers.logbook import pending_prompt

logger = logging.getLogger(__name__)


def register_cancel_handler(app: Client):

    @app.on_message(filters.command("cancel") & filters.private, group=15)
    async def cancel_handler(client: Client, message: Message):
        user_id = message.from_user.id
        state = user_states.get_state(user_id)
        was_cancelled = False

        if state:
            # Очищаем состояние
            user_states.clear_state(user_id)
            was_cancelled = True

            # Обрабатываем конкретные случаи
            if state in ["feedback"]:
                await message.reply("❌ Отменено. Фидбэк не отправлен.")

            elif state in ["logbook_new", "logbook_edit"]:
                # Удаляем prompt если есть
                pid = pending_prompt.pop(user_id, None)
                if pid:
                    try:
                        await client.delete_messages(user_id, pid, revoke=True)
                    except Exception:
                        pass

                kb_back = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔙  Назад к логбуку", callback_data="open_logbook"
                            )
                        ]
                    ]
                )
                await message.reply(
                    "❌ Отменено. Запись в логбук не создана.", reply_markup=kb_back
                )

            else:
                await message.reply("❌ Действие отменено.")

        else:
            await message.reply("ℹ️ Нечего отменять.")
