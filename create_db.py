import sqlite3

conn = sqlite3.connect("data.db")
c = conn.cursor()

c.execute(
    """
CREATE TABLE IF NOT EXISTS whitelist (
    user_id INTEGER PRIMARY KEY
)
"""
)

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