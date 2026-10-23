
from modules.auth_database import get_connection


def require_admin(admin_id):
    """Kiểm tra quyền Admin trực tiếp trong SQLite."""
    with get_connection() as conn:
        admin = conn.execute(
            """
            SELECT id
            FROM users
            WHERE id = ?
              AND role = 'admin'
              AND is_active = 1
            """,
            (admin_id,)
        ).fetchone()

    if admin is None:
        raise PermissionError(
            "Bạn không có quyền quản trị hệ thống."
        )


def get_admin_statistics(admin_id):
    require_admin(admin_id)

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN role = 'admin'
                    THEN 1 ELSE 0 END) AS admins,
                SUM(CASE WHEN role = 'user'
                    THEN 1 ELSE 0 END) AS users,
                SUM(CASE WHEN is_active = 0
                    THEN 1 ELSE 0 END) AS locked
            FROM users
            """
        ).fetchone()

    return dict(row)


def get_users_for_admin(admin_id):
    require_admin(admin_id)

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                full_name,
                email,
                role,
                is_active,
                created_at
            FROM users
            ORDER BY id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def set_user_active(admin_id, target_id, active):
    require_admin(admin_id)

    with get_connection() as conn:
        target = conn.execute(
            """
            SELECT id, role, is_active
            FROM users
            WHERE id = ?
            """,
            (target_id,)
        ).fetchone()

        if target is None:
            raise ValueError("Không tìm thấy tài khoản.")

        if target["role"] == "admin":
            raise ValueError(
                "Không thể khóa hoặc mở khóa "
                "tài khoản Admin tại đây."
            )

        if target["id"] == admin_id:
            raise ValueError(
                "Không thể tự khóa tài khoản."
            )

        conn.execute(
            """
            UPDATE users
            SET is_active = ?
            WHERE id = ?
              AND role = 'user'
            """,
            (1 if active else 0, target_id)
        )
