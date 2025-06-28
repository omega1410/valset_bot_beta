from pyrogram import Client
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils.menu import get_main_menu
import sqlite3


def register_menu_handlers(app: Client):
    @app.on_callback_query()
    async def handle_callback(client: Client, callback_query: CallbackQuery):
        data = callback_query.data
        await callback_query.answer()

        # 📚 показать список всех разделов
        if data.startswith("sections"):
            try:
                page = int(data.split("_")[1])
            except IndexError:
                page = 1

            PAGE_SIZE = 7
            offset = (page - 1) * PAGE_SIZE

            conn = sqlite3.connect("data.db")
            c = conn.cursor()
            c.execute("SELECT id, title FROM sections")
            sections = c.fetchall()
            conn.close()

            total_pages = (len(sections) + PAGE_SIZE - 1) // PAGE_SIZE
            page_sections = sections[offset : offset + PAGE_SIZE]

            keyboard = []

            for section_id, title in page_sections:
                keyboard.append(
                    [InlineKeyboardButton(title, callback_data=f"section_{section_id}")]
                )

            # кнопки навигации
            nav_buttons = []
            if page > 1:
                nav_buttons.append(
                    InlineKeyboardButton("◀", callback_data=f"sections_{page - 1}")
                )
            if page < total_pages:
                nav_buttons.append(
                    InlineKeyboardButton("▶", callback_data=f"sections_{page + 1}")
                )
            if nav_buttons:
                keyboard.append(nav_buttons)

            # кнопка назад
            keyboard.append(
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
            )

            await callback_query.message.edit_text(
                "📚 Доступные разделы:", reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        # 📌 показать содержимое раздела
        if data.startswith("section_"):
            section_id = int(data.split("_")[1])

            conn = sqlite3.connect("data.db")
            c = conn.cursor()
            c.execute("SELECT title, content FROM sections WHERE id = ?", (section_id,))
            row = c.fetchone()
            conn.close()

            if row:
                title, content = row
                text = f"📌 {title}\n\n{content}"
                keyboard = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Назад", callback_data="sections")]]
                )
                await callback_query.message.edit_text(text=text, reply_markup=keyboard)
            else:
                await callback_query.message.reply("Раздел не найден.")
            return

        # 🔙 назад в главное меню
        if data == "back_to_main":
            text, keyboard = get_main_menu()
            await callback_query.message.edit_text(text, reply_markup=keyboard)
