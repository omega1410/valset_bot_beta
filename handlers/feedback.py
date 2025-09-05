# handlers/feedback.py
"""
Модуль обработки обратной связи от пользователей.

Реализует:
- Команду /feedback для отправки сообщений разработчику
- Систему сбора текстовых фидбеков в приватных чатах
- Пересылку сообщений с метаданными в личный аккаунт владельца
"""

from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
import logging
from config import ADMIN_IDS
from utils.states import user_states, STATE_FEEDBACK

OWNER_ID = ADMIN_IDS[0] if ADMIN_IDS else None  # Защита от пустого списка админов
logger = logging.getLogger(__name__)


async def _send_to_owner(client: Client, original: Message, note: str | None = None):
    """
    Отправляет сообщение владельцу бота с метаданными пользователя.
    
    Args:
        client: Экземпляр клиента Pyrogram
        original: Оригинальное сообщение пользователя
        note: Дополнительная информация для шапки сообщения
    """
    try:
        # Используем безопасное получение имени пользователя
        first_name = original.from_user.first_name or "Неизвестный"
        last_name = original.from_user.last_name or ""
        
        header = (
            "📩 <b>Новый фидбек</b>\n"
            f"👤 <code>{first_name} {last_name}</code>\n"
            f"🆔 <code>{original.from_user.id}</code>\n"
            f"🕒 <code>{datetime.now():%d.%m.%Y %H:%M:%S}</code>\n"
        )
        if note:
            header += f"\n{note}"

        await client.send_message(OWNER_ID, header, disable_web_page_preview=True)
        await original.copy(OWNER_ID)
    except Exception as e:
        logger.error(f"Ошибка отправки фидбека: {e}")


def register_feedback_handlers(app: Client):
    """
    Регистрирует обработчики команды обратной связи.
    
    Обрабатывает:
    - /feedback в приватных чатах (текст и ответы)
    - /feedback в группах (текст и пересылка сообщений)
    - Автоматический сбор фидбека при включенном состоянии
    """
    
    @app.on_message(filters.command("feedback") & filters.private, group=5)
    async def cmd_feedback_pm(client: Client, message: Message):
        """
        Обработка команды /feedback в приватном чате.
        
        При наличии аргумента отправляет текст сразу.
        Иначе переводит пользователя в состояние ожидания сообщения.
        
        Args:
            client: Клиент Pyrogram
            message: Сообщение пользователя
        """
        if not OWNER_ID:
            await message.reply("⛔ Администратор не настроен")
            return
            
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
        """
        Обработка команды /feedback в групповом чате.
        
        Позволяет либо передать текст, либо переслать сообщение.
        
        Args:
            client: Клиент Pyrogram
            message: Сообщение пользователя
        """
        if not OWNER_ID:
            await message.reply("⛔ Администратор не настроен")
            return
            
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
        """
        Сбор фидбека из приватного чата при активном состоянии.
        
        Выполняется автоматически после использования команды /feedback
        без указания текста.
        
        Args:
            client: Клиент Pyrogram
            message: Сообщение пользователя
        """
        if not OWNER_ID:
            return
            
        user_id = message.from_user.id
        if user_states.get_state(user_id) == STATE_FEEDBACK:
            user_states.clear_state(user_id)
            await _send_to_owner(client, message)
            await message.reply("✅ Спасибо! Фидбек доставлен разработчику.")
