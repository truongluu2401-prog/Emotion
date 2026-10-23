
"""Lịch sử và thống kê phân tích cảm xúc trên Supabase."""

from datetime import datetime, timezone

import pandas as pd

from modules.auth_database import get_connection


def init_database():
    """Kiểm tra bảng lịch sử đã tồn tại trên Supabase."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT to_regclass('public.analysis_history') AS table_name"
            )
            row = cur.fetchone()

            if row["table_name"] is None:
                raise RuntimeError(
                    "Supabase chưa có bảng analysis_history."
                )


def _check_user(conn, user_id):
    """Chỉ cho phép tài khoản đang hoạt động."""
    if isinstance(user_id, bool) or not isinstance(user_id, int):
        raise ValueError("Thiếu ID tài khoản hợp lệ.")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id
            FROM users
            WHERE id = %s AND is_active = 1
            """,
            (user_id,)
        )

        if cur.fetchone() is None:
            raise PermissionError(
                "Tài khoản không tồn tại hoặc đã bị khóa."
            )


def save_analysis(
    analysis_type,
    result,
    confidence=None,
    bpm=None,
    *,
    user_id
):
    """Lưu kết quả phân tích lên Supabase."""
    init_database()

    with get_connection() as conn:
        _check_user(conn, user_id)

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO analysis_history (
                    analysis_type,
                    result,
                    confidence,
                    bpm,
                    created_at,
                    user_id
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    analysis_type,
                    result,
                    confidence,
                    bpm,
                    datetime.now(timezone.utc).isoformat(
                        timespec="seconds"
                    ),
                    user_id
                )
            )


def get_history(*, user_id):
    """Lấy lịch sử phân tích của tài khoản hiện tại."""
    init_database()

    with get_connection() as conn:
        _check_user(conn, user_id)

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id AS "ID",
                    created_at AS "Thời gian",
                    analysis_type AS "Phương thức",
                    result AS "Kết quả",
                   confidence AS "Điểm AI (%%)",
                    bpm AS "BPM"
                FROM analysis_history
                WHERE user_id = %s
                ORDER BY id DESC
                """,
                (user_id,)
            )
            rows = cur.fetchall()

    return pd.DataFrame(
        rows,
        columns=[
            "ID",
            "Thời gian",
            "Phương thức",
            "Kết quả",
            "Điểm AI (%)",
            "BPM"
        ]
    )


def get_statistics(*, user_id):
    """Thống kê số lần phân tích theo phương thức."""
    init_database()

    with get_connection() as conn:
        _check_user(conn, user_id)

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    analysis_type AS "Phương thức",
                    COUNT(*) AS "Số lần"
                FROM analysis_history
                WHERE user_id = %s
                GROUP BY analysis_type
                ORDER BY analysis_type
                """,
                (user_id,)
            )
            rows = cur.fetchall()

    return pd.DataFrame(
        rows,
        columns=["Phương thức", "Số lần"]
    )


if __name__ == "__main__":
    init_database()
    print("SUPABASE ANALYSIS DATABASE OK")
