from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils.menu import get_main_menu
from handlers.tests import tests


def register_menu_handlers(app: Client):
    @app.on_callback_query(
        filters.regex(
            r"^(sections_|view_section_|open_section_menu|back_to_main|open_checklists)"
        ),
        group=1,
    )
    async def handle_callback(client: Client, callback_query: CallbackQuery):
        data = callback_query.data
        user_id = callback_query.from_user.id
        await callback_query.answer()
        print(f"[menu] получен callback: {data}")

        try:
            # список разделов (страницы)
            if data.startswith("sections_"):
                page = int(data.split("_")[1])
                per_page = 7
                offset = (page - 1) * per_page

                from sqlite3 import connect

                conn = connect("data.db")
                c = conn.cursor()
                c.execute(
                    "SELECT id, title FROM sections LIMIT ? OFFSET ?",
                    (per_page, offset),
                )
                sections = c.fetchall()
                c.execute("SELECT COUNT(*) FROM sections")
                total = c.fetchone()[0]
                conn.close()

                if not sections:
                    await callback_query.message.edit_text("Разделов пока нет.")
                    return

                keyboard = [
                    [InlineKeyboardButton(title, callback_data=f"view_section_{sid}")]
                    for sid, title in sections
                ]

                nav = []
                if page > 1:
                    nav.append(
                        InlineKeyboardButton("⬅️", callback_data=f"sections_{page - 1}")
                    )
                if offset + per_page < total:
                    nav.append(
                        InlineKeyboardButton("➡️", callback_data=f"sections_{page + 1}")
                    )
                if nav:
                    keyboard.append(nav)

                keyboard.append(
                    [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
                )

                await callback_query.message.edit_text(
                    "📚 Доступные разделы:", reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return

            # один раздел
            if data.startswith("view_section_"):
                section_id = int(data.split("_")[2])

                from sqlite3 import connect

                conn = connect("data.db")
                c = conn.cursor()
                c.execute(
                    "SELECT title, content FROM sections WHERE id = ?", (section_id,)
                )
                row = c.fetchone()
                conn.close()

                if not row:
                    await callback_query.message.reply("Раздел не найден.")
                    return

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
                return

            # главное меню
            if data == "back_to_main":
                text, keyboard = get_main_menu()
                await callback_query.message.edit_text(text=text, reply_markup=keyboard)
                return

            # чек-листы
            if data == "open_checklists":
                await callback_query.message.edit_text(
                    "📋 Чек-листы пока не добавлены.",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "🔙 Назад", callback_data="back_to_main"
                                )
                            ]
                        ]
                    ),
                )
                return

        except Exception as e:
            print(f"[ОШИБКА menu.py] Пользователь {user_id} — {e}")
            await callback_query.message.reply("⚠️ Произошла непредвиденная ошибка")
