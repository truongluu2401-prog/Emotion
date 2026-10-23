
from datetime import datetime, timezone

import psycopg
import streamlit as st
from psycopg.rows import dict_row


def get_connection():
    """Kết nối Supabase PostgreSQL."""
    database_url = st.secrets["database"]["url"]

    return psycopg.connect(
        database_url,
        row_factory=dict_row
    )


def init_auth_database():
    """
    Kiểm tra các bảng tài khoản trên Supabase.

    Các bảng đã được tạo bằng Supabase SQL Editor.
    Không tự tạo lại để tránh sai cấu trúc.
    """
    required_tables = (
        "users",
        "auth_identities",
        "account_types",
        "doctor_applications",
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            for table_name in required_tables:
                cur.execute(
                    "SELECT to_regclass(%s) AS table_name",
                    (f"public.{table_name}",)
                )

                result = cur.fetchone()

                if result["table_name"] is None:
                    raise RuntimeError(
                        f"Supabase chưa có bảng: {table_name}"
                    )


def get_user_by_email(email):
    """Tìm người dùng theo email trên Supabase."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM users
                WHERE LOWER(email) = LOWER(%s)
                LIMIT 1
                """,
                (email.strip(),)
            )

            return cur.fetchone()


def get_user_by_id(user_id):
    """Tìm người dùng theo ID trên Supabase."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM users
                WHERE id = %s
                """,
                (user_id,)
            )

            return cur.fetchone()


def create_user(
    full_name,
    email,
    password_hash,
    account_type="patient",
    doctor_application=None
):
    """Đăng ký tài khoản Bệnh nhân hoặc Bác sĩ trên Supabase."""
    full_name = full_name.strip()
    email = email.strip().lower()

    if not full_name:
        raise ValueError("Họ tên không được để trống.")

    if not email:
        raise ValueError("Email không được để trống.")

    if not password_hash:
        raise ValueError("Mật khẩu chưa được mã hóa.")

    if account_type not in ("patient", "doctor"):
        raise ValueError("Vai trò không hợp lệ.")

    if account_type == "doctor" and not doctor_application:
        raise ValueError("Thiếu hồ sơ bác sĩ.")

    created_at = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO users (
                    full_name,
                    email,
                    password_hash,
                    role,
                    is_active,
                    created_at
                )
                VALUES (%s, %s, %s, 'user', 1, %s)
                RETURNING id
                """,
                (
                    full_name,
                    email,
                    password_hash,
                    created_at
                )
            )

            user_id = cur.fetchone()["id"]

            cur.execute(
                """
                INSERT INTO account_types (
                    user_id,
                    account_type
                )
                VALUES (%s, %s)
                """,
                (user_id, account_type)
            )

            if account_type == "doctor":
                app = doctor_application

                cur.execute(
                    """
                    INSERT INTO doctor_applications (
                        user_id,
                        school,
                        degree,
                        specialty,
                        license_number,
                        experience_years,
                        bio,
                        document_name,
                        document_data,
                        updated_at
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        user_id,
                        app["school"],
                        app["degree"],
                        app["specialty"],
                        app["license_number"],
                        app["experience_years"],
                        app.get("bio", ""),
                        app["document_name"],
                        app["document_data"],
                        datetime.now(timezone.utc).isoformat()
                    )
                )

        conn.commit()
        return user_id


def get_all_users():
    """Lấy danh sách tài khoản cho Admin."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    full_name,
                    email,
                    role,
                    is_active,
                    created_at
                FROM users
                ORDER BY id DESC
                """
            )

            return cur.fetchall()


def get_user_count():
    """Đếm số tài khoản trên Supabase."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS total FROM users"
            )

            return cur.fetchone()["total"]


if __name__ == "__main__":
    init_auth_database()
    print("SUPABASE AUTH DATABASE OK")
