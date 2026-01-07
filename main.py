import logging
import os
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from dotenv import load_dotenv
from handlers.feedback import register_feedback_handlers

load_dotenv()

from handlers import menu, access, sections, tests, search, news
from handlers.search import handle_search
from handlers.checklists import register_checklist_handlers
from db.database import init_db
from utils.search_state import search_state
from config import ADMIN_IDS
from handlers.help import register_help_handler
from handlers import ai_assistant
from handlers.logbook import register_logbook
from utils.states import user_states
from handlers.cancel import register_cancel_handler
from handlers.ai_assistant import generate_free_answer

logging.basicConfig(level=logging.INFO)

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not API_ID or not API_HASH or not BOT_TOKEN:
    raise ValueError("API_ID, API_HASH and BOT_TOKEN must be set")

app = Client(
    "otel_bot",
    api_id=int(API_ID),
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# Инициализация базы данных
init_db()

# Регистрация всех обработчиков
access.register_access_handlers(app)
register_help_handler(app)
tests.register_test_handlers(app)
search.register_search_handlers(app)
news.register_news_handlers(app)
sections.register_section_handlers(app)
register_checklist_handlers(app)
ai_assistant.init_vector_table()
ai_assistant.register_ai_handlers(app)
register_feedback_handlers(app)
register_logbook(app)
register_cancel_handler(app)
menu.register_menu_handlers(app)


@app.on_message(
    filters.text
    & filters.private
    & ~filters.create(lambda _, __, m: m.from_user.id in search_state)
)
async def handle_regular_messages(client: Client, message: Message):
    user_id = message.from_user.id
    print(f"[DEBUG] Обычное сообщение от {user_id}: {message.text}")

    if user_id in search_state:
        print(f"[DEBUG main] user {user_id} is in search_state, calling handle_search")
        await handle_search(client, message)
        return


if __name__ == "__main__":
    print("Bot is starting...")
    app.run()
