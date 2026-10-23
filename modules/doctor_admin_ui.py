import streamlit as st
from modules.doctor_approval import pending_applications, download_document, review_application

def show_doctor_approvals(admin_id):
    st.subheader('🩺 Xét duyệt hồ sơ bác sĩ')
    rows=pending_applications(admin_id)
    if not rows:
        st.info('Chưa có hồ sơ bác sĩ nào.'); return
    for d in rows:
        with st.expander(f"{d['full_name']} · {d['specialty']} · {d['status']}"):
            st.write(f"**Email:** {d['email']}")
            st.write(f"**Trường đào tạo:** {d['school']}")
            st.write(f"**Bằng cấp:** {d['degree']}")
            st.write(f"**Số chứng chỉ:** {d['license_number']}")
            st.write(f"**Kinh nghiệm:** {d['experience_years']} năm")
            st.write(f"**Giới thiệu:** {d['bio']}")
            doc=download_document(admin_id,d['user_id'])
            if doc: st.download_button('📄 Tải hồ sơ để kiểm tra',doc,file_name=d['document_name'],key=f"doc_{d['user_id']}")
            if d['status']=='pending':
                with st.form(f"review_{d['user_id']}"):
                    note=st.text_area('Ghi chú xét duyệt')
                    decision=st.radio('Quyết định',['Chấp nhận','Từ chối'],horizontal=True)
                    confirm=st.checkbox('Tôi đã kiểm tra hồ sơ và xác nhận quyết định')
                    if st.form_submit_button('Lưu quyết định',type='primary'):
                        if not confirm: st.warning('Cần xác nhận trước khi duyệt.')
                        else:
                            review_application(admin_id,d['user_id'],decision=='Chấp nhận',note)
                            st.success('Đã cập nhật hồ sơ.'); st.rerun()
            else: st.caption(f"Ghi chú: {d['review_note'] or 'Không có'}")
