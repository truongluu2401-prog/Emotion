
import cv2
import numpy as np
from deepface import DeepFace

# Tên biểu cảm tiếng Việt
EMOTION_NAMES = {
    "angry": "Tức giận",
    "disgust": "Ghê tởm",
    "fear": "Sợ hãi",
    "happy": "Vui vẻ",
    "sad": "Buồn bã",
    "surprise": "Ngạc nhiên",
    "neutral": "Trung tính"
}


# ==========================================
# HÀM PHÂN TÍCH BIỂU CẢM KHUÔN MẶT
# ==========================================

def analyze_face(image_bytes):

    # Chuyển ảnh thành mảng NumPy
    array = np.frombuffer(
        image_bytes,
        dtype=np.uint8
    )

    image = cv2.imdecode(
        array,
        cv2.IMREAD_COLOR
    )

    if image is None:
        raise ValueError("Không thể đọc ảnh.")

    # AI phân tích biểu cảm
    results = DeepFace.analyze(
        img_path=image,
        actions=["emotion"],
        detector_backend="opencv",
        enforce_detection=True,
        silent=True
    )

    # Chuẩn hóa kết quả thành danh sách
    if isinstance(results, dict):
        results = [results]

    if not results:
        return []

    faces = []

    for result in results:

        emotion = result["dominant_emotion"]
        scores = result["emotion"]

        faces.append({
            "emotion": EMOTION_NAMES.get(
                emotion, emotion
            ),
            "confidence": float(
                scores[emotion]
            ),
            "scores": {
                EMOTION_NAMES.get(key, key): float(value)
                for key, value in scores.items()
            },
            "region": result.get("region", {})
        })

    # Quan trọng: trả về kết quả
    return faces


# ==========================================
# HÀM VẼ KHUNG KHUÔN MẶT
# ==========================================

def draw_face_results(image_bytes, faces):

    array = np.frombuffer(
        image_bytes,
        dtype=np.uint8
    )

    image = cv2.imdecode(
        array,
        cv2.IMREAD_COLOR
    )

    if image is None:
        raise ValueError("Không thể đọc ảnh.")

    height, width = image.shape[:2]

    for face in faces:

        region = face.get("region", {})

        x = int(region.get("x", 0))
        y = int(region.get("y", 0))
        w = int(region.get("w", 0))
        h = int(region.get("h", 0))

        if w <= 0 or h <= 0:
            continue

        x1 = max(0, min(x, width - 1))
        y1 = max(0, min(y, height - 1))

        x2 = max(0, min(x + w, width - 1))
        y2 = max(0, min(y + h, height - 1))

        if x2 <= x1 or y2 <= y1:
            continue

        # Vẽ khung màu xanh
        cv2.rectangle(
            image,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            3
        )

        # Hiển thị điểm dự đoán
        confidence = face["confidence"]

        label = f"{confidence:.1f}%"

        cv2.putText(
            image,
            label,
            (x1, max(20, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

    # Chuyển BGR sang RGB
    return cv2.cvtColor(
        image,
        cv2.COLOR_BGR2RGB
    )
