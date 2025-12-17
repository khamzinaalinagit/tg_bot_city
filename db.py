import sqlite3
from typing import Optional, Dict
from config import DB_PATH, DEFAULT_LIMIT, DEFAULT_RATING, DEFAULT_LANG


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            rating_type TEXT NOT NULL,
            city_limit INTEGER NOT NULL,
            lang TEXT NOT NULL
        )
        """)
        c.commit()


def ensure_user(user_id: int):
    with _conn() as c:
        cur = c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if cur.fetchone() is None:
            c.execute(
                "INSERT INTO users(user_id, rating_type, city_limit, lang) VALUES(?,?,?,?)",
                (user_id, DEFAULT_RATING, DEFAULT_LIMIT, DEFAULT_LANG)
            )
            c.commit()
