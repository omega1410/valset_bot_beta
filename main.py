import logging
import os
from pyrogram import Client
from dotenv import load_dotenv
from handlers import menu, access, sections, tests
from db.database import init_db

load_dotenv()

logging.basicConfig(level=logging.INFO)

app = Client(
    "otel_bot",
    api_id=int(os.getenv("API_ID")),
    api_hash=os.getenv("API_HASH"),
    bot_token=os.getenv("BOT_TOKEN"),
)

init_db()
access.register_access_handlers(app)
menu.register_menu_handlers(app)
sections.register_section_handlers(app)
tests.register_test_handlers(app)

app.run()
