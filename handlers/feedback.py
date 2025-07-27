# handlers/feedback.py
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
import logging
from config import ADMIN_IDS
from utils.states import user_states, STATE_FEEDBACK

OWNER_ID = ADMIN_IDS[0]
logger = logging.getLogger(__name__)


async def _send_to_owner(client: Client, original: Message, note: str | None = None):
    header = (
        "📩 <b>Новый фидбек</b>\n"
        f"👤 <code>{original.from_user.first_name or ''}"
        f"{' ' + original.from_user.last_name if original.from_user.last_name else ''}</code>\n"
        f"🆔 <code>{original.from_user.id}</code>\n"
        f"🕒 <code>{datetime.now():%d.%m.%Y %H:%M:%S}</code>\n"
    )
    if note:
        header += f"\n{note}"

    await client.send_message(OWNER_ID, header, disable_web_page_preview=True)
    await original.copy(OWNER_ID)


def register_feedback_handlers(app: Client):

    @app.on_message(filters.command("feedback") & filters.private, group=5)
    async def cmd_feedback_pm(client: Client, message: Message):
        if len(message.command) > 1:
            text = message.text.split(maxsplit=1)[1].strip()
            if not text:
                await message.reply("❌ Сообщение пустое.")
                return

            await _send_to_owner(client, message, note="(передано текстом в /feedback)")
            await message.reply("✅ Спасибо! Я отправил твоё сообщение разработчику.")
        else:
            user_states.set_state(message.from_user.id, STATE_FEEDBACK)
            await message.reply(
                "✍️ Напиши сообщение одним ответом, я передам его разработчику.\n"
                "Чтобы отменить — /cancel"
            )
            message.stop_propagation()

    @app.on_message(filters.command("feedback") & ~filters.private, group=5)
    async def cmd_feedback_grp(client: Client, message: Message):
        if len(message.command) == 1 and not message.reply_to_message:
            await message.reply(
                "ℹ️ Ответь этой командой на сообщение, "
                "которое нужно передать. Или напиши так:\n"
                "/feedback <текст>"
            )
            return

        target = message.reply_to_message or message
        await _send_to_owner(client, target, note="(из группы)")
        await message.reply("✅ Передал!")

    @app.on_message(
        filters.text & filters.private & ~filters.command(["feedback", "cancel"]),
        group=6,
    )
    async def collect_feedback(client, message):
        user_id = message.from_user.id
        if user_states.get_state(user_id) == STATE_FEEDBACK:
            user_states.clear_state(user_id)
            await _send_to_owner(client, message)
            await message.reply("✅ Спасибо! Фидбек доставлен разработчику.")
