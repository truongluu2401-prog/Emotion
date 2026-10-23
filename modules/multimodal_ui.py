"""EmotionAI 8.1: AI đa phương thức + sàng lọc PHQ-9 + nhận định bác sĩ."""
from datetime import datetime
from io import StringIO
import streamlit as st
import pandas as pd
from modules.face_emotion import analyze_face
from modules.voice_emotion import analyze_voice
from modules.heart_rate import analyze_heart_rate
from modules.patient_database import get_patients
from modules.multimodal_database import save_multimodal_session, get_multimodal_sessions

EMOTION_MAP = {
    "happy": "vui vẻ", "happiness": "vui vẻ", "joy": "vui vẻ",
    "vui": "vui vẻ", "vui vẻ": "vui vẻ",
    "sad": "buồn", "sadness": "buồn", "buồn": "buồn",
    "angry": "tức giận", "anger": "tức giận", "tức giận": "tức giận",
    "fear": "sợ hãi", "fearful": "sợ hãi", "sợ hãi": "sợ hãi",
    "disgust": "khó chịu", "disgusted": "khó chịu",
    "surprise": "ngạc nhiên", "surprised": "ngạc nhiên",
    "neutral": "trung tính", "calm": "trung tính",
    "bình thường": "trung tính", "trung tính": "trung tính",
    "anxiety": "lo lắng", "anxious": "lo lắng", "lo lắng": "lo lắng",
    "stress": "căng thẳng", "stressed": "căng thẳng", "căng thẳng": "căng thẳng",
}
PHQ9_ITEMS = [
    "Ít hứng thú hoặc ít niềm vui khi làm mọi việc",
    "Cảm thấy buồn, chán nản hoặc tuyệt vọng",
    "Khó ngủ, ngủ không ngon hoặc ngủ quá nhiều",
    "Cảm thấy mệt mỏi hoặc thiếu năng lượng",
    "Ăn kém hoặc ăn quá nhiều",
    "Cảm thấy bản thân kém cỏi hoặc làm gia đình thất vọng",
    "Khó tập trung, ví dụ khi đọc hoặc xem truyền hình",
    "Cử động/nói chậm bất thường hoặc bồn chồn hơn thường lệ",
    "Nghĩ rằng thà chết còn hơn hoặc nghĩ đến việc tự làm hại bản thân",
]
PHQ9_OPTIONS = [
    "Không ngày nào (0)",
    "Vài ngày (1)",
    "Hơn một nửa số ngày (2)",
    "Gần như mỗi ngày (3)",
]


def _normalize(label):
    raw = str(label).strip().lower()
    return EMOTION_MAP.get(raw, raw)


def _ai_summary(results):
    """Nhãn mô tả dự đoán, tuyệt đối không phải chẩn đoán."""
    labels = []
    for source in ("face", "voice"):
        if source in results:
            labels.append(_normalize(results[source]["emotion"]))
    if not labels:
        return "Chưa đủ dữ liệu biểu cảm/giọng nói", (
            "Cần phân tích khuôn mặt hoặc giọng nói để có nhận xét AI. "
            "BPM không cho biết cảm xúc hoặc bệnh lý tâm thần."
        )
    if len(labels) == 1:
        return f"Tín hiệu {labels[0]} từ một nguồn", (
            f"Một mô hình ghi nhận nhãn '{labels[0]}'. "
            "Chưa có nguồn biểu cảm/giọng nói thứ hai để đối chiếu; "
            "không thể kết luận cảm xúc thực tế hay tình trạng tâm lý."
        )
    a, b = labels
    if a == b:
        return f"Hai mô hình cùng dự đoán: {a}", (
            f"Khuôn mặt và giọng nói đều được mô hình gán nhãn '{a}'. "
            "Đây là sự nhất quán giữa dự đoán, không chứng minh người được phân tích "
            "đang có cảm xúc đó hoặc mắc bệnh tâm lý."
        )
    return "Tín hiệu cảm xúc chưa thống nhất", (
        f"Mô hình khuôn mặt dự đoán '{a}', còn mô hình giọng nói dự đoán '{b}'. "
        "Kết quả khác nhau có thể do bối cảnh, chất lượng dữ liệu hoặc sai số mô hình. "
        "Bác sĩ nên trao đổi trực tiếp để làm rõ."
    )


def _phq9_band(score):
    if score <= 4:
        return "Tối thiểu (0–4)"
    if score <= 9:
        return "Nhẹ (5–9)"
    if score <= 14:
        return "Trung bình (10–14)"
    if score <= 19:
        return "Khá nặng (15–19)"
    return "Nặng (20–27)"


def show_multimodal_page(user_id):
    st.header("🧠 AI phân tích cảm xúc tổng hợp")
    st.write("Phân tích khuôn mặt, giọng nói và chỉ số BPM trong cùng một phiên để hỗ trợ bác sĩ.")
    st.info("AI chỉ dự đoán biểu cảm/tín hiệu giọng nói; không thể chẩn đoán trầm cảm, lo âu hoặc xác định cảm xúc thực tế từ các tín hiệu này.")
    st.warning("Chỉ sử dụng ảnh, âm thanh và thông tin sàng lọc khi người được phân tích đồng ý. Ưu tiên dữ liệu thử nghiệm trong đồ án.")

    key = f"multimodal_{user_id}"
    if key not in st.session_state:
        st.session_state[key] = {}
    results = st.session_state[key]

    patients = get_patients(user_id=user_id)
    st.subheader('0. Chọn bệnh nhân')
    if not patients:
        st.warning('Bạn cần tạo hồ sơ trong menu 👥 Hồ sơ bệnh nhân trước khi lưu kết quả AI.')
        selected_patient_id = None
    else:
        patient_lookup = {p['id']: p for p in patients}
        selected_patient_id = st.selectbox(
            'Hồ sơ nhận kết quả phân tích',
            list(patient_lookup),
            format_func=lambda pid: f"{patient_lookup[pid]['patient_code']} — {patient_lookup[pid]['display_name']}",
            key=f'mm_patient_{user_id}',
        )
        st.caption('Hãy xác nhận đúng bệnh nhân trước khi phân tích và lưu kết quả.')

    st.subheader("1. Cung cấp dữ liệu")
    left, middle, right = st.columns(3)
    with left:
        st.markdown("**😊 Khuôn mặt**")
        image_mode = st.radio("Nguồn hình ảnh", ["📷 Chụp webcam", "📁 Tải ảnh"], key=f"mm_image_mode_{user_id}")
        if image_mode == "📷 Chụp webcam":
            image = st.camera_input("Chụp ảnh khuôn mặt", key=f"mm_camera_{user_id}")
        else:
            image = st.file_uploader("Tải ảnh JPG/PNG", type=["jpg", "jpeg", "png"], key=f"mm_face_{user_id}")
        if st.button("🔍 Phân tích khuôn mặt", key=f"mm_run_face_{user_id}", disabled=image is None):
            try:
                with st.spinner("Đang phân tích ảnh..."):
                    faces = analyze_face(image.getvalue())
                if not faces:
                    st.warning("Không phát hiện khuôn mặt.")
                elif len(faces) != 1:
                    st.warning("Vui lòng dùng ảnh chỉ có một người.")
                else:
                    f = faces[0]
                    results["face"] = {"emotion": str(f["emotion"]), "confidence": float(f["confidence"])}
                    st.success("Đã phân tích khuôn mặt.")
            except Exception as exc:
                st.error(f"Lỗi phân tích khuôn mặt: {exc}")
    with middle:
        st.markdown("**🎤 Giọng nói**")
        voice_mode = st.radio("Nguồn âm thanh", ["🎙️ Thu âm micro", "📁 Tải file"], key=f"mm_voice_mode_{user_id}")
        if voice_mode == "🎙️ Thu âm micro":
            audio = st.audio_input("Nhấn để thu âm", key=f"mm_record_{user_id}")
        else:
            audio = st.file_uploader("Tải WAV/MP3", type=["wav", "mp3"], key=f"mm_voice_{user_id}")
        if audio is not None:
            st.audio(audio)
        if st.button("🎯 Phân tích giọng nói", key=f"mm_run_voice_{user_id}", disabled=audio is None):
            try:
                with st.spinner("Đang phân tích giọng nói..."):
                    v = analyze_voice(audio.getvalue())
                results["voice"] = {"emotion": str(v["emotion"]), "confidence": float(v["confidence"])}
                st.success("Đã phân tích giọng nói.")
            except Exception as exc:
                st.error(f"Lỗi phân tích giọng nói: {exc}")
    with right:
        st.markdown("**❤️ Nhịp tim**")
        bpm = st.number_input("BPM đo được (hoặc số liệu thử nghiệm)", min_value=30, max_value=220, value=75, key=f"mm_bpm_{user_id}")
        if st.button("Phân tích BPM", key=f"mm_run_bpm_{user_id}"):
            try:
                h = analyze_heart_rate(int(bpm))
                results["heart"] = {"bpm": int(h["bpm"]), "status": str(h["status"]), "note": str(h.get("note", ""))}
                st.success("Đã phân tích BPM.")
            except Exception as exc:
                st.error(f"Lỗi phân tích BPM: {exc}")

    st.divider()
    st.subheader("2. Kết quả từng nguồn")
    rows = []
    if "face" in results:
        f = results["face"]
        rows.append({"Nguồn": "Khuôn mặt", "Kết quả": f["emotion"], "Điểm mô hình": f'{f["confidence"]:.2f}%'})
    if "voice" in results:
        v = results["voice"]
        rows.append({"Nguồn": "Giọng nói", "Kết quả": v["emotion"], "Điểm mô hình": f'{v["confidence"]:.2f}%'})
    if "heart" in results:
        h = results["heart"]
        rows.append({"Nguồn": "Nhịp tim", "Kết quả": f'{h["bpm"]} BPM — {h["status"]}', "Điểm mô hình": "Không áp dụng"})
    if not rows:
        st.info("Hãy phân tích ít nhất một nguồn dữ liệu ở trên.")
        return
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader("3. Nhận xét AI tổng hợp")
    ai_label, ai_detail = _ai_summary(results)
    st.markdown(f"**Kết quả mô tả: {ai_label}**")
    st.info(ai_detail)
    if "heart" in results:
        st.caption("BPM là thông tin sinh lý độc lập, không dùng để suy ra cảm xúc hoặc trầm cảm.")
    st.caption("Không cộng hay lấy trung bình các điểm dự đoán từ các mô hình khác nhau.")

    st.divider()
    st.subheader("4. Sàng lọc triệu chứng PHQ-9 (tùy chọn)")
    st.write("PHQ-9 hỏi về tần suất triệu chứng trong **2 tuần qua**. Người được đánh giá tự trả lời; bác sĩ hướng dẫn khi cần. Điểm số chỉ phục vụ sàng lọc, không phải chẩn đoán.")
    use_phq = st.checkbox("Thực hiện PHQ-9 trong phiên này", key=f"mm_phq_enable_{user_id}")
    phq_score = None
    phq_band = None
    item9 = None
    if use_phq:
        scores = []
        with st.form(key=f"mm_phq_form_{user_id}"):
            for i, question in enumerate(PHQ9_ITEMS):
                answer = st.selectbox(
                    f"Câu {i+1}. {question}",
                    options=["— Chưa trả lời —"] + PHQ9_OPTIONS,
                    key=f"mm_phq_q{i}_{user_id}",
                )
                scores.append(None if answer.startswith("—") else PHQ9_OPTIONS.index(answer))
            submitted = st.form_submit_button("📋 Tính điểm PHQ-9")
        if submitted:
            if any(x is None for x in scores):
                st.warning("Vui lòng trả lời đủ 9 câu trước khi tính điểm.")
                st.session_state.pop(f"mm_phq_result_{user_id}", None)
            else:
                st.session_state[f"mm_phq_result_{user_id}"] = {"scores": scores}
        saved = st.session_state.get(f"mm_phq_result_{user_id}")
        # Chỉ sử dụng kết quả đã xác nhận bằng nút Tính điểm.
        # Không đặt callback trên widget bên trong st.form().
        if saved is not None and saved.get("scores") == scores:
            phq_score = sum(saved["scores"])
            item9 = saved["scores"][8]
            phq_band = _phq9_band(phq_score)
            st.metric("Điểm PHQ-9", f"{phq_score}/27")
            st.write(f"**Mức độ triệu chứng theo thang sàng lọc:** {phq_band}")
            st.caption("Không dùng điểm PHQ-9 đơn lẻ để xác nhận hoặc loại trừ chẩn đoán trầm cảm.")
            if item9 > 0:
                st.error(
                    "Câu 9 có câu trả lời khác 0: cần bác sĩ đánh giá an toàn trực tiếp, "
                    "hỏi thêm về ý nghĩ tự làm hại và mức độ nguy cơ ngay trong buổi đánh giá. "
                    "Không chỉ dựa vào tổng điểm PHQ-9. Nếu có nguy hiểm trước mắt, "
                    "cần hỗ trợ khẩn cấp theo quy trình tại cơ sở y tế."
                )

    st.divider()
    st.subheader("5. Kết luận của bác sĩ tâm lý")
    st.caption("Bác sĩ kết hợp phỏng vấn, quan sát, kết quả AI và công cụ sàng lọc (nếu có) để đưa ra nhận định.")
    doctor_name = st.text_input("Tên bác sĩ / người đánh giá", key=f"mm_doctor_{user_id}")
    assessment = st.selectbox(
        "Nhận định chuyên môn của bác sĩ",
        [
            "Chưa đủ thông tin để kết luận",
            "Chưa ghi nhận vấn đề rõ ràng qua đánh giá hiện tại",
            "Có biểu hiện cần theo dõi thêm",
            "Cần đánh giá chuyên sâu về triệu chứng trầm cảm",
            "Cần đánh giá chuyên sâu về triệu chứng lo âu",
            "Cần đánh giá an toàn và hỗ trợ khẩn cấp",
            "Nhận định khác (xem ghi chú)",
        ],
        key=f"mm_assessment_{user_id}",
    )
    doctor_notes = st.text_area(
        "Nhận xét và kết luận chuyên môn (bác sĩ tự viết)",
        placeholder="Ghi nhận dựa trên phỏng vấn, thời gian triệu chứng, mức độ ảnh hưởng sinh hoạt và kết quả hỗ trợ...",
        key=f"mm_notes_{user_id}",
        height=130,
    )
    if not doctor_name.strip() or not doctor_notes.strip():
        st.info("Nhập tên bác sĩ và nhận xét để hoàn thiện báo cáo.")
    else:
        st.success("Đã có nhận định của bác sĩ để đưa vào báo cáo.")

    st.divider()
    st.subheader("6. Lưu phiên phân tích vào SQLite")
    st.caption("Chỉ lưu nhãn dự đoán, BPM, điểm sàng lọc và ghi chú; không lưu ảnh hoặc bản ghi âm gốc.")
    consent = st.checkbox(
        "Tôi xác nhận người được phân tích đã đồng ý lưu kết quả cho mục đích phù hợp.",
        key=f"mm_consent_{user_id}",
    )
    if st.button(
        "💾 Lưu phiên phân tích",
        key=f"mm_save_{user_id}",
        disabled=not (consent and doctor_name.strip() and doctor_notes.strip() and selected_patient_id is not None),
        type="primary",
    ):
        try:
            session_id = save_multimodal_session(
                user_id=user_id,
                patient_id=selected_patient_id,
                results=results,
                ai_label=ai_label,
                ai_detail=ai_detail,
                doctor_name=doctor_name,
                assessment=assessment,
                doctor_notes=doctor_notes,
                phq9_score=phq_score,
                phq9_band=phq_band,
                phq9_item9=item9,
            )
            st.success(f"Đã lưu phiên phân tích #{session_id} cho tài khoản hiện tại.")
        except Exception as exc:
            st.error(f"Không thể lưu phiên: {exc}")

    with st.expander("📚 Xem các phiên phân tích đã lưu của tài khoản này"):
        try:
            saved_sessions = get_multimodal_sessions(user_id=user_id)
            if not saved_sessions:
                st.info("Chưa có phiên tổng hợp nào được lưu.")
            else:
                overview = pd.DataFrame([
                    {
                        "Mã phiên": s["id"],
                        "Thời gian": s["created_at"],
                        "Nhận xét AI": s["ai_label"],
                        "PHQ-9": (
                            f'{s["phq9_score"]}/27'
                            if s["phq9_score"] is not None else "Chưa thực hiện"
                        ),
                        "Bác sĩ": s["doctor_name"],
                        "Nhận định bác sĩ": s["assessment"],
                    }
                    for s in saved_sessions
                ])
                st.dataframe(overview, hide_index=True, use_container_width=True)
                chosen_id = st.selectbox(
                    "Xem chi tiết phiên đã lưu",
                    [s["id"] for s in saved_sessions],
                    key=f"mm_view_saved_{user_id}",
                )
                chosen = next(s for s in saved_sessions if s["id"] == chosen_id)
                st.write("**Nhận xét AI:**", chosen["ai_detail"])
                st.write("**Nhận định bác sĩ:**", chosen["assessment"])
                st.write("**Ghi chú bác sĩ:**", chosen["doctor_notes"])
                st.json(__import__("json").loads(chosen["results_json"]), expanded=False)
        except Exception as exc:
            st.error(f"Không thể tải lịch sử tổng hợp: {exc}")

    st.divider()
    st.subheader("7. Xuất báo cáo")
    report = StringIO()
    report.write("EMOTIONAI - BAO CAO HO TRO DANH GIA CAM XUC\n")
    report.write(f"Thoi gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.write(f"Bac si: {doctor_name.strip()}\n")
    if selected_patient_id is not None:
        report.write(f"Ma benh nhan: {patient_lookup[selected_patient_id]['patient_code']}\n")
    report.write("\nKET QUA AI (KHONG PHAI CHAN DOAN)\n")
    report.write(pd.DataFrame(rows).to_csv(index=False))
    report.write(f"\nNhan xet AI: {ai_label}\n{ai_detail}\n")
    if phq_score is not None:
        report.write(f"\nPHQ-9: {phq_score}/27 - {phq_band}\n")
        if item9 and item9 > 0:
            report.write("CAN DANH GIA AN TOAN TRUC TIEP: Cau 9 > 0\n")
    report.write(f"\nNhan dinh cua bac si: {assessment}\n")
    report.write(f"Ket luan / ghi chu: {doctor_notes.strip()}\n")
    report.write("\nAI va PHQ-9 khong thay the danh gia va chan doan chuyen mon.\n")
    st.download_button(
        "📥 Xuất báo cáo tổng hợp (TXT)",
        data=report.getvalue().encode("utf-8-sig"),
        file_name="emotionai_bao_cao_bac_si.txt",
        mime="text/plain",
        disabled=not (doctor_name.strip() and doctor_notes.strip()),
        key=f"mm_report_{user_id}",
    )
    st.download_button(
        "📥 Xuất bảng kết quả CSV",
        data=pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig"),
        file_name="emotionai_multimodal.csv",
        mime="text/csv",
        key=f"mm_export_{user_id}",
    )
    if st.button("🔄 Bắt đầu phiên mới", key=f"mm_clear_{user_id}"):
        st.session_state[key] = {}
        for suffix in ("doctor", "assessment", "notes", "phq_enable", "phq_result", "consent"):
            st.session_state.pop(f"mm_{suffix}_{user_id}", None)
        for i in range(9):
            st.session_state.pop(f"mm_phq_q{i}_{user_id}", None)
        st.rerun()
    st.caption("Các phiên đã lưu nằm trong emotionai.db và được phân tách theo tài khoản. Không sử dụng dữ liệu bệnh nhân thật nếu chưa có quy trình bảo mật và đồng ý phù hợp.")
