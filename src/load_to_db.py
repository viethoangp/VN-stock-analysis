"""Tạo bảng (sql/schema.sql) rồi nạp data/processed/*.parquet vào DB, sau đó chạy sql/integrity_checks.sql.

Chạy lại an toàn: mỗi lần chạy đều xóa và tạo lại bảng.
Chạy: python src/clean.py && python src/load_to_db.py
"""
import pandas as pd
import sqlalchemy as sa

from config import DB_URL, PROCESSED_DIR, ROOT

# Thứ tự nạp: bảng dim trước, fact sau (khóa ngoại).
TABLES = ["dim_stock", "dim_date", "fact_price", "fact_index_price", "fact_financials"]


def query(engine, sql):
    """Chạy SQL thô qua cursor psycopg2. exec_driver_sql lỗi khi bản C của SQLAlchemy bị Windows chặn một phần."""
    with engine.begin() as con:
        cur = con.connection.cursor()
        cur.execute(sql)
        if cur.description:
            return pd.DataFrame(cur.fetchall(), columns=[c[0] for c in cur.description])


def main():
    assert DB_URL, "Chưa có DB_URL: copy .env.example thành .env rồi điền mật khẩu"
    engine = sa.create_engine(DB_URL)
    query(engine, (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
    for t in TABLES:
        df = pd.read_parquet(PROCESSED_DIR / f"{t}.parquet")
        df.to_sql(t, engine, if_exists="append", index=False, chunksize=5000, method="multi")
        n = query(engine, f"SELECT COUNT(*) FROM {t}").iat[0, 0]
        assert n == len(df), f"{t}: DB có {n} dòng, file có {len(df)} dòng"
        print(f"{t}: {n:,} dòng")

    # Mỗi truy vấn kiểm tra cách nhau bởi ';', dòng chú thích cuối cùng ngay trước SQL là tên.
    sql = (ROOT / "sql" / "integrity_checks.sql").read_text(encoding="utf-8")
    for q in filter(str.strip, sql.split(";")):
        title = [line for line in q.splitlines() if line.startswith("--")][-1].lstrip("- ")
        print(f"\n## {title}\n{query(engine, q).to_string(index=False)}")


if __name__ == "__main__":
    main()
