from pyrogram import Client, filters
from pyrogram.types import Message
from utils.whitelist import (
    add_user_to_whitelist,
    remove_user_from_whitelist,
    get_complete_users_list,
    is_user_allowed,
    is_admin,
    get_whitelist_users,
)
from utils.menu import get_main_menu
import logging
from typing import List, Dict, Any

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def register_access_handlers(app: Client):
    # Фильтр для админов
    admin_filter = filters.create(lambda _, __, m: is_admin(m.from_user.id))

    @app.on_message(filters.command("start"))
    async def start(client: Client, message: Message):
        user_id = message.from_user.id
        if not is_user_allowed(user_id):
            await message.reply(
                "🚫 Доступ к боту ограничен. Для получения доступа обратитесь к администратору - @eternaltears14"
            )
            return

        name = message.from_user.first_name
        text, keyboard = get_main_menu()
        logger.info(f"Пользователь {name} (ID: {user_id}) успешно авторизовался")
        await message.reply(f"👋 Привет, {name}!\n\n{text}", reply_markup=keyboard)

    @app.on_message(filters.command("add") & admin_filter)
    async def add_user(client: Client, message: Message):
        try:
            user_id = int(message.command[1])
            if add_user_to_whitelist(user_id):
                await message.reply(f"✅ Пользователь {user_id} добавлен в whitelist")
            else:
                await message.reply(
                    "⚠️ Пользователь уже существует или является админом"
                )
        except (IndexError, ValueError):
            await message.reply("ℹ️ Использование: /add <ID_пользователя>")

    @app.on_message(filters.command("remove") & admin_filter)
    async def remove_user(client: Client, message: Message):
        try:
            user_id = int(message.command[1])
            if remove_user_from_whitelist(user_id):
                await message.reply(f"✅ Пользователь {user_id} удален из whitelist")
            else:
                await message.reply("⚠️ Пользователь не найден или является админом")
        except (IndexError, ValueError):
            await message.reply("ℹ️ Использование: /remove <ID_пользователя>")

    @app.on_message(filters.command("list") & admin_filter)
    async def list_users(client: Client, message: Message):
        try:
            users = get_complete_users_list()
            if not users:
                await message.reply("📭 Список пользователей пуст")
                return

            # Получаем информацию о пользователях
            users_info: List[Dict[str, Any]] = []
            for user in users:
                try:
                    tg_user = await client.get_users(user["user_id"])
                    name = (
                        f"{tg_user.first_name or ''} {tg_user.last_name or ''}".strip()
                    )
                    username = f" (@{tg_user.username})" if tg_user.username else ""
                    user_info = {
                        "id": user["user_id"],
                        "name": f"{name}{username}",
                        "is_admin": user["is_admin"],
                        "in_whitelist": user["in_whitelist"],
                    }
                    users_info.append(user_info)
                except Exception as e:
                    logger.warning(
                        f"Не удалось получить информацию о пользователе {user['user_id']}: {e}"
                    )
                    users_info.append(
                        {
                            "id": user["user_id"],
                            "name": "Неизвестный пользователь",
                            "is_admin": user["is_admin"],
                            "in_whitelist": user["in_whitelist"],
                        }
                    )

            # Сортируем: сначала админы, потом по ID
            users_info.sort(key=lambda x: (-x["is_admin"], x["id"]))

            response = "📋 Список пользователей:\n\n"
            for user in users_info:
                user_type = "👑 Админ" if user["is_admin"] else "👤 Пользователь"
                whitelist_status = (
                    ""
                    if user["is_admin"]
                    else " (whitelist)" if user["in_whitelist"] else ""
                )
                response += f"{user_type}: {user['name']} (ID: {user['id']}){whitelist_status}\n"

            # Разбиваем длинные сообщения
            for i in range(0, len(response), 4096):
                await message.reply(response[i : i + 4096])

        except Exception as e:
            logger.error(f"Ошибка в команде /list: {e}")
            await message.reply("⚠️ Произошла ошибка при получении списка пользователей")
