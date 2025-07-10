import sqlite3
from typing import List, Tuple, Optional


def get_user_stats(user_id: int) -> Optional[List[Tuple[int, int, int]]]:
    try:
        with sqlite3.connect("db/data.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT section_id, correct, total 
                FROM test_stats 
                WHERE user_id = ? 
                ORDER BY section_id""",
                (user_id,),
            )
            return cursor.fetchall()

    except sqlite3.Error as e:
        print(
            f"[ОШИБКА] Не удалось получить статистику для пользователя {user_id}: {e}"
        )
        return None
