
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "emotionai.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_auth_database():
    """Tạo các bảng tài khoản nếu chưa tồn tại."""

    with get_connection() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT,
                role TEXT NOT NULL DEFAULT 'user'
                    CHECK(role IN ('admin', 'user')),
                is_active INTEGER NOT NULL DEFAULT 1
                    CHECK(is_active IN (0, 1)),
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS auth_identities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                provider TEXT NOT NULL
                    CHECK(provider IN ('google', 'facebook')),
                provider_user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,

                FOREIGN KEY(user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                UNIQUE(provider, provider_user_id),
                UNIQUE(user_id, provider)
            )
        """)


def get_user_by_email(email):
    """Tìm người dùng theo email."""

    with get_connection() as conn:

        row = conn.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email.strip(),)
        ).fetchone()

        return dict(row) if row else None


def get_user_by_id(user_id):
    """Tìm người dùng theo ID."""

    with get_connection() as conn:

        row = conn.execute(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()

        return dict(row) if row else None


def create_user(full_name, email, password_hash):
    """Tạo tài khoản người dùng thông thường."""

    full_name = full_name.strip()
    email = email.strip().lower()

    if not full_name:
        raise ValueError("Họ tên không được để trống.")

    if not email:
        raise ValueError("Email không được để trống.")

    if not password_hash:
        raise ValueError("Mật khẩu chưa được mã hóa.")

    created_at = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    with get_connection() as conn:

        cursor = conn.execute(
            """
            INSERT INTO users (
                full_name,
                email,
                password_hash,
                role,
                is_active,
                created_at
            )
            VALUES (?, ?, ?, 'user', 1, ?)
            """,
            (
                full_name,
                email,
                password_hash,
                created_at
            )
        )

        return cursor.lastrowid


def get_all_users():
    """Lấy danh sách người dùng cho Admin."""

    with get_connection() as conn:

        rows = conn.execute(
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
        ).fetchall()

        return [dict(row) for row in rows]


def get_user_count():
    """Đếm số tài khoản."""

    with get_connection() as conn:

        row = conn.execute(
            "SELECT COUNT(*) AS total FROM users"
        ).fetchone()

        return row["total"]


if __name__ == "__main__":
    init_auth_database()
    print("AUTH DATABASE OK")
    print("Da tao bang users va auth_identities.")
