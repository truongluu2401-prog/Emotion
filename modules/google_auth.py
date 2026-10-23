
from datetime import datetime, timezone

import streamlit as st

from modules.auth_database import get_connection


def google_is_logged_in():
    """Kiểm tra trạng thái đăng nhập Google."""
    try:
        return bool(st.user.get("is_logged_in", False))
    except (KeyError, AttributeError, RuntimeError):
        return False
    except Exception as exc:
        if type(exc).__name__ in (
            "StreamlitAuthError",
            "StreamlitAPIException"
        ):
            return False
        raise


def google_login():
    """Đăng nhập bằng Google OAuth thật."""
    try:
        st.login("google")
    except Exception as exc:
        if type(exc).__name__ in (
            "StreamlitAuthError",
            "StreamlitAPIException",
            "KeyError"
        ):
            st.error(
                "Đăng nhập Google chưa được cấu hình. "
                "Hãy kiểm tra Google OAuth."
            )
            return
        raise


def sync_google_user():
    """Đồng bộ tài khoản Google vào Supabase."""
    if not google_is_logged_in():
        return None

    claims = st.user.to_dict()

    if claims.get("iss") not in (
        "https://accounts.google.com",
        "accounts.google.com"
    ):
        raise ValueError(
            "Nhà cung cấp Google không hợp lệ."
        )

    if claims.get("email_verified") not in (
        True, "true", "True"
    ):
        raise ValueError(
            "Email Google chưa được xác minh."
        )

    google_id = claims.get("sub")
    email = str(
        claims.get("email", "")
    ).strip().lower()

    name = claims.get("name") or email.split("@")[0]

    if not google_id or not email:
        raise ValueError(
            "Không lấy được thông tin Google."
        )

    now = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    with get_connection() as conn:
        with conn.cursor() as cur:

            # Khóa theo Google ID để tránh tạo
            # hai tài khoản khi có yêu cầu đồng thời.
            cur.execute(
                """
                SELECT pg_advisory_xact_lock(
                    hashtextextended(%s, 0)
                )
                """,
                (f"google:{google_id}",)
            )

            cur.execute(
                """
                SELECT u.*
                FROM users u
                JOIN auth_identities a
                    ON a.user_id = u.id
                WHERE a.provider = 'google'
                  AND a.provider_user_id = %s
                """,
                (str(google_id),)
            )

            existing = cur.fetchone()

            if existing:
                if not existing["is_active"]:
                    raise ValueError(
                        "Tài khoản đã bị khóa."
                    )

                return {
                    "id": existing["id"],
                    "full_name": existing["full_name"],
                    "email": existing["email"],
                    "role": existing["role"],
                }

            # Không tự động liên kết Google
            # với tài khoản mật khẩu cùng email.
            cur.execute(
                """
                SELECT id
                FROM users
                WHERE LOWER(email) = LOWER(%s)
                """,
                (email,)
            )

            if cur.fetchone():
                raise ValueError(
                    "Email này đã được đăng ký. "
                    "Hãy đăng nhập bằng mật khẩu trước."
                )

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
                VALUES (
                    %s, %s, NULL, 'user', 1, %s
                )
                RETURNING id
                """,
                (name, email, now)
            )

            user_id = cur.fetchone()["id"]

            cur.execute(
                """
                INSERT INTO auth_identities (
                    user_id,
                    provider,
                    provider_user_id,
                    created_at
                )
                VALUES (%s, 'google', %s, %s)
                """,
                (user_id, str(google_id), now)
            )

            # Google đăng ký mới mặc định
            # là tài khoản Bệnh nhân.
            cur.execute(
                """
                INSERT INTO account_types (
                    user_id,
                    account_type
                )
                VALUES (%s, 'patient')
                """,
                (user_id,)
            )

    return {
        "id": user_id,
        "full_name": name,
        "email": email,
        "role": "user",
    }
