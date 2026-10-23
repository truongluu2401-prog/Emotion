"""Đăng ký bác sĩ và duyệt hồ sơ (demo SQLite, không dùng dữ liệu thật)."""
from datetime import datetime, timezone
from modules.auth_database import get_connection

def initialize():
    with get_connection() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS account_types (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            account_type TEXT NOT NULL CHECK(account_type IN ('patient','doctor'))
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS doctor_applications (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            school TEXT NOT NULL, degree TEXT NOT NULL, specialty TEXT NOT NULL,
            license_number TEXT NOT NULL, experience_years INTEGER NOT NULL,
            bio TEXT NOT NULL DEFAULT '', document_name TEXT NOT NULL,
            document_data BLOB NOT NULL, status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','approved','rejected')),
            review_note TEXT NOT NULL DEFAULT '', reviewed_by INTEGER,
            updated_at TEXT NOT NULL
        )""")

def register_account_type(user_id, account_type, application=None):
    if account_type not in ('patient','doctor'): raise ValueError('Vai trò không hợp lệ')
    with get_connection() as c:
        c.execute('INSERT INTO account_types(user_id,account_type) VALUES (?,?)',(user_id,account_type))
        if account_type=='doctor':
            if not application: raise ValueError('Thiếu hồ sơ bác sĩ')
            fields=['school','degree','specialty','license_number','bio','document_name','document_data']
            if any(not application.get(k) for k in fields if k!='bio'): raise ValueError('Hồ sơ bác sĩ chưa đầy đủ')
            c.execute("""INSERT INTO doctor_applications
                (user_id,school,degree,specialty,license_number,experience_years,bio,document_name,document_data,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",(
                user_id,application['school'],application['degree'],application['specialty'],
                application['license_number'],application['experience_years'],application.get('bio',''),
                application['document_name'],application['document_data'],datetime.now(timezone.utc).isoformat()))

def get_account_type(user_id):
    with get_connection() as c:
        row=c.execute('SELECT account_type FROM account_types WHERE user_id=?',(user_id,)).fetchone()
    return row['account_type'] if row else 'patient'  # legacy users

def get_application(user_id):
    with get_connection() as c:
        row=c.execute('SELECT user_id,school,degree,specialty,license_number,experience_years,bio,document_name,status,review_note FROM doctor_applications WHERE user_id=?',(user_id,)).fetchone()
    return dict(row) if row else None

def require_approved_doctor(user_id):
    with get_connection() as c:
        row=c.execute("""SELECT 1 FROM doctor_applications d JOIN users u ON u.id=d.user_id
            WHERE d.user_id=? AND d.status='approved' AND u.is_active=1""",(user_id,)).fetchone()
    if not row: raise PermissionError('Tài khoản bác sĩ chưa được Admin duyệt.')

def pending_applications(admin_id):
    from modules.admin_service import require_admin
    require_admin(admin_id)
    with get_connection() as c:
        rows=c.execute("""SELECT d.user_id,u.full_name,u.email,d.school,d.degree,d.specialty,
            d.license_number,d.experience_years,d.bio,d.document_name,d.status,d.review_note
            FROM doctor_applications d JOIN users u ON u.id=d.user_id ORDER BY d.updated_at DESC""").fetchall()
    return [dict(r) for r in rows]

def download_document(admin_id,doctor_id):
    from modules.admin_service import require_admin
    require_admin(admin_id)
    with get_connection() as c:
        row=c.execute('SELECT document_data FROM doctor_applications WHERE user_id=?',(doctor_id,)).fetchone()
    return row['document_data'] if row else None

def review_application(admin_id, doctor_id, approve, note):
    from modules.admin_service import require_admin
    require_admin(admin_id)
    with get_connection() as c:
        cur=c.execute("""UPDATE doctor_applications SET status=?,review_note=?,reviewed_by=?,updated_at=?
            WHERE user_id=? AND status='pending' """,('approved' if approve else 'rejected',note.strip(),admin_id,datetime.now(timezone.utc).isoformat(),doctor_id))
        if cur.rowcount != 1: raise ValueError('Hồ sơ không còn ở trạng thái chờ duyệt.')

def approved_doctors():
    with get_connection() as c:
        rows=c.execute("""SELECT u.id,u.full_name,d.school,d.degree,d.specialty,d.experience_years,d.bio
            FROM doctor_applications d JOIN users u ON u.id=d.user_id
            WHERE d.status='approved' AND u.is_active=1 ORDER BY u.full_name""").fetchall()
    return [dict(r) for r in rows]
