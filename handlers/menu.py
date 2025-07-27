# handlers/menu.py
import os
from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
)
import sqlite3
import logging
from utils.menu import get_main_menu
from handlers.tests import tests
from utils.search_state import search_state
from config import ADMIN_IDS

logger = logging.getLogger(__name__)
SCHEDULE_PATH = "assets/schedule.png"


def register_menu_handlers(app: Client):
    @app.on_callback_query(filters.regex("^show_schedule$"), group=10)
    async def handle_show_schedule(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        await callback_query.answer()

        if not os.path.exists(SCHEDULE_PATH):
            await callback_query.message.edit_text(
                "⚠️ График смен временно недоступен",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
                ),
            )
            return

        try:
            await callback_query.message.delete()
        except Exception:
            pass

        await client.send_photo(
            chat_id=callback_query.message.chat.id,
            photo=SCHEDULE_PATH,
            caption="📆 Актуальный график смен",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
            ),
        )

    @app.on_message(filters.command("add_schedule") & filters.private, group=11)
    async def cmd_add_schedule(client: Client, message: Message):
        user_id = message.from_user.id
        if user_id not in ADMIN_IDS:
            await message.reply("⛔️ Нет доступа")
            return

        photo = None
        if message.photo:
            photo = message.photo
        elif message.reply_to_message and message.reply_to_message.photo:
            photo = message.reply_to_message.photo

        if not photo:
            await message.reply(
                "ℹ️ Пришлите фото графика или ответьте на фото командой /add_schedule"
            )
            return

        try:
            await client.download_media(photo.file_id, SCHEDULE_PATH)
            await message.reply("✅ График смен успешно обновлён!")
            logger.info(f"Админ {user_id} обновил график смен")
        except Exception as e:
            await message.reply(f"❌ Ошибка при сохранении: {e}")
            logger.error(f"Ошибка обновления графика: {e}")

    @app.on_message(filters.command("delete_schedule") & filters.private, group=11)
    async def cmd_delete_schedule(client: Client, message: Message):
        user_id = message.from_user.id
        if user_id not in ADMIN_IDS:
            await message.reply("⛔️ Нет доступа")
            return

        if not os.path.exists(SCHEDULE_PATH):
            await message.reply("⚠️ График смен не найден")
            return

        try:
            os.remove(SCHEDULE_PATH)
            await message.reply("✅ График смен удалён")
            logger.info(f"Админ {user_id} удалил график смен")
        except Exception as e:
            await message.reply(f"❌ Ошибка при удалении: {e}")
            logger.error(f"Ошибка удаления графика: {e}")

    @app.on_callback_query(group=10)
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

            if page:
                per_page = 8
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

                keyboard = [
                    [
                        InlineKeyboardButton(
                            title, callback_data=f"view_section_{section_id}"
                        )
                    ]
                    for section_id, title in sections
                ]

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

                keyboard.append(
                    [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
                )

                await callback_query.message.edit_text(
                    "📚 Доступные разделы:", reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return

            elif data.startswith("show_photo_"):
                parts = data.split("_")
                sec_id = int(parts[2])
                slot = int(parts[3])

                column = "photo_id" if slot == 1 else f"photo_id{slot}"
                conn = sqlite3.connect("data.db")
                c = conn.cursor()
                c.execute(f"SELECT title, {column} FROM sections WHERE id=?", (sec_id,))
                row = c.fetchone()
                conn.close()

                if not row or not row[1]:
                    await callback_query.answer("Фото отсутствует", show_alert=True)
                    return

                title, photo_id = row

                try:
                    await callback_query.message.delete()
                except Exception:
                    pass

                await client.send_photo(
                    chat_id=callback_query.message.chat.id,
                    photo=photo_id,
                    caption=f"📌 {title} (Фото {slot})",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "🔙 Назад", callback_data=f"view_section_{sec_id}"
                                )
                            ]
                        ]
                    ),
                )
                return

            elif data.startswith("view_section_"):
                section_id = int(data.split("_")[2])

                conn = sqlite3.connect("data.db")
                c = conn.cursor()
                c.execute(
                    """
                    SELECT title, content,
                        photo_id, photo_id2, photo_id3, photo_id4
                    FROM sections WHERE id=?""",
                    (section_id,),
                )
                row = c.fetchone()
                conn.close()

                if not row:
                    await callback_query.answer("Раздел не найден", show_alert=True)
                    return

                title, content, *photos = row
                try:
                    await callback_query.message.delete()
                except Exception:
                    pass

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

                for idx, ph in enumerate(photos, start=1):
                    if ph:
                        buttons.append(
                            [
                                InlineKeyboardButton(
                                    f"🖼 Фото {idx}",
                                    callback_data=f"show_photo_{section_id}_{idx}",
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
                kb = InlineKeyboardMarkup(buttons)

                text = f"📌 {title}\n\n{content}"
                await client.send_message(
                    callback_query.message.chat.id, text, reply_markup=kb
                )
                return

            elif data == "open_checklists":
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

            elif data == "search":
                await callback_query.message.edit_text(
                    "🔍 Введите ключевое слово для поиска по разделам:",
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
                search_state.add(user_id)
                return

            elif data == "back_to_main":
                text, keyboard = get_main_menu()

                try:
                    await callback_query.message.delete()
                except Exception:
                    pass

                await client.send_message(
                    chat_id=callback_query.message.chat.id,
                    text=text,
                    reply_markup=keyboard,
                )
                return

        except Exception as e:
            await callback_query.message.reply("⚠️ Произошла непредвиденная ошибка")
            print(f"[ОШИБКА menu.py] Пользователь {user_id} — {e}")
