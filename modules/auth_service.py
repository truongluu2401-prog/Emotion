
import re
import sqlite3
import bcrypt

from modules.auth_database import (
    create_user,
    get_user_by_email,
    get_user_by_id,
)


def validate_email(email):
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return re.fullmatch(pattern, email) is not None


def register_user(full_name, email, password, confirm_password):
    full_name = full_name.strip()
    email = email.strip().lower()

    if len(full_name) < 2:
        return False, "Họ tên phải có ít nhất 2 ký tự."

    if not validate_email(email):
        return False, "Email không hợp lệ."

    if len(password) < 8:
        return False, "Mật khẩu phải có ít nhất 8 ký tự."

    if len(password.encode("utf-8")) > 72:
        return False, "Mật khẩu quá dài."

    if password != confirm_password:
        return False, "Mật khẩu xác nhận không khớp."

    if get_user_by_email(email):
        return False, "Email này đã được đăng ký."

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    try:
        user_id = create_user(
            full_name=full_name,
            email=email,
            password_hash=password_hash
        )

        return True, (
            f"Đăng ký thành công! "
            f"Mã tài khoản: {user_id}"
        )

    except sqlite3.IntegrityError:
        return False, "Email này đã tồn tại."


def login_user(email, password):
    email = email.strip().lower()

    user = get_user_by_email(email)

    if user is None:
        return False, "Email hoặc mật khẩu không đúng.", None

    if not user["is_active"]:
        return False, "Tài khoản đã bị khóa.", None

    if not user["password_hash"]:
        return False, (
            "Tài khoản chưa có mật khẩu. "
            "Hãy đăng nhập bằng phương thức đã liên kết."
        ), None

    try:
        password_valid = bcrypt.checkpw(
            password.encode("utf-8"),
            user["password_hash"].encode("utf-8")
        )
    except (ValueError, TypeError):
        return False, "Không thể xác minh mật khẩu.", None

    if not password_valid:
        return False, "Email hoặc mật khẩu không đúng.", None

    # Không đưa password_hash vào session
    safe_user = {
        "id": user["id"],
        "full_name": user["full_name"],
        "email": user["email"],
        "role": user["role"]
    }

    return True, "Đăng nhập thành công!", safe_user


def refresh_user(user_id):
    user = get_user_by_id(user_id)

    if user is None or not user["is_active"]:
        return None

    return {
        "id": user["id"],
        "full_name": user["full_name"],
        "email": user["email"],
        "role": user["role"]
    }
