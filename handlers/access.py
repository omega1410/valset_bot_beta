from pyrogram import Client, filters
from pyrogram.types import Message
from utils.whitelist import (
    add_user_to_whitelist,
    remove_user_from_whitelist,
    get_whitelist,
    is_user_allowed,
)
from utils.menu import get_main_menu
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_IDS = [5669245603]

admin_filter = filters.user(ADMIN_IDS)


def validate_user_id(user_id: int) -> bool:
    return 0 < user_id < 2**31 


async def get_user_info(client: Client, user_id: int) -> str:
    try:
        user = await client.get_users(user_id)
        return f"{user.first_name} (ID: {user.id})"
    except Exception:
        return f"ID: {user_id} (пользователь не найден)"


def register_access_handlers(app: Client):
    @app.on_message(filters.command("start"))
    async def start(client: Client, message: Message):
        user_id = message.from_user.id
        if not is_user_allowed(user_id):
            logger.warning(
                f"Попытка доступа от неавторизованного пользователя: {user_id}"
            )
            await message.reply(
                "🚫 Доступ к боту ограничен.\n"
                "Для получения доступа обратитесь к администратору."
            )
            return

        name = message.from_user.first_name
        text, keyboard = get_main_menu()
        await message.reply(f"👋 Привет, {name}!\n\n{text}", reply_markup=keyboard)
        logger.info(f"Пользователь {user_id} успешно авторизовался")

    @app.on_message(filters.command("add") & admin_filter)
    async def add_user(client: Client, message: Message):
        try:
            args = message.text.split()
            if len(args) < 2:
                raise ValueError

            user_id_to_add = int(args[1])

            if not validate_user_id(user_id_to_add):
                await message.reply("❌ Неверный формат ID пользователя")
                return

            user_info = await get_user_info(client, user_id_to_add)
            added = add_user_to_whitelist(user_id_to_add)

            if added:
                logger.info(
                    f"Админ {message.from_user.id} добавил пользователя {user_id_to_add}"
                )
                await message.reply(
                    f"✅ Пользователь {user_info} успешно добавлен в белый список."
                )
            else:
                await message.reply(
                    f"⚠️ Пользователь {user_info} уже находится в белом списке"
                )

        except (IndexError, ValueError):
            await message.reply(
                "ℹ️ Использование команды:\n"
                "<code>/add &lt;ID_пользователя&gt;</code>\n\n"
                "Пример: <code>/add 123456789</code>"
            )

    @app.on_message(filters.command("remove") & admin_filter)
    async def remove_user(client: Client, message: Message):
        try:
            args = message.text.split()
            if len(args) < 2:
                raise ValueError

            user_id_to_remove = int(args[1])

            if not validate_user_id(user_id_to_remove):
                await message.reply("❌ Неверный формат ID пользователя")
                return

            user_info = await get_user_info(client, user_id_to_remove)
            removed = remove_user_from_whitelist(user_id_to_remove)

            if removed:
                logger.info(
                    f"Админ {message.from_user.id} удалил пользователя {user_id_to_remove}"
                )
                await message.reply(
                    f"✅ Пользователь {user_info} успешно удален из белого списка."
                )
            else:
                await message.reply(
                    f"⚠️ Пользователь {user_info} не найден в белом списке"
                )

        except (IndexError, ValueError):
            await message.reply(
                "ℹ️ Использование команды:\n"
                "<code>/remove &lt;ID_пользователя&gt;</code>\n\n"
                "Пример: <code>/remove 123456789</code>"
            )

    @app.on_message(filters.command("list") & admin_filter)
    async def list_users(client: Client, message: Message):
        try:
            whitelist = get_whitelist()

            if not whitelist:
                await message.reply("📝 Белый список пуст")
                return

            response = "📝 Пользователи в белом списке:\n\n"
            for user_id in whitelist:
                user_info = await get_user_info(client, user_id)
                response += f"• {user_info}\n"

            for i in range(0, len(response), 4096):
                await message.reply(response[i : i + 4096])

            logger.info(f"Админ {message.from_user.id} запросил список пользователей")

        except Exception as e:
            logger.error(f"Ошибка при получении списка пользователей: {e}")
            await message.reply(
                "❌ Произошла ошибка при получении списка пользователей"
            )
