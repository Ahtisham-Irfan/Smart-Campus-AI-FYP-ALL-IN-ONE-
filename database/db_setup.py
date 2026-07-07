# ============================================================
# Smart Campus AI v2 — Database Setup
# ============================================================
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "smart_campus.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def initialize_database():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        username    TEXT UNIQUE NOT NULL,
        password    TEXT NOT NULL,
        full_name   TEXT NOT NULL,
        role        TEXT NOT NULL DEFAULT 'student',
        email       TEXT DEFAULT '',
        created_at  TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS students (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id   TEXT UNIQUE NOT NULL,
        full_name    TEXT NOT NULL,
        department   TEXT DEFAULT 'Computer Science',
        semester     TEXT DEFAULT '—',
        dataset_path TEXT DEFAULT '',
        photo_count  INTEGER DEFAULT 0,
        model_trained INTEGER DEFAULT 0,
        enrolled_at  TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS attendance (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id  TEXT NOT NULL,
        full_name   TEXT NOT NULL,
        date        TEXT NOT NULL,
        time        TEXT NOT NULL,
        subject     TEXT DEFAULT 'General',
        status      TEXT DEFAULT 'Present',
        marked_by   TEXT DEFAULT 'AI System',
        UNIQUE(student_id, date, subject)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS emotion_logs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id  TEXT NOT NULL,
        timestamp   TEXT NOT NULL,
        emotion     TEXT NOT NULL,
        confidence  REAL DEFAULT 0.5,
        subject     TEXT DEFAULT '',
        logged_at   TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS study_plans (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id  TEXT DEFAULT '',
        title       TEXT NOT NULL,
        subjects    TEXT DEFAULT '',
        deadline    TEXT DEFAULT '',
        plan_data   TEXT DEFAULT '',
        created_at  TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS summaries (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        title        TEXT DEFAULT '',
        original_len INTEGER DEFAULT 0,
        summary      TEXT NOT NULL,
        word_count   INTEGER DEFAULT 0,
        method       TEXT DEFAULT 'Extractive',
        created_at   TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS resume_screenings (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate   TEXT DEFAULT '',
        filename    TEXT DEFAULT '',
        skills      TEXT DEFAULT '',
        education   TEXT DEFAULT '',
        experience  TEXT DEFAULT '',
        match_score REAL DEFAULT 0,
        rank        INTEGER DEFAULT 0,
        job_title   TEXT DEFAULT '',
        screened_at TEXT DEFAULT (datetime('now'))
    )""")

    # Default users
    defaults = [
        ('admin',   'admin123',   'Administrator',    'admin'),
        ('teacher', 'teacher123', 'Mr. Faheem Tariq', 'teacher'),
        ('student', 'student123', 'Muhammad Ahtisham','student'),
    ]
    for u, p, n, r in defaults:
        c.execute("INSERT OR IGNORE INTO users (username,password,full_name,role) VALUES (?,?,?,?)",
                  (u, p, n, r))

    conn.commit()
    conn.close()
    print("[DB] Initialized OK")

if __name__ == "__main__":
    initialize_database()
