
import hashlib
import hmac
import secrets
import smtplib
import time

from email.message import EmailMessage

import streamlit as st


OTP_TTL = 300
RESEND_DELAY = 60
MAX_ATTEMPTS = 5


def send_email_otp(destination, otp):
    sender = st.secrets["email"]["address"]
    password = st.secrets["email"]["app_password"]

    message = EmailMessage()
    message["Subject"] = "EmotionAI - Ma xac thuc dang ky"
    message["From"] = sender
    message["To"] = destination

    message.set_content(
        f"Ma OTP dang ky EmotionAI: {otp}\n\n"
        "Ma co hieu luc trong 5 phut.\n"
        "Khong chia se ma nay voi bat ky ai."
    )

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465,
        timeout=20
    ) as smtp:
        smtp.login(sender, password)
        smtp.send_message(message)


def issue_otp(email, name, password_hash):
    pending = st.session_state.get("signup_pending")
    now = time.time()

    if pending and now - pending["sent_at"] < RESEND_DELAY:
        return False, "Vui lòng đợi 60 giây trước khi gửi lại."

    otp = f"{secrets.randbelow(1000000):06d}"
    salt = secrets.token_hex(16)

    otp_hash = hashlib.sha256(
        f"{salt}:{otp}".encode()
    ).hexdigest()

    # Chỉ lưu yêu cầu sau khi gửi email thành công
    send_email_otp(email, otp)

    st.session_state["signup_pending"] = {
        "email": email,
        "name": name,
        "password_hash": password_hash,
        "salt": salt,
        "otp_hash": otp_hash,
        "expires_at": now + OTP_TTL,
        "sent_at": now,
        "attempts": 0
    }

    return True, "Đã gửi OTP. Hãy kiểm tra Gmail hoặc Spam."


def verify_otp(code):
    pending = st.session_state.get("signup_pending")

    if not pending:
        return False, "Chưa có yêu cầu xác thực."

    if time.time() > pending["expires_at"]:
        st.session_state.pop("signup_pending", None)
        return False, "OTP đã hết hạn. Vui lòng đăng ký lại."

    if pending["attempts"] >= MAX_ATTEMPTS:
        st.session_state.pop("signup_pending", None)
        return False, "Đã vượt quá số lần nhập OTP."

    pending["attempts"] += 1

    actual_hash = hashlib.sha256(
        f"{pending['salt']}:{code.strip()}".encode()
    ).hexdigest()

    if not hmac.compare_digest(
        actual_hash,
        pending["otp_hash"]
    ):
        return False, "Mã OTP không đúng."

    return True, "Xác thực OTP thành công."
