
"""Quản lý vai trò và duyệt hồ sơ Bác sĩ bằng Supabase PostgreSQL."""

from datetime import datetime, timezone

from modules.auth_database import get_connection


def initialize():
    """Kiểm tra các bảng đã được tạo trên Supabase."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            for table in ("account_types", "doctor_applications"):
                cur.execute(
                    "SELECT to_regclass(%s) AS table_name",
                    (f"public.{table}",)
                )
                if cur.fetchone()["table_name"] is None:
                    raise RuntimeError(
                        f"Supabase chưa có bảng {table}"
                    )


def register_account_type(user_id, account_type, application=None):
    if account_type not in ("patient", "doctor"):
        raise ValueError("Vai trò không hợp lệ.")

    if account_type == "doctor":
        if not application:
            raise ValueError("Thiếu hồ sơ bác sĩ.")

        required = (
            "school", "degree", "specialty",
            "license_number", "document_name", "document_data"
        )
        if any(not application.get(k) for k in required):
            raise ValueError("Hồ sơ bác sĩ chưa đầy đủ.")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO account_types (user_id, account_type)
                VALUES (%s, %s)
                """,
                (user_id, account_type)
            )

            if account_type == "doctor":
                cur.execute(
                    """
                    INSERT INTO doctor_applications (
                        user_id, school, degree, specialty,
                        license_number, experience_years, bio,
                        document_name, document_data, updated_at
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        user_id,
                        application["school"],
                        application["degree"],
                        application["specialty"],
                        application["license_number"],
                        application["experience_years"],
                        application.get("bio", ""),
                        application["document_name"],
                        application["document_data"],
                        datetime.now(timezone.utc).isoformat()
                    )
                )


def get_account_type(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT account_type
                FROM account_types
                WHERE user_id = %s
                """,
                (user_id,)
            )
            row = cur.fetchone()

    return row["account_type"] if row else "patient"


def get_application(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    user_id, school, degree, specialty,
                    license_number, experience_years, bio,
                    document_name, status, review_note
                FROM doctor_applications
                WHERE user_id = %s
                """,
                (user_id,)
            )
            return cur.fetchone()


def require_approved_doctor(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM doctor_applications d
                JOIN users u ON u.id = d.user_id
                WHERE d.user_id = %s
                  AND d.status = 'approved'
                  AND u.is_active = 1
                """,
                (user_id,)
            )
            row = cur.fetchone()

    if not row:
        raise PermissionError(
            "Tài khoản bác sĩ chưa được Admin duyệt."
        )


def pending_applications(admin_id):
    from modules.admin_service import require_admin
    require_admin(admin_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    d.user_id, u.full_name, u.email,
                    d.school, d.degree, d.specialty,
                    d.license_number, d.experience_years,
                    d.bio, d.document_name, d.status,
                    d.review_note
                FROM doctor_applications d
                JOIN users u ON u.id = d.user_id
                ORDER BY d.updated_at DESC
                """
            )
            return cur.fetchall()


def download_document(admin_id, doctor_id):
    from modules.admin_service import require_admin
    require_admin(admin_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT document_data
                FROM doctor_applications
                WHERE user_id = %s
                """,
                (doctor_id,)
            )
            row = cur.fetchone()

    if not row:
        return None

    data = row["document_data"]
    return bytes(data) if data is not None else None


def review_application(admin_id, doctor_id, approve, note):
    from modules.admin_service import require_admin
    require_admin(admin_id)

    status = "approved" if approve else "rejected"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE doctor_applications
                SET status = %s,
                    review_note = %s,
                    reviewed_by = %s,
                    updated_at = %s
                WHERE user_id = %s
                  AND status = 'pending'
                """,
                (
                    status,
                    note.strip(),
                    admin_id,
                    datetime.now(timezone.utc).isoformat(),
                    doctor_id
                )
            )

            if cur.rowcount != 1:
                raise ValueError(
                    "Hồ sơ không còn ở trạng thái chờ duyệt."
                )


def approved_doctors():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    u.id, u.full_name, d.school, d.degree,
                    d.specialty, d.experience_years, d.bio
                FROM doctor_applications d
                JOIN users u ON u.id = d.user_id
                WHERE d.status = 'approved'
                  AND u.is_active = 1
                ORDER BY u.full_name
                """
            )
            return cur.fetchall()


if __name__ == "__main__":
    initialize()
    print("SUPABASE DOCTOR APPROVAL OK")
