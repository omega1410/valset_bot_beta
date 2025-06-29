import sqlite3

conn = sqlite3.connect("data.db")
c = conn.cursor()

# создаёт таблицу whitelist
c.execute(
    """
CREATE TABLE IF NOT EXISTS whitelist (
    user_id INTEGER PRIMARY KEY
)
"""
)

# если таблица sections ещё не создана — создаёт и её
c.execute(
    """
CREATE TABLE IF NOT EXISTS sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL
)
"""
)

conn.commit()
conn.close()