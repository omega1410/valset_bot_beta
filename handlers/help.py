from pyrogram import Client, filters
from pyrogram.types import Message
from utils.whitelist import is_admin


def register_help_handler(app: Client):
    @app.on_message(filters.command("help") & filters.private, group=0)
    async def cmd_help(client: Client, message: Message):
        user_id = message.from_user.id

        common_commands = {
            "/start": "Запустить бота и открыть главное меню",
            "/help": "Показать это сообщение",
            "/stats": "Посмотреть статистику",
        }

        admin_commands = {
            "/list": "Показать список пользователей",
            "/add ID": "Добавить пользователя в whitelist",
            "/remove ID": "Удалить пользователя из whitelist",
            "/news": "Разослать новость",
            "/add_section": "Создать новый раздел",
            "/edit_section": "Редактировать раздел",
            "/set_photo ID раздела": "Добавить фото к разделу",
            "/remove_photo ID раздела": "Удалить фото из раздела"
        }

        lines = ["💡 Доступные команды:\n"]
        for cmd, desc in common_commands.items():
            lines.append(f"{cmd:<15} — {desc}")

        if is_admin(user_id):
            lines.append("\n🔑 Админ-команды:")
            for cmd, desc in admin_commands.items():
                lines.append(f"{cmd:<15} — {desc}")

        text = "\n".join(lines)
        for chunk in (text[i : i + 4096] for i in range(0, len(text), 4096)):
            await message.reply_text(chunk, quote=True)
