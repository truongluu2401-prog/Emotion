"""Trang tạo và xem hồ sơ bệnh nhân phục vụ phân tích AI."""
import streamlit as st
from modules.patient_database import add_patient, get_patients

def show_patient_page(user_id):
    st.header('👥 Hồ sơ bệnh nhân')
    st.info('Đây là hồ sơ tối giản để gắn kết quả AI với đúng bệnh nhân, không phải hồ sơ bệnh án chính thức.')
    st.warning('Chỉ nhập dữ liệu thử nghiệm hoặc dữ liệu đã được cho phép. Tránh nhập thông tin định danh nhạy cảm không cần thiết.')
    with st.form(f'patient_new_{user_id}', clear_on_submit=True):
        code=st.text_input('Mã bệnh nhân (ví dụ: BN001)')
        name=st.text_input('Tên hiển thị / bí danh')
        notes=st.text_area('Ghi chú hồ sơ (không bắt buộc)')
        submitted=st.form_submit_button('➕ Tạo hồ sơ bệnh nhân')
    if submitted:
        try:
            patient_id=add_patient(user_id=user_id,code=code,name=name,notes=notes)
            st.success(f'Đã tạo hồ sơ bệnh nhân #{patient_id}.')
        except Exception as exc:
            st.error(str(exc))
    patients=get_patients(user_id=user_id)
    if patients:
        st.subheader('Danh sách hồ sơ của tài khoản này')
        import pandas as pd
        st.dataframe(pd.DataFrame([{'Mã hồ sơ':p['id'],'Mã bệnh nhân':p['patient_code'],
          'Tên hiển thị':p['display_name'],'Ngày tạo':p['created_at']} for p in patients]),
          use_container_width=True,hide_index=True)
    else:
        st.info('Chưa có hồ sơ bệnh nhân. Hãy tạo một hồ sơ để bắt đầu.')
