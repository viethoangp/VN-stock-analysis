"""Tham số chung của dự án. Các script khác import từ đây, không viết cứng ở nơi khác."""
import os
from pathlib import Path

from dotenv import load_dotenv

# --- Đường dẫn ---
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
LOG_DIR = ROOT / "logs"

# --- Phạm vi dữ liệu ---
# Giai đoạn thử nghiệm dùng "VN30", khi pipeline ổn thì đổi sang "VN100".
UNIVERSE = "VN30"
START_DATE = "2021-01-01"
END_DATE = "2026-09-30"  # ngày chốt dữ liệu cố định, để kết quả tái lập được
INDEX_CODES = ["VNINDEX", "VN30"]

# --- Crawl ---
SLEEP_SECONDS = 1.0      # nghỉ giữa các lần gọi API
MAX_RETRIES = 3

# --- Phân tích ---
TRADING_DAYS_PER_YEAR = 252
RISK_FREE_RATE = 0.03    # TODO: ghi rõ nguồn (VD: lợi suất TPCP 10 năm) trong docs/data_notes.md
FINANCIALS_LAG_MONTH_DAY = "04-01"  # BCTC năm N coi như công bố từ 01/04/N+1 (tránh look-ahead bias)

# --- Cơ sở dữ liệu ---
load_dotenv(ROOT / ".env")
DB_URL = os.getenv("DB_URL", "")
