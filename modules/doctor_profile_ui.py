"""Doctor-owned profile controls and public doctor listing details."""
import calendar
from datetime import date, time
import streamlit as st
from modules.doctor_profile import save_photo, get_photo, list_slots, add_slot, remove_slot


def show_doctor_profile(doctor_id):
    st.subheader('📷 Ảnh đại diện bác sĩ')
    photo = get_photo(doctor_id)
    if photo:
        st.image(photo, width=160)
    upload = st.file_uploader('Chọn ảnh JPG, PNG hoặc WEBP (tối đa 2 MB)',type=['jpg','jpeg','png','webp'],key='doctor_photo_upload')
    if upload and st.button('💾 Lưu ảnh đại diện',key='save_doctor_photo'):
        try:
            save_photo(doctor_id, upload.getvalue())
            st.success('Đã cập nhật ảnh đại diện.')
            st.rerun()
        except (ValueError, PermissionError) as exc:
            st.error(str(exc))

    st.divider()
    st.subheader('📅 Lịch làm việc của tôi')
    today = date.today()
    with st.form('doctor_new_slot',clear_on_submit=True):
        work_date = st.date_input('Ngày làm việc',value=today,min_value=today)
        a,b = st.columns(2)
        with a:
            start = st.time_input('Bắt đầu',value=time(8,0),step=1800)
        with b:
            end = st.time_input('Kết thúc',value=time(12,0),step=1800)
        submitted = st.form_submit_button('➕ Thêm ca làm việc',type='primary')
    if submitted:
        try:
            add_slot(doctor_id,work_date,start,end)
            st.success('Đã thêm lịch làm việc.')
            st.rerun()
        except (ValueError,PermissionError) as exc:
            st.error(str(exc))

    month = st.date_input('Xem lịch từ ngày',value=today,key='doctor_calendar_month')
    first = month.replace(day=1)
    last = month.replace(day=calendar.monthrange(month.year,month.month)[1])
    slots = list_slots(doctor_id,first,last)
    if not slots:
        st.info('Tháng này chưa có lịch làm việc.')
    for slot in slots:
        a,b = st.columns([5,1])
        with a:
            st.write(f"{slot['work_date']} · {slot['start_time']} – {slot['end_time']}")
        with b:
            if st.button('Xóa',key=f"remove_slot_{slot['id']}"):
                remove_slot(doctor_id,slot['id'])
                st.rerun()
    st.caption('Đây là lịch làm việc dự kiến. Chức năng đặt lịch hẹn sẽ được phát triển ở bước tiếp theo.')


def show_public_doctor_details(doctor_id):
    photo = get_photo(doctor_id)
    if photo:
        st.image(photo,width=140)
    slots = list_slots(doctor_id,from_date=date.today())
    st.write('**Lịch làm việc sắp tới:**')
    if not slots:
        st.caption('Bác sĩ chưa cập nhật lịch làm việc.')
    else:
        for slot in slots[:15]:
            st.write(f"• {slot['work_date']}: {slot['start_time']} – {slot['end_time']}")
        if len(slots)>15:
            st.caption(f'Và {len(slots)-15} ca làm việc khác.')
