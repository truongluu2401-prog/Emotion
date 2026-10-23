"""Quản lý lịch hẹn bác sĩ / bệnh nhân trên Supabase PostgreSQL.

Giữ tương thích với modules/appointments_ui.py hiện tại.
"""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from psycopg.errors import UniqueViolation

from modules.auth_database import get_connection
from modules.doctor_approval import get_account_type, require_approved_doctor

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
ACTIVE_STATUSES = ("pending", "confirmed")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _as_time(value):
    if isinstance(value, time):
        return value.replace(tzinfo=None)
    return time.fromisoformat(str(value))


def _slot_datetime(work_date, start_time):
    """Thời điểm bắt đầu ca khám theo múi giờ Việt Nam."""
    return datetime.combine(
        _as_date(work_date), _as_time(start_time), tzinfo=VN_TZ
    )


def _display_slot(row):
    """Chuyển DATE/TIME PostgreSQL thành chuỗi cho giao diện Streamlit."""
    result = dict(row)
    if result.get("work_date") is not None:
        result["work_date"] = _as_date(result["work_date"]).isoformat()
    for key in ("start_time", "end_time"):
        if result.get(key) is not None:
            result[key] = _as_time(result[key]).strftime("%H:%M")
    return result


def initialize():
    """Kiểm tra bảng và tạo chỉ mục chống đặt trùng ca."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            for table in ("users", "doctor_work_slots", "doctor_appointments"):
                cur.execute(
                    "SELECT to_regclass(%s) AS table_name",
                    (f"public.{table}",),
                )
                if cur.fetchone()["table_name"] is None:
                    raise RuntimeError(f"Supabase chưa có bảng {table}.")

            # Nếu dữ liệu cũ có lịch trùng, PostgreSQL sẽ báo lỗi ở đây.
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_appt_active_slot
                ON doctor_appointments(slot_id)
                WHERE status IN ('pending', 'confirmed')
            """)


def _patient(patient_id):
    """Xác minh tài khoản bệnh nhân còn hoạt động."""
    if type(patient_id) is not int:
        raise PermissionError("ID bệnh nhân không hợp lệ.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role, is_active FROM users WHERE id = %s",
                (patient_id,),
            )
            row = cur.fetchone()

    if (
        row is None
        or not bool(row["is_active"])
        or row["role"] == "admin"
        or get_account_type(patient_id) != "patient"
    ):
        raise PermissionError(
            "Chỉ bệnh nhân đang hoạt động mới được đặt lịch."
        )


def available_slots(doctor_id, selected_date=None):
    """Lấy ca chưa có lịch hẹn, có thể lọc theo ngày.

    Không dùng biểu thức '%s IS NULL' để tránh lỗi
    IndeterminateDatatype của PostgreSQL.
    """
    require_approved_doctor(doctor_id)

    today = datetime.now(VN_TZ).date()
    sql = """
        SELECT s.id, s.work_date, s.start_time, s.end_time
        FROM doctor_work_slots AS s
        WHERE s.doctor_id = %s
          AND s.work_date::date >= %s::date
          AND NOT EXISTS (
              SELECT 1
              FROM doctor_appointments AS a
              WHERE a.slot_id = s.id
                AND a.status IN ('pending', 'confirmed')
          )
    """
    params = [doctor_id, today.isoformat()]

    if selected_date is not None:
        day = _as_date(selected_date)
        sql += " AND s.work_date::date = %s::date"
        params.append(day.isoformat())

    sql += " ORDER BY s.work_date::date, s.start_time"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()

    now = datetime.now(VN_TZ)
    return [
        _display_slot(row)
        for row in rows
        if _slot_datetime(row["work_date"], row["start_time"]) > now
    ]


def book(patient_id, slot_id, note=""):
    """Bệnh nhân đặt ca khám; khóa dòng để tránh đặt trùng đồng thời."""
    _patient(patient_id)
    note = (note or "").strip()
    if len(note) > 500:
        raise ValueError("Ghi chú tối đa 500 ký tự.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT doctor_id, work_date, start_time
                FROM doctor_work_slots
                WHERE id = %s
                FOR UPDATE
                """,
                (slot_id,),
            )
            slot = cur.fetchone()
            if slot is None:
                raise ValueError("Ca làm việc không tồn tại.")

            if _slot_datetime(
                slot["work_date"], slot["start_time"]
            ) <= datetime.now(VN_TZ):
                raise ValueError("Không thể đặt lịch đã qua.")

            require_approved_doctor(slot["doctor_id"])

            cur.execute(
                """
                SELECT 1
                FROM doctor_appointments
                WHERE slot_id = %s
                  AND status IN ('pending', 'confirmed')
                """,
                (slot_id,),
            )
            if cur.fetchone() is not None:
                raise ValueError(
                    "Ca này đã được đặt, vui lòng chọn ca khác."
                )

            now = _now()
            try:
                cur.execute(
                    """
                    INSERT INTO doctor_appointments (
                        slot_id, doctor_id, patient_id,
                        patient_note, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (slot_id, slot["doctor_id"], patient_id, note, now, now),
                )
            except UniqueViolation as exc:
                raise ValueError(
                    "Ca này vừa được người khác đặt."
                ) from exc


def list_for_patient(patient_id):
    """Danh sách lịch hẹn của bệnh nhân hiện tại."""
    _patient(patient_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.id, a.status, a.patient_note, a.doctor_note,
                       s.work_date, s.start_time, s.end_time,
                       u.full_name AS doctor_name
                FROM doctor_appointments AS a
                JOIN doctor_work_slots AS s ON s.id = a.slot_id
                JOIN users AS u ON u.id = a.doctor_id
                WHERE a.patient_id = %s
                ORDER BY s.work_date::date DESC, s.start_time DESC
                """,
                (patient_id,),
            )
            return [_display_slot(row) for row in cur.fetchall()]


def list_for_doctor(doctor_id):
    """Danh sách lịch hẹn của bác sĩ hiện tại."""
    require_approved_doctor(doctor_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.id, a.status, a.patient_note, a.doctor_note,
                       s.work_date, s.start_time, s.end_time,
                       u.full_name AS patient_name
                FROM doctor_appointments AS a
                JOIN doctor_work_slots AS s ON s.id = a.slot_id
                JOIN users AS u ON u.id = a.patient_id
                WHERE a.doctor_id = %s
                ORDER BY
                    CASE a.status
                        WHEN 'pending' THEN 0
                        WHEN 'confirmed' THEN 1
                        ELSE 2
                    END,
                    s.work_date, s.start_time
                """,
                (doctor_id,),
            )
            return [_display_slot(row) for row in cur.fetchall()]


def doctor_action(doctor_id, appointment_id, action, note=""):
    """Bác sĩ xác nhận, từ chối hoặc hủy lịch hẹn."""
    require_approved_doctor(doctor_id)
    if action not in ("confirmed", "rejected", "cancelled"):
        raise ValueError("Hành động không hợp lệ.")

    note = (note or "").strip()
    if len(note) > 500:
        raise ValueError("Lý do tối đa 500 ký tự.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status
                FROM doctor_appointments
                WHERE id = %s AND doctor_id = %s
                FOR UPDATE
                """,
                (appointment_id, doctor_id),
            )
            row = cur.fetchone()
            if row is None:
                raise PermissionError(
                    "Không tìm thấy lịch hẹn thuộc bác sĩ này."
                )

            allowed = {
                "pending": ("confirmed", "rejected"),
                "confirmed": ("cancelled",),
            }
            if action not in allowed.get(row["status"], ()):
                raise ValueError(
                    "Không thể thay đổi lịch hẹn ở trạng thái này."
                )

            if action in ("rejected", "cancelled") and not note:
                raise ValueError(
                    "Vui lòng nhập lý do từ chối/hủy lịch."
                )

            cur.execute(
                """
                UPDATE doctor_appointments
                SET status = %s, doctor_note = %s, updated_at = %s
                WHERE id = %s AND doctor_id = %s
                """,
                (action, note, _now(), appointment_id, doctor_id),
            )


def patient_cancel(patient_id, appointment_id):
    """Bệnh nhân hủy lịch đang chờ hoặc đã xác nhận."""
    _patient(patient_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status
                FROM doctor_appointments
                WHERE id = %s AND patient_id = %s
                FOR UPDATE
                """,
                (appointment_id, patient_id),
            )
            row = cur.fetchone()
            if row is None:
                raise PermissionError(
                    "Không tìm thấy lịch hẹn của bạn."
                )
            if row["status"] not in ACTIVE_STATUSES:
                raise ValueError("Lịch hẹn không thể hủy.")

            cur.execute(
                """
                UPDATE doctor_appointments
                SET status = 'cancelled', updated_at = %s
                WHERE id = %s AND patient_id = %s
                """,
                (_now(), appointment_id, patient_id),
            )


if __name__ == "__main__":
    initialize()
    print("SUPABASE APPOINTMENTS OK")
