
import streamlit as st
import pandas as pd
import sqlite3
from modules.google_auth import sync_google_user, google_is_logged_in
from pathlib import Path
from modules.auth_database import init_auth_database
from modules.auth_service import refresh_user
from modules.admin_ui import show_admin_dashboard
from modules.profile_ui import show_profile_page
from modules.password_reset import show_reset_password
from modules.multimodal_ui import show_multimodal_page
from modules.doctor_dashboard import show_doctor_dashboard
from modules.patient_ui import show_patient_page
from modules.auth_ui import show_auth_page
from modules.face_emotion import analyze_face, draw_face_results
from modules.voice_emotion import analyze_voice
from modules.heart_rate import analyze_heart_rate, simulate_heart_rate
from modules.database import (
    init_database,
    save_analysis,
    get_history,
    get_statistics
)


# ==========================================
# 1. CẤU HÌNH WEBSITE
# ==========================================

st.set_page_config(
    page_title="EmotionAI - Nhận diện cảm xúc",
    page_icon="🧠",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent
CSS_PATH = BASE_DIR / "assets" / "style.css"

# Tải giao diện CSS
if CSS_PATH.exists():
    css_content = CSS_PATH.read_text(encoding="utf-8")
    st.markdown(
        f"<style>{css_content}</style>",
        unsafe_allow_html=True
    )
else:
    st.warning(f"Không tìm thấy CSS: {CSS_PATH}")

# Giao diện mới được nạp sau CSS cũ để ghi đè kiểu hiển thị.
MODERN_CSS = BASE_DIR / "assets" / "style_emotionai_modern.css"
if MODERN_CSS.exists():
    st.markdown(f"<style>{MODERN_CSS.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# Khởi tạo SQLite
init_database()
init_auth_database()

# ==========================================
# ĐĂNG KÝ - ĐĂNG NHẬP - ĐĂNG XUẤT
# ==========================================

if "auth_user" not in st.session_state:
    st.session_state["auth_user"] = None

# Đồng bộ danh tính Google (nếu đăng nhập qua Google).
if google_is_logged_in():
    try:
        google_user = sync_google_user()
        if google_user is None:
            raise ValueError("Không thể lấy thông tin tài khoản Google.")
        st.session_state["auth_user"] = google_user
    except (ValueError, sqlite3.Error) as e:
        st.session_state["auth_user"] = None
        st.error(f"Đăng nhập Google chưa hoàn tất: {e}")
        if st.button("🚪 Thoát đăng nhập Google"):
            st.logout()
        st.stop()

# Kiểm tra lại tài khoản với SQLite, bao gồm trạng thái bị khóa.
if st.session_state["auth_user"] is not None:
    current_id = st.session_state["auth_user"]["id"]
    st.session_state["auth_user"] = refresh_user(current_id)


def logout_user():
    st.session_state["auth_user"] = None
    st.session_state["current_menu"] = "🏠 Trang chủ"
    if google_is_logged_in():
        st.logout()


# Khách chỉ xem nội dung giới thiệu; tất cả tính năng đều cần đăng nhập.
PUBLIC_FEATURES = [
    ("📸", "Nhận diện khuôn mặt", "Dự đoán biểu cảm từ ảnh hoặc webcam.", "😊 Nhận diện khuôn mặt"),
    ("🎙️", "Phân tích giọng nói", "Phân tích tín hiệu cảm xúc từ âm thanh.", "🎤 Phân tích giọng nói"),
    ("❤️", "Phân tích nhịp tim", "Nhập chỉ số BPM để xem kết quả tham khảo.", "❤️ Phân tích nhịp tim"),
    ("🧠", "AI tổng hợp & PHQ-9", "Kết hợp nhiều nguồn dữ liệu và bảng sàng lọc.", "🧠 Phân tích cảm xúc tổng hợp"),
    ("👥", "Hồ sơ bệnh nhân", "Lưu phiên phân tích theo từng bệnh nhân.", "👥 Hồ sơ bệnh nhân"),
    ("📊", "Dashboard bác sĩ", "Xem xu hướng và báo cáo phân tích.", "📈 AI Dashboard bác sĩ"),
]

def require_login(target):
    st.session_state["pending_menu"] = target
    st.session_state["public_view"] = "auth"
    st.session_state["auth_mode"] = "Đăng nhập"
    st.rerun()

if st.session_state["auth_user"] is None:
    # Tránh sidebar xuất hiện với người xem chưa đăng nhập.
    st.markdown('<style>[data-testid="stSidebar"]{display:none!important} [data-testid="stMainBlockContainer"]{max-width:1600px!important}</style>',unsafe_allow_html=True)
    st.markdown('<div class="public-strip">✦ EMOTIONAI · NỀN TẢNG AI HỖ TRỢ PHÂN TÍCH CẢM XÚC</div>',unsafe_allow_html=True)
    brand, home, about, login, signup = st.columns([4.7,1.2,1.35,1.4,1.4],vertical_alignment="center",gap="small")
    with brand:
        st.markdown('<div class="public-brand"><div class="brand-mark">🧠</div><div><strong>EmotionAI</strong><small>AI Emotion Analysis for Clinicians</small></div></div>',unsafe_allow_html=True)
    with home:
        if st.button("⌂ Trang chủ",key="pub_home",use_container_width=True):
            st.session_state["public_view"]="home";st.rerun()
    with about:
        if st.button("◈ Giới thiệu",key="pub_about",use_container_width=True):
            st.session_state["public_view"]="about";st.rerun()
    with login:
        if st.button("⇥ Đăng nhập",key="pub_login",use_container_width=True):
            st.session_state["public_view"]="auth";st.session_state["auth_mode"]="Đăng nhập";st.rerun()
    with signup:
        if st.button("Đăng ký",key="pub_signup",type="primary",use_container_width=True):
            st.session_state["public_view"]="auth";st.session_state["auth_mode"]="Đăng ký";st.rerun()

    if st.session_state.get("public_view","home") == "auth":
        if st.button("← Quay về trang chủ",key="pub_back"):
            st.session_state["public_view"]="home";st.rerun()
        show_auth_page()
        with st.expander("🔑 Quên mật khẩu? Đặt lại bằng OTP Gmail"):
            show_reset_password()
    else:
        st.markdown('''<section class="landing-hero"><div class="landing-hero-content">
        <div class="landing-pill">✦ CÔNG NGHỆ AI HỖ TRỢ CHUYÊN GIA TÂM LÝ</div>
        <h1>Hiểu cảm xúc sâu hơn<br><span>cùng trí tuệ nhân tạo</span></h1>
        <p>EmotionAI hỗ trợ bác sĩ quan sát biểu cảm khuôn mặt, tín hiệu giọng nói,
        nhịp tim và kết quả PHQ-9. Theo dõi các phiên phân tích theo từng bệnh nhân
        và tổng hợp thông tin phục vụ đánh giá chuyên môn.</p>
        <div class="landing-mini">✧ AI đa phương thức &nbsp;&nbsp; ✧ Dashboard trực quan &nbsp;&nbsp; ✧ Báo cáo PDF</div>
        </div></section>''',unsafe_allow_html=True)
        start, learn, spacer = st.columns([1.6,1.6,5],gap="medium")
        with start:
            if st.button("✨ Bắt đầu phân tích  →",type="primary",use_container_width=True,key="pub_start"):
                require_login("🧠 Phân tích cảm xúc tổng hợp")
        with learn:
            if st.button("Tìm hiểu thêm  →",use_container_width=True,key="pub_learn"):
                st.session_state["public_view"]="about";st.rerun()
        st.markdown('''<div class="landing-benefits"><div><b>🔬 Phân tích đa phương thức</b><span>Kết hợp khuôn mặt, giọng nói và BPM</span></div>
        <div><b>📋 Đánh giá có cơ sở</b><span>Ghi nhận PHQ-9 và nhận định bác sĩ</span></div>
        <div><b>🔐 Dữ liệu theo tài khoản</b><span>Yêu cầu đăng nhập khi sử dụng tính năng</span></div></div>''',unsafe_allow_html=True)
        st.markdown('''<div class="landing-section-head"><span>✦ KHÁM PHÁ EMOTIONAI</span><h2>Công cụ hỗ trợ phân tích cảm xúc</h2>
        <p>Chọn một tính năng để bắt đầu. Hệ thống sẽ yêu cầu đăng nhập để bảo vệ dữ liệu.</p></div>''',unsafe_allow_html=True)
        for i in range(0,len(PUBLIC_FEATURES),3):
            cols=st.columns(3,gap="large")
            for j,(icon,title,desc,target) in enumerate(PUBLIC_FEATURES[i:i+3]):
                with cols[j]:
                    st.markdown(f'<div class="landing-feature"><div class="landing-feature-icon">{icon}</div><h3>{title}</h3><p>{desc}</p></div>',unsafe_allow_html=True)
                    if st.button("Khám phá chức năng  →",key=f"feature_{i+j}",use_container_width=True):
                        require_login(target)
        st.markdown('''<div class="landing-about"><span>AI HỖ TRỢ BÁC SĨ</span><h2>Quy trình phân tích rõ ràng, dễ theo dõi</h2>
        <p>Đăng nhập → Chọn bệnh nhân → Thu thập dữ liệu → Phân tích AI → Bác sĩ đánh giá → Lưu phiên và xuất báo cáo.</p></div>''',unsafe_allow_html=True)
        if st.session_state.get("public_view") == "about":
            st.info("EmotionAI là đồ án thử nghiệm. Kết quả AI và PHQ-9 hỗ trợ tham khảo, không phải chẩn đoán y khoa. Dữ liệu BPM mô phỏng không phải số đo thật.")
        st.markdown('''<div class="landing-footer"><div><h3>🧠 EmotionAI</h3><p>Nền tảng AI phân tích cảm xúc đa phương thức dành cho chuyên gia tâm lý.</p></div>
        <div><h4>Chức năng</h4><p>Khuôn mặt · Giọng nói · Nhịp tim<br>PHQ-9 · Dashboard · PDF</p></div>
        <div><h4>Thông tin dự án</h4><p>Đồ án Công nghệ phần mềm nâng cao<br>Python · Streamlit · SQLite</p></div>
        <div class="footer-bottom">© 2026 EmotionAI · Sản phẩm phục vụ học tập và nghiên cứu</div></div>''',unsafe_allow_html=True)
    st.stop()

# Chỉ truy cập thông tin người dùng sau khi đã xác thực.
user = st.session_state["auth_user"]
if st.session_state.get("pending_menu"):
    st.session_state["current_menu"] = st.session_state.pop("pending_menu")
    st.session_state["public_view"] = "home"


st.sidebar.success(f"Xin chào, {user['full_name']}")
st.sidebar.caption(f"Vai trò: {user['role'].upper()}")
st.sidebar.button(
    "🚪 Đăng xuất",
    on_click=logout_user,
    use_container_width=True
)


# ==========================================
# 2. MENU VÀ ĐIỀU HƯỚNG
# ==========================================

MENU_OPTIONS = [
    "🏠 Trang chủ",
    "😊 Nhận diện khuôn mặt",
    "🎤 Phân tích giọng nói",
    "❤️ Phân tích nhịp tim",
    "📊 Thống kê kết quả",
    "🧠 Phân tích cảm xúc tổng hợp",
    "👥 Hồ sơ bệnh nhân",
    "📈 AI Dashboard bác sĩ",
    "👤 Hồ sơ cá nhân"
]

if user["role"] == "admin":
    MENU_OPTIONS.append("🛡️ Quản trị hệ thống")

if "current_menu" not in st.session_state:
    st.session_state["current_menu"] = MENU_OPTIONS[0]


def change_page(page):
    """Chuyển trang trước khi Streamlit tạo lại widget."""
    if page in MENU_OPTIONS:
        st.session_state["current_menu"] = page


st.sidebar.markdown("## 🧠 EmotionAI")
st.sidebar.caption("AI Emotion Analysis Platform")
if st.session_state.get("current_menu") not in MENU_OPTIONS:
    st.session_state["current_menu"] = MENU_OPTIONS[0]

menu = st.sidebar.radio(
    "CHỨC NĂNG",
    MENU_OPTIONS,
    key="current_menu"
)

st.sidebar.divider()
st.sidebar.caption("Đồ án Công nghệ phần mềm nâng cao")


# ==========================================
# 3. TIÊU ĐỀ WEBSITE
# ==========================================

# Thanh thương hiệu phong cách website hiện đại
st.markdown("""<div class="emotion-topbar"><span>✦ EMOTIONAI</span><span>AI hỗ trợ phân tích cảm xúc đa phương thức</span></div>""", unsafe_allow_html=True)
if menu != "🏠 Trang chủ":
    st.markdown(f"<div class='emotion-page-heading'><span>EMOTIONAI · AI WORKSPACE</span><h1>{menu}</h1><p>Nền tảng phân tích cảm xúc và theo dõi kết quả theo từng phiên</p></div>", unsafe_allow_html=True)



# ==========================================
# 4. TRANG CHỦ
# ==========================================

if menu == "🏠 Trang chủ":

    # --------------------------------------
    # BANNER GIỚI THIỆU
    # --------------------------------------

    # HTML viết thành một chuỗi liên tục
    # để tránh lỗi hiển thị thẻ h2, p.
    hero_html = (
        '<div class="emotion-hero">'
        '<div class="emotion-hero-inner">'
        '<span class="emotion-tag">✦ EMOTIONAI · AI EMOTION PLATFORM</span>'
        '<h2>Hiểu cảm xúc.<br><em>Đồng hành tốt hơn.</em></h2>'
        '<p>Phân tích biểu cảm khuôn mặt, tín hiệu giọng nói và nhịp tim bằng AI. '
        'Hỗ trợ chuyên gia tổng hợp kết quả và theo dõi các phiên đánh giá.</p>'
        '<div class="emotion-hero-chips"><span>✧ Phân tích đa phương thức</span>'
        '<span>✧ Dashboard trực quan</span><span>✧ Báo cáo theo bệnh nhân</span></div>'
        '</div></div>'
    )
    st.markdown(hero_html, unsafe_allow_html=True)
    action1, action2, action3 = st.columns([1.15, 1.15, 2.7])
    with action1:
        st.button("✨ Bắt đầu phân tích", type="primary", use_container_width=True,
                  key="hero_start", on_click=change_page,
                  args=("🧠 Phân tích cảm xúc tổng hợp",))
    with action2:
        st.button("📈 Xem AI Dashboard", use_container_width=True,
                  key="hero_dashboard", on_click=change_page,
                  args=("📈 AI Dashboard bác sĩ",))
    st.write("")

    st.subheader("🚀 Khám phá các chức năng")

    st.write(
        "Lựa chọn công cụ bạn muốn sử dụng để bắt đầu."
    )

    col1, col2, col3 = st.columns(
        3,
        gap="large"
    )

    # --------------------------------------
    # THẺ KHUÔN MẶT
    # --------------------------------------

    with col1:

        face_html = (
            '<div class="emotion-card">'
            '<div class="card-icon">📸</div>'
            '<h3>Nhận diện khuôn mặt</h3>'
            '<p>'
            'Tải ảnh hoặc chụp bằng webcam. '
            'AI phân tích biểu cảm khuôn mặt '
            'và hiển thị biểu đồ kết quả.'
            '</p>'
            '</div>'
        )

        st.markdown(
            face_html,
            unsafe_allow_html=True
        )

        st.button(
            "✨ Bắt đầu nhận diện",
            use_container_width=True,
            key="home_face",
            on_click=change_page,
            args=("😊 Nhận diện khuôn mặt",)
        )

    # --------------------------------------
    # THẺ GIỌNG NÓI
    # --------------------------------------

    with col2:

        voice_html = (
            '<div class="emotion-card">'
            '<div class="card-icon">🎙️</div>'
            '<h3>Phân tích giọng nói</h3>'
            '<p>'
            'Thu âm bằng micro hoặc tải file '
            'WAV, MP3 để mô hình AI dự đoán '
            'tín hiệu cảm xúc trong giọng nói.'
            '</p>'
            '</div>'
        )

        st.markdown(
            voice_html,
            unsafe_allow_html=True
        )

        st.button(
            "🎤 Phân tích giọng nói",
            use_container_width=True,
            key="home_voice",
            on_click=change_page,
            args=("🎤 Phân tích giọng nói",)
        )

    # --------------------------------------
    # THẺ NHỊP TIM
    # --------------------------------------

    with col3:

        heart_html = (
            '<div class="emotion-card">'
            '<div class="card-icon">💗</div>'
            '<h3>Phân tích nhịp tim</h3>'
            '<p>'
            'Nhập chỉ số BPM hoặc tạo dữ liệu '
            'mô phỏng để xem biểu đồ và '
            'khoảng tham khảo nhịp tim.'
            '</p>'
            '</div>'
        )

        st.markdown(
            heart_html,
            unsafe_allow_html=True
        )

        st.button(
            "💓 Phân tích BPM",
            use_container_width=True,
            key="home_heart",
            on_click=change_page,
            args=("❤️ Phân tích nhịp tim",)
        )

    st.divider()

    # --------------------------------------
    # CÔNG NGHỆ SỬ DỤNG
    # --------------------------------------

    st.subheader("🧠 Công nghệ sử dụng")

    tech1, tech2, tech3, tech4 = st.columns(4)

    with tech1:
        st.metric("Ngôn ngữ", "Python")

    with tech2:
        st.metric("Giao diện", "Streamlit")

    with tech3:
        st.metric("AI khuôn mặt", "DeepFace")

    with tech4:
        st.metric("Cơ sở dữ liệu", "SQLite")

    st.divider()

    # --------------------------------------
    # THỐNG KÊ VÀ LỊCH SỬ
    # --------------------------------------

    st.subheader("📊 Thống kê và lịch sử")

    st.write(
        "Theo dõi kết quả phân tích, xem biểu đồ "
        "thống kê và xuất dữ liệu CSV."
    )

    st.button(
        "📈 Xem thống kê kết quả",
        use_container_width=True,
        key="home_statistics",
        on_click=change_page,
        args=("📊 Thống kê kết quả",)
    )

    st.info(
        "Kết quả AI chỉ mang tính tham khảo, "
        "không thay thế đánh giá tâm lý "
        "hoặc chẩn đoán y tế."
    )


# ==========================================
# 5. NHẬN DIỆN KHUÔN MẶT
# ==========================================

elif menu == "😊 Nhận diện khuôn mặt":

    st.header("😊 Nhận diện biểu cảm khuôn mặt")

    st.write(
        "Hệ thống sử dụng trí tuệ nhân tạo "
        "để phân tích biểu cảm khuôn mặt từ hình ảnh."
    )

    mode = st.radio(
        "Chọn phương thức nhận diện",
        [
            "Tải ảnh lên",
            "Chụp ảnh webcam"
        ],
        horizontal=True
    )

    image_file = None

    if mode == "Tải ảnh lên":

        image_file = st.file_uploader(
            "Chọn ảnh khuôn mặt",
            type=["jpg", "jpeg", "png"]
        )

    else:

        image_file = st.camera_input(
            "Chụp ảnh khuôn mặt"
        )

    if image_file is not None:

        image_bytes = image_file.getvalue()

        st.subheader("📷 Hình ảnh đầu vào")

        st.image(
            image_bytes,
            caption="Ảnh cần phân tích",
            width=400
        )

        if st.button(
            "🔍 Phân tích cảm xúc",
            type="primary"
        ):

            with st.spinner(
                "AI đang phân tích khuôn mặt..."
            ):

                try:

                    faces = analyze_face(image_bytes)

                    if faces is None:
                        raise ValueError(
                            "Hàm analyze_face không trả về "
                            "kết quả. Kiểm tra face_emotion.py."
                        )

                    if len(faces) == 0:

                        st.warning(
                            "Không phát hiện khuôn mặt trong ảnh."
                        )

                    else:

                        st.success(
                            f"Đã phát hiện {len(faces)} khuôn mặt!"
                        )

                        result_image = draw_face_results(
                            image_bytes,
                            faces
                        )

                        st.subheader(
                            "📸 Kết quả nhận diện khuôn mặt"
                        )

                        st.image(
                            result_image,
                            caption="Ảnh sau khi nhận diện",
                            width=500
                        )

                        st.divider()

                        for index, face in enumerate(faces, 1):

                            # Lưu lịch sử riêng cho tài khoản đang đăng nhập
                            save_analysis(
                                analysis_type="Khuôn mặt",
                                result=face["emotion"],
                                confidence=face["confidence"],
                                user_id=user["id"]
                            )

                            st.subheader(
                                f"😊 Khuôn mặt {index}"
                            )

                            col1, col2 = st.columns(2)

                            with col1:

                                st.metric(
                                    "Biểu cảm nổi bật",
                                    face["emotion"]
                                )

                            with col2:

                                st.metric(
                                    "Điểm dự đoán",
                                    f'{face["confidence"]:.2f}%'
                                )

                            st.subheader(
                                "📊 Biểu đồ phân tích biểu cảm"
                            )

                            df = pd.DataFrame(
                                list(face["scores"].items()),
                                columns=[
                                    "Biểu cảm",
                                    "Điểm (%)"
                                ]
                            )

                            df = df.sort_values(
                                by="Điểm (%)",
                                ascending=False
                            )

                            st.bar_chart(
                                df.set_index("Biểu cảm")
                            )

                            with st.expander(
                                "Xem kết quả chi tiết"
                            ):

                                st.dataframe(
                                    df,
                                    use_container_width=True,
                                    hide_index=True
                                )

                        st.info(
                            "AI chỉ dự đoán biểu cảm khuôn mặt, "
                            "không xác định chắc chắn cảm xúc "
                            "thực tế của người trong ảnh."
                        )

                except ValueError as e:

                    st.warning(
                        f"Không thể phân tích ảnh: {e}"
                    )

                except Exception as e:

                    st.error(
                        "Đã xảy ra lỗi khi phân tích khuôn mặt."
                    )

                    st.exception(e)


# ==========================================
# 6. PHÂN TÍCH GIỌNG NÓI
# ==========================================

elif menu == "🎤 Phân tích giọng nói":

    st.header("🎤 Phân tích cảm xúc qua giọng nói")

    st.write(
        "Hệ thống sử dụng mô hình AI để phân tích "
        "đặc trưng âm thanh và dự đoán cảm xúc "
        "được thể hiện qua giọng nói."
    )

    mode_voice = st.radio(
        "Chọn phương thức",
        [
            "Tải file âm thanh",
            "Thu âm bằng micro"
        ],
        horizontal=True
    )

    audio_file = None

    if mode_voice == "Tải file âm thanh":

        audio_file = st.file_uploader(
            "Chọn file WAV hoặc MP3",
            type=["wav", "mp3"],
            key="voice_upload"
        )

    else:

        audio_file = st.audio_input(
            "Nhấn để thu âm giọng nói",
            key="voice_record"
        )

    if audio_file is not None:

        audio_bytes = audio_file.getvalue()

        st.subheader("🔊 Nghe lại âm thanh")

        st.audio(audio_bytes)

        if st.button(
            "🎯 Phân tích cảm xúc giọng nói",
            type="primary"
        ):

            with st.spinner(
                "AI đang xử lý âm thanh..."
            ):

                try:

                    result = analyze_voice(audio_bytes)

                    # Lưu lịch sử SQLite
                    save_analysis(
                        user_id=user["id"],
                        analysis_type="Giọng nói",
                        result=result["emotion"],
                        confidence=result["confidence"]
                    )

                    st.success(
                        "Phân tích giọng nói thành công!"
                    )

                    col1, col2, col3 = st.columns(3)

                    with col1:

                        st.metric(
                            "Cảm xúc dự đoán",
                            result["emotion"]
                        )

                    with col2:

                        st.metric(
                            "Điểm dự đoán",
                            f'{result["confidence"]:.2f}%'
                        )

                    with col3:

                        st.metric(
                            "Thời lượng",
                            f'{result["duration"]:.2f} giây'
                        )

                    st.subheader(
                        "📊 Biểu đồ cảm xúc giọng nói"
                    )

                    df_voice = pd.DataFrame(
                        list(result["scores"].items()),
                        columns=[
                            "Cảm xúc",
                            "Điểm (%)"
                        ]
                    )

                    df_voice = df_voice.sort_values(
                        by="Điểm (%)",
                        ascending=False
                    )

                    st.bar_chart(
                        df_voice.set_index("Cảm xúc")
                    )

                    with st.expander(
                        "Xem kết quả chi tiết"
                    ):

                        st.dataframe(
                            df_voice,
                            use_container_width=True,
                            hide_index=True
                        )

                    st.info(
                        "Đây là dự đoán của mô hình AI. "
                        "Mô hình chủ yếu được huấn luyện "
                        "trên dữ liệu tiếng Anh, nên kết quả "
                        "với tiếng Việt cần được kiểm chứng."
                    )

                except ValueError as e:

                    st.warning(str(e))

                except Exception as e:

                    st.error(
                        "Không thể phân tích âm thanh."
                    )

                    st.exception(e)


# ==========================================
# 7. PHÂN TÍCH NHỊP TIM
# ==========================================

elif menu == "❤️ Phân tích nhịp tim":

    st.header("❤️ Phân tích nhịp tim BPM")

    st.write(
        "Hệ thống hỗ trợ nhập nhịp tim thủ công "
        "hoặc mô phỏng dữ liệu để kiểm thử."
    )

    mode_heart = st.radio(
        "Chọn phương thức",
        [
            "Nhập nhịp tim thủ công",
            "Mô phỏng nhịp tim"
        ],
        horizontal=True
    )

    # --------------------------------------
    # NHẬP BPM THỦ CÔNG
    # --------------------------------------

    if mode_heart == "Nhập nhịp tim thủ công":

        bpm = st.number_input(
            "Nhập nhịp tim (BPM)",
            min_value=30,
            max_value=220,
            value=75,
            step=1
        )

        if st.button(
            "❤️ Phân tích nhịp tim",
            type="primary"
        ):

            try:

                result = analyze_heart_rate(bpm)

                # Lưu lịch sử SQLite
                save_analysis(
                    user_id=user["id"],
                    analysis_type="Nhịp tim",
                    result=result["status"],
                    bpm=result["bpm"]
                )

                st.metric(
                    "Nhịp tim",
                    f'{result["bpm"]} BPM'
                )

                st.info(result["status"])

                st.caption(result["note"])

            except ValueError as e:

                st.warning(str(e))

            except Exception as e:

                st.error(
                    "Không thể phân tích nhịp tim."
                )

                st.exception(e)

    # --------------------------------------
    # MÔ PHỎNG BPM
    # --------------------------------------

    else:

        base_bpm = st.slider(
            "Nhịp tim trung bình mô phỏng",
            min_value=40,
            max_value=160,
            value=75
        )

        samples = st.slider(
            "Số mẫu dữ liệu",
            min_value=10,
            max_value=100,
            value=30
        )

        if st.button(
            "▶️ Bắt đầu mô phỏng",
            type="primary"
        ):

            df_heart = simulate_heart_rate(
                base_bpm=base_bpm,
                samples=samples
            )

            st.success(
                "Đã tạo dữ liệu nhịp tim mô phỏng!"
            )

            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "BPM trung bình",
                    f'{df_heart["Nhịp tim (BPM)"].mean():.1f}'
                )

            with col2:

                st.metric(
                    "BPM thấp nhất",
                    int(df_heart["Nhịp tim (BPM)"].min())
                )

            with col3:

                st.metric(
                    "BPM cao nhất",
                    int(df_heart["Nhịp tim (BPM)"].max())
                )

            st.subheader("📈 Biểu đồ nhịp tim")

            st.line_chart(
                df_heart.set_index("Thời điểm (giây)")
            )

            with st.expander(
                "Xem dữ liệu mô phỏng"
            ):

                st.dataframe(
                    df_heart,
                    use_container_width=True,
                    hide_index=True
                )

            st.caption(
                "Dữ liệu được tạo ngẫu nhiên để minh họa, "
                "không phải nhịp tim đo từ người thật."
            )


# ==========================================
# 8. THỐNG KÊ VÀ LỊCH SỬ
# ==========================================

elif menu == "📊 Thống kê kết quả":

    st.header("📊 Thống kê và lịch sử phân tích")

    st.write(
        "Theo dõi các kết quả phân tích "
        "đã được lưu trong hệ thống EmotionAI."
    )

    history = get_history(user_id=user["id"])

    if history.empty:

        st.info(
            "Chưa có dữ liệu. Hãy thực hiện "
            "phân tích khuôn mặt, giọng nói "
            "hoặc nhịp tim trước."
        )

    else:

        total = len(history)

        face_count = len(
            history[
                history["Phương thức"] == "Khuôn mặt"
            ]
        )

        voice_count = len(
            history[
                history["Phương thức"] == "Giọng nói"
            ]
        )

        heart_count = len(
            history[
                history["Phương thức"] == "Nhịp tim"
            ]
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Tổng kết quả", total)

        with col2:
            st.metric("Khuôn mặt", face_count)

        with col3:
            st.metric("Giọng nói", voice_count)

        with col4:
            st.metric("Nhịp tim", heart_count)

        st.divider()

        st.subheader(
            "📈 Thống kê theo phương thức"
        )

        statistics = get_statistics(user_id=user["id"])

        if not statistics.empty:

            st.bar_chart(
                statistics.set_index("Phương thức")
            )

        st.divider()

        st.subheader("📋 Lịch sử phân tích")

        filter_type = st.selectbox(
            "Lọc kết quả",
            [
                "Tất cả",
                "Khuôn mặt",
                "Giọng nói",
                "Nhịp tim"
            ]
        )

        if filter_type == "Tất cả":

            filtered_history = history

        else:

            filtered_history = history[
                history["Phương thức"] == filter_type
            ]

        st.dataframe(
            filtered_history,
            use_container_width=True,
            hide_index=True
        )

        # Xuất dữ liệu CSV
        csv_data = filtered_history.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            label="📥 Tải lịch sử phân tích (CSV)",
            data=csv_data,
            file_name="emotionai_history.csv",
            mime="text/csv"
        )


# ==========================================
# 9. QUẢN TRỊ HỆ THỐNG
# ==========================================

elif menu == "👥 Hồ sơ bệnh nhân":
    show_patient_page(user["id"])


elif menu == "🧠 Phân tích cảm xúc tổng hợp":
    show_multimodal_page(user["id"])


elif menu == "📈 AI Dashboard bác sĩ":
    show_doctor_dashboard(user["id"])

elif menu == "🛡️ Quản trị hệ thống":
    if user["role"] != "admin":
        st.error("Bạn không có quyền truy cập.")
        st.stop()
    show_admin_dashboard(user["id"])


elif menu == "👤 Hồ sơ cá nhân":
    show_profile_page(user["id"])


# ==========================================
# 11. CHÂN TRANG WEBSITE
# ==========================================

st.divider()

st.caption(
    "EmotionAI | Đồ án Công nghệ phần mềm nâng cao"
)
