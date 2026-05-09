import sqlite3
from datetime import datetime, date
from contextlib import contextmanager

DB_FILE = "bot.db"

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                is_vip      INTEGER DEFAULT 0,
                vip_expire  TEXT,
                joined_at   TEXT DEFAULT (date('now')),
                last_active TEXT DEFAULT (date('now'))
            );

            CREATE TABLE IF NOT EXISTS daily_counts (
                user_id  INTEGER,
                day      TEXT,
                count    INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, day)
            );

            CREATE TABLE IF NOT EXISTS query_log (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id  INTEGER,
                domain   TEXT,
                source   INTEGER,
                found    INTEGER,
                created  TEXT DEFAULT (datetime('now'))
            );
        """)

# ─── Kullanıcı işlemleri ───

def add_user(user_id: int, username: str):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, last_active)
            VALUES (?, ?, date('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                last_active = date('now')
        """, (user_id, username))

def get_user(user_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else {}

def get_all_users() -> list:
    with get_conn() as conn:
        rows = conn.execute("SELECT user_id FROM users").fetchall()
        return [r["user_id"] for r in rows]

# ─── VIP işlemleri ───

def is_vip(user_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT is_vip, vip_expire FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row or not row["is_vip"]:
            return False
        if row["vip_expire"] and row["vip_expire"] < date.today().isoformat():
            # Süresi dolmuş, VIP'i kapat
            conn.execute("UPDATE users SET is_vip = 0 WHERE user_id = ?", (user_id,))
            return False
        return True

def set_vip(user_id: int, expire_date: str):
    with get_conn() as conn:
        conn.execute("""
            UPDATE users SET is_vip = 1, vip_expire = ? WHERE user_id = ?
        """, (expire_date, user_id))

# ─── Günlük limit ───

def get_daily_count(user_id: int) -> int:
    today = date.today().isoformat()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT count FROM daily_counts WHERE user_id = ? AND day = ?",
            (user_id, today)
        ).fetchone()
        return row["count"] if row else 0

def inc_daily_count(user_id: int):
    today = date.today().isoformat()
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO daily_counts (user_id, day, count) VALUES (?, ?, 1)
            ON CONFLICT(user_id, day) DO UPDATE SET count = count + 1
        """, (user_id, today))

# ─── İstatistik ───

def get_stats() -> dict:
    today = date.today().isoformat()
    with get_conn() as conn:
        total  = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        vip    = conn.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1").fetchone()[0]
        active = conn.execute(
            "SELECT COUNT(*) FROM users WHERE last_active = ?", (today,)
        ).fetchone()[0]
        queries = conn.execute(
            "SELECT SUM(count) FROM daily_counts WHERE day = ?", (today,)
        ).fetchone()[0] or 0
    return {"total_users": total, "vip_users": vip, "today_active": active, "today_queries": queries}

# Başlangıçta veritabanını oluştur
init_db()
