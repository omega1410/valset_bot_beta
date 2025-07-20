from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import logging

logger = logging.getLogger(__name__)

FIXED_TASKS = {
    "day": [
        {"text": "Принять смену", "order": 1},
        {"text": "Сверить кассу", "order": 2},
        {"text": "Заполнить журнал", "order": 3},
        {"text": "Просмотреть отчет за смену", "order": 4},
        {"text": "Проверить заезды", "order": 5},
        {"text": "Сделать ключи", "order": 6},
        {"text": "Заполнить EMIS", "order": 7},
        {"text": "Заполнить Profiles", "order": 8},
        {"text": "Сверить кассу", "order": 9},
        {"text": "Заполнить журнал", "order": 10},
        {"text": "Передать смену", "order": 11},
    ],
    "night": [
        {"text": "Принять смену", "order": 12},
        {"text": "Сверить кассу", "order": 13},
        {"text": "Заполнить журнал", "order": 14},
        {"text": "Отправить отчет проживающих", "order": 15},
        {"text": "Позвонить гостям по уборке", "order": 16},
        {"text": "Проверить выезды", "order": 17},
        {"text": "Заполнить EMIS", "order": 18},
        {"text": "Заполнить Profiles", "order": 19},
        {"text": "Сверить кассу и закрыться", "order": 20},
        {"text": "Провести ночной аудит", "order": 21},
        {"text": "Отправить отчет No Show", "order": 22},
        {"text": "Отправить отчет за смену", "order": 23},
    ],
}


def register_checklist_handlers(app: Client):
    def init_db():
        with sqlite3.connect("data.db") as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checklist_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    checklist_name TEXT NOT NULL,
                    task_text TEXT NOT NULL,
                    task_order INTEGER NOT NULL,
                    is_done BOOLEAN DEFAULT 0,
                    user_id INTEGER NOT NULL,
                    UNIQUE(checklist_name, task_text, user_id)
                )
                """
            )

            for shift_type, tasks in FIXED_TASKS.items():
                for task in tasks:
                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO checklist_tasks "
                            "(checklist_name, task_text, task_order, user_id) "
                            "VALUES (?, ?, ?, ?)",
                            (shift_type, task["text"], task["order"], 0),
                        )
                    except sqlite3.Error as e:
                        logger.error(f"Ошибка добавления задачи: {e}")
            conn.commit()

    init_db()

    async def show_checklist(
        client: Client, callback_query: CallbackQuery, shift_type: str
    ):
        user_id = callback_query.from_user.id

        with sqlite3.connect("data.db") as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            c.execute(
                "SELECT id, task_text, is_done FROM checklist_tasks "
                "WHERE checklist_name = ? AND user_id IN (0, ?) "
                "ORDER BY task_order",
                (shift_type, user_id),
            )
            tasks = c.fetchall()

        keyboard = []
        for task in tasks:
            status = "✅" if task["is_done"] else "☑️"
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"{status} {task['task_text']}",
                        callback_data=f"toggle_task_{task['id']}_{shift_type}",
                    )
                ]
            )

        keyboard.append(
            [InlineKeyboardButton("🔙 Назад", callback_data="open_checklists")]
        )

        await callback_query.message.edit_text(
            f"📋 Чек-лист {'дневной' if shift_type == 'day' else 'ночной'} смены:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    @app.on_callback_query(filters.regex("^open_checklists$"), group=12)
    async def open_checklists(client: Client, callback_query: CallbackQuery):
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🌞 Дневная смена", callback_data="day_checklist"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🌙 Ночная смена", callback_data="night_checklist"
                    )
                ],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
            ]
        )
        await callback_query.message.edit_text(
            "📋 Выберите тип смены:", reply_markup=keyboard
        )

    @app.on_callback_query(filters.regex("^day_checklist$"), group=12)
    async def show_day_checklist(client: Client, callback_query: CallbackQuery):
        await show_checklist(client, callback_query, "day")

    @app.on_callback_query(filters.regex("^night_checklist$"), group=12)
    async def show_night_checklist(client: Client, callback_query: CallbackQuery):
        await show_checklist(client, callback_query, "night")

    @app.on_callback_query(filters.regex("^toggle_task_"), group=12)
    async def toggle_task(client: Client, callback_query: CallbackQuery):
        data = callback_query.data.split("_")
        task_id = int(data[2])
        shift_type = data[3]
        user_id = callback_query.from_user.id

        with sqlite3.connect("data.db") as conn:
            c = conn.cursor()

            c.execute(
                "UPDATE checklist_tasks SET is_done = NOT is_done "
                "WHERE id = ? AND user_id IN (0, ?)",
                (task_id, user_id),
            )
            conn.commit()

            c.execute(
                "SELECT COUNT(*) FROM checklist_tasks "
                "WHERE checklist_name = ? AND user_id IN (0, ?) AND is_done = 0",
                (shift_type, user_id),
            )

            if c.fetchone()[0] == 0:
                c.execute(
                    "UPDATE checklist_tasks SET is_done = 0 "
                    "WHERE checklist_name = ? AND user_id IN (0, ?)",
                    (shift_type, user_id),
                )
                conn.commit()

                await callback_query.message.edit_text(
                    f"🎉 Все задачи {'дневной' if shift_type == 'day' else 'ночной'} смены выполнены!\n"
                    "Чек-лист сброшен.",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "🔙 Назад", callback_data="open_checklists"
                                )
                            ]
                        ]
                    ),
                )
                return

        if shift_type == "day":
            await show_day_checklist(client, callback_query)
        else:
            await show_night_checklist(client, callback_query)
