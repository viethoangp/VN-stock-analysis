"""Gọi API công khai của Vietcap (VCI). Không có tài liệu chính thức, nên có thể thay đổi."""
import logging
import time

import requests

from config import MAX_RETRIES, SLEEP_SECONDS

BASE = "https://trading.vietcap.com.vn/api"
IQ = "https://iq.vietcap.com.vn/api/iq-insight-service/v1/company"  # BCTC
HEADERS = {
    "Referer": "https://trading.vietcap.com.vn/",
    "Origin": "https://trading.vietcap.com.vn",
    "User-Agent": "Mozilla/5.0",
}
log = logging.getLogger(__name__)


def call(method, path, **kwargs):
    """Gọi API, thử lại tối đa MAX_RETRIES lần, nghỉ SLEEP_SECONDS giữa các lần gọi."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            url = path if path.startswith("http") else BASE + path
            r = requests.request(method, url, headers=HEADERS, timeout=30, **kwargs)
            r.raise_for_status()
            time.sleep(SLEEP_SECONDS)
            return r.json()
        except (requests.RequestException, ValueError) as e:
            log.warning("Lỗi %s %s (lần %d/%d): %s", method, path, attempt, MAX_RETRIES, e)
            time.sleep(SLEEP_SECONDS * 2 ** attempt)
    raise RuntimeError(f"Gọi {path} thất bại sau {MAX_RETRIES} lần")


def group_symbols(group):
    """Danh sách mã trong rổ hiện tại (VN30, VN100...)."""
    return [x["symbol"] for x in call("GET", "/price/symbols/getByGroup", params={"group": group})]


def all_symbols():
    """Thông tin mọi mã niêm yết: tên, sàn, mã ngành ICB cấp 2."""
    return call("GET", "/price/symbols/getAll")


def daily_ohlcv(symbol, to_ts, count_back):
    """OHLCV theo ngày (giá điều chỉnh, đơn vị đồng), count_back phiên tính lùi từ to_ts."""
    body = {"timeFrame": "ONE_DAY", "symbols": [symbol], "to": to_ts, "countBack": count_back}
    data = call("POST", "/chart/OHLCChart/gap-chart", json=body)
    return data[0] if data else None


def company(symbol, path):
    """API BCTC (iq.vietcap). path VD: "/financial-statement?section=BALANCE_SHEET", "/statistics-financial"."""
    r = call("GET", f"{IQ}/{symbol}{path}")
    if not r.get("successful"):
        raise RuntimeError(f"{symbol}{path}: {r.get('msg')}")
    return r["data"]
