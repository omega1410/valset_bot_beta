from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
import logging

from config import ADMIN_IDS  # уже есть у тебя

OWNER_ID = ADMIN_IDS[0]

logger = logging.getLogger(__name__)

# --- runtime-состояние -------------------------------------------------------
awaiting_feedback = {}  # user_id -> True  (ждём сообщение с фидбеком)


# --- утилита -----------------------------------------------------------------
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

    # без цикла, ровно одно сообщение
    await client.send_message(OWNER_ID, header, disable_web_page_preview=True)
    await original.copy(OWNER_ID)


# --- хендлеры ----------------------------------------------------------------
def register_feedback_handlers(app: Client):

    @app.on_message(filters.command("feedback") & filters.private, group=5)
    async def cmd_feedback_pm(client: Client, message: Message):
        """
        /feedback <текст> — сразу отправляем
        /feedback         — ждём следующее сообщение как фидбек
        """
        if len(message.command) > 1:  # пришёл текст сразу
            text = message.text.split(maxsplit=1)[1].strip()
            if not text:
                await message.reply("❌ Сообщение пустое.")
                return

            await _send_to_owner(client, message, note="(передано текстом в /feedback)")
            await message.reply("✅ Спасибо! Я отправил твоё сообщение разработчику.")
        else:  # ждём следующее сообщение
            awaiting_feedback[message.from_user.id] = True
            await message.reply(
                "✍️ Напиши сообщение одним ответом, я передам его разработчику.\n"
                "Чтобы отменить — /cancel"
            )
            message.stop_propagation()

    # Можно принимать фидбек даже в группах
    @app.on_message(filters.command("feedback") & ~filters.private, group=5)
    async def cmd_feedback_grp(client: Client, message: Message):
        if len(message.command) == 1 and not message.reply_to_message:
            await message.reply(
                "ℹ️ Ответь этой командой на сообщение, "
                "которое нужно передать. Или напиши так:\n"
                "/feedback <текст>"
            )
            return

        # Если была реплайнутого — копируем именно его
        target = message.reply_to_message or message
        await _send_to_owner(client, target, note="(из группы)")
        await message.reply("✅ Передал!")

    @app.on_message(
        filters.text & filters.private & ~filters.command(["feedback", "cancel"]),
        group=6,
    )
    async def collect_feedback(client, message):
        if awaiting_feedback.pop(message.from_user.id, None):
            await _send_to_owner(client, message)
            await message.reply("✅ Спасибо! Фидбек доставлен разработчику.")

    @app.on_message(filters.command("cancel") & filters.private, group=6)
    async def cancel_feedback(client: Client, message: Message):
        if awaiting_feedback.pop(message.from_user.id, None):
            await message.reply("❌ Отменено.")
        else:
            await message.reply("Нечего отменять 🤷‍♂️")
