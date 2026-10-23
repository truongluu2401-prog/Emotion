
# EmotionAI

## Giới thiệu

EmotionAI là hệ thống phân tích biểu cảm và dữ liệu
đa phương thức được xây dựng cho đồ án môn
Công nghệ phần mềm nâng cao.

## Chức năng

1. Nhận diện biểu cảm khuôn mặt qua ảnh.
2. Nhận diện biểu cảm khuôn mặt qua webcam.
3. Phân tích cảm xúc giọng nói qua file WAV/MP3.
4. Phân tích giọng nói thu trực tiếp từ micro.
5. Phân tích nhịp tim BPM nhập thủ công.
6. Mô phỏng dữ liệu nhịp tim.
7. Lưu lịch sử phân tích bằng SQLite.
8. Thống kê kết quả và xuất dữ liệu CSV.

## Công nghệ sử dụng

- Python 3.11
- Streamlit
- DeepFace
- OpenCV
- Librosa
- Transformers
- PyTorch
- SQLite
- Pandas

## Hướng dẫn cài đặt

### 1. Tạo môi trường ảo

python -m venv .venv

### 2. Kích hoạt môi trường (Windows CMD)

.venv\Scripts\activate.bat

### 3. Cài thư viện

python -m pip install -r requirements.txt

### 4. Chạy ứng dụng

python -m streamlit run app.py

### 5. Truy cập

http://localhost:8501

## Lưu ý

- Cần có kết nối Internet khi tải mô hình AI lần đầu.
- Kết quả AI chỉ mang tính dự đoán.
- Dữ liệu BPM mô phỏng không phải dữ liệu đo thực tế.
- Nhịp tim không được sử dụng để kết luận cảm xúc.
