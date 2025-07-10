import sqlite3
from typing import Optional, List, Tuple, Dict, Any
import logging
from contextlib import contextmanager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DB_PATH = "db/data.db"


@contextmanager
def db_connection():
    """Контекстный менеджер для работы с БД"""
    conn = sqlite3.connect(DB_PATH, timeout=20, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
    try:
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Ошибка БД: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Инициализация структуры БД с проверкой существования таблиц"""
    try:
        with db_connection() as conn:
            cursor = conn.cursor()

            # Таблица пользователей
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS whitelist (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )"""
            )

            # Таблица статистики (исправленные названия колонок)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS test_stats (
                    user_id INTEGER NOT NULL,
                    section_id INTEGER NOT NULL,
                    correct_answers INTEGER NOT NULL,
                    total_questions INTEGER NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, section_id),
                    FOREIGN KEY (user_id) REFERENCES whitelist(user_id) ON DELETE CASCADE
                )"""
            )

            # Индексы
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_test_stats_user 
                ON test_stats(user_id)"""
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_test_stats_section 
                ON test_stats(section_id)"""
            )

            conn.commit()
            logger.info("База данных инициализирована")

    except Exception as e:
        logger.critical(f"Ошибка инициализации БД: {e}")
        raise


def add_user(user_id: int, name: str) -> bool:
    """Добавление пользователя с проверкой"""
    try:
        with db_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO whitelist (user_id, name)
                VALUES (?, ?)""",
                (user_id, name.strip()),
            )
            conn.commit()
            logger.info(f"Добавлен пользователь {user_id}")
            return True
    except Exception as e:
        logger.error(f"Ошибка добавления {user_id}: {e}")
        return False


def get_whitelist_users() -> List[Dict[str, Any]]:
    """Получение всех пользователей из whitelist"""
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, name FROM whitelist")
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Ошибка получения whitelist: {e}")
        return []


def save_test_result(user_id: int, section_id: int, correct: int, total: int) -> bool:
    """Сохранение результатов теста с проверкой пользователя"""
    if not is_user_allowed(user_id):
        logger.warning(f"Пользователь {user_id} не в whitelist")
        return False

    try:
        with db_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO test_stats 
                (user_id, section_id, correct_answers, total_questions)
                VALUES (?, ?, ?, ?)""",
                (user_id, section_id, correct, total),
            )
            conn.commit()
            logger.info(f"Сохранены результаты для {user_id}")
            return True
    except Exception as e:
        logger.error(f"Ошибка сохранения результатов: {e}")
        return False
    
    def get_connection():
        conn = sqlite3.connect(
            DB_PATH,
            timeout=30,  # Увеличиваем время ожидания
            check_same_thread=False,  # Разрешаем доступ из разных потоков
            isolation_level=None  # Автоматическое управление транзакциями
        )
        conn.execute("PRAGMA journal_mode=WAL")  # Режим журналирования
        conn.execute("PRAGMA busy_timeout=30000")  # Таймаут 30 секунд
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    