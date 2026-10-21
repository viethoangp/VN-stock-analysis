"""Lấy OHLCV theo ngày cho các mã trong stock_list.csv và các chỉ số INDEX_CODES.

Mỗi mã lưu một file data/raw/prices/<MÃ>.csv; mã đã có file thì bỏ qua (chạy lại an toàn).
Muốn lấy lại một mã thì xóa file của mã đó.
Chạy: python src/crawl_prices.py
"""
import logging
from datetime import date, datetime, timedelta, timezone

import pandas as pd

import vci
from config import END_DATE, INDEX_CODES, LOG_DIR, RAW_DIR, START_DATE

OUT_DIR = RAW_DIR / "prices"
log = logging.getLogger("crawl_prices")


def fetch(symbol):
    start, end = date.fromisoformat(START_DATE), date.fromisoformat(END_DATE)
    to_ts = int(datetime.combine(end + timedelta(days=1), datetime.min.time(), timezone.utc).timestamp())
    # Số ngày lịch luôn >= số phiên giao dịch, nên lấy dư rồi lọc theo ngày.
    r = vci.daily_ohlcv(symbol, to_ts, (end - start).days + 1)
    if not r or not r["t"]:
        return None
    assert len({len(r[k]) for k in ("t", "o", "h", "l", "c", "v")}) == 1, f"{symbol}: các mảng lệch độ dài"
    df = pd.DataFrame({
        "ticker": symbol,
        "date": pd.to_datetime(pd.Series(r["t"]).astype(int), unit="s").dt.date,
        "open": r["o"], "high": r["h"], "low": r["l"], "close": r["c"],
        "volume": r["v"],
        "value_mil_vnd": r["accumulatedValue"],  # giá trị giao dịch, triệu đồng
    })
    df = df[(df.date >= start) & (df.date <= end)]
    df["crawled_at"] = datetime.now().isoformat(timespec="seconds")
    return df


def main():
    LOG_DIR.mkdir(exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(LOG_DIR / "crawl_prices.log", encoding="utf-8"), logging.StreamHandler()],
    )
    tickers = pd.read_csv(RAW_DIR / "stock_list.csv").ticker.tolist()
    failed = []
    for s in tickers + INDEX_CODES:
        path = OUT_DIR / f"{s}.csv"
        if path.exists():
            continue
        try:
            df = fetch(s)
        except Exception as e:  # một mã lỗi không được làm dừng cả lượt crawl
            log.error("%s: %s", s, e)
            failed.append(s)
            continue
        if df is None or df.empty:
            log.warning("%s: không có dữ liệu", s)
            failed.append(s)
            continue
        df.to_csv(path, index=False)
        log.info("%s: %d phiên (%s -> %s)", s, len(df), df.date.min(), df.date.max())
    log.info("Xong. Lỗi: %s", failed or "không có")


if __name__ == "__main__":
    main()
