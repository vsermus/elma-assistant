import hashlib
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "users.db"


def _hash(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex() + ":" + key.hex()


def _verify(password: str, hashed: str) -> bool:
    salt = bytes.fromhex(hashed[:64])
    key = bytes.fromhex(hashed[65:])
    return key == hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)


def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    """)
    conn.commit()

    cur = conn.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        h = _hash("admin")
        conn.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, 1)", ("admin", h))
        conn.commit()
    conn.close()


def get_user(username: str):
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.execute("SELECT username, password, is_admin FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"username": row[0], "password": row[1], "is_admin": bool(row[2])}
    return None


def verify_user(username: str, password: str):
    user = get_user(username)
    if user and _verify(password, user["password"]):
        return {"username": user["username"], "is_admin": user["is_admin"]}
    return None


def add_user(username: str, password: str, is_admin: bool = False):
    conn = sqlite3.connect(str(DB_PATH))
    try:
        h = _hash(password)
        conn.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
                     (username, h, int(is_admin)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def list_users():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.execute("SELECT username, is_admin FROM users ORDER BY username")
    rows = cur.fetchall()
    conn.close()
    return [{"username": r[0], "is_admin": bool(r[1])} for r in rows]
