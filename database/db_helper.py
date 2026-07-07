# ============================================================
# Smart Campus AI v2 — Database Helper
# ============================================================
import sqlite3, os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "smart_campus.db")

def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

# ── AUTH ────────────────────────────────────────────────────
def verify_login(username, password):
    c = _conn()
    row = c.execute("SELECT * FROM users WHERE username=? AND password=?",
                    (username, password)).fetchone()
    c.close()
    return dict(row) if row else None

def get_all_users():
    c = _conn()
    rows = c.execute("SELECT id,username,full_name,role,email,created_at FROM users ORDER BY id").fetchall()
    c.close()
    return [dict(r) for r in rows]

def add_user(username, password, full_name, role, email=""):
    try:
        c = _conn()
        c.execute("INSERT INTO users(username,password,full_name,role,email) VALUES(?,?,?,?,?)",
                  (username, password, full_name, role, email))
        c.commit(); c.close()
        return True
    except sqlite3.IntegrityError:
        return False

def update_user(uid, full_name, role, email):
    c = _conn()
    c.execute("UPDATE users SET full_name=?,role=?,email=? WHERE id=?",
              (full_name, role, email, uid))
    c.commit(); c.close()

def delete_user(uid):
    c = _conn()
    c.execute("DELETE FROM users WHERE id=?", (uid,))
    c.commit(); c.close()

def change_password(uid, new_password):
    c = _conn()
    c.execute("UPDATE users SET password=? WHERE id=?", (new_password, uid))
    c.commit(); c.close()

# ── STUDENTS ────────────────────────────────────────────────
def add_student(student_id, full_name, department, semester, dataset_path=""):
    try:
        c = _conn()
        c.execute("""INSERT INTO students(student_id,full_name,department,semester,dataset_path)
                     VALUES(?,?,?,?,?)""",
                  (student_id, full_name, department, semester, dataset_path))
        c.commit(); c.close()
        return True
    except sqlite3.IntegrityError:
        return False

def update_student_photos(student_id, count, trained=False):
    c = _conn()
    c.execute("UPDATE students SET photo_count=?, model_trained=? WHERE student_id=?",
              (count, 1 if trained else 0, student_id))
    c.commit(); c.close()

def get_all_students():
    c = _conn()
    rows = c.execute("SELECT * FROM students ORDER BY enrolled_at DESC").fetchall()
    c.close()
    return [dict(r) for r in rows]

def get_student(student_id):
    c = _conn()
    row = c.execute("SELECT * FROM students WHERE student_id=?", (student_id,)).fetchone()
    c.close()
    return dict(row) if row else None

def student_exists(student_id):
    c = _conn()
    r = c.execute("SELECT id FROM students WHERE student_id=?", (student_id,)).fetchone()
    c.close()
    return r is not None

def update_student(student_id, full_name, department, semester):
    c = _conn()
    c.execute("UPDATE students SET full_name=?,department=?,semester=? WHERE student_id=?",
              (full_name, department, semester, student_id))
    c.commit(); c.close()

def delete_student(student_id):
    c = _conn()
    c.execute("DELETE FROM students WHERE student_id=?", (student_id,))
    c.execute("DELETE FROM attendance WHERE student_id=?", (student_id,))
    c.commit(); c.close()

# ── ATTENDANCE ──────────────────────────────────────────────
def mark_attendance(student_id, full_name, subject="General"):
    today = datetime.now().strftime("%Y-%m-%d")
    now   = datetime.now().strftime("%H:%M:%S")
    c     = _conn()
    try:
        c.execute("""INSERT INTO attendance(student_id,full_name,date,time,subject)
                     VALUES(?,?,?,?,?)""",
                  (student_id, full_name, today, now, subject))
        c.commit(); c.close()
        return True
    except sqlite3.IntegrityError:
        c.close()
        return False

def get_attendance(date=None, subject=None, student_id=None):
    c = _conn()
    q = "SELECT * FROM attendance WHERE 1=1"
    p = []
    if date:       q += " AND date=?";       p.append(date)
    if subject:    q += " AND subject=?";    p.append(subject)
    if student_id: q += " AND student_id=?"; p.append(student_id)
    q += " ORDER BY date DESC, time DESC"
    rows = c.execute(q, p).fetchall()
    c.close()
    return [dict(r) for r in rows]

def get_attendance_stats():
    c = _conn()
    today   = datetime.now().strftime("%Y-%m-%d")
    total   = c.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
    today_c = c.execute("SELECT COUNT(*) FROM attendance WHERE date=?", (today,)).fetchone()[0]
    studs   = c.execute("SELECT COUNT(DISTINCT student_id) FROM attendance").fetchone()[0]
    c.close()
    return {"total": total, "today": today_c, "unique_students": studs}

def get_student_attendance_stats(student_id):
    c = _conn()
    total = c.execute("SELECT COUNT(*) FROM attendance WHERE student_id=?",
                      (student_id,)).fetchone()[0]
    last  = c.execute("SELECT date FROM attendance WHERE student_id=? ORDER BY date DESC LIMIT 1",
                      (student_id,)).fetchone()
    # Total school days = distinct dates in attendance table
    school_days = c.execute("SELECT COUNT(DISTINCT date) FROM attendance").fetchone()[0]
    pct = round((total / school_days) * 100) if school_days > 0 else 0
    c.close()
    return {"total": total, "last_date": last[0] if last else "Never",
            "percentage": pct, "school_days": school_days}

def get_attendance_by_period(period="daily"):
    c = _conn()
    if period == "daily":
        rows = c.execute("""SELECT date, COUNT(*) as cnt FROM attendance
                            GROUP BY date ORDER BY date DESC LIMIT 30""").fetchall()
    elif period == "weekly":
        rows = c.execute("""SELECT strftime('%Y-W%W', date) as wk, COUNT(*) as cnt
                            FROM attendance GROUP BY wk ORDER BY wk DESC LIMIT 12""").fetchall()
    elif period == "monthly":
        rows = c.execute("""SELECT strftime('%Y-%m', date) as mo, COUNT(*) as cnt
                            FROM attendance GROUP BY mo ORDER BY mo DESC LIMIT 12""").fetchall()
    else:
        rows = c.execute("""SELECT strftime('%Y', date) as yr, COUNT(*) as cnt
                            FROM attendance GROUP BY yr ORDER BY yr DESC""").fetchall()
    c.close()
    return [dict(r) for r in rows]

def delete_attendance(att_id):
    c = _conn()
    c.execute("DELETE FROM attendance WHERE id=?", (att_id,))
    c.commit(); c.close()

def reset_attendance(student_id=None):
    c = _conn()
    if student_id:
        c.execute("DELETE FROM attendance WHERE student_id=?", (student_id,))
    else:
        c.execute("DELETE FROM attendance")
    c.commit(); c.close()

# ── EMOTION LOGS ────────────────────────────────────────────
def log_emotion(session_id, emotion, confidence, subject=""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c  = _conn()
    c.execute("INSERT INTO emotion_logs(session_id,timestamp,emotion,confidence,subject) VALUES(?,?,?,?,?)",
              (session_id, ts, emotion, confidence, subject))
    c.commit(); c.close()

def get_emotion_logs(session_id=None):
    c = _conn()
    if session_id:
        rows = c.execute("SELECT * FROM emotion_logs WHERE session_id=? ORDER BY timestamp",
                         (session_id,)).fetchall()
    else:
        rows = c.execute("SELECT * FROM emotion_logs ORDER BY logged_at DESC LIMIT 1000").fetchall()
    c.close()
    return [dict(r) for r in rows]

def get_emotion_summary(session_id):
    c = _conn()
    rows = c.execute("""SELECT emotion, COUNT(*) as count FROM emotion_logs
                        WHERE session_id=? GROUP BY emotion ORDER BY count DESC""",
                     (session_id,)).fetchall()
    c.close()
    return [dict(r) for r in rows]

def delete_emotion_logs(session_id=None):
    c = _conn()
    if session_id:
        c.execute("DELETE FROM emotion_logs WHERE session_id=?", (session_id,))
    else:
        c.execute("DELETE FROM emotion_logs")
    c.commit(); c.close()

# ── STUDY PLANS ─────────────────────────────────────────────
def save_study_plan(student_id, title, subjects, deadline, plan_data):
    c = _conn()
    c.execute("INSERT INTO study_plans(student_id,title,subjects,deadline,plan_data) VALUES(?,?,?,?,?)",
              (student_id, title, subjects, deadline, plan_data))
    c.commit(); c.close()

def get_study_plans(student_id=None):
    c = _conn()
    if student_id:
        rows = c.execute("SELECT * FROM study_plans WHERE student_id=? ORDER BY created_at DESC",
                         (student_id,)).fetchall()
    else:
        rows = c.execute("SELECT * FROM study_plans ORDER BY created_at DESC").fetchall()
    c.close()
    return [dict(r) for r in rows]

def delete_study_plan(plan_id):
    c = _conn()
    c.execute("DELETE FROM study_plans WHERE id=?", (plan_id,))
    c.commit(); c.close()

# ── SUMMARIES ───────────────────────────────────────────────
def save_summary(title, original_len, summary, word_count, method="Extractive"):
    c = _conn()
    c.execute("INSERT INTO summaries(title,original_len,summary,word_count,method) VALUES(?,?,?,?,?)",
              (title, original_len, summary, word_count, method))
    c.commit(); c.close()

def get_summaries():
    c = _conn()
    rows = c.execute("SELECT * FROM summaries ORDER BY created_at DESC").fetchall()
    c.close()
    return [dict(r) for r in rows]

def delete_summary(sid):
    c = _conn()
    c.execute("DELETE FROM summaries WHERE id=?", (sid,))
    c.commit(); c.close()

# ── RESUME SCREENINGS ───────────────────────────────────────
def save_screening(candidate, filename, skills, education, experience,
                   match_score, rank, job_title=""):
    c = _conn()
    c.execute("""INSERT INTO resume_screenings
                 (candidate,filename,skills,education,experience,match_score,rank,job_title)
                 VALUES(?,?,?,?,?,?,?,?)""",
              (candidate, filename, skills, education, experience,
               match_score, rank, job_title))
    c.commit(); c.close()

def get_screenings():
    c = _conn()
    rows = c.execute("SELECT * FROM resume_screenings ORDER BY rank ASC").fetchall()
    c.close()
    return [dict(r) for r in rows]

def delete_screenings():
    c = _conn()
    c.execute("DELETE FROM resume_screenings")
    c.commit(); c.close()
