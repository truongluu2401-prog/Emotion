
import pandas as pd
import streamlit as st

from modules.admin_service import (
    get_admin_statistics,
    get_users_for_admin,
    set_user_active,
)


def show_admin_dashboard(admin_id):
    from modules.doctor_admin_ui import show_doctor_approvals
    st.header("🛡️ Admin Dashboard")
    st.write("Quản lý tài khoản và theo dõi hệ thống EmotionAI.")

    try:
        stats = get_admin_statistics(admin_id)
        users = get_users_for_admin(admin_id)
    except PermissionError as e:
        st.error(str(e))
        st.stop()

    show_doctor_approvals(admin_id)
    st.divider()
    st.subheader("📊 Thống kê tài khoản")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Tổng tài khoản", stats["total"])
    col2.metric("Admin", stats["admins"])
    col3.metric("User", stats["users"])
    col4.metric("Bị khóa", stats["locked"])

    st.divider()
    st.subheader("👥 Danh sách tài khoản")

    if not users:
        st.info("Chưa có tài khoản nào.")
        return

    df = pd.DataFrame(users)

    df["is_active"] = df["is_active"].map({
        1: "Hoạt động",
        0: "Đã khóa"
    })

    df = df.rename(columns={
        "id": "ID",
        "full_name": "Họ tên",
        "email": "Email",
        "role": "Vai trò",
        "is_active": "Trạng thái",
        "created_at": "Ngày tạo"
    })

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.divider()
    st.subheader("🔐 Khóa / mở khóa User")

    normal_users = [
        user for user in users
        if user["role"] == "user"
    ]

    if not normal_users:
        st.info("Chưa có tài khoản User để quản lý.")
        return

    user_map = {
        f"{u['id']} - {u['full_name']} ({u['email']})": u
        for u in normal_users
    }

    selected_label = st.selectbox(
        "Chọn tài khoản User",
        list(user_map.keys())
    )

    selected_user = user_map[selected_label]
    is_active = bool(selected_user["is_active"])

    if is_active:
        st.success("Trạng thái hiện tại: Đang hoạt động")
        action_label = "🔒 Khóa tài khoản"
    else:
        st.warning("Trạng thái hiện tại: Đã khóa")
        action_label = "🔓 Mở khóa tài khoản"

    with st.form("change_user_status"):
        confirmed = st.checkbox(
            "Tôi xác nhận muốn thay đổi trạng thái tài khoản này."
        )

        submitted = st.form_submit_button(
            action_label,
            use_container_width=True,
            type="primary"
        )

    if submitted:
        if not confirmed:
            st.warning("Bạn cần xác nhận trước khi thực hiện.")
            return

        try:
            set_user_active(
                admin_id=admin_id,
                target_id=selected_user["id"],
                active=not is_active
            )

            st.success("Đã cập nhật trạng thái tài khoản.")
            st.rerun()

        except (PermissionError, ValueError) as e:
            st.error(str(e))
