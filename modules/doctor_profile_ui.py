"""Doctor-owned profile, weekly scheduling and patient-facing directory."""
import calendar
from datetime import date, time, timedelta
import streamlit as st
from modules.doctor_profile import (
    save_photo, get_photo, list_slots, add_slot, add_week_slots, remove_slot,
)

WEEKDAYS = ['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ Nhật']


def show_doctor_profile(doctor_id):
    st.subheader('📷 Ảnh đại diện bác sĩ')
    photo = get_photo(doctor_id)
    if photo:
        st.image(photo, width=180)
        st.caption('Ảnh hiện tại — bệnh nhân sẽ thấy ảnh này trong hồ sơ sau khi bác sĩ được duyệt.')
    upload = st.file_uploader('Chọn ảnh JPG, PNG hoặc WEBP (tối đa 2 MB)',
                              type=['jpg', 'jpeg', 'png', 'webp'], key='doctor_photo_upload')
    if upload is not None:
        st.image(upload, width=180, caption='Xem trước ảnh mới')
        if st.button('💾 Lưu ảnh vào hồ sơ', key='save_doctor_photo', type='primary'):
            try:
                save_photo(doctor_id, upload.getvalue())
                st.success('Đã lưu ảnh. Ảnh sẽ xuất hiện trong danh sách và hồ sơ bác sĩ.')
                st.rerun()
            except (ValueError, PermissionError) as exc:
                st.error(str(exc))

    st.divider()
    st.subheader('📅 Cài đặt lịch làm việc theo tuần')
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    with st.form('doctor_week_schedule'):
        chosen_day = st.date_input('Chọn một ngày thuộc tuần muốn cài đặt', value=today, min_value=today)
        week_start = chosen_day - timedelta(days=chosen_day.weekday())
        st.caption(f'Tuần: {week_start:%d/%m/%Y} – {(week_start + timedelta(days=6)):%d/%m/%Y}')
        chosen_weekdays = st.multiselect('Những ngày làm việc trong tuần', WEEKDAYS,
                                         default=WEEKDAYS[:5])
        a, b = st.columns(2)
        with a:
            start = st.time_input('Giờ bắt đầu', value=time(8, 0), step=1800, key='week_start_time')
        with b:
            end = st.time_input('Giờ kết thúc', value=time(12, 0), step=1800, key='week_end_time')
        save_week = st.form_submit_button('💾 Lưu lịch cho cả tuần', type='primary')
    if save_week:
        try:
            count = add_week_slots(doctor_id, week_start,
                                   [WEEKDAYS.index(d) for d in chosen_weekdays], start, end)
            st.success(f'Đã tạo {count} ca làm việc trong tuần.')
            st.rerun()
        except (ValueError, PermissionError) as exc:
            st.error(str(exc))

    with st.expander('➕ Thêm một ca riêng lẻ'):
        with st.form('doctor_new_slot', clear_on_submit=True):
            work_date = st.date_input('Ngày làm việc', value=today, min_value=today)
            a, b = st.columns(2)
            with a:
                single_start = st.time_input('Bắt đầu', value=time(13, 0), step=1800)
            with b:
                single_end = st.time_input('Kết thúc', value=time(17, 0), step=1800)
            submitted = st.form_submit_button('Thêm ca')
        if submitted:
            try:
                add_slot(doctor_id, work_date, single_start, single_end)
                st.success('Đã thêm ca làm việc.')
                st.rerun()
            except (ValueError, PermissionError) as exc:
                st.error(str(exc))

    st.subheader('Lịch đã lưu')
    selected = st.date_input('Xem lịch tháng chứa ngày', value=today, key='doctor_calendar_month')
    first = selected.replace(day=1)
    last = selected.replace(day=calendar.monthrange(selected.year, selected.month)[1])
    slots = list_slots(doctor_id, first, last)
    if not slots:
        st.info('Tháng này chưa có lịch làm việc.')
    for slot in slots:
        a, b = st.columns([5, 1])
        with a:
            st.write(f"{slot['work_date']} · {slot['start_time']} – {slot['end_time']}")
        with b:
            if st.button('Xóa', key=f"remove_slot_{slot['id']}"):
                remove_slot(doctor_id, slot['id'])
                st.rerun()
    st.caption('Lịch theo tuần chỉ áp dụng cho tuần đã chọn, không tự lặp vô thời hạn. Chưa có đặt lịch khám.')


def show_public_doctor_details(doctor_id, doctor=None):
    """Render doctor details only after caller verifies doctor is approved."""
    from modules.doctor_approval import approved_doctors
    approved = next((d for d in approved_doctors() if d['id'] == doctor_id), None)
    if not approved:
        st.warning('Hồ sơ bác sĩ chưa được phê duyệt hoặc không còn khả dụng.')
        return
    doctor = approved
    photo = get_photo(doctor_id)
    a, b = st.columns([1, 3])
    with a:
        if photo:
            st.image(photo, width=190)
        else:
            st.info('Chưa có ảnh đại diện')
    with b:
        st.subheader(doctor['full_name'])
        st.write(f"**Chuyên ngành:** {doctor['specialty']}")
        st.write(f"**Trường đào tạo:** {doctor['school']}")
        st.write(f"**Bằng cấp:** {doctor['degree']}")
        st.write(f"**Kinh nghiệm:** {doctor['experience_years']} năm")
        if doctor.get('bio'):
            st.write(f"**Giới thiệu:** {doctor['bio']}")
    st.markdown('#### 📅 Lịch làm việc sắp tới')
    slots = list_slots(doctor_id, from_date=date.today())
    if not slots:
        st.caption('Bác sĩ chưa cập nhật lịch làm việc.')
    else:
        for slot in slots[:35]:
            st.write(f"• {slot['work_date']}: {slot['start_time']} – {slot['end_time']}")
        if len(slots) > 35:
            st.caption(f'Và {len(slots) - 35} ca khác.')
    st.caption('Lịch dự kiến, chưa phải xác nhận đặt lịch khám.')


def show_doctor_directory():
    from modules.doctor_approval import approved_doctors
    st.header('🩺 Đội ngũ bác sĩ')
    doctors = approved_doctors()
    ids = {d['id'] for d in doctors}
    selected = st.session_state.get('selected_doctor_profile')
    if selected not in ids:
        st.session_state.pop('selected_doctor_profile', None)
        selected = None
    if selected is not None:
        if st.button('← Quay lại danh sách bác sĩ'):
            st.session_state.pop('selected_doctor_profile', None)
            st.rerun()
        show_public_doctor_details(selected)
        return
    if not doctors:
        st.info('Hiện chưa có bác sĩ được xác minh.')
        return
    for doctor in doctors:
        with st.container(border=True):
            a, b = st.columns([1, 4])
            with a:
                photo = get_photo(doctor['id'])
                if photo:
                    st.image(photo, width=120)
                else:
                    st.caption('👨‍⚕️ Chưa có ảnh')
            with b:
                st.markdown(f"**{doctor['full_name']}**")
                st.write(f"{doctor['specialty']} · {doctor['degree']}")
                if st.button('Xem chi tiết hồ sơ →', key=f"doctor_detail_{doctor['id']}"):
                    st.session_state['selected_doctor_profile'] = doctor['id']
                    st.rerun()
