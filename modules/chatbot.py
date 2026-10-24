"""Chatbot hướng dẫn theo quy tắc cho Alone – EmotionAI.
Không phải mô hình AI tạo sinh hoặc dịch vụ tư vấn sức khỏe tâm thần.
"""
import unicodedata
import streamlit as st


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.casefold().strip())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.replace("đ", "d")


def get_bot_response(message: str) -> str:
    msg = normalize(message)
    if any(x in msg for x in ("tu tu", "tu sat", "muon chet", "lam hai ban than")):
        return ("Mình rất tiếc vì bạn đang gặp khó khăn. Nếu bạn có nguy cơ làm hại bản thân "
                "ngay lúc này, hãy gọi dịch vụ cấp cứu tại nơi bạn sống hoặc nhờ người đáng tin cậy "
                "ở cạnh bạn. Bạn có muốn chia sẻ điều gì đang xảy ra không?")
    if any(x in msg for x in ("xin chao", "hello", "chao bot", "hi bot")):
        return "Xin chào! Mình là trợ lý hướng dẫn Alone. Bạn muốn tìm hiểu chức năng nào?"
    if any(x in msg for x in ("buon", "met moi", "co don")):
        return ("Mình nghe bạn đang không vui. Bạn có thể thử nghỉ ngơi, trò chuyện với người tin tưởng "
                "hoặc chia sẻ thêm điều khiến bạn buồn. Nếu cảm giác này kéo dài, hãy cân nhắc tìm hỗ trợ chuyên môn.")
    if any(x in msg for x in ("cang thang", "stress", "lo lang")):
        return ("Bạn có thể thử thở chậm, nghỉ ngơi và chia nhỏ công việc. "
                "Nếu căng thẳng kéo dài hoặc ảnh hưởng sinh hoạt, hãy tìm hỗ trợ từ chuyên gia.")
    if any(x in msg for x in ("khuon mat", "deepface", "opencv")):
        return "Mở mục Nhận diện khuôn mặt, tải ảnh hoặc chụp webcam. Hệ thống dùng OpenCV và DeepFace để dự đoán biểu cảm."
    if any(x in msg for x in ("giong noi", "am thanh", "micro")):
        return "Mở mục Phân tích giọng nói, tải WAV/MP3 hoặc thu âm bằng micro, sau đó nhấn Phân tích."
    if any(x in msg for x in ("nhip tim", "bpm")):
        return "Mở mục Phân tích nhịp tim để nhập BPM hoặc mô phỏng. Kết quả không phải chẩn đoán y khoa."
    if any(x in msg for x in ("bac si", "dat lich", "lich kham")):
        return "Đăng nhập tài khoản phù hợp, mở Danh sách bác sĩ hoặc Đặt lịch khám để xem lựa chọn có sẵn."
    if any(x in msg for x in ("cam on", "thank")):
        return "Rất vui vì đã hỗ trợ bạn!"
    return ("Mình có thể hướng dẫn sử dụng các mục khuôn mặt, giọng nói, nhịp tim, "
            "phân tích tổng hợp và đặt lịch bác sĩ. Bạn muốn hỏi về mục nào?")


def show_chatbot():
    st.subheader("💬 Trợ lý Alone")
    st.caption("Chatbot trả lời theo quy tắc có sẵn; không phải AI tạo sinh hay chuyên gia tâm lý.")
    key = "alone_chat_history"
    if key not in st.session_state:
        st.session_state[key] = [{"role": "assistant", "content": "Xin chào! Mình có thể hướng dẫn bạn sử dụng Alone."}]
    if st.button("🗑️ Xóa cuộc trò chuyện", key="alone_clear_chat"):
        st.session_state[key] = [{"role": "assistant", "content": "Xin chào! Mình có thể hướng dẫn bạn sử dụng Alone."}]
    for item in st.session_state[key]:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
    prompt = st.chat_input("Nhập câu hỏi của bạn...", key="alone_chat_input")
    if prompt and prompt.strip():
        st.session_state[key].append({"role": "user", "content": prompt})
        response = get_bot_response(prompt)
        st.session_state[key].append({"role": "assistant", "content": response})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            st.markdown(response)
