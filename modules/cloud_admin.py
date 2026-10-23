
import bcrypt
import streamlit as st

from modules.auth_database import get_connection


def bootstrap_cloud_admin():
    config = st.secrets.get("bootstrap_admin", {})

    email = str(config.get("email", "")).strip().lower()
    password = str(config.get("password", ""))
    full_name = str(config.get("full_name", "Quản trị viên")).strip()

    if not email or not password:
        return

    if "@" not in email or not (8 <= len(password.encode("utf-8")) <= 72):
        raise ValueError("Cấu hình Admin không hợp lệ.")

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing:
            # Không tự nâng quyền hoặc đổi mật khẩu tài khoản cũ.
            return

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        conn.execute(
            """
            INSERT INTO users (
                full_name, email, password_hash,
                role, is_active, created_at
            )
            VALUES (?, ?, ?, 'admin', 1, datetime('now'))
            """,
            (full_name, email, password_hash)
        )
