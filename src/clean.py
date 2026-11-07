"""Làm sạch dữ liệu thô -> data/processed/*.parquet (5 bảng của star schema).

Chạy: python src/clean.py   (không cần DB; nạp DB bằng load_to_db.py)
"""
import json

import pandas as pd

from config import (END_DATE, FIN_END_YEAR, FIN_START_YEAR, FINANCIALS_LAG_MONTH_DAY, INDEX_CODES,
                    PROCESSED_DIR, RAW_DIR, START_DATE)
from metrics import market_regimes

# Doanh thu theo mẫu BCTC: ngân hàng = tổng thu nhập hoạt động, bảo hiểm = doanh thu phí bảo hiểm.
REVENUE = {"thuong": "isa3", "chung_khoan": "isa3", "ngan_hang": "isb38", "bao_hiem": "isi103"}
# Cột BCTC -> trường API (đơn vị đồng), dùng chung mọi mẫu.
FIELDS = {
    "profit_before_tax": "isa16", "net_income": "isa20", "net_income_parent": "isa22",
    "total_assets": "bsa53", "total_liabilities": "bsa54", "total_equity": "bsa78",
}
RATIOS = {"roe": "roe", "roa": "roa", "pe": "pe", "pb": "pb", "gross_margin": "grossMargin",
          "net_margin": "afterTaxProfitMargin", "debt_to_equity": "debtToEquity"}


def prices():
    df = pd.concat(pd.read_csv(f) for f in sorted((RAW_DIR / "prices").glob("*.csv")))
    df["date"] = pd.to_datetime(df.date).dt.date
    df["crawled_at"] = pd.to_datetime(df.crawled_at)
    df["volume"] = df.volume.astype("int64")
    # Giá trị giao dịch của API thiếu 28% phiên và lệch đơn vị trước 2025 (gấp ~20–90 lần, có phiên = 0)
    # -> tính lại toàn bộ để thống nhất. Dùng giá điều chỉnh nên giá trị quá khứ thấp hơn thực tế vài %.
    # Chỉ số: close là điểm nên không nhân được; số của API tính bằng đồng đến hết 2025, triệu đồng từ 2026.
    is_index = df.ticker.isin(INDEX_CODES)
    api = df.value_mil_vnd
    df["value_mil_vnd"] = (df.close * df.volume / 1e6).where(~is_index, api.where(api < 1e9, api / 1e6))
    v = df.loc[is_index, "value_mil_vnd"]
    assert v.between(1e6, 1e8).all(), f"Giá trị giao dịch chỉ số ngoài 1.000–100.000 tỷ: {v.min()}–{v.max()}"
    bad = (df.close < df.low) | (df.close > df.high)
    print(f"Kẹp {bad.sum()} dòng close nằm ngoài [low, high]")
    df["close"] = df.close.clip(df.low, df.high)
    index = df[is_index].rename(columns={"ticker": "index_code"})
    return df[~is_index].reset_index(drop=True), index.reset_index(drop=True)


def bn(v):
    """Đồng -> tỷ đồng."""
    return None if v is None else v / 1e9


def template(metrics):
    """Mẫu BCTC theo tiền tố trường báo cáo KQKD: isb ngân hàng, iss chứng khoán, isi bảo hiểm."""
    kinds = {m["field"][2] for m in metrics["INCOME_STATEMENT"] if m["field"] and m["field"].startswith("is")}
    for k, name in [("i", "bao_hiem"), ("s", "chung_khoan"), ("b", "ngan_hang")]:
        if k in kinds:
            return name
    return "thuong"


def financials():
    rows, templates = [], {}
    for f in sorted((RAW_DIR / "financials").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        t = f.stem
        templates[t] = tpl = template(d["metrics"])
        bs = {y["yearReport"]: y for y in d["BALANCE_SHEET"]["years"]}
        ratios = {r["yearReport"]: r for r in d["ratios"] if r["ratioType"] == "RATIO_YEAR"}
        for inc in d["INCOME_STATEMENT"]["years"]:
            y = inc["yearReport"]
            if not FIN_START_YEAR <= y <= FIN_END_YEAR:
                continue
            src = {**bs.get(y, {}), **inc}
            row = {"ticker": t, "fiscal_year": y,
                   "available_date": pd.Timestamp(inc["publicDate"] or f"{y + 1}-{FINANCIALS_LAG_MONTH_DAY}").date(),
                   "revenue": bn(src.get(REVENUE[tpl]))}
            row |= {col: bn(src.get(field)) for col, field in FIELDS.items()}
            row["eps"] = src.get("isa23")  # đồng/cổ phiếu, không đổi sang tỷ
            r = ratios.get(y, {})
            row |= {col: r.get(field) for col, field in RATIOS.items()}
            if tpl in ("ngan_hang", "bao_hiem"):  # API trả 0 / số không có ý nghĩa với hai mẫu này
                row["gross_margin"] = row["debt_to_equity"] = None
            rows.append(row)
    return pd.DataFrame(rows), templates


def dim_stock(templates, price):
    df = pd.read_csv(RAW_DIR / "stock_list.csv", dtype={"icb_code_l2": str})
    df["fs_template"] = df.ticker.map(templates)
    df["first_trade_date"] = df.ticker.map(price.groupby("ticker").date.min())
    return df


def dim_date(index_price):
    d = pd.date_range(START_DATE, END_DATE)
    iso = d.isocalendar()
    vnindex = index_price[index_price.index_code == "VNINDEX"].set_index("date").close
    # Ngày nghỉ lấy nhãn của phiên gần nhất trước đó (ngày đầu năm chưa có phiên thì lấy phiên sau).
    regime = market_regimes(vnindex)[1].reindex(d.date).ffill().bfill()
    return pd.DataFrame({
        "date": d.date, "year": d.year, "quarter": d.quarter, "month": d.month,
        "week": iso.week.to_numpy(), "day_of_week": iso.day.to_numpy(),  # 1 = thứ Hai
        "is_trading_day": d.isin(pd.to_datetime(vnindex.index)), "market_regime": regime.to_numpy(),
    })


def main():
    price, index_price = prices()
    fin, templates = financials()
    tables = {
        "dim_stock": dim_stock(templates, price),
        "dim_date": dim_date(index_price),
        "fact_price": price,
        "fact_index_price": index_price,
        "fact_financials": fin,
    }
    check(tables)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_parquet(PROCESSED_DIR / f"{name}.parquet", index=False)
        print(f"{name}: {len(df):,} dòng")


def check(t):
    keys = {"dim_stock": ["ticker"], "dim_date": ["date"], "fact_price": ["ticker", "date"],
            "fact_index_price": ["index_code", "date"], "fact_financials": ["ticker", "fiscal_year"]}
    for name, k in keys.items():
        assert not t[name].duplicated(k).any(), f"{name}: trùng khóa {k}"
    stocks, dates = set(t["dim_stock"].ticker), set(t["dim_date"].date)
    for name in ("fact_price", "fact_financials"):
        assert set(t[name].ticker) <= stocks, f"{name}: có mã không thuộc dim_stock"
    for name in ("fact_price", "fact_index_price"):
        assert set(t[name].date) <= dates, f"{name}: có ngày ngoài dim_date"
    assert t["dim_stock"].fs_template.notna().all(), "Có mã thiếu BCTC"
    assert t["dim_date"].market_regime.notna().all(), "Có ngày chưa gán market_regime"
    assert (t["fact_financials"].revenue > 0).all(), "Có dòng doanh thu <= 0, kiểm tra ánh xạ REVENUE"
    fin = t["fact_financials"].set_index(["ticker", "fiscal_year"])
    assert abs(fin.loc[("FPT", 2024), "net_income"] - 9427) < 1, "FPT FY2024 lợi nhuận sau thuế lệch"
    assert abs(fin.loc[("VCB", 2024), "profit_before_tax"] - 42236) < 1, "VCB FY2024 lợi nhuận trước thuế lệch"


if __name__ == "__main__":
    main()
