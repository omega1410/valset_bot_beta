import logging
import os
from pyrogram.client import Client
from dotenv import load_dotenv
from handlers import menu, access, sections, tests
from db.database import init_db

load_dotenv()

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

init_db()
access.register_access_handlers(app)
menu.register_menu_handlers(app)
sections.register_section_handlers(app)
tests.register_test_handlers(app)

app.run()
