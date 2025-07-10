import sqlite3
from typing import List, Dict, Set, Any
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DB_PATH = "data.db"

# Жёстко заданные ID администраторов
HARDCODED_ADMINS = {
    5669245603,  # Ваш текущий ID
    551125461,  # Другой текущий админ
    655805086,  
    # Добавляйте новые ID админов здесь
}


def get_db_connection():
    """Создает и возвращает соединение с БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь админом"""
    return user_id in HARDCODED_ADMINS


def add_user_to_whitelist(user_id: int) -> bool:
    """Добавляет обычного пользователя в whitelist"""
    if is_admin(user_id):
        logger.warning(f"Попытка добавить админа {user_id} через whitelist")
        return False

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO whitelist (user_id) VALUES (?)", (user_id,)
            )
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Добавлен пользователь в whitelist: {user_id}")
                return True
            return False
    except sqlite3.Error as e:
        logger.error(f"Ошибка добавления пользователя {user_id}: {e}")
        return False


def remove_user_from_whitelist(user_id: int) -> bool:
    """Удаляет пользователя из whitelist"""
    if is_admin(user_id):
        logger.warning(f"Попытка удалить админа {user_id} из whitelist")
        return False

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM whitelist WHERE user_id = ?", (user_id,))
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Удален пользователь из whitelist: {user_id}")
                return True
            return False
    except sqlite3.Error as e:
        logger.error(f"Ошибка удаления пользователя {user_id}: {e}")
        return False


def is_user_in_whitelist(user_id: int) -> bool:
    """Проверяет наличие пользователя в whitelist"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM whitelist WHERE user_id = ?", (user_id,))
            return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logger.error(f"Ошибка проверки whitelist для {user_id}: {e}")
        return False


def is_user_allowed(user_id: int) -> bool:
    """Проверяет, имеет ли пользователь доступ"""
    allowed = is_admin(user_id) or is_user_in_whitelist(user_id)
    logger.info(f"Авторизация: {'УСПЕШНО' if allowed else 'ОТКАЗАНО'} для {user_id}")
    return allowed


def get_whitelist_users() -> List[int]:
    """Возвращает список ID пользователей в whitelist"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM whitelist")
            return [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Ошибка получения whitelist: {e}")
        return []


def get_complete_users_list() -> List[Dict[str, Any]]:
    """Возвращает список всех пользователей с их статусами"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM whitelist")
            whitelist_users = {row[0] for row in cursor.fetchall()}

            result = []
            for user_id in HARDCODED_ADMINS.union(whitelist_users):
                result.append(
                    {
                        "user_id": user_id,
                        "is_admin": user_id in HARDCODED_ADMINS,
                        "in_whitelist": user_id in whitelist_users,
                    }
                )
            return result
    except sqlite3.Error as e:
        logger.error(f"Ошибка получения списка пользователей: {e}")
        return []
