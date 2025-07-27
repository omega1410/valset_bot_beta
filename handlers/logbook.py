# handlers/logbook.py
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
import sqlite3, logging, textwrap
from pyrogram.enums import ParseMode
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from config import LOCAL_TZ
from utils.states import user_states, STATE_LOGBOOK_NEW, STATE_LOGBOOK_EDIT

DB = "data.db"
logger = logging.getLogger(__name__)

pending_prompt = {}
from utils.menu import get_main_menu


def utc_to_local(ts: str) -> str:
    dt_utc = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
    return dt_utc.astimezone(LOCAL_TZ).strftime("%d.%m.%Y %H:%M")


def _init_table():
    with sqlite3.connect(DB) as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS logbook (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                author_id   INTEGER,
                author_name TEXT,
                text        TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'open',
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );"""
        )


def _build_list():
    with sqlite3.connect(DB) as db:
        rows = db.execute(
            "SELECT id, text, author_name, status FROM logbook "
            "ORDER BY status, id DESC"
        ).fetchall()

    buttons = []
    for rid, txt, author, status in rows:
        prefix = "✅" if status == "done" else "🟢"
        short = textwrap.shorten(txt, width=30, placeholder="…")
        label = f"{prefix} {short} — {author}"

        row = [InlineKeyboardButton(label, callback_data=f"view:{rid}")]
        if status == "open":
            row.extend((InlineKeyboardButton("❌", callback_data=f"del:{rid}"),))
        buttons.append(row)

    buttons.append(
        [
            InlineKeyboardButton("➕  Добавить запись", callback_data="add"),
            InlineKeyboardButton("🔙  Назад", callback_data="back_main"),
        ]
    )
    return InlineKeyboardMarkup(buttons)


def _back_to_main(cq: CallbackQuery):
    text, kb = get_main_menu()
    return cq.message.edit_text(text, reply_markup=kb)


def register_logbook(app: Client):
    _init_table()

    @app.on_callback_query(filters.regex("^open_logbook$"), group=3)
    async def cb_open(_, cq: CallbackQuery):
        await cq.message.edit_text("📔 Логбук:", reply_markup=_build_list())
        await cq.answer()

    @app.on_callback_query(filters.regex("^back_main$"), group=3)
    async def cb_back_main(_, cq: CallbackQuery):
        await _back_to_main(cq)
        await cq.answer()

    @app.on_callback_query(filters.regex("^(add|view:|edit:|del:|done:)"), group=3)
    async def cb_router(_, cq: CallbackQuery):
        data = cq.data
        uid = cq.from_user.id
        name = cq.from_user.first_name or "Anon"

        if data == "add":
            user_states.set_state(uid, STATE_LOGBOOK_NEW)
            await cq.message.delete()
            prompt = await cq.message._client.send_message(
                uid, "✍️ Введите текст новой записи.\n\nДля отмены — /cancel"
            )
            pending_prompt[uid] = prompt.id
            await cq.answer()
            return

        action, param_str = data.split(":", 1)

        try:
            rid = int(param_str)
        except ValueError:
            await cq.answer("Некорректные данные ❌", show_alert=True)
            logger.warning(f"Некорректные данные callback: {cq.data}")
            return

        if action == "view":
            with sqlite3.connect(DB) as db:
                row = db.execute(
                    "SELECT text, status, author_name, created_at "
                    "FROM logbook WHERE id=?",
                    (rid,),
                ).fetchone()

            if not row:
                await cq.answer("Запись не найдена", True)
                return

            txt, st, author, dt = row
            dt = utc_to_local(dt)

            icon = "✅" if st == "done" else "🟢"
            await cq.message.delete()

            await cq.message._client.send_message(
                chat_id=uid,
                text=(
                    f"{icon} <b>Запись #{rid}</b>\n" f"<i>{author}, {dt}</i>\n\n{txt}"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔙  Назад к логбуку", callback_data="open_logbook"
                            )
                        ]
                    ]
                ),
            )
            await cq.answer()
            return

        if action == "del":
            with sqlite3.connect(DB) as db:
                db.execute("DELETE FROM logbook WHERE id=?", (rid,))
            await cq.message.edit_reply_markup(_build_list())
            await cq.answer("Удалено")
            return

    @app.on_message(
        filters.text & filters.private & ~filters.command(["cancel"]), group=4
    )
    async def catch_text(client, msg: Message):
        user_id = msg.from_user.id
        text = msg.text.strip()
        name = (
            (msg.from_user.first_name or "") + " " + (msg.from_user.last_name or "")
        ).strip() or "Anon"

        # Проверяем состояние пользователя
        state = user_states.get_state(user_id)

        # Очищаем prompt если он есть
        pid = pending_prompt.pop(user_id, None)
        if pid:
            try:
                await client.delete_messages(user_id, pid, revoke=True)
            except Exception:
                pass

        if state == STATE_LOGBOOK_NEW:
            user_states.clear_state(user_id)
            with sqlite3.connect(DB) as db:
                db.execute(
                    "INSERT INTO logbook(author_id, author_name, text) VALUES (?,?,?)",
                    (user_id, name, text),
                )
            await msg.reply("✅ Запись добавлена", reply_markup=_build_list())
            return

        elif state == STATE_LOGBOOK_EDIT:
            rid = user_states.get_data(user_id)
            user_states.clear_state(user_id)
            if rid:
                with sqlite3.connect(DB) as db:
                    db.execute(
                        "UPDATE logbook SET text=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                        (text, rid),
                    )
                await msg.reply("✏️ Запись обновлена", reply_markup=_build_list())
            return
