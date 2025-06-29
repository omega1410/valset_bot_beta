import sqlite3


def add_user_to_whitelist(user_id: int) -> bool:
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO whitelist (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def is_user_allowed(user_id: int) -> bool:
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT 1 FROM whitelist WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None
