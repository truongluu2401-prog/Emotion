import streamlit as st
from modules.auth_database import get_user_by_id
from modules.profile_service import update_full_name, change_password


def show_profile_page(user_id):
    user = get_user_by_id(user_id)
    if not user or not user["is_active"]:
        st.error("Phiên đăng nhập không còn hợp lệ.")
        st.stop()

    st.header("👤 Hồ sơ cá nhân")
    st.write(f"**Email:** {user['email']}")
    st.write(f"**Vai trò:** {user['role'].upper()}")
    st.write(f"**Trạng thái:** Đang hoạt động")

    st.subheader("✏️ Chỉnh sửa họ tên")
    with st.form("profile_name_form"):
        full_name = st.text_input("Họ và tên", value=user["full_name"])
        save = st.form_submit_button("Lưu thay đổi", use_container_width=True)
    if save:
        try:
            update_full_name(user_id, full_name)
            st.success("Đã cập nhật họ tên.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("🔒 Đổi mật khẩu")
    if not user["password_hash"]:
        st.info("Tài khoản Google chưa thiết lập mật khẩu riêng. Bạn vẫn có thể đăng nhập bằng Google.")
        return

    with st.form("profile_password_form", clear_on_submit=True):
        old = st.text_input("Mật khẩu hiện tại", type="password")
        new = st.text_input("Mật khẩu mới", type="password")
        confirm = st.text_input("Nhập lại mật khẩu mới", type="password")
        submit = st.form_submit_button("Đổi mật khẩu", use_container_width=True)

    if submit:
        if new != confirm:
            st.error("Mật khẩu xác nhận không khớp.")
        else:
            try:
                change_password(user_id, old, new)
                st.success("Đổi mật khẩu thành công.")
            except ValueError as exc:
                st.error(str(exc))
