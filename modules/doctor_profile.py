"""Doctor photo and availability management (SQLite demo)."""
from datetime import date, datetime, time, timezone
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from modules.auth_database import get_connection
from modules.doctor_approval import get_account_type


def initialize():
    with get_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS doctor_photos (
            doctor_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            photo_data BLOB NOT NULL, updated_at TEXT NOT NULL)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS doctor_work_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            work_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(doctor_id,work_date,start_time,end_time))''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_doctor_work_slots ON doctor_work_slots(doctor_id,work_date)')


def _require_doctor(doctor_id):
    if get_account_type(doctor_id) != 'doctor':
        raise PermissionError('Chỉ tài khoản bác sĩ được cập nhật hồ sơ bác sĩ.')


def save_photo(doctor_id, raw):
    _require_doctor(doctor_id)
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError('Ảnh phải nhỏ hơn hoặc bằng 2 MB.')
    try:
        with Image.open(BytesIO(raw)) as im:
            if im.format not in ('PNG','JPEG','WEBP'):
                raise ValueError('Chỉ chấp nhận PNG, JPG hoặc WEBP.')
            im.thumbnail((640, 640))
            converted = im.convert('RGB')
            out = BytesIO()
            converted.save(out, format='JPEG', quality=85)
            photo = out.getvalue()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError('File không phải ảnh hợp lệ.') from exc
    with get_connection() as conn:
        conn.execute('''INSERT INTO doctor_photos(doctor_id,photo_data,updated_at) VALUES (?,?,?)
            ON CONFLICT(doctor_id) DO UPDATE SET photo_data=excluded.photo_data, updated_at=excluded.updated_at''',
            (doctor_id, photo, datetime.now(timezone.utc).isoformat()))


def get_photo(doctor_id):
    with get_connection() as conn:
        row = conn.execute('SELECT photo_data FROM doctor_photos WHERE doctor_id=?',(doctor_id,)).fetchone()
    return bytes(row['photo_data']) if row else None


def list_slots(doctor_id, from_date=None, to_date=None):
    sql = 'SELECT id,work_date,start_time,end_time FROM doctor_work_slots WHERE doctor_id=?'
    args = [doctor_id]
    if from_date:
        sql += ' AND work_date>=?'
        args.append(from_date.isoformat() if isinstance(from_date,date) else str(from_date))
    if to_date:
        sql += ' AND work_date<=?'
        args.append(to_date.isoformat() if isinstance(to_date,date) else str(to_date))
    sql += ' ORDER BY work_date,start_time'
    with get_connection() as conn:
        return [dict(row) for row in conn.execute(sql,args).fetchall()]


def add_slot(doctor_id, work_date, start_time, end_time):
    _require_doctor(doctor_id)
    if work_date < date.today():
        raise ValueError('Không thể thêm lịch trong quá khứ.')
    if not isinstance(start_time,time) or not isinstance(end_time,time) or start_time >= end_time:
        raise ValueError('Giờ kết thúc phải sau giờ bắt đầu.')
    day, start, end = work_date.isoformat(), start_time.strftime('%H:%M'), end_time.strftime('%H:%M')
    with get_connection() as conn:
        overlapping = conn.execute('''SELECT 1 FROM doctor_work_slots
            WHERE doctor_id=? AND work_date=? AND start_time<? AND end_time>?''',
            (doctor_id,day,end,start)).fetchone()
        if overlapping:
            raise ValueError('Ca làm việc trùng với lịch đã tạo.')
        conn.execute('''INSERT INTO doctor_work_slots(doctor_id,work_date,start_time,end_time,created_at)
            VALUES (?,?,?,?,?)''',(doctor_id,day,start,end,datetime.now(timezone.utc).isoformat()))


def remove_slot(doctor_id, slot_id):
    _require_doctor(doctor_id)
    with get_connection() as conn:
        conn.execute('DELETE FROM doctor_work_slots WHERE id=? AND doctor_id=?',(slot_id,doctor_id))
