from __future__ import annotations
import os, sqlite3, textwrap, functools, numpy as np
from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
)

from yandex.cloud.ai.foundation_models.v1.text_generation.text_generation_service_pb2_grpc import (
    TextGenerationServiceStub,
)
from yandex.cloud.ai.foundation_models.v1.text_generation.text_generation_service_pb2 import (
    TextGenerationRequest,
)
from yandex.cloud.ai.foundation_models.v1.text_generation import token as token_pb
from yandex.cloud.ai.foundation_models.v1 import text_generation_model_spec_pb2
from yandex.cloud.ai.foundation_models.v1.text_embedding import (
    text_embedding_service_pb2_grpc,
    text_embedding_service_pb2,
)
from yandex.cloud.ai.foundation_models.v1.text_embedding.text_embedding_model_spec_pb2 import (
    TextEmbeddingModelSpec,
)
from yandex.cloud.ai.foundation_models.v1.text_embedding.text_embedding_model_spec_pb2 import (
    TextEmbeddingModelSpec as EmbeddingSpec,
)
import grpc
from config import ADMIN_IDS
from utils.ai_state import ai_state

DB_PATH = "data.db"
CHUNK_SIZE = 1500  # символов
TOP_K = 15  # сколько кусков отдаём в контекст

API_KEY = os.getenv("YANDEX_API_KEY")
FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")


auth_token = API_KEY
if not auth_token:
    raise ValueError("Необходимо установить YANDEX_API_KEY или YANDEX_IAM_TOKEN")
if not FOLDER_ID:
    raise ValueError("Необходимо установить YANDEX_FOLDER_ID")


def call_yandex_gpt_generate(messages, model_uri):
    channel = grpc.insecure_channel(
        "ai.api.cloud.yandex.net:443",
        options=(("grpc.ssl_target_name_override", "ai.api.cloud.yandex.net"),),
    )
    call_credentials = grpc.access_token_call_credentials(auth_token)
    channel_credentials = grpc.ssl_channel_credentials()
    secure_channel = grpc.composite_channel_credentials(
        channel_credentials, call_credentials
    )
    stub = TextGenerationServiceStub(
        grpc.secure_channel("ai.api.cloud.yandex.net:443", secure_channel)
    )

    request = TextGenerationRequest(
        model_uri=model_uri,
        partial_results=True,
        temperature=0.1,
        text_generation_options=text_generation_model_spec_pb2.TextGenerationOptions(
            temperature=0.1,
        ),
        text=messages,
    )

    try:
        response = stub.Generate(request)
        if response.partial_results:
            return response.partial_results[0].text
        else:
            if hasattr(response, "alternatives") and response.alternatives:
                return response.alternatives[0].text
            else:
                print(
                    f"Warning: No partial_results or alternatives found in response: {response}"
                )
                return "Не удалось получить ответ от модели."
    except grpc.RpcError as e:
        print(f"GRPC Error: {e.code()}, {e.details()}")
        raise e
    except Exception as e:
        print(f"General Error: {e}")
        raise e
    finally:
        channel.close()


def call_yandex_embeddings(text):
    channel = grpc.insecure_channel(
        "embeddings.api.cloud.yandex.net:443",
        options=(("grpc.ssl_target_name_override", "embeddings.api.cloud.yandex.net"),),
    )
    call_credentials = grpc.access_token_call_credentials(auth_token)
    channel_credentials = grpc.ssl_channel_credentials()
    secure_channel = grpc.composite_channel_credentials(
        channel_credentials, call_credentials
    )
    stub = text_embedding_service_pb2_grpc.TextEmbeddingServiceStub(
        grpc.secure_channel("embeddings.api.cloud.yandex.net:443", secure_channel)
    )

    request = text_embedding_service_pb2.TextEmbeddingRequest(
        model_uri=f"emb://{FOLDER_ID}/text-search-document/latest",
        text=text,
    )

    try:
        response = stub.Embed(request)
        return np.asarray(response.embedding.values, dtype="float32")
    except grpc.RpcError as e:
        print(f"GRPC Embedding Error: {e.code()}, {e.details()}")
        raise e
    except Exception as e:
        print(f"General Embedding Error: {e}")
        raise e
    finally:
        channel.close()


CHAT_MODEL_URI = f"gpt://{FOLDER_ID}/yandexgpt/latest"


# ─────── 1. База данных для хранения состояния диалога ───────
def init_ai_sessions_table():
    with db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS ai_sessions(
                   user_id     INTEGER PRIMARY KEY,
                   active      BOOLEAN DEFAULT 1,
                   created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
               )"""
        )


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


# ─────── 2. Управление сессиями AI ───────
def start_ai_session(user_id: int):
    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO ai_sessions (user_id, active) VALUES (?, 1)",
            (user_id,),
        )
        conn.commit()


def end_ai_session(user_id: int):
    with db() as conn:
        conn.execute("UPDATE ai_sessions SET active = 0 WHERE user_id = ?", (user_id,))
        conn.commit()


def is_ai_session_active(user_id: int) -> bool:
    with db() as conn:
        result = conn.execute(
            "SELECT active FROM ai_sessions WHERE user_id = ? AND active = 1",
            (user_id,),
        ).fetchone()
        return result is not None


# ─────── 3. Утилиты ───────
def embed(text: str) -> np.ndarray:
    return call_yandex_embeddings(text)


def chunk_text(text: str) -> list[str]:
    return textwrap.wrap(text, CHUNK_SIZE)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


# ─────── 4. Индексация разделов ───────
def full_reindex():
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
    with db() as conn:
        conn.execute("DELETE FROM ai_chunks WHERE section_id=?", (sid,))
        for chunk in chunk_text(f"{title}\n{content}"):
            conn.execute(
                "INSERT INTO ai_chunks(section_id, chunk, vector) VALUES(?,?,?)",
                (
                    sid,
                    chunk,
                    embed(chunk).tobytes(),
                ),
            )
        conn.commit()


# ─────── 5. Поиск ───────
def retrieve_chunks(question: str, k: int = TOP_K) -> list[str]:
    q_vec = embed(question)
    with db() as conn:
        scored: list[tuple[float, str]] = []
        for chunk, vec_blob in conn.execute("SELECT chunk, vector FROM ai_chunks"):
            v = np.frombuffer(vec_blob, dtype="float32")
            scored.append((cosine(q_vec, v), chunk))

    scored.sort(reverse=True)
    return [c for _, c in scored[:k]]


# ─────── 6. Генерация ответа ───────
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
    try:
        resp_text = call_yandex_gpt_generate(prompt, CHAT_MODEL_URI)
        return resp_text.strip()
    except Exception as e:
        print(f"Error generating answer with Yandex GPT: {e}")
        return "Извините, возникла ошибка при генерации ответа. Пожалуйста, попробуйте позже."


# ─────── 7. Pyrogram-хендлеры ───────
def register_ai_handlers(app: Client):

    init_ai_sessions_table()

    @app.on_callback_query(filters.regex("^start_ai$"), group=20)
    async def start_ai(_, cq: CallbackQuery):
        uid = cq.from_user.id
        start_ai_session(uid)
        await cq.message.edit_text(
            "🤖 AI-помощник активен! Введите ваш вопрос.\n"
            "Для выхода из режима AI нажмите кнопку 'Завершить диалог'.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⏹ Завершить диалог", callback_data="stop_ai"
                        )
                    ],
                    [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
                ]
            ),
        )
        await cq.answer()

    @app.on_callback_query(filters.regex("^stop_ai$"), group=20)
    async def stop_ai(_, cq: CallbackQuery):
        uid = cq.from_user.id
        end_ai_session(uid)
        await cq.message.edit_text(
            "✅ Диалог с AI-помощником завершен.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🤖 AI-помощник", callback_data="start_ai")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
                ]
            ),
        )
        await cq.answer()

    @app.on_message(
        filters.text
        & filters.private
        & filters.create(lambda _, __, m: is_ai_session_active(m.from_user.id)),
        group=21,
    )
    async def handle_ai_question(_, msg: Message):
        uid = msg.from_user.id

        if msg.text.strip().lower() in ["/stop", "/exit", "стоп", "выход"]:
            end_ai_session(uid)
            await msg.reply(
                "✅ Диалог с AI-помощником завершен.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🤖 AI-помощник", callback_data="start_ai"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "🔙 Назад", callback_data="back_to_main"
                            )
                        ],
                    ]
                ),
            )
            return

        question = msg.text.strip()
        thinking_msg = await msg.reply("⏳ Думаю…")

        try:
            answer = generate_answer(question)
        finally:
            try:
                await thinking_msg.delete()
            except Exception:
                pass

        await msg.reply(
            answer,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⏹ Завершить диалог", callback_data="stop_ai"
                        )
                    ],
                    [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
                ]
            ),
        )

    @app.on_message(filters.command("reindex_ai") & filters.private, group=15)
    async def reindex_cmd(_, m: Message):
        if m.from_user.id not in ADMIN_IDS:
            await m.reply("⛔️ Нет доступа")
            return
        await m.reply("🔄 Пересчитываю эмбеддинги (это может занять время)...")
        full_reindex()
        await m.reply("✅ Готово!")
