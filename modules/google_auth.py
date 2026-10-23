
import sqlite3
from datetime import datetime, timezone

import streamlit as st

from modules.auth_database import get_connection


def google_is_logged_in():
    """Return False if Streamlit OIDC is not configured or not available."""
    try:
        return bool(st.user.get("is_logged_in", False))
    except (KeyError, AttributeError, RuntimeError):
        return False
    except Exception as exc:
        # Some Streamlit releases raise StreamlitAuthError for missing OIDC settings.
        if type(exc).__name__ in ("StreamlitAuthError", "StreamlitAPIException"):
            return False
        raise


def google_login():
    """Attempt real Google OAuth; do not create a fake login session."""
    try:
        st.login("google")
    except Exception as exc:
        if type(exc).__name__ in ("StreamlitAuthError", "StreamlitAPIException", "KeyError"):
            st.error(
                "Đăng nhập Google chưa được cấu hình trên máy chủ. "
                "Hãy dùng email/mật khẩu hoặc liên hệ quản trị viên để cấu hình Google OAuth."
            )
            return
        raise


def sync_google_user():
    """Đồng bộ tài khoản Google đã xác thực với SQLite."""
    if not google_is_logged_in():
        return None

    claims = st.user.to_dict()

    if claims.get("iss") not in (
        "https://accounts.google.com",
        "accounts.google.com",
    ):
        raise ValueError("Nhà cung cấp Google không hợp lệ.")

    if claims.get("email_verified") not in (True, "true", "True"):
        raise ValueError("Email Google chưa được xác minh.")

    google_id = claims.get("sub")
    email = str(claims.get("email", "")).strip().lower()
    name = claims.get("name") or email.split("@")[0]

    if not google_id or not email:
        raise ValueError("Không lấy được thông tin Google.")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")

        existing = conn.execute(
            """
            SELECT u.*
            FROM users u
            JOIN auth_identities a ON a.user_id = u.id
            WHERE a.provider = 'google'
              AND a.provider_user_id = ?
            """,
            (str(google_id),),
        ).fetchone()

        if existing:
            if not existing["is_active"]:
                raise ValueError("Tài khoản đã bị khóa.")

            return {
                "id": existing["id"],
                "full_name": existing["full_name"],
                "email": existing["email"],
                "role": existing["role"],
            }

        same_email = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        if same_email:
            raise ValueError(
                "Email này đã đăng ký bằng OTP. "
                "Hãy đăng nhập bằng mật khẩu trước. "
                "Chức năng liên kết Google sẽ làm ở bước sau."
            )

        cursor = conn.execute(
            """
            INSERT INTO users
                (full_name, email, password_hash, role, is_active, created_at)
            VALUES (?, ?, NULL, 'user', 1, ?)
            """,
            (name, email, now),
        )

        user_id = cursor.lastrowid

        conn.execute(
            """
            INSERT INTO auth_identities
                (user_id, provider, provider_user_id, created_at)
            VALUES (?, 'google', ?, ?)
            """,
            (user_id, str(google_id), now),
        )

    return {
        "id": user_id,
        "full_name": name,
        "email": email,
        "role": "user",
    }
