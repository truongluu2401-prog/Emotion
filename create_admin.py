
import getpass
import sqlite3
import bcrypt

from modules.auth_database import (
    init_auth_database,
    get_connection,
)


def main():
    init_auth_database()

    print("=== TAO TAI KHOAN ADMIN EMOTIONAI ===")

    full_name = input("Ho va ten Admin: ").strip()
    email = input("Email Admin: ").strip().lower()

    if len(full_name) < 2:
        print("Ho ten phai co it nhat 2 ky tu.")
        return

    if not email or "@" not in email:
        print("Email khong hop le.")
        return

    password = getpass.getpass("Mat khau Admin: ")
    confirm = getpass.getpass("Nhap lai mat khau: ")

    if len(password) < 8:
        print("Mat khau phai co it nhat 8 ky tu.")
        return

    if len(password.encode("utf-8")) > 72:
        print("Mat khau qua dai.")
        return

    if password != confirm:
        print("Mat khau xac nhan khong khop.")
        return

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    try:
        with get_connection() as conn:
            existing = conn.execute(
                "SELECT id FROM users WHERE email = ?",
                (email,)
            ).fetchone()

            if existing:
                print(
                    "Email da ton tai. "
                    "Khong tu dong nang quyen tai khoan."
                )
                return

            conn.execute(
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
                    ?, ?, ?, 'admin', 1,
                    datetime('now')
                )
                """,
                (full_name, email, password_hash)
            )

        print("Tao tai khoan Admin thanh cong!")

    except sqlite3.Error as error:
        print(f"Loi SQLite: {error}")


if __name__ == "__main__":
    main()
