"""Streamlit appointment views for patient and doctor."""
import streamlit as st
from datetime import date, timedelta
from modules.appointments import available_slots, book, list_for_patient, list_for_doctor, doctor_action, patient_cancel
from modules.doctor_approval import approved_doctors

LABEL={'pending':'🟡 Chờ bác sĩ xác nhận','confirmed':'🟢 Đã xác nhận','rejected':'🔴 Bị từ chối','cancelled':'⚪ Đã hủy'}


def show_patient_appointments(patient_id):
    st.header('📅 Đặt lịch khám')
    doctors=approved_doctors()
    if not doctors:
        st.info('Chưa có bác sĩ được phê duyệt.')
    else:
        doctor=st.selectbox('Chọn bác sĩ',doctors,format_func=lambda d:f"{d['full_name']} — {d['specialty']}")
        st.caption('Chọn ngày trước, sau đó chọn ca còn trống của bác sĩ.')
        selected_day=st.date_input('Chọn ngày khám', value=date.today(), min_value=date.today(), max_value=date.today()+timedelta(days=180), key=f"appointment_date_{doctor['id']}", format='DD/MM/YYYY')
        slots=available_slots(doctor['id'], selected_day)
        if not slots:
            st.info('Ngày này chưa có giờ trống hoặc các ca đã được đặt. Hãy chọn ngày khác.')
        else:
            with st.form('patient_book_appointment'):
                slot=st.selectbox('Chọn giờ khám',slots,format_func=lambda s:f"{s['start_time']} – {s['end_time']}")
                note=st.text_area('Ghi chú ngắn (không bắt buộc, không nhập thông tin sức khỏe nhạy cảm)',max_chars=500)
                submit=st.form_submit_button('Gửi yêu cầu đặt lịch',type='primary')
            if submit:
                try:
                    book(patient_id,slot['id'],note)
                    st.success('Đã gửi yêu cầu. Ca được giữ chỗ trong khi chờ bác sĩ xác nhận.')
                    st.rerun()
                except (ValueError,PermissionError) as e: st.error(str(e))
    st.divider()
    st.subheader('Lịch hẹn của tôi')
    appointments=list_for_patient(patient_id)
    if not appointments: st.info('Bạn chưa có lịch hẹn nào.')
    for a in appointments:
        with st.container(border=True):
            st.write(f"**{a['doctor_name']}** · {a['work_date']} · {a['start_time']}–{a['end_time']}")
            st.write(LABEL[a['status']])
            if a['doctor_note']: st.caption('Phản hồi của bác sĩ: '+a['doctor_note'])
            if a['status'] in ('pending','confirmed'):
                if st.button('Hủy yêu cầu/lịch hẹn',key=f"patient_cancel_{a['id']}"):
                    try:
                        patient_cancel(patient_id,a['id'])
                        st.rerun()
                    except (ValueError,PermissionError) as e: st.error(str(e))


def show_doctor_appointments(doctor_id):
    st.header('🗓️ Quản lý lịch hẹn')
    appointments=list_for_doctor(doctor_id)
    if not appointments: st.info('Chưa có bệnh nhân đặt lịch.')
    for a in appointments:
        with st.container(border=True):
            st.write(f"**{a['patient_name']}** · {a['work_date']} · {a['start_time']}–{a['end_time']}")
            st.write(LABEL[a['status']])
            if a['patient_note']: st.caption('Ghi chú: '+a['patient_note'])
            if a['doctor_note']: st.caption('Phản hồi đã lưu: '+a['doctor_note'])
            if a['status'] in ('pending','confirmed'):
                reason=st.text_input('Lý do từ chối/hủy (bắt buộc khi từ chối hoặc hủy)',key=f"doctor_reason_{a['id']}",max_chars=500)
                col1,col2=st.columns(2)
                with col1:
                    if a['status']=='pending' and st.button('✅ Xác nhận',key=f"doctor_accept_{a['id']}",type='primary'):
                        try:
                            doctor_action(doctor_id,a['id'],'confirmed')
                            st.rerun()
                        except (ValueError,PermissionError) as e: st.error(str(e))
                with col2:
                    label='❌ Từ chối' if a['status']=='pending' else '🚫 Hủy lịch đã xác nhận'
                    if st.button(label,key=f"doctor_reject_{a['id']}"):
                        try:
                            doctor_action(doctor_id,a['id'],'rejected' if a['status']=='pending' else 'cancelled',reason)
                            st.rerun()
                        except (ValueError,PermissionError) as e: st.error(str(e))
