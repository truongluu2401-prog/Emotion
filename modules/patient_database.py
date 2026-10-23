
"""Quản lý hồ sơ bệnh nhân trên Supabase PostgreSQL."""

from datetime import datetime, timezone

from psycopg import IntegrityError

from modules.auth_database import get_connection


def connect():
    """Kết nối Supabase PostgreSQL."""
    return get_connection()


def init_patient_database():
    """Kiểm tra bảng patients trên Supabase."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT to_regclass('public.patients') AS table_name"
            )
            result = cur.fetchone()

            if result["table_name"] is None:
                raise RuntimeError(
                    "Supabase chưa có bảng patients."
                )


def add_patient(*, user_id, code, name, notes=""):
    """Tạo hồ sơ bệnh nhân cho tài khoản hiện tại."""
    code = code.strip().upper()
    name = name.strip()

    if (
        not code
        or not name
        or len(code) > 40
        or len(name) > 120
    ):
        raise ValueError(
            "Nhập mã bệnh nhân (tối đa 40 ký tự) "
            "và tên hiển thị (tối đa 120 ký tự)."
        )

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM users
                WHERE id = %s
                  AND is_active = 1
                """,
                (user_id,)
            )

            if not cur.fetchone():
                raise PermissionError(
                    "Tài khoản không hợp lệ hoặc đã bị khóa."
                )

            try:
                cur.execute(
                    """
                    INSERT INTO patients (
                        owner_user_id,
                        patient_code,
                        display_name,
                        notes,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        user_id,
                        code,
                        name,
                        notes.strip(),
                        datetime.now(timezone.utc).isoformat()
                    )
                )

                patient_id = cur.fetchone()["id"]

            except IntegrityError as exc:
                raise ValueError(
                    "Không thể tạo hồ sơ. "
                    "Mã bệnh nhân có thể đã tồn tại "
                    "trong tài khoản này."
                ) from exc

    return patient_id


def get_patients(*, user_id):
    """Lấy danh sách hồ sơ thuộc tài khoản hiện tại."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    patient_code,
                    display_name,
                    notes,
                    created_at
                FROM patients
                WHERE owner_user_id = %s
                ORDER BY id DESC
                """,
                (user_id,)
            )

            return cur.fetchall()


def check_patient(conn, *, user_id, patient_id):
    """Kiểm tra quyền truy cập hồ sơ bệnh nhân."""
    if type(patient_id) is not int:
        raise ValueError(
            "Chưa chọn bệnh nhân hợp lệ."
        )

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM patients
            WHERE id = %s
              AND owner_user_id = %s
            """,
            (patient_id, user_id)
        )

        found = cur.fetchone()

    if not found:
        raise PermissionError(
            "Không có quyền sử dụng hồ sơ bệnh nhân này."
        )


if __name__ == "__main__":
    init_patient_database()
    print("SUPABASE PATIENT DATABASE OK")
