from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
)
import sqlite3
from utils.search_state import search_state


def register_search_handlers(app: Client):
    @app.on_callback_query(filters.regex("^start_search$"), group=30)
    async def start_search(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        search_state.add(user_id)
        await callback_query.message.edit_text(
            "🔍 Введите ключевое слово для поиска по разделам:"
        )
        await callback_query.answer()

    @app.on_message(
        filters.text
        & filters.private
        & filters.create(lambda _, __, m: m.from_user.id in search_state),
        group=2
    )
    async def search_handler(client: Client, message: Message):
        await handle_search(client, message)


async def handle_search(client: Client, message: Message):
    user_id = message.from_user.id
    keyword = message.text.lower().strip()
    search_state.discard(user_id)

    print(f"[ПОИСК] Обработка запроса от {user_id}: {keyword}")

    try:
        conn = sqlite3.connect("data.db")
        c = conn.cursor()

        query = """
        SELECT id, title 
        FROM sections 
        WHERE title LIKE ? ESCAPE '\\' OR content LIKE ? ESCAPE '\\'
        """
        search_pattern = f"%{keyword}%"
        c.execute(query, (search_pattern, search_pattern))
        results = c.fetchall()

    except Exception as e:
        print(f"[ОШИБКА] Ошибка БД: {e}")
        await message.reply(
            "⚠️ Ошибка при поиске. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
            ),
        )
        return
    finally:
        conn.close()

    if not results:
        await message.reply(
            "🔍 Ничего не найдено.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
            ),
        )
        return

    keyboard = [
        [InlineKeyboardButton(title, callback_data=f"view_section_{section_id}")]
        for section_id, title in results
    ]
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])

    await message.reply(
        f"🔍 Результаты поиска ({len(results)}):",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
