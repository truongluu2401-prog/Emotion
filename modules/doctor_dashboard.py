"""EmotionAI - Dashboard phân tích tổng hợp riêng theo tài khoản."""
import json
import pandas as pd
import streamlit as st
from modules.multimodal_database import get_multimodal_sessions
from modules.patient_database import get_patients
from modules.patient_trends import show_patient_trends
from modules.patient_report import build_patient_report_pdf


def show_doctor_dashboard(user_id):
    st.header("📈 AI Dashboard hỗ trợ bác sĩ tâm lý")
    st.write("Theo dõi các phiên phân tích cảm xúc tổng hợp đã lưu của tài khoản đang đăng nhập.")
    st.info("Biểu đồ chỉ phản ánh dự đoán AI và điểm sàng lọc của bệnh nhân được chọn, không phải chẩn đoán bệnh lý.")

    try:
        sessions = get_multimodal_sessions(user_id=user_id, limit=500)
    except Exception as exc:
        st.error(f"Không thể đọc các phiên phân tích từ SQLite: {exc}")
        return

    if not sessions:
        st.warning("Chưa có phiên AI tổng hợp nào được lưu. Hãy vào '🧠 Phân tích cảm xúc tổng hợp', phân tích và bấm '💾 Lưu phiên phân tích'.")
        return

    patients = get_patients(user_id=user_id)
    patient_lookup = {p['id']: p for p in patients}
    st.subheader('Chọn bệnh nhân để theo dõi')
    options = [p['id'] for p in patients]
    selected_patient = st.selectbox(
        'Bệnh nhân', options,
        format_func=lambda pid: f"{patient_lookup[pid]['patient_code']} — {patient_lookup[pid]['display_name']}",
        key=f'dash_patient_{user_id}',
        placeholder='Chọn bệnh nhân',
        index=None,
    )
    if selected_patient is None:
        st.info('Chọn một bệnh nhân để xem Dashboard riêng. Phiên cũ chưa gắn bệnh nhân sẽ không được tính vào biểu đồ.')
        return
    sessions = [s for s in sessions if s.get('patient_id') == selected_patient]
    if not sessions:
        st.info('Bệnh nhân này chưa có phiên AI tổng hợp đã lưu.')
        return

    df = pd.DataFrame(sessions)
    df["Thời gian"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["Ngày"] = df["Thời gian"].dt.date

    st.subheader("1. Bộ lọc")
    col1, col2 = st.columns(2)
    with col1:
        labels = sorted(df["ai_label"].dropna().unique().tolist())
        selected_label = st.selectbox("Nhận xét AI", ["Tất cả"] + labels, key=f"dash_label_{user_id}")
    with col2:
        only_phq = st.checkbox("Chỉ xem phiên có PHQ-9", key=f"dash_phq_{user_id}")

    filtered = df.copy()
    if selected_label != "Tất cả":
        filtered = filtered[filtered["ai_label"] == selected_label]
    if only_phq:
        filtered = filtered[filtered["phq9_score"].notna()]

    if filtered.empty:
        st.info("Không có phiên phân tích phù hợp với bộ lọc.")
        return

    st.subheader("2. Tổng quan")
    total = len(filtered)
    phq_count = int(filtered["phq9_score"].notna().sum())
    distinct_labels = int(filtered["ai_label"].nunique())
    safety_flags = int((pd.to_numeric(filtered["phq9_item9"], errors="coerce") > 0).sum())
    a, b, c, d = st.columns(4)
    a.metric("Phiên phân tích", total)
    b.metric("Phiên có PHQ-9", phq_count)
    c.metric("Loại nhận xét AI", distinct_labels)
    d.metric("Phiên có câu 9 > 0", safety_flags)
    if safety_flags:
        st.warning("Có phiên PHQ-9 với câu 9 > 0. Đây là tín hiệu cần bác sĩ đánh giá an toàn trực tiếp, không phải kết luận mức độ nguy cơ.")

    st.subheader("3. Biểu đồ kết quả AI")
    counts = filtered["ai_label"].value_counts().rename_axis("Nhận xét AI").to_frame("Số phiên")
    st.bar_chart(counts)
    st.caption("Thống kê số phiên theo nhãn mô tả của AI; không dùng để suy ra tỷ lệ mắc bệnh.")

    phq = filtered[filtered["phq9_score"].notna()].copy()
    st.subheader("4. Xu hướng điểm PHQ-9")
    if phq.empty:
        st.info("Chưa có phiên PHQ-9 trong bộ lọc hiện tại.")
    else:
        phq["Điểm PHQ-9"] = pd.to_numeric(phq["phq9_score"], errors="coerce")
        phq = phq.sort_values(["Thời gian", "id"])
        phq["Phiên"] = phq.apply(lambda r: f'#{int(r["id"])} | {r["created_at"]}', axis=1)
        st.line_chart(phq.set_index("Phiên")[["Điểm PHQ-9"]], y_label="Điểm PHQ-9 (0–27)")
        st.caption("Các điểm thuộc hồ sơ bệnh nhân được chọn. Cần kiểm tra điều kiện đánh giá và diễn giải cùng bác sĩ.")

    st.subheader("5. Lịch sử và chi tiết phiên")
    display = filtered[["id", "created_at", "ai_label", "phq9_score", "phq9_band", "doctor_name", "assessment"]].rename(columns={
        "id": "Mã phiên", "created_at": "Thời gian", "ai_label": "Nhận xét AI",
        "phq9_score": "PHQ-9", "phq9_band": "Mức sàng lọc", "doctor_name": "Người đánh giá",
        "assessment": "Nhận định bác sĩ",
    })
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.download_button("📥 Xuất danh sách phiên (CSV)", display.to_csv(index=False).encode("utf-8-sig"), file_name="emotionai_dashboard.csv", mime="text/csv", key=f"dash_export_{user_id}")

    chosen_id = st.selectbox("Chọn phiên để xem chi tiết", filtered["id"].astype(int).tolist(), format_func=lambda x: f"Phiên #{x}", key=f"dash_selected_{user_id}")
    chosen = next(s for s in sessions if s["id"] == chosen_id)
    st.write("**Thời gian:**", chosen["created_at"])
    st.write("**Nhận xét AI:**", chosen["ai_label"])
    st.write(chosen["ai_detail"])
    if chosen["phq9_score"] is not None:
        st.write("**PHQ-9:**", f'{chosen["phq9_score"]}/27 — {chosen["phq9_band"]}')
    st.write("**Bác sĩ/người đánh giá:**", chosen["doctor_name"])
    st.write("**Nhận định:**", chosen["assessment"])
    st.write("**Ghi chú:**", chosen["doctor_notes"])
    try:
        results = json.loads(chosen["results_json"])
        with st.expander("Xem dữ liệu từng nguồn AI"):
            st.json(results)
    except (TypeError, ValueError):
        st.warning("Dữ liệu nguồn của phiên này không đọc được.")

    show_patient_trends(sessions, user_id=user_id, patient_id=selected_patient)

    st.divider()
    st.subheader("7. Xuất báo cáo PDF bệnh nhân")
    st.caption("Báo cáo chỉ dành cho bệnh nhân đang chọn. Chỉ xuất khi có sự đồng ý và sử dụng theo quy trình bảo mật.")
    confirm = st.checkbox("Tôi xác nhận được phép xuất báo cáo của bệnh nhân này", key=f"pdf_consent_{user_id}_{selected_patient}")
    report_scope = st.radio("Phạm vi báo cáo", ["Phiên đang chọn", "Tất cả phiên của bệnh nhân"], horizontal=True, key=f"pdf_scope_{user_id}_{selected_patient}")
    if confirm:
        try:
            pdf_sessions = [chosen] if report_scope == "Phiên đang chọn" else sessions
            pdf_bytes = build_patient_report_pdf(patient_lookup[selected_patient], pdf_sessions)
            st.download_button(
                "📄 Tải báo cáo PDF", data=pdf_bytes,
                file_name=f"EmotionAI_{patient_lookup[selected_patient]['patient_code']}.pdf",
                mime="application/pdf", key=f"pdf_download_{user_id}_{selected_patient}"
            )
        except Exception as exc:
            st.error(f"Không tạo được PDF: {exc}")


