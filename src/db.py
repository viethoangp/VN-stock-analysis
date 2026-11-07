"""Kết nối PostgreSQL dùng chung cho script và notebook.

Dùng: from db import query; df = query("SELECT * FROM dim_stock")
"""
from functools import cache

import pandas as pd
import psycopg2.extensions
import sqlalchemy as sa

from config import DB_URL

# NUMERIC trả về float thay vì Decimal, để pandas tính toán được ngay.
psycopg2.extensions.register_type(psycopg2.extensions.new_type(
    psycopg2.extensions.DECIMAL.values, "DEC2FLOAT", lambda v, cur: None if v is None else float(v)))


@cache
def engine():
    assert DB_URL, "Chưa có DB_URL: copy .env.example thành .env rồi điền mật khẩu"
    return sa.create_engine(DB_URL)


def query(sql):
    """Chạy SQL thô qua cursor psycopg2, trả DataFrame nếu là câu SELECT.

    Không dùng exec_driver_sql/pd.read_sql: lỗi khi bản C của SQLAlchemy bị Windows chặn một phần.
    """
    with engine().begin() as con:
        cur = con.connection.cursor()
        cur.execute(sql)
        if cur.description:
            return pd.DataFrame(cur.fetchall(), columns=[c[0] for c in cur.description])
