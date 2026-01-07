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
        raise ValueError("Текст для эмбеддинга пуст или содержит только пробелы")

    max_length = 2048
    if len(text) > max_length:
        print(
            f"Warning: Text length ({len(text)}) exceeds max length ({max_length}) for embedding. Truncating."
        )
        text = text[:max_length]

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/textEmbedding"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {auth_token}",
    }

    # ДЛЯ ОТЛАДКИ: Показываем что отправляем
    print(f"DEBUG call_yandex_embeddings: FOLDER_ID = {FOLDER_ID}")

    # Пробуем text-search-query (для поисковых запросов)
    model_uri = f"emb://{FOLDER_ID}/text-search-query/latest"
    payload = {"modelUri": model_uri, "text": text}

    print(f"DEBUG: Sending to {url}")
    print(f"DEBUG: Model URI: {model_uri}")
    print(f"DEBUG: Text sample: {text[:100]}...")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        print(f"DEBUG: Response status: {response.status_code}")
        print(f"DEBUG: Response headers: {response.headers}")

        # Сначала посмотрим сырой ответ
        raw_response = response.text
        print(f"DEBUG: Raw response (first 500 chars): {raw_response[:500]}")

        response.raise_for_status()
        data = response.json()

        # ВАЖНОЕ ИСПРАВЛЕНИЕ: Yandex API возвращает данные в неожиданном формате
        print(
            f"DEBUG: Parsed JSON type: {type(data)}, content keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}"
        )

        # Обрабатываем разные форматы ответа
        embedding_values = None

        # Вариант 1: data уже содержит embedding как список напрямую
        if isinstance(data, list):
            print(f"DEBUG: Response is a list with {len(data)} elements")
            if len(data) > 0 and isinstance(data[0], dict):
                # Может быть [{"embedding": {...}}] или [{"values": [...]}]
                first_item = data[0]
                if "embedding" in first_item:
                    embedding_data = first_item["embedding"]
                elif "values" in first_item:
                    embedding_data = {"values": first_item["values"]}
                else:
                    embedding_data = first_item

                if isinstance(embedding_data, dict):
                    embedding_values = embedding_data.get("values")
                elif isinstance(embedding_data, list):
                    embedding_values = embedding_data
            else:
                # Возможно, data уже список значений
                embedding_values = data

        # Вариант 2: data - словарь с embedding
        elif isinstance(data, dict):
            print(f"DEBUG: Response is a dict with keys: {data.keys()}")

            # Прямой доступ к values
            if "values" in data:
                embedding_values = data["values"]
            # Или через embedding
            elif "embedding" in data:
                embedding = data["embedding"]
                if isinstance(embedding, dict):
                    embedding_values = embedding.get("values")
                elif isinstance(embedding, list):
                    embedding_values = embedding

        # Проверяем, что получили значения
        if embedding_values and isinstance(embedding_values, list):
            print(
                f"DEBUG: Success! Got embedding vector with {len(embedding_values)} dimensions"
            )
            print(f"DEBUG: First 5 values: {embedding_values[:5]}")
            return np.asarray(embedding_values, dtype="float32")
        else:
            print(
                f"ERROR: Could not extract embedding values. Full response structure:"
            )
            print(f"Full data: {data}")

            # Попробуем пройти по структуре рекурсивно
            def find_values(obj, path=""):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if k == "values" and isinstance(v, list):
                            print(f"Found 'values' at path: {path}.{k}")
                            return v
                        elif isinstance(v, (dict, list)):
                            result = find_values(v, f"{path}.{k}")
                            if result:
                                return result
                elif isinstance(obj, list) and len(obj) > 0:
                    for i, item in enumerate(obj):
                        if isinstance(item, (dict, list)):
                            result = find_values(item, f"{path}[{i}]")
                            if result:
                                return result
                return None

            found_values = find_values(data, "root")
            if found_values:
                print(
                    f"DEBUG: Found values recursively: {len(found_values)} dimensions"
                )
                return np.asarray(found_values, dtype="float32")

            raise ValueError(
                f"Не удалось получить вектор эмбеддинга. Структура ответа: {data}"
            )

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error {e.response.status_code} for Embedding API")
        print(f"Request URL: {url}")
        print(f"Request payload: {payload}")
        print(f"Response body: {e.response.text[:500]}")

        # Попробуем с другим model_uri
        print("Trying with text-search-document model...")
        try:
            alt_payload = payload.copy()
            alt_payload["modelUri"] = f"emb://{FOLDER_ID}/text-search-document/latest"
            print(f"DEBUG: Alternative payload: {alt_payload}")

            alt_response = requests.post(
                url, headers=headers, json=alt_payload, timeout=30
            )
            alt_response.raise_for_status()
            alt_data = alt_response.json()

            print(f"DEBUG: Alternative response: {alt_data}")

            # Простая логика: если это список, берем первый элемент
            if isinstance(alt_data, list) and len(alt_data) > 0:
                alt_data = alt_data[0]

            # Прямой доступ к значениям
            if isinstance(alt_data, dict) and "embedding" in alt_data:
                embedding = alt_data["embedding"]
                if isinstance(embedding, dict):
                    values = embedding.get("values")
                elif isinstance(embedding, list):
                    values = embedding

                if values and isinstance(values, list):
                    return np.asarray(values, dtype="float32")

        except Exception as alt_e:
            print(f"Alternative model also failed: {alt_e}")

        raise e
    except Exception as e:
        print(f"General Error during Embedding API call: {e}")
        print(f"Request was to: {url}")
        print(f"Payload was: {payload}")
        raise e


# Модель для генерации (Yandex GPT)
CHAT_MODEL_URI = f"gpt://{FOLDER_ID}/yandexgpt-4-lite/latest"  # Или другая модель, например, /summarization/latest
# Также можно использовать:
# f"gpt://{FOLDER_ID}/yandexgpt-lite/latest" для более быстрой и дешевой модели
# f"gpt://{FOLDER_ID}/prologue/latest" для диалоговых моделей (требует немного другой структуры сообщений)


# --- Остальная часть вашего кода остается без изменений ---
# (Все функции ниже остаются как есть, кроме embed и generate_answer)


# ─────── 1. База данных для хранения состояния диалога ───────
def init_ai_sessions_table():
    with db() as conn:
        # Создаем таблицу если её нет
        conn.execute(
            """CREATE TABLE IF NOT EXISTS ai_sessions(
                   user_id     INTEGER PRIMARY KEY,
                   active      BOOLEAN DEFAULT 1,
                   mode        TEXT DEFAULT 'rag',
                   created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
               )"""
        )
        
        # Добавляем колонку mode если её нет
        try:
            conn.execute("ALTER TABLE ai_sessions ADD COLUMN mode TEXT DEFAULT 'rag'")
        except sqlite3.OperationalError:
            # Колонка уже существует - это нормально
            pass
        conn.commit()

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
def start_ai_session(user_id: int, mode: str = "rag"):
    """Начать сессию AI для пользователя"""
    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO ai_sessions (user_id, active, mode) VALUES (?, 1, ?)",
            (user_id, mode),
        )
        conn.commit()


def get_ai_session_mode(user_id: int) -> str:
    """Получить режим AI сессии"""
    with db() as conn:
        result = conn.execute(
            "SELECT mode FROM ai_sessions WHERE user_id = ? AND active = 1", (user_id,)
        ).fetchone()
        return result[0] if result else "rag"


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
    # Получаем релевантные чанки
    ctx_chunks = retrieve_chunks(question)

    # Если нет релевантных чанков
    if not ctx_chunks:
        return "Не знаю. Информация по данному вопросу отсутствует в базе знаний."

    ctx = "\n\n".join(ctx_chunks)

    # СТРОГИЙ промпт для RAG
    prompt = f"""Ты — ассистент сотрудников отеля, отвечающий ТОЛЬКО на основе предоставленной базы знаний.

ИСПОЛЬЗУЙ ТОЛЬКО ЭТУ ИНФОРМАЦИЮ:
{ctx}

ВОПРОС: {question}

ПРАВИЛА:
1. Ответь ТОЛЬКО если точный ответ есть в информации выше
2. Если ответа нет - скажи "Не знаю"
3. НЕ добавляй информацию из своих знаний
4. НЕ объясняй почему не знаешь
5. Будь кратким

ОТВЕТ:"""

    try:
        answer = call_yandex_gpt_generate(prompt, CHAT_MODEL_URI)

        # Дополнительная проверка - если ответ слишком общий
        vague_phrases = [
            "в общем",
            "обычно",
            "как правило",
            "согласно общим правилам",
            "в большинстве случаев",
        ]
        if any(phrase in answer.lower() for phrase in vague_phrases):
            return "Не знаю"

        # Если ответ не содержит полезной информации
        if len(answer.strip()) < 10 or "не знаю" not in answer.lower():
            # Проверяем, есть ли в ответе реальная информация
            return answer

        return "Не знаю"
    except Exception as e:
        print(f"Error in generate_answer: {e}")
        return "Не знаю"


def generate_free_answer(question: str) -> str:
    """Генерация ответа без ограничений БД - обычный ИИ-бот"""
    # Простой промпт без контекста БД
    prompt = f"""Ты — полезный AI-ассистент для сотрудников отеля.
Отвечай на вопросы максимально полезно и информативно.
Будь вежливым и профессиональным.

Вопрос пользователя: {question}

Полезный и развернутый ответ:"""

    try:
        answer = call_yandex_gpt_generate(prompt, CHAT_MODEL_URI)
        return answer
    except Exception as e:
        print(f"Error in generate_free_answer: {e}")
        return "Извините, произошла ошибка при генерации ответа."


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

        # Определяем режим (rag или free)
        mode = get_ai_session_mode(uid)

        # Если пользователь хочет выйти
        if msg.text.strip().lower() in ["/stop", "/exit", "стоп", "выход"]:
            end_ai_session(uid)
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🤖 AI по БД", callback_data="start_ai"),
                        InlineKeyboardButton(
                            "🧠 Общий AI", callback_data="free_ai_menu"
                        ),
                    ],
                    [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
                ]
            )
            await msg.reply("✅ Диалог завершен.", reply_markup=keyboard)
            return

        question = msg.text.strip()
        thinking_msg = await msg.reply("⏳ Думаю…")

        try:
            # В зависимости от режима
            if mode == "rag":
                answer = generate_answer(question)  # AI по БД
                mode_text = "🤖 AI по БД"
            else:
                answer = generate_free_answer(question)  # Общий AI
                mode_text = "🧠 Общий AI"
        finally:
            try:
                await thinking_msg.delete()
            except Exception:
                pass

        # Отправляем ответ
        await msg.reply(
            answer,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            f"⏹ Завершить ({mode_text})", callback_data="stop_ai"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            (
                                "🤖 Перейти к AI по БД"
                                if mode == "free"
                                else "🧠 Перейти к общему AI"
                            ),
                            callback_data=(
                                "start_ai" if mode == "free" else "free_ai_menu"
                            ),
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

    @app.on_message(filters.command("free_ai") & filters.private, group=22)
    async def free_ai_cmd(client, m: Message):
        """Быстрый доступ к обычному ИИ (без БД)"""
        if len(m.text.split()) > 1:
            # Пользователь написал вопрос сразу: /free_ai Как погода?
            question = " ".join(m.text.split()[1:])
            thinking = await m.reply("🧠 Думаю над ответом...")

            try:
                answer = generate_free_answer(question)
                await thinking.delete()
                await m.reply(
                    f"<b>🧠 Общий AI-ответ:</b>\n\n{answer}",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "🤖 Перейти к AI по БД", callback_data="start_ai"
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
            except Exception as e:
                await thinking.delete()
                await m.reply(f"⚠️ Ошибка: {str(e)}")
        else:
            # Пользователь просто написал /free_ai без вопроса
            await m.reply(
                "🧠 <b>Общий AI-чат</b>\n\n"
                "Я могу ответить на любые вопросы, не ограничиваясь базой данных.\n\n"
                "<b>Использование:</b>\n"
                "• Напишите вопрос сразу: <code>/free_ai Как погода в Москве?</code>\n"
                "• Или просто напишите <code>/free_ai</code> и затем задайте вопрос\n\n"
                "<b>Режимы работы:</b>\n"
                "• 🤖 <b>AI по БД</b> - только информация из базы знаний\n"
                "• 🧠 <b>Общий AI</b> - любые вопросы",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🤖 AI по базе данных", callback_data="start_ai"
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

    @app.on_callback_query(filters.regex("^free_ai_menu$"), group=20)
    async def free_ai_menu_callback(_, cq: CallbackQuery):
        """Кнопка 'Общий AI' в меню"""
        uid = cq.from_user.id
        start_ai_session(uid, "free")  # Запускаем сессию в режиме 'free'

        await cq.message.edit_text(
            "🧠 <b>Общий AI-чат активирован!</b>\n\n"
            "Теперь я буду отвечать на <b>любые ваши вопросы</b>.\n"
            "Просто напишите ваш вопрос в чат.\n\n"
            "<b>Примеры вопросов:</b>\n"
            "• Что такое искусственный интеллект?\n"
            "• Как улучшить работу ресепшена?\n"
            "• Расскажи интересный факт\n\n"
            "Для выхода нажмите кнопку ниже.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⏹ Завершить общий чат", callback_data="stop_ai"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🤖 Перейти к AI по БД", callback_data="start_ai"
                        )
                    ],
                    [InlineKeyboardButton("🔙 В меню", callback_data="back_to_main")],
                ]
            ),
        )
        await cq.answer()

    @app.on_callback_query(filters.regex("^ask_free_ai$"), group=20)
    async def ask_free_ai_callback(_, cq: CallbackQuery):
        """Кнопка 'Задать вопрос'"""
        await cq.message.edit_text(
            "🧠 <b>Задайте ваш вопрос:</b>\n\n"
            "Просто <b>напишите вопрос в чат</b>.\n\n"
            "Или используйте команду:\n"
            "<code>/free_ai ваш вопрос</code>\n\n"
            "<i>Например: 'Какие есть лайфхаки для работы?'</i>",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🔙 Назад", callback_data="free_ai_menu")],
                    [InlineKeyboardButton("🏠 В меню", callback_data="back_to_main")],
                ]
            ),
        )
        await cq.answer()
