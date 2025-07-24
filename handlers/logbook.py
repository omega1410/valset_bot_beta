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
from zoneinfo import ZoneInfo  # Py 3.9+
from config import LOCAL_TZ

# -------- настройка ----------------------------------------------------------
DB = "data.db"
logger = logging.getLogger(__name__)

awaiting_new = {}  # user_id -> True
awaiting_edit = {}  # user_id -> record_id
pending_prompt = {}  # user_id -> message_id  ← новый

# Импортируем главное меню, чтобы уметь возвращаться назад
from utils.menu import get_main_menu  # <-- укажи, где у тебя лежит функция


def utc_to_local(ts: str) -> str:
    # ts из БД: "2024-06-16 21:24:00"
    dt_utc = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
    return dt_utc.astimezone(LOCAL_TZ).strftime("%d.%m.%Y %H:%M")


# -------- БД -----------------------------------------------------------------
def _init_table():
    with sqlite3.connect(DB) as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS logbook (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                author_id   INTEGER,
                author_name TEXT,
                text        TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'open',   -- open / done
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );"""
        )


# -------- клавиатуры ---------------------------------------------------------
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
            row.append(InlineKeyboardButton("✅", callback_data=f"done:{rid}"))
        row.extend(
            (
                InlineKeyboardButton("✏️", callback_data=f"edit:{rid}"),
                InlineKeyboardButton("❌", callback_data=f"del:{rid}"),
            )
        )
        buttons.append(row)

    # Последняя строка: ➕ + 🔙
    buttons.append(
        [
            InlineKeyboardButton("➕  Добавить запись", callback_data="add"),
            InlineKeyboardButton("🔙  Назад", callback_data="back_main"),
        ]
    )
    return InlineKeyboardMarkup(buttons)


def _back_to_main(cq: CallbackQuery):
    """Возврат к главному меню"""
    text, kb = get_main_menu()
    return cq.message.edit_text(text, reply_markup=kb)


# -------- регистрация обработчиков ------------------------------------------
def register_logbook(app: Client):

    _init_table()

    # ── открыть логбук ───────────────────────────────────────────────────────
    @app.on_callback_query(filters.regex("^open_logbook$"), group=3)
    async def cb_open(_, cq: CallbackQuery):
        await cq.message.edit_text("📔 Логбук:", reply_markup=_build_list())
        await cq.answer()

    # ── кнопка «Назад» из списка ─────────────────────────────────────────────
    @app.on_callback_query(filters.regex("^back_main$"), group=3)
    async def cb_back_main(_, cq: CallbackQuery):
        await _back_to_main(cq)
        await cq.answer()

    # ── роутер действий с записями ───────────────────────────────────────────
    @app.on_callback_query(filters.regex("^(add|view|edit|del|done):?"), group=3)
    async def cb_router(_, cq: CallbackQuery):
        action, *param = cq.data.split(":")
        uid = cq.from_user.id
        name = cq.from_user.first_name or "Anon"

        # ---------- ADD ----------
        if action == "add":
            awaiting_new[uid] = True
            await cq.message.delete()  # убираем список
            prompt = await cq.message._client.send_message(  # показываем промпт
                uid, "✍️ Введите текст новой записи.\n\nДля отмены — /cancel"
            )
            pending_prompt[uid] = prompt.id  # запоминаем id
            await cq.answer()
            return

        rid = int(param[0])

        # ---------- VIEW ----------
        # ---------- VIEW ----------
        if action == "view":
            with sqlite3.connect(DB) as db:
                row = db.execute(
                    "SELECT text, status, author_name, created_at "
                    "FROM logbook WHERE id=?",
                    (rid,),
                ).fetchone()
                txt, st, author, dt = row
                dt = utc_to_local(dt)

            if not row:
                await cq.answer("Запись не найдена", True)
                return

            txt, st, author, dt = row
            icon = "✅" if st == "done" else "🟢"

            # 1) удаляем сообщение-список
            await cq.message.delete()

            # 2) отправляем карточку записи с кнопкой «Назад»
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

        # ---------- DELETE ----------
        if action == "del":
            with sqlite3.connect(DB) as db:
                db.execute("DELETE FROM logbook WHERE id=?", (rid,))
            await cq.message.edit_reply_markup(_build_list())
            await cq.answer("Удалено")
            return

        # ---------- DONE ----------
        if action == "done":
            with sqlite3.connect(DB) as db:
                db.execute(
                    "UPDATE logbook SET status='done', "
                    "updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (rid,),
                )
            await cq.message.edit_reply_markup(_build_list())
            await cq.answer("Завершено ✅")
            return

        # ---------- EDIT ----------
        if action == "edit":
            awaiting_edit[uid] = rid
            await cq.message.delete()
            prompt = await cq.message._client.send_message(
                uid, "📝 Пришлите новый текст для записи.\n\nДля отмены — /cancel"
            )
            pending_prompt[uid] = prompt.id
            await cq.answer()
            return

    @app.on_message(filters.command("cancel") & filters.private, group=3)
    async def cmd_cancel(client, msg: Message):
        uid = msg.from_user.id
        was = awaiting_new.pop(uid, None) or awaiting_edit.pop(uid, None)

        # удалить промпт, если был
        pid = pending_prompt.pop(uid, None)
        if pid:
            await client.delete_messages(uid, pid, revoke=True)

        kb_back = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔙  Назад к логбуку", callback_data="open_logbook"
                    )
                ]
            ]
        )

        if was:
            await msg.reply("❌ Действие отменено.", reply_markup=kb_back)
        else:
            await msg.reply("Нечего отменять 🤷‍♂️", reply_markup=kb_back)

        # чтобы этот апдейт не схватил catch_text
        msg.stop_propagation()

    # ── приём текста (новая / редакт) ────────────────────────────────────────

    # ── приём текста (новая запись / редакт) ──────────────────────────────────
    @app.on_message(filters.text & filters.private, group=4)
    async def catch_text(client, msg: Message):
        uid = msg.from_user.id  # ← сначала определяем uid
        text = msg.text.strip()
        name = (
            (msg.from_user.first_name or "") + " " + (msg.from_user.last_name or "")
        ).strip() or "Anon"

        # убрать промпт, если был
        pid = pending_prompt.pop(uid, None)
        if pid:
            await client.delete_messages(uid, pid, revoke=True)

        # --- новая запись ---
        if awaiting_new.pop(uid, None):
            with sqlite3.connect(DB) as db:
                db.execute(
                    "INSERT INTO logbook(author_id, author_name, text) VALUES (?,?,?)",
                    (uid, name, text),
                )
            await msg.reply("✅ Запись добавлена", reply_markup=_build_list())
            return

        # --- редактирование ---
        rid = awaiting_edit.pop(uid, None)
        if rid:
            with sqlite3.connect(DB) as db:
                db.execute(
                    "UPDATE logbook SET text=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (text, rid),
                )
            await msg.reply("✏️ Запись обновлена", reply_markup=_build_list())
