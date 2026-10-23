
import streamlit as st
import psycopg
from psycopg.rows import dict_row


def get_supabase_user_by_email(email):
    database_url = st.secrets["database"]["url"]

    with psycopg.connect(
        database_url,
        row_factory=dict_row,
        connect_timeout=15
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, full_name, email,
                       password_hash, role, is_active
                FROM users
                WHERE LOWER(email) = LOWER(%s)
                LIMIT 1
                """,
                (email.strip(),)
            )
            return cur.fetchone()


def get_supabase_user_by_id(user_id):
    database_url = st.secrets["database"]["url"]

    with psycopg.connect(
        database_url,
        row_factory=dict_row,
        connect_timeout=15
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, full_name, email,
                       password_hash, role, is_active
                FROM users
                WHERE id = %s
                """,
                (user_id,)
            )
            return cur.fetchone()
