from pyrogram import Client
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
from utils.menu import get_main_menu
from handlers.tests import tests
from pyrogram import filters


def register_menu_handlers(app: Client):

    @app.on_callback_query(
        filters.regex(
            "^(sections_|view_section_|start_test_|open_section_menu|back_to_main)$"
        )
    )
    async def handle_callback(client: Client, callback_query: CallbackQuery):
        data = callback_query.data
        user_id = callback_query.from_user.id
        await callback_query.answer()

        try:
            if data.startswith("sections_"):
                try:
                    page = int(data.split("_")[1])
                except ValueError:
                    page = 1
            elif data == "open_section_menu":
                page = 1
            else:
                page = None

            if page is not None:
                per_page = 7
                offset = (page - 1) * per_page

                conn = sqlite3.connect("data.db")
                c = conn.cursor()
                c.execute(
                    "SELECT id, title FROM sections LIMIT ? OFFSET ?",
                    (per_page, offset),
                )
                sections = c.fetchall()

                c.execute("SELECT COUNT(*) FROM sections")
                total_sections = c.fetchone()[0]
                conn.close()

                if not sections:
                    await callback_query.message.edit_text("Разделов пока нет.")
                    return

                keyboard = []
                for section_id, title in sections:
                    keyboard.append(
                        [
                            InlineKeyboardButton(
                                title, callback_data=f"view_section_{section_id}"
                            )
                        ]
                    )

                # пагинация
                pagination = []
                if page > 1:
                    pagination.append(
                        InlineKeyboardButton("⬅️", callback_data=f"sections_{page - 1}")
                    )
                if offset + per_page < total_sections:
                    pagination.append(
                        InlineKeyboardButton("➡️", callback_data=f"sections_{page + 1}")
                    )
                if pagination:
                    keyboard.append(pagination)

                # назад
                keyboard.append(
                    [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
                )

                await callback_query.message.edit_text(
                    "📚 Доступные разделы:", reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return

            elif data.startswith("view_section_"):
                section_id = int(data.split("_")[2])

                conn = sqlite3.connect("data.db")
                c = conn.cursor()
                c.execute(
                    "SELECT title, content FROM sections WHERE id = ?", (section_id,)
                )
                row = c.fetchone()
                conn.close()

                if row:
                    title, content = row
                    text = f"📌 {title}\n\n{content}"

                    buttons = []

                    if section_id in tests:
                        buttons.append(
                            [
                                InlineKeyboardButton(
                                    "📝 Пройти тест",
                                    callback_data=f"start_test_{section_id}",
                                )
                            ]
                        )

                    buttons.append(
                        [
                            InlineKeyboardButton(
                                "🔙 Назад", callback_data="open_section_menu"
                            )
                        ]
                    )

                    await callback_query.message.edit_text(
                        text=text, reply_markup=InlineKeyboardMarkup(buttons)
                    )
                else:
                    await callback_query.message.reply("Раздел не найден.")
                return

            elif data == "back_to_main":
                text, keyboard = get_main_menu()
                await callback_query.message.edit_text(text=text, reply_markup=keyboard)
                return

        except Exception as e:
            await callback_query.message.reply("⚠️ Произошла непредвиденная ошибка")
            print(f"[ОШИБКА menu.py] Пользователь {user_id} — {e}")
