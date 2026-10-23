"""SQLite appointment workflow for Alone demo. Never store real clinical information here."""
from datetime import date, datetime, timezone
from modules.auth_database import get_connection
from modules.doctor_approval import get_account_type, require_approved_doctor


def initialize():
    with get_connection() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS doctor_appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slot_id INTEGER NOT NULL REFERENCES doctor_work_slots(id),
            doctor_id INTEGER NOT NULL REFERENCES users(id),
            patient_id INTEGER NOT NULL REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','confirmed','rejected','cancelled')),
            patient_note TEXT NOT NULL DEFAULT '', doctor_note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)''')
        c.execute("CREATE INDEX IF NOT EXISTS idx_appt_doctor ON doctor_appointments(doctor_id,status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_appt_patient ON doctor_appointments(patient_id,status)")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_appt_active_slot ON doctor_appointments(slot_id) WHERE status IN ('pending','confirmed')")


def _patient(patient_id):
    with get_connection() as c:
        row=c.execute('SELECT role,is_active FROM users WHERE id=?',(patient_id,)).fetchone()
    if not row or not row['is_active'] or row['role']=='admin' or get_account_type(patient_id)!='patient':
        raise PermissionError('Chỉ bệnh nhân đang hoạt động mới được đặt lịch.')


def available_slots(doctor_id, selected_date=None):
    require_approved_doctor(doctor_id)
    day = selected_date.isoformat() if isinstance(selected_date, date) else selected_date
    with get_connection() as c:
        rows = c.execute("""SELECT s.id,s.work_date,s.start_time,s.end_time
            FROM doctor_work_slots s WHERE s.doctor_id=? AND s.work_date>=?
            AND (? IS NULL OR s.work_date=?)
            AND NOT EXISTS (SELECT 1 FROM doctor_appointments a
                WHERE a.slot_id=s.id AND a.status IN ('pending','confirmed'))
            ORDER BY s.work_date,s.start_time""",
            (doctor_id,date.today().isoformat(),day,day)).fetchall()
    return [dict(r) for r in rows if datetime.fromisoformat(r['work_date']+'T'+r['start_time']) > datetime.now()]


def book(patient_id,slot_id,note=''):
    _patient(patient_id)
    if len(note)>500: raise ValueError('Ghi chú tối đa 500 ký tự.')
    with get_connection() as c:
        slot=c.execute('SELECT doctor_id,work_date,start_time FROM doctor_work_slots WHERE id=?',(slot_id,)).fetchone()
        if not slot: raise ValueError('Ca làm việc không tồn tại.')
        if datetime.fromisoformat(slot['work_date']+'T'+slot['start_time'])<=datetime.now():
            raise ValueError('Không thể đặt lịch đã qua.')
        require_approved_doctor(slot['doctor_id'])
        busy=c.execute("SELECT 1 FROM doctor_appointments WHERE slot_id=? AND status IN ('pending','confirmed')",(slot_id,)).fetchone()
        if busy: raise ValueError('Ca này đã được đặt, vui lòng chọn ca khác.')
        now=datetime.now(timezone.utc).isoformat()
        try:
            c.execute('INSERT INTO doctor_appointments(slot_id,doctor_id,patient_id,patient_note,created_at,updated_at) VALUES (?,?,?,?,?,?)',
                      (slot_id,slot['doctor_id'],patient_id,note.strip(),now,now))
        except Exception as e:
            if 'UNIQUE constraint failed' in str(e): raise ValueError('Ca này vừa được người khác đặt.') from e
            raise


def list_for_patient(patient_id):
    _patient(patient_id)
    with get_connection() as c:
        return [dict(r) for r in c.execute('''SELECT a.id,a.status,a.patient_note,a.doctor_note,s.work_date,s.start_time,s.end_time,u.full_name AS doctor_name
            FROM doctor_appointments a JOIN doctor_work_slots s ON s.id=a.slot_id JOIN users u ON u.id=a.doctor_id
            WHERE a.patient_id=? ORDER BY s.work_date DESC,s.start_time DESC''',(patient_id,)).fetchall()]


def list_for_doctor(doctor_id):
    require_approved_doctor(doctor_id)
    with get_connection() as c:
        return [dict(r) for r in c.execute('''SELECT a.id,a.status,a.patient_note,a.doctor_note,s.work_date,s.start_time,s.end_time,u.full_name AS patient_name
            FROM doctor_appointments a JOIN doctor_work_slots s ON s.id=a.slot_id JOIN users u ON u.id=a.patient_id
            WHERE a.doctor_id=? ORDER BY CASE a.status WHEN 'pending' THEN 0 WHEN 'confirmed' THEN 1 ELSE 2 END,s.work_date,s.start_time''',(doctor_id,)).fetchall()]


def doctor_action(doctor_id,appointment_id,action,note=''):
    require_approved_doctor(doctor_id)
    if action not in ('confirmed','rejected','cancelled'): raise ValueError('Hành động không hợp lệ.')
    if len(note)>500: raise ValueError('Lý do tối đa 500 ký tự.')
    with get_connection() as c:
        row=c.execute('SELECT status FROM doctor_appointments WHERE id=? AND doctor_id=?',(appointment_id,doctor_id)).fetchone()
        if not row: raise PermissionError('Không tìm thấy lịch hẹn thuộc bác sĩ này.')
        allowed={'pending':('confirmed','rejected'),'confirmed':('cancelled',)}
        if action not in allowed.get(row['status'],()): raise ValueError('Không thể thay đổi lịch hẹn ở trạng thái này.')
        if action in ('rejected','cancelled') and not note.strip(): raise ValueError('Vui lòng nhập lý do từ chối/hủy lịch.')
        c.execute('UPDATE doctor_appointments SET status=?,doctor_note=?,updated_at=? WHERE id=? AND doctor_id=?',
                  (action,note.strip(),datetime.now(timezone.utc).isoformat(),appointment_id,doctor_id))


def patient_cancel(patient_id,appointment_id):
    _patient(patient_id)
    with get_connection() as c:
        row=c.execute('SELECT status FROM doctor_appointments WHERE id=? AND patient_id=?',(appointment_id,patient_id)).fetchone()
        if not row: raise PermissionError('Không tìm thấy lịch hẹn của bạn.')
        if row['status'] not in ('pending','confirmed'): raise ValueError('Lịch hẹn không thể hủy.')
        c.execute("UPDATE doctor_appointments SET status='cancelled',updated_at=? WHERE id=? AND patient_id=?",
                  (datetime.now(timezone.utc).isoformat(),appointment_id,patient_id))
