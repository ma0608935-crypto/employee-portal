"""
modules/database.py
Database layer — uses Supabase (PostgreSQL) in production,
falls back to SQLite for local development automatically.
"""

import os
import hashlib
import sqlite3
from datetime import datetime

# ── Detect environment ────────────────────────────────────────────────────────
def _get_db_url():
    """Return Supabase URL from Streamlit secrets or env variable, or None for local.
    Returns None if the URL is a placeholder or missing — SQLite is used locally.
    """
    PLACEHOLDERS = {"", "YOUR_PASSWORD", "XXXX", "your-password", "YOUR_SUPABASE"}

    try:
        import streamlit as st
        url = st.secrets.get("database", {}).get("url", None)
        if url and not any(p in url for p in PLACEHOLDERS):
            return url
    except Exception:
        pass

    env_url = os.environ.get("DATABASE_URL", None)
    if env_url and not any(p in env_url for p in PLACEHOLDERS):
        return env_url

    return None  # fall back to SQLite


USE_POSTGRES = bool(_get_db_url())

# ── SQLite fallback path ──────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "portal.db")


def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
#  Connection helpers
# ═══════════════════════════════════════════════════════════════════════════════

def get_conn():
    url = _get_db_url()
    if url:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
        conn.autocommit = False
        return conn, "pg"
    else:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"


def _fetchall(cursor):
    rows = cursor.fetchall()
    return [dict(r) for r in rows]


def _fetchone(cursor):
    row = cursor.fetchone()
    return dict(row) if row else None


# ═══════════════════════════════════════════════════════════════════════════════
#  Schema init
# ═══════════════════════════════════════════════════════════════════════════════

def init_db():
    conn, engine = get_conn()
    c = conn.cursor()

    if engine == "pg":
        # PostgreSQL — use SERIAL and TEXT types
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          SERIAL PRIMARY KEY,
                username    TEXT UNIQUE NOT NULL,
                password    TEXT NOT NULL,
                role        TEXT NOT NULL DEFAULT 'employee',
                full_name   TEXT,
                employee_id TEXT UNIQUE,
                department  TEXT,
                position    TEXT,
                email       TEXT,
                phone       TEXT,
                hire_date   TEXT,
                photo_path  TEXT,
                is_active   INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS leader_notes (
                id          SERIAL PRIMARY KEY,
                employee_id TEXT NOT NULL,
                author      TEXT NOT NULL,
                note        TEXT NOT NULL,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id          SERIAL PRIMARY KEY,
                employee_id TEXT NOT NULL,
                full_name   TEXT,
                date        TEXT NOT NULL,
                check_in    TEXT,
                status      TEXT DEFAULT 'Present',
                source      TEXT DEFAULT 'qr'
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS breaks (
                id          SERIAL PRIMARY KEY,
                employee_id TEXT NOT NULL,
                full_name   TEXT,
                break_name  TEXT,
                start_time  TEXT,
                end_time    TEXT,
                duration    FLOAT,
                date        TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS callbacks (
                id              SERIAL PRIMARY KEY,
                employee_id     TEXT NOT NULL,
                customer_name   TEXT,
                phone           TEXT,
                callback_date   TEXT,
                callback_time   TEXT,
                status          TEXT DEFAULT 'Pending',
                notes           TEXT,
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        # SQLite
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT UNIQUE NOT NULL,
                password    TEXT NOT NULL,
                role        TEXT NOT NULL DEFAULT 'employee',
                full_name   TEXT,
                employee_id TEXT UNIQUE,
                department  TEXT,
                position    TEXT,
                email       TEXT,
                phone       TEXT,
                hire_date   TEXT,
                photo_path  TEXT,
                is_active   INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS leader_notes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                author      TEXT NOT NULL,
                note        TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                full_name   TEXT,
                date        TEXT NOT NULL,
                check_in    TEXT,
                status      TEXT DEFAULT 'Present',
                source      TEXT DEFAULT 'qr'
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS breaks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                full_name   TEXT,
                break_name  TEXT,
                start_time  TEXT,
                end_time    TEXT,
                duration    REAL,
                date        TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS callbacks (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id     TEXT NOT NULL,
                customer_name   TEXT,
                phone           TEXT,
                callback_date   TEXT,
                callback_time   TEXT,
                status          TEXT DEFAULT 'Pending',
                notes           TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    conn.commit()
    _seed_users(conn, engine)
    conn.close()


def _seed_users(conn, engine):
    c = conn.cursor()
    defaults = [
        ("admin",  "admin123", "admin",    "System Admin",  "ADM-001", "IT",    "Administrator",   "admin@company.com",  "000-000-0000", "2020-01-01"),
        ("john",   "john123",  "employee", "John Smith",    "EMP-001", "Sales", "Sales Executive", "john@company.com",   "555-123-4567", "2022-03-15"),
        ("sara",   "sara123",  "employee", "Sara Johnson",  "EMP-002", "Sales", "Account Manager", "sara@company.com",   "555-234-5678", "2021-07-20"),
        ("leader", "lead123",  "leader",   "Team Leader",   "LDR-001", "Sales", "Team Leader",     "leader@company.com", "555-345-6789", "2019-06-01"),
    ]
    for row in defaults:
        try:
            if engine == "pg":
                c.execute("""
                    INSERT INTO users (username,password,role,full_name,employee_id,
                                       department,position,email,phone,hire_date)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (username) DO NOTHING
                """, (row[0], hash_pw(row[1]), row[2], row[3], row[4],
                      row[5], row[6], row[7], row[8], row[9]))
            else:
                c.execute("""
                    INSERT OR IGNORE INTO users
                    (username,password,role,full_name,employee_id,
                     department,position,email,phone,hire_date)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (row[0], hash_pw(row[1]), row[2], row[3], row[4],
                      row[5], row[6], row[7], row[8], row[9]))
        except Exception:
            pass
    conn.commit()


# ═══════════════════════════════════════════════════════════════════════════════
#  Query helper — handles ? vs %s placeholder difference
# ═══════════════════════════════════════════════════════════════════════════════

def _q(sql: str, engine: str) -> str:
    """Convert SQLite ? placeholders to PostgreSQL %s."""
    if engine == "pg":
        return sql.replace("?", "%s")
    return sql


# ═══════════════════════════════════════════════════════════════════════════════
#  Users
# ═══════════════════════════════════════════════════════════════════════════════

def get_user(username: str):
    conn, engine = get_conn()
    c = conn.cursor()
    c.execute(_q("SELECT * FROM users WHERE username=?", engine), (username,))
    row = _fetchone(c)
    conn.close()
    return row


def verify_login(username: str, password: str):
    user = get_user(username)
    if user and user["password"] == hash_pw(password):
        return user
    return None


def get_all_users():
    conn, engine = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE is_active=1 ORDER BY full_name")
    rows = _fetchall(c)
    conn.close()
    return rows


def get_employee(employee_id: str):
    conn, engine = get_conn()
    c = conn.cursor()
    c.execute(_q("SELECT * FROM users WHERE employee_id=?", engine), (employee_id,))
    row = _fetchone(c)
    conn.close()
    return row


def update_user(user_id: int, **kwargs):
    conn, engine = get_conn()
    c = conn.cursor()
    if engine == "pg":
        sets = ", ".join(f"{k}=%s" for k in kwargs)
    else:
        sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [user_id]
    c.execute(f"UPDATE users SET {sets} WHERE id={('%s' if engine=='pg' else '?')}", vals)
    conn.commit()
    conn.close()


def add_user(username, password, role, full_name, employee_id,
             department, position, email, phone, hire_date):
    conn, engine = get_conn()
    c = conn.cursor()
    try:
        c.execute(_q("""
            INSERT INTO users (username,password,role,full_name,employee_id,
                               department,position,email,phone,hire_date)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, engine), (username, hash_pw(password), role, full_name, employee_id,
                       department, position, email, phone, hire_date))
        conn.commit()
        return True, "User created successfully."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def delete_user(user_id: int):
    conn, engine = get_conn()
    c = conn.cursor()
    c.execute(_q("UPDATE users SET is_active=0 WHERE id=?", engine), (user_id,))
    conn.commit()
    conn.close()


def reset_password(user_id: int, new_pw: str):
    conn, engine = get_conn()
    c = conn.cursor()
    c.execute(_q("UPDATE users SET password=? WHERE id=?", engine), (hash_pw(new_pw), user_id))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  Notes
# ═══════════════════════════════════════════════════════════════════════════════

def add_note(employee_id, author, note):
    conn, engine = get_conn()
    c = conn.cursor()
    c.execute(_q("INSERT INTO leader_notes (employee_id,author,note) VALUES (?,?,?)", engine),
              (employee_id, author, note))
    conn.commit()
    conn.close()


def get_notes(employee_id):
    conn, engine = get_conn()
    c = conn.cursor()
    c.execute(_q("SELECT * FROM leader_notes WHERE employee_id=? ORDER BY created_at DESC", engine),
              (employee_id,))
    rows = _fetchall(c)
    conn.close()
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
#  Attendance
# ═══════════════════════════════════════════════════════════════════════════════

def record_attendance(employee_id, full_name, date, check_in, status="Present"):
    conn, engine = get_conn()
    c = conn.cursor()
    c.execute(_q("SELECT id FROM attendance WHERE employee_id=? AND date=?", engine),
              (employee_id, date))
    if _fetchone(c):
        conn.close()
        return False, "Already checked in today."
    c.execute(_q("""
        INSERT INTO attendance (employee_id,full_name,date,check_in,status)
        VALUES (?,?,?,?,?)
    """, engine), (employee_id, full_name, date, check_in, status))
    conn.commit()
    conn.close()
    return True, "Attendance recorded."


def get_attendance(employee_id=None):
    conn, engine = get_conn()
    c = conn.cursor()
    if employee_id:
        c.execute(_q("SELECT * FROM attendance WHERE employee_id=? ORDER BY date DESC", engine),
                  (employee_id,))
    else:
        c.execute("SELECT * FROM attendance ORDER BY date DESC")
    rows = _fetchall(c)
    conn.close()
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
#  Breaks
# ═══════════════════════════════════════════════════════════════════════════════

def start_break(employee_id, full_name, break_name, start_time, date):
    conn, engine = get_conn()
    c = conn.cursor()
    c.execute(_q("""
        INSERT INTO breaks (employee_id,full_name,break_name,start_time,date)
        VALUES (?,?,?,?,?)
    """, engine), (employee_id, full_name, break_name, start_time, date))
    conn.commit()
    conn.close()


def end_break(break_id, end_time, duration):
    conn, engine = get_conn()
    c = conn.cursor()
    c.execute(_q("UPDATE breaks SET end_time=?, duration=? WHERE id=?", engine),
              (end_time, duration, break_id))
    conn.commit()
    conn.close()


def get_open_break(employee_id, break_name, date):
    conn, engine = get_conn()
    c = conn.cursor()
    c.execute(_q("""
        SELECT * FROM breaks
        WHERE employee_id=? AND break_name=? AND date=? AND end_time IS NULL
    """, engine), (employee_id, break_name, date))
    row = _fetchone(c)
    conn.close()
    return row


def get_breaks(employee_id=None):
    conn, engine = get_conn()
    c = conn.cursor()
    if employee_id:
        c.execute(_q("SELECT * FROM breaks WHERE employee_id=? ORDER BY date DESC", engine),
                  (employee_id,))
    else:
        c.execute("SELECT * FROM breaks ORDER BY date DESC")
    rows = _fetchall(c)
    conn.close()
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
#  Callbacks
# ═══════════════════════════════════════════════════════════════════════════════

def add_callback(employee_id, customer_name, phone, cb_date, cb_time, status, notes):
    conn, engine = get_conn()
    c = conn.cursor()
    c.execute(_q("""
        INSERT INTO callbacks
        (employee_id,customer_name,phone,callback_date,callback_time,status,notes)
        VALUES (?,?,?,?,?,?,?)
    """, engine), (employee_id, customer_name, phone, cb_date, cb_time, status, notes))
    conn.commit()
    conn.close()


def update_callback(cb_id, **kwargs):
    conn, engine = get_conn()
    c = conn.cursor()
    if engine == "pg":
        sets = ", ".join(f"{k}=%s" for k in kwargs)
        ph = "%s"
    else:
        sets = ", ".join(f"{k}=?" for k in kwargs)
        ph = "?"
    vals = list(kwargs.values()) + [cb_id]
    c.execute(f"UPDATE callbacks SET {sets} WHERE id={ph}", vals)
    conn.commit()
    conn.close()


def delete_callback(cb_id):
    conn, engine = get_conn()
    c = conn.cursor()
    c.execute(_q("DELETE FROM callbacks WHERE id=?", engine), (cb_id,))
    conn.commit()
    conn.close()


def get_callbacks(employee_id=None):
    conn, engine = get_conn()
    c = conn.cursor()
    if employee_id:
        c.execute(_q("SELECT * FROM callbacks WHERE employee_id=? ORDER BY callback_date DESC", engine),
                  (employee_id,))
    else:
        c.execute("SELECT * FROM callbacks ORDER BY callback_date DESC")
    rows = _fetchall(c)
    conn.close()
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
#  System Settings
# ═══════════════════════════════════════════════════════════════════════════════

def get_system_setting(key: str, default=None):
    """Get a system setting from the database."""
    conn, engine = get_conn()
    c = conn.cursor()
    c.execute(_q("SELECT value FROM system_settings WHERE key=?", engine), (key,))
    row = _fetchone(c)
    conn.close()
    
    if row:
        return row["value"]
    return default


def set_system_setting(key: str, value: str):
    """Set a system setting in the database."""
    conn, engine = get_conn()
    c = conn.cursor()
    
    if engine == "pg":
        c.execute("""
            INSERT INTO system_settings (key, value, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
        """, (key, value))
    else:
        c.execute("""
            INSERT OR REPLACE INTO system_settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, value))
    
    conn.commit()
    conn.close()
