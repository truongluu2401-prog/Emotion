import bcrypt
from modules.auth_database import get_connection, get_user_by_id


def _validate_password(password):
    if len(password) < 8:
        raise ValueError("Mật khẩu phải có ít nhất 8 ký tự.")
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Mật khẩu quá dài (tối đa 72 byte UTF-8).")


def update_full_name(user_id, full_name):
    name = full_name.strip()
    if len(name) < 2 or len(name) > 100:
        raise ValueError("Họ tên phải từ 2 đến 100 ký tự.")
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE users SET full_name=? WHERE id=? AND is_active=1",
            (name, user_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("Tài khoản không còn hoạt động.")


def change_password(user_id, current_password, new_password):
    user = get_user_by_id(user_id)
    if not user or not user["is_active"]:
        raise ValueError("Tài khoản không hợp lệ hoặc đã bị khóa.")
    if not user["password_hash"]:
        raise ValueError("Tài khoản Google chưa có mật khẩu riêng.")
    _validate_password(new_password)
    if current_password == new_password:
        raise ValueError("Mật khẩu mới phải khác mật khẩu hiện tại.")
    try:
        verified = bcrypt.checkpw(
            current_password.encode("utf-8"),
            user["password_hash"].encode("utf-8"),
        )
    except (ValueError, TypeError):
        verified = False
    if not verified:
        raise ValueError("Mật khẩu hiện tại không đúng.")
    new_hash = bcrypt.hashpw(
        new_password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE users SET password_hash=? WHERE id=? AND is_active=1 AND password_hash=?",
            (new_hash, user_id, user["password_hash"]),
        )
        if cursor.rowcount != 1:
            raise ValueError("Mật khẩu đã thay đổi ở phiên khác. Hãy thử lại.")


def reset_password_by_email(email, new_password):
    # Chỉ được gọi sau khi xác minh OTP thành công.
    user_email = email.strip().lower()
    user = None
    with get_connection() as conn:
        user = conn.execute(
            "SELECT id, password_hash, is_active FROM users WHERE email=?",
            (user_email,),
        ).fetchone()
        if not user or not user["is_active"] or not user["password_hash"]:
            raise ValueError("Không thể đặt lại mật khẩu cho tài khoản này.")
        _validate_password(new_password)
        password_hash = bcrypt.hashpw(
            new_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        conn.execute(
            "UPDATE users SET password_hash=? WHERE id=? AND is_active=1",
            (password_hash, user["id"]),
        )
