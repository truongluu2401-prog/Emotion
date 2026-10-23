"""Hồ sơ bệnh nhân tối giản, tách riêng theo tài khoản người tạo."""
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "emotionai.db"

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_patient_database():
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER NOT NULL,
            patient_code TEXT NOT NULL,
            display_name TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            UNIQUE(owner_user_id, patient_code),
            FOREIGN KEY(owner_user_id) REFERENCES users(id)
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_patients_owner ON patients(owner_user_id)")

def add_patient(*, user_id, code, name, notes=''):
    init_patient_database()
    code, name = code.strip().upper(), name.strip()
    if not code or not name or len(code)>40 or len(name)>120:
        raise ValueError('Nhập mã bệnh nhân (tối đa 40 ký tự) và tên hiển thị (tối đa 120 ký tự).')
    with connect() as conn:
        active=conn.execute('SELECT 1 FROM users WHERE id=? AND is_active=1',(user_id,)).fetchone()
        if not active: raise PermissionError('Tài khoản không hợp lệ hoặc đã bị khóa.')
        try:
            cur=conn.execute("""INSERT INTO patients(owner_user_id, patient_code, display_name, notes, created_at)
                VALUES(?,?,?,?,?)""",(user_id,code,name,notes.strip(),datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        except sqlite3.IntegrityError as exc:
            raise ValueError('Mã bệnh nhân đã tồn tại trong tài khoản này.') from exc
        return cur.lastrowid

def get_patients(*, user_id):
    init_patient_database()
    with connect() as conn:
        return [dict(x) for x in conn.execute("""SELECT id, patient_code, display_name, notes, created_at
            FROM patients WHERE owner_user_id=? ORDER BY id DESC""",(user_id,)).fetchall()]

def check_patient(conn, *, user_id, patient_id):
    if type(patient_id) is not int:
        raise ValueError('Chưa chọn bệnh nhân hợp lệ.')
    found=conn.execute('SELECT 1 FROM patients WHERE id=? AND owner_user_id=?',(patient_id,user_id)).fetchone()
    if not found: raise PermissionError('Không có quyền sử dụng hồ sơ bệnh nhân này.')
