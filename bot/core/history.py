"""
История чатов пользователей — хранение в SQLite.
Обеспечивает:
- Лог всех сообщений (кто, когда, что спросил и что ответил)
- Контекст разговора для передачи в AI (последние N сообщений)
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'chat_history.db')
CONTEXT_MESSAGES = 4  # последних сообщений передаём в AI как контекст разговора


def _conn():
    return sqlite3.connect(os.path.normpath(DB_PATH))


def init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                username  TEXT,
                full_name TEXT,
                role      TEXT NOT NULL,  -- 'user' или 'assistant'
                text      TEXT NOT NULL,
                ts        TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS failures (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                type           TEXT NOT NULL,
                question       TEXT NOT NULL,
                bot_answer     TEXT NOT NULL,
                user_id        INTEGER,
                ts             TEXT NOT NULL,
                status         TEXT DEFAULT 'new',
                resolution     TEXT,
                category       TEXT,
                recommendation TEXT,
                fixed_at       TEXT
            )
        """)
        for col, definition in [('recommendation', 'TEXT'), ('fixed_at', 'TEXT')]:
            try:
                c.execute(f"ALTER TABLE failures ADD COLUMN {col} {definition}")
            except Exception:
                pass
        c.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)


def save_message(user_id: int, username: str, full_name: str, role: str, text: str):
    with _conn() as c:
        c.execute(
            "INSERT INTO messages (user_id, username, full_name, role, text, ts) VALUES (?,?,?,?,?,?)",
            (user_id, username, full_name, role, text, datetime.now().isoformat(timespec='seconds'))
        )


def get_context(user_id: int) -> list[dict]:
    """Последние CONTEXT_MESSAGES сообщений пользователя для передачи в AI."""
    with _conn() as c:
        rows = c.execute(
            "SELECT role, text FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, CONTEXT_MESSAGES)
        ).fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


def get_recent(user_id: int, limit: int = 10) -> list[dict]:
    """Последние сообщения для команды /history."""
    with _conn() as c:
        rows = c.execute(
            "SELECT role, text, ts FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
    return [{"role": r[0], "text": r[1], "ts": r[2]} for r in reversed(rows)]
