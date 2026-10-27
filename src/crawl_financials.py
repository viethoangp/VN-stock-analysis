"""Lấy BCTC (năm + quý) và chỉ số tài chính cho các mã trong stock_list.csv.

Mỗi mã lưu nguyên JSON thô của API vào data/raw/financials/<MÃ>.json; mã đã có file thì bỏ qua.
Làm phẳng, lọc năm FY2020-2025 và tách ngân hàng/doanh nghiệp thường để sang clean.py.
Chạy: python src/crawl_financials.py
"""
import json
import logging

import pandas as pd

import vci
from config import FIN_END_YEAR, FIN_START_YEAR, LOG_DIR, RAW_DIR

OUT_DIR = RAW_DIR / "financials"
SECTIONS = ["INCOME_STATEMENT", "BALANCE_SHEET", "CASH_FLOW"]
log = logging.getLogger("crawl_financials")


def fetch(symbol):
    out = {s: vci.company(symbol, f"/financial-statement?section={s}") for s in SECTIONS}
    out["metrics"] = vci.company(symbol, "/financial-statement/metrics")  # tên khoản mục theo mẫu của mã
    out["ratios"] = vci.company(symbol, "/statistics-financial")
    return out


def missing_years(data):
    """Năm FY trong phạm vi mà báo cáo kết quả kinh doanh không có."""
    have = {y["yearReport"] for y in data["INCOME_STATEMENT"]["years"]}
    return sorted(set(range(FIN_START_YEAR, FIN_END_YEAR + 1)) - have)


def main():
    LOG_DIR.mkdir(exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(LOG_DIR / "crawl_financials.log", encoding="utf-8"), logging.StreamHandler()],
    )
    failed = []
    for s in pd.read_csv(RAW_DIR / "stock_list.csv").ticker:
        path = OUT_DIR / f"{s}.json"
        if path.exists():
            continue
        try:
            data = fetch(s)
        except Exception as e:  # một mã lỗi không được làm dừng cả lượt crawl
            log.error("%s: %s", s, e)
            failed.append(s)
            continue
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        gap = missing_years(data)
        if gap:
            log.warning("%s: thiếu FY %s", s, gap)
        else:
            log.info("%s: đủ FY%d-%d", s, FIN_START_YEAR, FIN_END_YEAR)
    log.info("Xong. Lỗi: %s", failed or "không có")


if __name__ == "__main__":
    main()
