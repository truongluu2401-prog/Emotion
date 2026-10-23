
import re
import sqlite3
from modules.google_auth import google_login

import bcrypt
import streamlit as st

from modules.auth_service import (
    login_user,
    validate_email
)
from modules.auth_database import (
    create_user,
    get_user_by_email
)
from modules.otp_service import (
    issue_otp,
    verify_otp
)


def show_auth_page():

    st.markdown("""
    <style>
    .block-container {
        max-width: 900px;
        padding-top: 2rem;
    }

    .auth-heading {
        text-align: center;
        font-size: 30px;
        font-weight: 750;
        color: #172554;
        margin-bottom: 10px;
    }

    .auth-subtitle {
        text-align: center;
        color: #64748b;
        margin-bottom: 25px;
    }

    div[data-testid="stForm"] {
        border-radius: 16px;
        border: 1px solid #dbe4f0;
        background: rgba(255,255,255,0.94);
        padding: 20px;
    }

    div.stButton > button,
    div.stFormSubmitButton > button {
        border-radius: 10px;
        min-height: 44px;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

    if "auth_mode" not in st.session_state:
        st.session_state["auth_mode"] = "Đăng ký"

    _, center, _ = st.columns([1, 2, 1])

    with center:

        st.markdown(
            '<div class="auth-heading">🧠 EmotionAI</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="auth-subtitle">'
            'AI Emotion Analysis Platform'
            '</div>',
            unsafe_allow_html=True
        )

        mode = st.radio(
            "Tài khoản",
            ["Đăng ký", "Đăng nhập"],
            key="auth_mode",
            horizontal=True
        )

        if mode == "Đăng ký":

            st.subheader("Sign up for EmotionAI")

            # Google/Facebook sẽ tích hợp OAuth thật
            # ở các bước tiếp theo.
            st.button(
                "🌐 Continue with Google",
                key="google_signup",
                use_container_width=True,
                on_click=google_login
            )

            st.markdown("**──────── OR ────────**")

            pending = st.session_state.get(
                "signup_pending"
            )

            # ---------------------------------
            # MÀN HÌNH NHẬP OTP
            # ---------------------------------

            if pending:

                st.success(
                    "Mã OTP đã được gửi đến "
                    f"{pending['email']}"
                )

                st.caption(
                    "Nhập mã gồm 6 chữ số. "
                    "Mã có hiệu lực trong 5 phút."
                )

                with st.form("otp_verify_form"):

                    otp_input = st.text_input(
                        "Mã OTP",
                        max_chars=6,
                        placeholder="Nhập 6 chữ số"
                    )

                    verify_submit = st.form_submit_button(
                        "Xác nhận OTP",
                        use_container_width=True
                    )

                if verify_submit:

                    if not re.fullmatch(
                        r"\d{6}",
                        otp_input.strip()
                    ):
                        st.error(
                            "Vui lòng nhập đúng 6 chữ số."
                        )

                    else:

                        success, message = verify_otp(
                            otp_input
                        )

                        if not success:
                            st.error(message)

                        else:

                            try:

                                create_user(
                                    full_name=pending["name"],
                                    email=pending["email"],
                                    password_hash=pending[
                                        "password_hash"
                                    ]
                                )

                                st.session_state.pop(
                                    "signup_pending",
                                    None
                                )

                                st.success(
                                    "Đăng ký thành công! "
                                    "Hãy chuyển sang Đăng nhập."
                                )

                            except sqlite3.IntegrityError:

                                st.session_state.pop(
                                    "signup_pending",
                                    None
                                )

                                st.error(
                                    "Email đã được đăng ký."
                                )

                if st.button(
                    "Gửi lại mã OTP",
                    use_container_width=True
                ):

                    try:

                        success, message = issue_otp(
                            email=pending["email"],
                            name=pending["name"],
                            password_hash=pending[
                                "password_hash"
                            ]
                        )

                        if success:
                            st.success(message)
                        else:
                            st.warning(message)

                    except Exception:
                        st.error(
                            "Không thể gửi email. "
                            "Kiểm tra cấu hình Gmail SMTP."
                        )

                if st.button(
                    "Quay lại đăng ký",
                    use_container_width=True
                ):

                    st.session_state.pop(
                        "signup_pending",
                        None
                    )

                    st.rerun()

            # ---------------------------------
            # FORM ĐĂNG KÝ
            # ---------------------------------

            else:

                with st.form("signup_form"):

                    email = st.text_input(
                        "Email *",
                        placeholder="example@gmail.com"
                    )

                    password = st.text_input(
                        "Password *",
                        type="password",
                        placeholder="Tối thiểu 8 ký tự"
                    )

                    username = st.text_input(
                        "Username *",
                        placeholder="Tên người dùng"
                    )

                    full_name = st.text_input(
                        "Full name",
                        placeholder="Họ và tên"
                    )

                    confirm_password = st.text_input(
                        "Confirm password *",
                        type="password"
                    )

                    submitted = st.form_submit_button(
                        "Continue",
                        use_container_width=True
                    )

                if submitted:

                    email = email.strip().lower()
                    username = username.strip()
                    name = full_name.strip() or username

                    if not validate_email(email):
                        st.error("Email không hợp lệ.")

                    elif len(username) < 3:
                        st.error(
                            "Username phải có ít nhất 3 ký tự."
                        )

                    elif len(password) < 8:
                        st.error(
                            "Mật khẩu phải có ít nhất 8 ký tự."
                        )

                    elif len(
                        password.encode("utf-8")
                    ) > 72:
                        st.error("Mật khẩu quá dài.")

                    elif password != confirm_password:
                        st.error(
                            "Mật khẩu xác nhận không khớp."
                        )

                    elif get_user_by_email(email):
                        st.error(
                            "Email này đã được đăng ký."
                        )

                    else:

                        password_hash = bcrypt.hashpw(
                            password.encode("utf-8"),
                            bcrypt.gensalt()
                        ).decode("utf-8")

                        try:

                            success, message = issue_otp(
                                email=email,
                                name=name,
                                password_hash=password_hash
                            )

                            if success:
                                st.rerun()
                            else:
                                st.warning(message)

                        except Exception:
                            st.error(
                                "Gửi OTP thất bại. "
                                "Hãy kiểm tra Gmail và "
                                "App Password trong secrets.toml."
                            )

        # ---------------------------------
        # FORM ĐĂNG NHẬP
        # ---------------------------------

        else:

            st.subheader("Sign in to EmotionAI")
            st.button(
                "🌐 Continue with Google",
                key="google_signin",
                use_container_width=True,
                on_click=google_login
            )

            st.markdown("**──────── OR ────────**")

            with st.form("signin_form"):

                email = st.text_input(
                    "Email",
                    placeholder="example@gmail.com"
                )

                password = st.text_input(
                    "Password",
                    type="password"
                )

                submitted = st.form_submit_button(
                    "Sign in",
                    use_container_width=True
                )

            if submitted:

                success, message, user = login_user(
                    email,
                    password
                )

                if success:

                    st.session_state["auth_user"] = user
                    st.session_state["current_menu"] = (
                        "🏠 Trang chủ"
                    )

                    st.rerun()

                else:
                    st.error(message)
