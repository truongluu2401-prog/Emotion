"""SQLite lưu phiên AI tổng hợp riêng theo tài khoản, không sửa bảng cũ."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from modules.patient_database import init_patient_database, check_patient

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "emotionai.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_multimodal_database():
    init_patient_database()
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS multimodal_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                ai_label TEXT NOT NULL,
                ai_detail TEXT NOT NULL,
                results_json TEXT NOT NULL,
                phq9_score INTEGER,
                phq9_band TEXT,
                phq9_item9 INTEGER,
                doctor_name TEXT NOT NULL,
                assessment TEXT NOT NULL,
                doctor_notes TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(multimodal_sessions)")}
        if "patient_id" not in columns:
            conn.execute("ALTER TABLE multimodal_sessions ADD COLUMN patient_id INTEGER REFERENCES patients(id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_multimodal_patient ON multimodal_sessions(user_id, patient_id)")
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_multimodal_sessions_user
            ON multimodal_sessions(user_id, id DESC)
        """)


def _require_user(conn, user_id):
    if type(user_id) is not int:
        raise ValueError("ID tài khoản không hợp lệ.")
    row = conn.execute(
        "SELECT id FROM users WHERE id = ? AND is_active = 1",
        (user_id,)
    ).fetchone()
    if row is None:
        raise PermissionError("Tài khoản không tồn tại hoặc đã bị khóa.")


def save_multimodal_session(
    *, user_id, results, ai_label, ai_detail,
    doctor_name, assessment, doctor_notes,
    phq9_score=None, phq9_band=None, phq9_item9=None, patient_id=None
):
    """Chỉ lưu dữ liệu tổng hợp dạng nhãn/số liệu, không lưu ảnh/âm thanh gốc."""
    init_multimodal_database()
    if not results or not any(k in results for k in ("face", "voice", "heart")):
        raise ValueError("Cần phân tích ít nhất một nguồn dữ liệu.")
    if not doctor_name.strip() or not doctor_notes.strip():
        raise ValueError("Vui lòng nhập tên và kết luận của bác sĩ.")
    if phq9_score is not None and not 0 <= int(phq9_score) <= 27:
        raise ValueError("Điểm PHQ-9 không hợp lệ.")
    with _connect() as conn:
        _require_user(conn, user_id)
        if patient_id is None:
            raise ValueError('Vui lòng chọn hồ sơ bệnh nhân trước khi lưu.')
        check_patient(conn, user_id=user_id, patient_id=patient_id)
        cur = conn.execute("""
            INSERT INTO multimodal_sessions (
                user_id, created_at, ai_label, ai_detail, results_json,
                phq9_score, phq9_band, phq9_item9,
                doctor_name, assessment, doctor_notes, patient_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ai_label, ai_detail, json.dumps(results, ensure_ascii=False),
            phq9_score, phq9_band, phq9_item9,
            doctor_name.strip(), assessment, doctor_notes.strip(), patient_id
        ))
        return cur.lastrowid


def get_multimodal_sessions(*, user_id, limit=100):
    init_multimodal_database()
    with _connect() as conn:
        _require_user(conn, user_id)
        records = conn.execute("""
            SELECT id, created_at, ai_label, ai_detail,
                   results_json, phq9_score, phq9_band, phq9_item9,
                   doctor_name, assessment, doctor_notes, patient_id
            FROM multimodal_sessions
            WHERE user_id = ?
            ORDER BY id DESC LIMIT ?
        """, (user_id, max(1, min(int(limit), 500)))).fetchall()
        return [dict(row) for row in records]


def get_multimodal_session(*, user_id, session_id):
    init_multimodal_database()
    with _connect() as conn:
        _require_user(conn, user_id)
        row = conn.execute("""
            SELECT * FROM multimodal_sessions
            WHERE user_id = ? AND id = ?
        """, (user_id, session_id)).fetchone()
        return dict(row) if row else None
