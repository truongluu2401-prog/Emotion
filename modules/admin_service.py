
from modules.auth_database import get_connection


def require_admin(admin_id):
    """Kiểm tra quyền Admin trên Supabase."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM users
                WHERE id = %s
                  AND role = 'admin'
                  AND is_active = 1
                """,
                (admin_id,)
            )
            admin = cur.fetchone()

    if admin is None:
        raise PermissionError(
            "Bạn không có quyền quản trị hệ thống."
        )


def get_admin_statistics(admin_id):
    """Thống kê số tài khoản trên Supabase."""
    require_admin(admin_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (
                        WHERE role = 'admin'
                    ) AS admins,
                    COUNT(*) FILTER (
                        WHERE role = 'user'
                    ) AS users,
                    COUNT(*) FILTER (
                        WHERE is_active = 0
                    ) AS locked
                FROM users
                """
            )
            row = cur.fetchone()

    return dict(row)


def get_users_for_admin(admin_id):
    """Lấy danh sách tài khoản cho Admin."""
    require_admin(admin_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
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
            )
            rows = cur.fetchall()

    return [dict(row) for row in rows]


def set_user_active(admin_id, target_id, active):
    """Khóa hoặc mở khóa tài khoản người dùng."""
    require_admin(admin_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, role, is_active
                FROM users
                WHERE id = %s
                FOR UPDATE
                """,
                (target_id,)
            )
            target = cur.fetchone()

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

            cur.execute(
                """
                UPDATE users
                SET is_active = %s
                WHERE id = %s
                  AND role = 'user'
                """,
                (1 if active else 0, target_id)
            )

            if cur.rowcount != 1:
                raise ValueError(
                    "Không thể cập nhật trạng thái tài khoản."
                )


if __name__ == "__main__":
    print("SUPABASE ADMIN SERVICE OK")
