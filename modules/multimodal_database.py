
"""Lưu phiên AI tổng hợp trên Supabase PostgreSQL."""

import json
from datetime import datetime, timezone

from modules.auth_database import get_connection
from modules.patient_database import (
    init_patient_database,
    check_patient,
)


def _connect():
    return get_connection()


def init_multimodal_database():
    """Tạo bảng phiên phân tích nếu chưa tồn tại."""
    init_patient_database()

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS multimodal_sessions (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL
                        REFERENCES users(id),
                    created_at TEXT NOT NULL,
                    ai_label TEXT NOT NULL,
                    ai_detail TEXT NOT NULL,
                    results_json TEXT NOT NULL,
                    phq9_score INTEGER,
                    phq9_band TEXT,
                    phq9_item9 INTEGER,
                    doctor_name TEXT NOT NULL,
                    assessment TEXT NOT NULL,
                    doctor_notes TEXT NOT NULL,
                    patient_id INTEGER
                        REFERENCES patients(id)
                )
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_multimodal_patient
                ON multimodal_sessions(user_id, patient_id)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_multimodal_sessions_user
                ON multimodal_sessions(user_id, id DESC)
            """)


def _require_user(conn, user_id):
    if type(user_id) is not int:
        raise ValueError("ID tài khoản không hợp lệ.")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id
            FROM users
            WHERE id = %s AND is_active = 1
            """,
            (user_id,)
        )
        row = cur.fetchone()

    if row is None:
        raise PermissionError(
            "Tài khoản không tồn tại hoặc đã bị khóa."
        )


def save_multimodal_session(
    *,
    user_id,
    results,
    ai_label,
    ai_detail,
    doctor_name,
    assessment,
    doctor_notes,
    phq9_score=None,
    phq9_band=None,
    phq9_item9=None,
    patient_id=None
):
    """
    Lưu kết quả phân tích tổng hợp.
    Không lưu ảnh hoặc âm thanh gốc.
    """
    init_multimodal_database()

    if not results or not any(
        k in results for k in ("face", "voice", "heart")
    ):
        raise ValueError(
            "Cần phân tích ít nhất một nguồn dữ liệu."
        )

    if not doctor_name.strip() or not doctor_notes.strip():
        raise ValueError(
            "Vui lòng nhập tên và kết luận của bác sĩ."
        )

    if phq9_score is not None:
        if not 0 <= int(phq9_score) <= 27:
            raise ValueError("Điểm PHQ-9 không hợp lệ.")

    if patient_id is None:
        raise ValueError(
            "Vui lòng chọn hồ sơ bệnh nhân trước khi lưu."
        )

    with _connect() as conn:
        _require_user(conn, user_id)

        check_patient(
            conn,
            user_id=user_id,
            patient_id=patient_id
        )

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO multimodal_sessions (
                    user_id,
                    created_at,
                    ai_label,
                    ai_detail,
                    results_json,
                    phq9_score,
                    phq9_band,
                    phq9_item9,
                    doctor_name,
                    assessment,
                    doctor_notes,
                    patient_id
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                RETURNING id
                """,
                (
                    user_id,
                    datetime.now(timezone.utc).isoformat(),
                    ai_label,
                    ai_detail,
                    json.dumps(results, ensure_ascii=False),
                    phq9_score,
                    phq9_band,
                    phq9_item9,
                    doctor_name.strip(),
                    assessment,
                    doctor_notes.strip(),
                    patient_id
                )
            )

            session_id = cur.fetchone()["id"]

    return session_id


def get_multimodal_sessions(*, user_id, limit=100):
    """Lấy lịch sử phiên AI của tài khoản."""
    init_multimodal_database()

    safe_limit = max(1, min(int(limit), 500))

    with _connect() as conn:
        _require_user(conn, user_id)

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    created_at,
                    ai_label,
                    ai_detail,
                    results_json,
                    phq9_score,
                    phq9_band,
                    phq9_item9,
                    doctor_name,
                    assessment,
                    doctor_notes,
                    patient_id
                FROM multimodal_sessions
                WHERE user_id = %s
                ORDER BY id DESC
                LIMIT %s
                """,
                (user_id, safe_limit)
            )

            return cur.fetchall()


def get_multimodal_session(*, user_id, session_id):
    """Lấy một phiên AI thuộc tài khoản."""
    init_multimodal_database()

    with _connect() as conn:
        _require_user(conn, user_id)

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM multimodal_sessions
                WHERE user_id = %s
                  AND id = %s
                """,
                (user_id, session_id)
            )

            return cur.fetchone()
