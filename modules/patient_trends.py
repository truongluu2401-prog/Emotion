"""So sánh các phiên AI của cùng bệnh nhân, không tự động chẩn đoán."""
import json
import pandas as pd
import streamlit as st


def _signals(record):
    try:
        raw = json.loads(record.get("results_json") or "{}")
        if not isinstance(raw, dict):
            return {}
        return raw
    except (TypeError, ValueError):
        return {}


def _signal_label(record, source):
    obj = _signals(record).get(source)
    if isinstance(obj, dict):
        return str(obj.get("emotion") or "Chưa có dữ liệu")
    return "Chưa có dữ liệu"


def show_patient_trends(sessions, user_id, patient_id):
    """sessions phải được lọc user_id và patient_id từ tầng truy vấn/giao diện."""
    st.divider()
    st.subheader("6. Theo dõi xu hướng cảm xúc theo từng buổi")
    st.caption("Biểu đồ so sánh nhãn AI và PHQ-9 qua thời gian; không xác định bệnh lý hay hiệu quả điều trị.")
    ordered = sorted(sessions, key=lambda x: (x["created_at"], x["id"]))
    if len(ordered) < 2:
        st.info("Cần ít nhất hai phiên phân tích của cùng bệnh nhân để so sánh.")
        return

    trend_rows = []
    for s in ordered:
        trend_rows.append({
            "Phiên": f'#{s["id"]} · {s["created_at"]}',
            "Mã phiên": int(s["id"]),
            "Thời gian": s["created_at"],
            "Khuôn mặt": _signal_label(s, "face"),
            "Giọng nói": _signal_label(s, "voice"),
            "Nhận xét AI": s["ai_label"],
            "PHQ-9": s.get("phq9_score"),
        })
    df = pd.DataFrame(trend_rows)
    st.markdown("**Biến đổi nhãn dự đoán theo từng phiên**")
    st.dataframe(df[["Mã phiên", "Thời gian", "Khuôn mặt", "Giọng nói", "Nhận xét AI", "PHQ-9"]], hide_index=True, use_container_width=True)
    st.caption("Các nhãn biểu cảm không có thang đo liên tục nên được trình bày bằng bảng, không nối thành đường biểu đồ.")

    phq = df.dropna(subset=["PHQ-9"]).copy()
    if len(phq) >= 2:
        phq["Điểm PHQ-9"] = pd.to_numeric(phq["PHQ-9"], errors="coerce")
        st.markdown("**Xu hướng điểm sàng lọc PHQ-9**")
        st.line_chart(phq.set_index("Phiên")[["Điểm PHQ-9"]], y_label="Điểm PHQ-9 (0–27)")
        first, last = phq.iloc[0], phq.iloc[-1]
        change = int(last["Điểm PHQ-9"] - first["Điểm PHQ-9"])
        if change < 0:
            st.info(f"Điểm PHQ-9 ở phiên cuối thấp hơn phiên đầu {abs(change)} điểm. Đây là thay đổi điểm sàng lọc, không chứng minh bệnh nhân đã khỏi bệnh.")
        elif change > 0:
            st.info(f"Điểm PHQ-9 ở phiên cuối cao hơn phiên đầu {change} điểm. Bác sĩ cần xem xét bối cảnh và đánh giá thêm.")
        else:
            st.info("Điểm PHQ-9 đầu và cuối bằng nhau; không đủ cơ sở để kết luận tình trạng không thay đổi.")
        if any((s.get("phq9_item9") or 0) > 0 for s in ordered):
            st.warning("Có phiên ghi nhận câu 9 PHQ-9 > 0. Cần đánh giá an toàn trực tiếp theo quy trình chuyên môn.")
    else:
        st.caption("Cần ít nhất hai phiên có PHQ-9 để hiển thị biểu đồ điểm sàng lọc.")

    st.markdown("**So sánh hai phiên do bác sĩ chọn**")
    ids = [int(s["id"]) for s in ordered]
    col1, col2 = st.columns(2)
    with col1:
        before_id = st.selectbox("Phiên trước", ids, index=0, format_func=lambda x: f"Phiên #{x}", key=f"trend_before_{user_id}_{patient_id}")
    with col2:
        after_id = st.selectbox("Phiên sau", ids, index=len(ids)-1, format_func=lambda x: f"Phiên #{x}", key=f"trend_after_{user_id}_{patient_id}")
    if before_id == after_id:
        st.warning("Hãy chọn hai phiên khác nhau.")
        return
    lookup = {int(s["id"]): s for s in ordered}
    a, b = lookup[before_id], lookup[after_id]
    comparison = pd.DataFrame([
        {"Chỉ số": "Thời gian", "Phiên A": a["created_at"], "Phiên B": b["created_at"]},
        {"Chỉ số": "Khuôn mặt", "Phiên A": _signal_label(a, "face"), "Phiên B": _signal_label(b, "face")},
        {"Chỉ số": "Giọng nói", "Phiên A": _signal_label(a, "voice"), "Phiên B": _signal_label(b, "voice")},
        {"Chỉ số": "Nhận xét AI", "Phiên A": a["ai_label"], "Phiên B": b["ai_label"]},
        {"Chỉ số": "PHQ-9", "Phiên A": "Chưa thực hiện" if a["phq9_score"] is None else f'{a["phq9_score"]}/27', "Phiên B": "Chưa thực hiện" if b["phq9_score"] is None else f'{b["phq9_score"]}/27'},
        {"Chỉ số": "Nhận định bác sĩ", "Phiên A": a["assessment"], "Phiên B": b["assessment"]},
    ])
    st.dataframe(comparison, hide_index=True, use_container_width=True)
    st.download_button("📥 Xuất bảng so sánh CSV", comparison.to_csv(index=False).encode("utf-8-sig"), file_name=f"emotionai_so_sanh_benh_nhan_{patient_id}.csv", mime="text/csv", key=f"trend_export_{user_id}_{patient_id}")
    st.caption("Chỉ sử dụng dữ liệu của bệnh nhân được chọn và tài khoản đang đăng nhập.")
