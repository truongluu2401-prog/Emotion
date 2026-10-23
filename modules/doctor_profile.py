
"""Quản lý ảnh và lịch làm việc bác sĩ trên Supabase."""

from datetime import date, datetime, time, timedelta, timezone
from io import BytesIO

from PIL import Image, UnidentifiedImageError
from psycopg.errors import UniqueViolation

from modules.auth_database import get_connection
from modules.doctor_approval import get_account_type


def initialize():
    """Kiểm tra các bảng đã tạo trên Supabase."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            for table in (
                "doctor_photos",
                "doctor_work_slots",
                "doctor_appointments",
            ):
                cur.execute(
                    "SELECT to_regclass(%s) AS table_name",
                    (f"public.{table}",)
                )
                if cur.fetchone()["table_name"] is None:
                    raise RuntimeError(
                        f"Supabase chưa có bảng {table}."
                    )


def _require_doctor(doctor_id):
    if get_account_type(doctor_id) != "doctor":
        raise PermissionError(
            "Chỉ tài khoản bác sĩ được cập nhật hồ sơ bác sĩ."
        )


def save_photo(doctor_id, raw):
    """Lưu ảnh đại diện bác sĩ vào PostgreSQL."""
    _require_doctor(doctor_id)

    if len(raw) > 2 * 1024 * 1024:
        raise ValueError("Ảnh phải nhỏ hơn hoặc bằng 2 MB.")

    try:
        with Image.open(BytesIO(raw)) as im:
            if im.format not in ("PNG", "JPEG", "WEBP"):
                raise ValueError(
                    "Chỉ chấp nhận PNG, JPG hoặc WEBP."
                )

            im.thumbnail((640, 640))
            converted = im.convert("RGB")
            out = BytesIO()
            converted.save(out, format="JPEG", quality=85)
            photo = out.getvalue()

    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(
            "File không phải ảnh hợp lệ."
        ) from exc

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO doctor_photos (
                    doctor_id, photo_data, updated_at
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (doctor_id)
                DO UPDATE SET
                    photo_data = EXCLUDED.photo_data,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    doctor_id,
                    photo,
                    datetime.now(timezone.utc).isoformat()
                )
            )


def get_photo(doctor_id):
    """Lấy ảnh bác sĩ từ Supabase."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT photo_data
                FROM doctor_photos
                WHERE doctor_id = %s
                """,
                (doctor_id,)
            )
            row = cur.fetchone()

    if not row or row["photo_data"] is None:
        return None

    return bytes(row["photo_data"])


def list_slots(doctor_id, from_date=None, to_date=None):
    """Danh sách ca làm việc của bác sĩ."""
    sql = """
        SELECT id, work_date, start_time, end_time
        FROM doctor_work_slots
        WHERE doctor_id = %s
    """
    args = [doctor_id]

    if from_date:
        sql += " AND work_date >= %s"
        args.append(
            from_date.isoformat()
            if isinstance(from_date, date)
            else str(from_date)
        )

    if to_date:
        sql += " AND work_date <= %s"
        args.append(
            to_date.isoformat()
            if isinstance(to_date, date)
            else str(to_date)
        )

    sql += " ORDER BY work_date, start_time"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(args))
            return cur.fetchall()


def add_slot(doctor_id, work_date, start_time, end_time):
    """Thêm một ca làm việc."""
    _require_doctor(doctor_id)

    if work_date < date.today():
        raise ValueError(
            "Không thể thêm lịch trong quá khứ."
        )

    if (
        not isinstance(start_time, time)
        or not isinstance(end_time, time)
        or start_time >= end_time
    ):
        raise ValueError(
            "Giờ kết thúc phải sau giờ bắt đầu."
        )

    day = work_date.isoformat()
    start = start_time.strftime("%H:%M")
    end = end_time.strftime("%H:%M")

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Khóa theo bác sĩ để các thao tác thêm lịch
            # qua ứng dụng không chạy đồng thời.
            cur.execute(
                "SELECT pg_advisory_xact_lock(%s)",
                (doctor_id,)
            )

            cur.execute(
                """
                SELECT 1
                FROM doctor_work_slots
                WHERE doctor_id = %s
                  AND work_date = %s
                  AND start_time < %s
                  AND end_time > %s
                """,
                (doctor_id, day, end, start)
            )

            if cur.fetchone():
                raise ValueError(
                    "Ca làm việc trùng với lịch đã tạo."
                )

            try:
                cur.execute(
                    """
                    INSERT INTO doctor_work_slots (
                        doctor_id, work_date,
                        start_time, end_time, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        doctor_id,
                        day,
                        start,
                        end,
                        datetime.now(timezone.utc).isoformat()
                    )
                )
            except UniqueViolation as exc:
                raise ValueError(
                    "Ca làm việc đã tồn tại."
                ) from exc


def remove_slot(doctor_id, slot_id):
    """Xóa ca nếu không có lịch hẹn đang hoạt động."""
    _require_doctor(doctor_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM doctor_work_slots
                WHERE id = %s AND doctor_id = %s
                FOR UPDATE
                """,
                (slot_id, doctor_id)
            )

            if cur.fetchone() is None:
                raise ValueError(
                    "Không tìm thấy ca làm việc."
                )

            cur.execute(
                """
                SELECT 1
                FROM doctor_appointments
                WHERE slot_id = %s
                  AND status IN ('pending', 'confirmed')
                """,
                (slot_id,)
            )

            if cur.fetchone():
                raise ValueError(
                    "Ca đang có lịch hẹn chờ xác nhận "
                    "hoặc đã xác nhận. "
                    "Hãy xử lý lịch hẹn trước khi xóa ca."
                )

            cur.execute(
                """
                DELETE FROM doctor_work_slots
                WHERE id = %s AND doctor_id = %s
                """,
                (slot_id, doctor_id)
            )


def add_week_slots(
    doctor_id,
    week_start,
    weekdays,
    start_time,
    end_time
):
    """Thêm nhiều ca trong một tuần, cùng giao dịch."""
    _require_doctor(doctor_id)

    if (
        not isinstance(week_start, date)
        or week_start.weekday() != 0
    ):
        raise ValueError(
            "Ngày bắt đầu tuần phải là thứ Hai."
        )

    if (
        not isinstance(start_time, time)
        or not isinstance(end_time, time)
        or start_time >= end_time
    ):
        raise ValueError(
            "Giờ kết thúc phải sau giờ bắt đầu."
        )

    days = sorted(set(weekdays))

    if (
        not days
        or any(
            type(day) is not int or day not in range(7)
            for day in days
        )
    ):
        raise ValueError(
            "Hãy chọn ít nhất một ngày hợp lệ trong tuần."
        )

    start = start_time.strftime("%H:%M")
    end = end_time.strftime("%H:%M")
    now = datetime.now(timezone.utc).isoformat()

    dates = [
        week_start + timedelta(days=d)
        for d in days
    ]
    dates = [
        d for d in dates
        if d >= date.today()
    ]

    if not dates:
        raise ValueError(
            "Các ngày được chọn đều đã qua."
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pg_advisory_xact_lock(%s)",
                (doctor_id,)
            )

            for d in dates:
                day = d.isoformat()

                cur.execute(
                    """
                    SELECT 1
                    FROM doctor_work_slots
                    WHERE doctor_id = %s
                      AND work_date = %s
                      AND start_time < %s
                      AND end_time > %s
                    """,
                    (doctor_id, day, end, start)
                )

                if cur.fetchone():
                    raise ValueError(
                        f"Lịch ngày {day} bị trùng. "
                        "Chưa thêm ca nào."
                    )

            for d in dates:
                cur.execute(
                    """
                    INSERT INTO doctor_work_slots (
                        doctor_id, work_date,
                        start_time, end_time, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        doctor_id,
                        d.isoformat(),
                        start,
                        end,
                        now
                    )
                )

    return len(dates)


if __name__ == "__main__":
    initialize()
    print("SUPABASE DOCTOR PROFILE OK")
