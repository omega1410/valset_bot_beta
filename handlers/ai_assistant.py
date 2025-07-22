from __future__ import annotations
import os, sqlite3, textwrap, functools, numpy as np
from pyrogram import Client, filters
from pyrogram.types import Message
import google.generativeai as genai
from config import ADMIN_IDS  # чтобы ограничить /reindex_ai

DB_PATH = "data.db"
CHUNK_SIZE = 1500  # символов
TOP_K = 15  # сколько кусков отдаём в контекст

# ─────── 0. Инициализация Gemini ───────
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
CHAT_MODEL = genai.GenerativeModel("models/gemini-1.5-flash-latest")


# ─────── 1. База данных ───────
def db() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_vector_table():
    with db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS ai_chunks(
                   id          INTEGER PRIMARY KEY AUTOINCREMENT,
                   section_id  INTEGER,
                   chunk       TEXT,
                   vector      BLOB
               )"""
        )


# ─────── 2. Утилиты ───────
def embed(text: str) -> np.ndarray:
    """Вернуть эмбеддинг (float32[768]) для куска текста."""
    res = genai.embed_content(
        model="models/embedding-001", content=text, task_type="retrieval_document"
    )
    return np.asarray(res["embedding"], dtype="float32")


def chunk_text(text: str) -> list[str]:
    return textwrap.wrap(text, CHUNK_SIZE)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


# ─────── 3. Индексация разделов ───────
def full_reindex():
    """Полностью пересоздать таблицу эмбеддингов (админ-команда)."""
    with db() as conn:
        conn.execute("DELETE FROM ai_chunks")

        rows = conn.execute("SELECT id, title, content FROM sections").fetchall()
        for sid, title, content in rows:
            text = f"{title}\n{content}"
            for chunk in chunk_text(text):
                vec = embed(chunk).tobytes()
                conn.execute(
                    "INSERT INTO ai_chunks(section_id, chunk, vector) VALUES(?,?,?)",
                    (sid, chunk, vec),
                )
        conn.commit()


def upsert_section(sid: int, title: str, content: str):
    """Обновить эмбеддинги одного раздела (вызывайте из /add_section + /edit_section)."""
    with db() as conn:
        conn.execute("DELETE FROM ai_chunks WHERE section_id=?", (sid,))
        for chunk in chunk_text(f"{title}\n{content}"):
            conn.execute(
                "INSERT INTO ai_chunks(section_id, chunk, vector) VALUES(?,?,?)",
                (sid, chunk, embed(chunk).tobytes()),
            )
        conn.commit()


# ─────── 4. Поиск ───────
def retrieve_chunks(question: str, k: int = TOP_K) -> list[str]:
    q_vec = embed(question)
    with db() as conn:
        # многое хранится – читаем построчно
        scored: list[tuple[float, str]] = []
        for chunk, vec_blob in conn.execute("SELECT chunk, vector FROM ai_chunks"):
            v = np.frombuffer(vec_blob, dtype="float32")
            scored.append((cosine(q_vec, v), chunk))

    scored.sort(reverse=True)
    return [c for _, c in scored[:k]]


# ─────── 5. Генерация ответа ───────
def generate_answer(question: str) -> str:
    ctx = "\n\n".join(retrieve_chunks(question))
    prompt = f"""Ты — ассистент сотрудников стойки регистрации.
Отвечай строго на основе КОНТЕКСТА. 
Если информации недостаточно — ответь "Не знаю".

=== КОНТЕКСТ ===
{ctx}

=== ВОПРОС ===
{question}

=== ОТВЕТ (на русском) ==="""
    resp = CHAT_MODEL.generate_content(prompt)
    return resp.text.strip()


# ─────── 6. Pyrogram-хендлеры ───────
def register_ai_handlers(app: Client):

    # /ask_ai <вопрос>
    @app.on_message(filters.command("ask_ai") & filters.private, group=15)
    async def ask_ai_cmd(_, m: Message):
        if len(m.command) == 1:
            await m.reply("Использование:  /ask_ai <вопрос>")
            return

        question = " ".join(m.command[1:])
        await m.reply("⏳ Думаю...")
        answer = generate_answer(question)
        await m.reply(answer)

    # /reindex_ai  (только для админов)
    @app.on_message(filters.command("reindex_ai") & filters.private, group=15)
    async def reindex_cmd(_, m: Message):
        if m.from_user.id not in ADMIN_IDS:
            await m.reply("⛔️ Нет доступа")
            return
        await m.reply("🔄 Пересчитываю эмбеддинги (это может занять время)...")
        full_reindex()
        await m.reply("✅ Готово!")
