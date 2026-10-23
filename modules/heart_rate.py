
import random
import pandas as pd


def classify_heart_rate(bpm):
    """
    Phân loại nhịp tim theo ngưỡng tham khảo
    cho người trưởng thành lúc nghỉ.
    Không dùng để chẩn đoán y tế.
    """
    if bpm < 60:
        return "Dưới khoảng tham khảo lúc nghỉ"
    elif bpm <= 100:
        return "Trong khoảng tham khảo lúc nghỉ"
    else:
        return "Trên khoảng tham khảo lúc nghỉ"


def analyze_heart_rate(bpm):
    bpm = int(bpm)

    if bpm < 30 or bpm > 220:
        raise ValueError("BPM phải nằm trong khoảng 30–220.")

    return {
        "bpm": bpm,
        "status": classify_heart_rate(bpm),
        "note": (
            "Các ngưỡng chỉ mang tính tham khảo "
            "cho người trưởng thành lúc nghỉ. "
            "Vận động, tuổi tác, thuốc và sức khỏe "
            "có thể ảnh hưởng đến nhịp tim."
        )
    }


def simulate_heart_rate(
    base_bpm=75,
    samples=30
):
    """
    Tạo dữ liệu mô phỏng để thử nghiệm giao diện.
    Không phải dữ liệu từ cảm biến thực tế.
    """
    values = []
    current = int(base_bpm)

    for i in range(samples):
        current += random.randint(-3, 3)
        current = max(30, min(220, current))

        values.append({
            "Thời điểm (giây)": i + 1,
            "Nhịp tim (BPM)": current
        })

    return pd.DataFrame(values)
