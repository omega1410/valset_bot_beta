from __future__ import annotations
import os, sqlite3, textwrap, functools, numpy as np
from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
)

# Заменяем импорт Gemini на вызовы Yandex GPT через requests
import requests  # Импортируем requests
from config import ADMIN_IDS
from utils.ai_state import ai_state

DB_PATH = "data.db"
CHUNK_SIZE = 1500  # символов
TOP_K = 15  # сколько кусков отдаём в контекст

# ─────── 0. Инициализация Yandex GPT и Embeddings ───────
# Необходимо установить переменные окружения YANDEX_API_KEY, YANDEX_FOLDER_ID
# (или использовать IAM токен, как показано в следующем блоке)
# Убедитесь, что у вас установлен пакет requests: pip install requests

API_KEY = os.getenv("YANDEX_API_KEY")  # Убедитесь, что переменная установлена
FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")  # Убедитесь, что переменная установлена

# Устанавливаем переменные для аутентификации (один из вариантов)
auth_token = API_KEY  # используем API Key
if not auth_token:
    raise ValueError("Необходимо установить YANDEX_API_KEY")
if not FOLDER_ID:
    raise ValueError("Необходимо установить YANDEX_FOLDER_ID")


# Функция для вызова генерации текста (Yandex GPT) через REST API
# Функция для вызова генерации текста (Yandex GPT) через REST API
def call_yandex_gpt_generate(messages, model_uri):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {auth_token}",
        # "Authorization": f"Bearer {IAM_TOKEN}", # Используйте этот заголовок, если используете IAM токен
    }
    payload = {
        "modelUri": model_uri,
        "completionOptions": {
            "stream": False,  # Не используем потоковую передачу
            "temperature": 0.1,  # Настройте по необходимости
            "maxTokens": "2000",  # Настройте по необходимости
        },
        "messages": [
            {
                "role": "user",
                "text": messages,  # Передаем весь промпт как текст сообщения пользователя
            }
        ],
    }

    # Указываем пустой словарь прокси
    proxies = {}

    try:
        response = requests.post(url, headers=headers, json=payload, proxies=proxies)
        response.raise_for_status()  # Возбуждает исключение для кодов ошибок HTTP
        data = response.json()
        # print(f"Debug: Full API response: {data}") # Для отладки
        # Путь к тексту ответа может отличаться, проверьте структуру ответа API
        # Обычно находится в data['result']['alternatives'][0]['message']['text']
        # или data['alternatives'][0]['text']
        # Пример структуры: {"result": {"alternatives": [{"message": {"role": "assistant", "text": "Ответ модели"}, "modelVersion": "..."}], "usage": {...}}}
        # Или: {"alternatives": [{"text": "Ответ модели", "stop_reason": "..."}], "usage": {...}}
        # Попробуем стандартный путь:
        alternatives = data.get("result", {}).get("alternatives", []) or data.get(
            "alternatives", []
        )
        if alternatives:
            # Берем первый альтернативный ответ
            first_alt = alternatives[0]
            # Извлекаем текст из 'message' или напрямую из 'text'
            text_response = first_alt.get("message", {}).get("text") or first_alt.get(
                "text"
            )
            if text_response:
                return text_response.strip()
            else:
                print(f"Warning: Could not find 'text' in alternative: {first_alt}")
                return "Не удалось получить ответ от модели (ошибка структуры)."
        else:
            print(f"Warning: No alternatives found in API response: {data}")
            return "Не удалось получить ответ от модели (нет альтернатив)."
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e.response.status_code}, {e.response.text}")
        # Возвращаем сообщение об ошибке или вызываем исключение
        error_detail = (
            e.response.json().get("error", {}).get("message", "Неизвестная ошибка HTTP")
        )
        return f"Ошибка при обращении к Yandex GPT: {error_detail}"
    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")
        # Возвращаем сообщение об ошибке или вызываем исключение
        return f"Ошибка при обращении к Yandex GPT: {str(e)}"
    except Exception as e:
        print(f"General Error during API call: {e}")
        return f"Ошибка при обращении к Yandex GPT: {str(e)}"


# Функция для вызова генерации эмбеддингов (Yandex Embeddings) через REST API
def call_yandex_embeddings(text):
    # --- Добавляем проверки ---
    if not text or not text.strip():
        print(
            f"Warning: Empty or whitespace-only text provided for embedding: '{text}'"
        )
        # Возвращаем нулевой вектор или вызываем ошибку, в зависимости от логики вашей системы
        # В данном случае, можно вернуть вектор нулей подходящей размерности, например, 1024 для yandex embedding
        # Или бросить исключение, чтобы пропустить этот чанк
        # Пока бросим исключение, чтобы было видно в логах
        raise ValueError("Текст для эмбеддинга пуст или содержит только пробелы")
    # Проверка максимальной длины (примерный лимит, уточните в документации Yandex)
    max_length = 2048  # Установим лимит, например, 2048 символов
    if len(text) > max_length:
        print(
            f"Warning: Text length ({len(text)}) exceeds max length ({max_length}) for embedding. Truncating."
        )
        text = text[:max_length]  # Обрезаем до лимита

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/textEmbedding"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {auth_token}",
        # "Authorization": f"Bearer {IAM_TOKEN}", # Используйте этот заголовок, если используете IAM токен
    }
    # Убедитесь, что FOLDER_ID подставляется правильно
    model_uri = f"emb://{FOLDER_ID}/text-search-document/latest"
    if not FOLDER_ID or "{FOLDER_ID}" in model_uri:  # Простая проверка подстановки
        print(
            f"Error: FOLDER_ID is not set or is invalid. Current value: '{FOLDER_ID}'. Model URI would be: '{model_uri}'"
        )
        raise ValueError("FOLDER_ID is not configured correctly.")
    payload = {"modelUri": model_uri, "text": text}  # Используем переменную model_uri

    proxies = {}  # Убедитесь, что прокси отключен

    try:
        # print(f"Debug: Calling embedding API with payload: {payload}") # Для отладки, можно включить временно
        response = requests.post(url, headers=headers, json=payload, proxies=proxies)
        # print(f"Debug: Raw response status: {response.status_code}") # Для отладки
        # print(f"Debug: Raw response text: {response.text}") # Для отладки
        response.raise_for_status()  # Возбуждает исключение для кодов ошибок HTTP
        data = response.json()
        # print(f"Debug: Embedding API response: {data}") # Для отладки
        # Путь к вектору: data['embedding']['values']
        embedding_values = data.get("embedding", {}).get("values")
        if embedding_values and isinstance(embedding_values, list):
            # print(f"Debug: Embedding vector (first 5 values): {embedding_values[:5]}...") # Для отладки
            return np.asarray(embedding_values, dtype="float32")
        else:
            print(f"Warning: Could not find embedding values in API response: {data}")
            raise ValueError(
                "Не удалось получить вектор эмбеддинга из API (поле 'embedding.values' отсутствует или пусто)"
            )
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error for Embedding: {e.response.status_code}")
        print(f"Response Body: {e.response.text}")  # Вывод тела ответа ошибки
        raise e
    except requests.exceptions.RequestException as e:
        print(f"Request Error for Embedding: {e}")
        raise e
    except Exception as e:
        print(f"General Error during Embedding API call: {e}")
        raise e


# Модель для генерации (Yandex GPT)
CHAT_MODEL_URI = f"gpt://{FOLDER_ID}/yandexgpt/latest"  # Или другая модель, например, /summarization/latest
# Также можно использовать:
# f"gpt://{FOLDER_ID}/yandexgpt-lite/latest" для более быстрой и дешевой модели
# f"gpt://{FOLDER_ID}/prologue/latest" для диалоговых моделей (требует немного другой структуры сообщений)


# --- Остальная часть вашего кода остается без изменений ---
# (Все функции ниже остаются как есть, кроме embed и generate_answer)


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
    """Начать сессию AI для пользователя"""
    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO ai_sessions (user_id, active) VALUES (?, 1)",
            (user_id,),
        )
        conn.commit()


def end_ai_session(user_id: int):
    """Завершить сессию AI для пользователя"""
    with db() as conn:
        conn.execute("UPDATE ai_sessions SET active = 0 WHERE user_id = ?", (user_id,))
        conn.commit()


def is_ai_session_active(user_id: int) -> bool:
    """Проверить, активна ли сессия AI для пользователя"""
    with db() as conn:
        result = conn.execute(
            "SELECT active FROM ai_sessions WHERE user_id = ? AND active = 1",
            (user_id,),
        ).fetchone()
        return result is not None


# ─────── 3. Утилиты ───────
def embed(text: str) -> np.ndarray:
    """Вернуть эмбеддинг (float32[768]) для куска текста."""
    # Заменяем вызов Gemini на Yandex через requests
    return call_yandex_embeddings(text)
    # res = genai.embed_content(
    #     model="models/embedding-001", content=text, task_type="retrieval_document"
    # )
    # return np.asarray(res["embedding"], dtype="float32")


def chunk_text(text: str) -> list[str]:
    return textwrap.wrap(text, CHUNK_SIZE)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


# ─────── 4. Индексация разделов ───────
def full_reindex():
    """Полностью пересоздать таблицу эмбеддингов (админ-команда)."""
    with db() as conn:
        conn.execute("DELETE FROM ai_chunks")

        rows = conn.execute("SELECT id, title, content FROM sections").fetchall()
        for sid, title, content in rows:
            text = f"{title}\n{content}"
            for chunk in chunk_text(text):
                vec = embed(chunk).tobytes()  # Вызов embed теперь использует Yandex
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
                (
                    sid,
                    chunk,
                    embed(chunk).tobytes(),
                ),  # Вызов embed теперь использует Yandex
            )
        conn.commit()


# ─────── 5. Поиск ───────
def retrieve_chunks(question: str, k: int = TOP_K) -> list[str]:
    q_vec = embed(question)  # Вызов embed теперь использует Yandex
    with db() as conn:
        # многое хранится – читаем построчно
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
    # Заменяем вызов Gemini на Yandex GPT через requests
    try:
        # print(f"Debug: Prompt sent to Yandex GPT: {repr(prompt)}") # Для отладки
        resp_text = call_yandex_gpt_generate(prompt, CHAT_MODEL_URI)
        # print(f"Debug: Raw response from Yandex GPT: {repr(resp_text)}") # Для отладки
        return resp_text
    except Exception as e:
        print(f"Error generating answer with Yandex GPT: {e}")
        return "Извините, возникла ошибка при генерации ответа. Пожалуйста, попробуйте позже."


# ─────── 7. Pyrogram-хендлеры ───────
def register_ai_handlers(app: Client):

    # Инициализация таблицы сессий
    init_ai_sessions_table()

    # КНОПКА в меню ➜ callback «start_ai»
    @app.on_callback_query(filters.regex("^start_ai$"), group=20)
    async def start_ai(_, cq: CallbackQuery):
        uid = cq.from_user.id
        start_ai_session(uid)  # Активируем сессию
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

    # Кнопка завершения диалога
    @app.on_callback_query(filters.regex("^stop_ai$"), group=20)
    async def stop_ai(_, cq: CallbackQuery):
        uid = cq.from_user.id
        end_ai_session(uid)  # Завершаем сессию
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

    # Обычное текст-сообщение от пользователя с активной AI сессией
    @app.on_message(
        filters.text
        & filters.private
        & filters.create(lambda _, __, m: is_ai_session_active(m.from_user.id)),
        group=21,
    )
    async def handle_ai_question(_, msg: Message):
        uid = msg.from_user.id

        # Если пользователь хочет выйти
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
        thinking_msg = await msg.reply("⏳ Думаю…")  # ← индикатор

        try:
            answer = generate_answer(question)
        finally:
            try:
                await thinking_msg.delete()  # ← удаляем
            except Exception:
                pass

        # Отправляем ответ и предлагаем продолжить диалог
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

    # /reindex_ai  (только для админов)
    @app.on_message(filters.command("reindex_ai") & filters.private, group=15)
    async def reindex_cmd(_, m: Message):
        if m.from_user.id not in ADMIN_IDS:
            await m.reply("⛔️ Нет доступа")
            return
        await m.reply("🔄 Пересчитываю эмбеддинги (это может занять время)...")
        full_reindex()
        await m.reply("✅ Готово!")
