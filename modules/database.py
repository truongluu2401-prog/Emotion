
import sqlite3
from pathlib import Path
from datetime import datetime

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "emotionai.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database():
    """Tạo bảng và bổ sung user_id nếu database đang dùng cấu trúc cũ."""

    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_type TEXT NOT NULL,
                result TEXT NOT NULL,
                confidence REAL,
                bpm INTEGER,
                created_at TEXT NOT NULL,
                user_id INTEGER
            )
        """)

        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(analysis_history)"
            )
        }

        if "user_id" not in columns:
            conn.execute("""
                ALTER TABLE analysis_history
                ADD COLUMN user_id INTEGER
            """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_analysis_user_id
            ON analysis_history(user_id, id)
        """)


def _check_user(conn, user_id):
    """Kiểm tra tài khoản có tồn tại và đang hoạt động."""

    if isinstance(user_id, bool) or not isinstance(user_id, int):
        raise ValueError("Thiếu ID tài khoản hợp lệ.")

    row = conn.execute("""
        SELECT id
        FROM users
        WHERE id = ? AND is_active = 1
    """, (user_id,)).fetchone()

    if row is None:
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
    """Lưu kết quả phân tích theo tài khoản đang đăng nhập."""

    init_database()

    with get_connection() as conn:
        _check_user(conn, user_id)

        conn.execute("""
            INSERT INTO analysis_history (
                analysis_type,
                result,
                confidence,
                bpm,
                created_at,
                user_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            analysis_type,
            result,
            confidence,
            bpm,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user_id
        ))


def get_history(*, user_id):
    """Chỉ lấy lịch sử phân tích của tài khoản hiện tại."""

    init_database()

    with get_connection() as conn:
        _check_user(conn, user_id)

        df = pd.read_sql_query("""
            SELECT
                id AS ID,
                created_at AS "Thời gian",
                analysis_type AS "Phương thức",
                result AS "Kết quả",
                confidence AS "Điểm AI (%)",
                bpm AS BPM
            FROM analysis_history
            WHERE user_id = ?
            ORDER BY id DESC
        """, conn, params=(user_id,))

    return df


def get_statistics(*, user_id):
    """Thống kê số lần phân tích của riêng tài khoản hiện tại."""

    init_database()

    with get_connection() as conn:
        _check_user(conn, user_id)

        df = pd.read_sql_query("""
            SELECT
                analysis_type AS "Phương thức",
                COUNT(*) AS "Số lần"
            FROM analysis_history
            WHERE user_id = ?
            GROUP BY analysis_type
        """, conn, params=(user_id,))

    return df
