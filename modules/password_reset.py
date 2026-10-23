import hashlib
import hmac
import secrets
import time
import re
import streamlit as st

from modules.auth_database import get_user_by_email
from modules.otp_service import send_email_otp
from modules.profile_service import reset_password_by_email

TTL = 300
COOLDOWN = 60
MAX_ATTEMPTS = 5


def request_reset(email):
    email = email.strip().lower()
    if not re.fullmatch(r"[^@\\s]+@[^@\\s]+\\.[^@\\s]+", email):
        return False, "Email không hợp lệ."

    previous = st.session_state.get("reset_pending")
    now = time.time()
    if previous and now - previous["sent_at"] < COOLDOWN:
        return False, "Vui lòng đợi 60 giây trước khi yêu cầu mã mới."

    user = get_user_by_email(email)
    if not user or not user["is_active"] or not user["password_hash"]:
        return False, "Không thể đặt lại mật khẩu cho tài khoản này."

    code = f"{secrets.randbelow(1000000):06d}"
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{code}".encode()).hexdigest()

    send_email_otp(email, code)
    st.session_state["reset_pending"] = {
        "email": email,
        "salt": salt,
        "digest": digest,
        "expires_at": time.time() + TTL,
        "sent_at": time.time(),
        "attempts": 0,
    }
    return True, "Đã gửi mã OTP đến email của bạn (hiệu lực 5 phút)."


def confirm_reset(code, new_password):
    pending = st.session_state.get("reset_pending")
    if not pending:
        raise ValueError("Chưa có yêu cầu đặt lại mật khẩu.")
    if time.time() > pending["expires_at"]:
        st.session_state.pop("reset_pending", None)
        raise ValueError("OTP đã hết hạn.")
    if pending["attempts"] >= MAX_ATTEMPTS:
        st.session_state.pop("reset_pending", None)
        raise ValueError("Đã vượt quá số lần nhập OTP.")

    pending["attempts"] += 1
    if not re.fullmatch(r"\\d{6}", code.strip()):
        raise ValueError("OTP phải gồm đúng 6 chữ số.")
    digest = hashlib.sha256(f"{pending['salt']}:{code.strip()}".encode()).hexdigest()
    if not hmac.compare_digest(digest, pending["digest"]):
        raise ValueError("Mã OTP không đúng.")

    reset_password_by_email(pending["email"], new_password)
    st.session_state.pop("reset_pending", None)


def show_reset_password():
    st.subheader("🔑 Quên mật khẩu")
    pending = st.session_state.get("reset_pending")
    if not pending:
        with st.form("reset_request_form"):
            email = st.text_input("Email đã đăng ký", key="reset_email")
            sent = st.form_submit_button("Gửi mã OTP")
        if sent:
            try:
                ok, message = request_reset(email)
                (st.success if ok else st.warning)(message)
                if ok:
                    st.rerun()
            except Exception:
                st.error("Không gửi được OTP. Kiểm tra cấu hình Gmail SMTP.")
    else:
        st.info(f"Mã OTP đã gửi đến {pending['email']}.")
        with st.form("reset_confirm_form"):
            code = st.text_input("Mã OTP (6 chữ số)", max_chars=6)
            password = st.text_input("Mật khẩu mới", type="password")
            confirm = st.text_input("Xác nhận mật khẩu", type="password")
            done = st.form_submit_button("Đặt lại mật khẩu")
        if done:
            if password != confirm:
                st.error("Mật khẩu xác nhận không khớp.")
            else:
                try:
                    confirm_reset(code, password)
                    st.success("Đặt lại mật khẩu thành công. Hãy đăng nhập.")
                except ValueError as exc:
                    st.error(str(exc))
        if st.button("Hủy đặt lại mật khẩu"):
            st.session_state.pop("reset_pending", None)
            st.rerun()
