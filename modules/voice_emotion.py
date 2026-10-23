
import io
import numpy as np
import librosa
import streamlit as st
from transformers import pipeline

MODEL_NAME = "superb/wav2vec2-base-superb-er"

EMOTION_NAMES = {
    "ang": "Tức giận",
    "hap": "Vui vẻ",
    "neu": "Trung tính",
    "sad": "Buồn bã",
    "angry": "Tức giận",
    "happy": "Vui vẻ",
    "neutral": "Trung tính"
}


@st.cache_resource(show_spinner=False)
def load_voice_model():
    # Tải mô hình một lần và dùng lại
    return pipeline(
        task="audio-classification",
        model=MODEL_NAME,
        device=-1
    )


def analyze_voice(audio_bytes):
    # Đọc dữ liệu âm thanh từ bộ nhớ
    audio, sr = librosa.load(
        io.BytesIO(audio_bytes),
        sr=16000,
        mono=True
    )

    if len(audio) == 0:
        raise ValueError("File âm thanh không có dữ liệu.")

    duration = len(audio) / sr

    if duration < 1:
        raise ValueError(
            "Âm thanh quá ngắn. Hãy thu âm ít nhất 2 giây."
        )

    if duration > 30:
        raise ValueError(
            "Âm thanh quá dài. Hãy dùng bản ghi tối đa 30 giây."
        )

    # Kiểm tra âm thanh quá nhỏ hoặc im lặng
    rms = float(np.sqrt(np.mean(audio ** 2)))

    if rms < 0.001:
        raise ValueError(
            "Âm thanh quá nhỏ hoặc không có giọng nói rõ ràng."
        )

    # Chạy mô hình AI
    classifier = load_voice_model()

    predictions = classifier(
        {"array": audio, "sampling_rate": sr},
        top_k=4
    )

    scores = {}

    for item in predictions:
        label = item["label"].lower()
        name = EMOTION_NAMES.get(label, label)
        scores[name] = float(item["score"]) * 100

    if not scores:
        raise ValueError("AI không trả về kết quả phân tích.")

    dominant = max(scores, key=scores.get)

    return {
        "emotion": dominant,
        "confidence": scores[dominant],
        "scores": scores,
        "duration": round(duration, 2),
        "sample_rate": sr
    }
