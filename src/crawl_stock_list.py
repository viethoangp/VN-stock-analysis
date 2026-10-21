"""Lấy danh sách mã trong rổ UNIVERSE kèm sàn, ngành ICB, cờ is_vn30 / is_bank.

Chạy: python src/crawl_stock_list.py  ->  data/raw/stock_list.csv
"""
import pandas as pd

import vci
from config import RAW_DIR, UNIVERSE

# ICB cấp 2 (supersector) -> (ngành cấp 1, ngành cấp 2). API chỉ trả mã, không trả tên.
ICB = {
    "0500": ("Dầu khí", "Dầu khí"),
    "1300": ("Nguyên vật liệu", "Hóa chất"),
    "1700": ("Nguyên vật liệu", "Tài nguyên cơ bản"),
    "2300": ("Công nghiệp", "Xây dựng và vật liệu"),
    "2700": ("Công nghiệp", "Hàng và dịch vụ công nghiệp"),
    "3300": ("Hàng tiêu dùng", "Ô tô và phụ tùng"),
    "3500": ("Hàng tiêu dùng", "Thực phẩm và đồ uống"),
    "3700": ("Hàng tiêu dùng", "Hàng cá nhân và gia dụng"),
    "4500": ("Y tế", "Y tế"),
    "5300": ("Dịch vụ tiêu dùng", "Bán lẻ"),
    "5500": ("Dịch vụ tiêu dùng", "Truyền thông"),
    "5700": ("Dịch vụ tiêu dùng", "Du lịch và giải trí"),
    "6500": ("Viễn thông", "Viễn thông"),
    "7500": ("Tiện ích cộng đồng", "Điện, nước và xăng dầu khí đốt"),
    "8300": ("Tài chính", "Ngân hàng"),
    "8500": ("Tài chính", "Bảo hiểm"),
    "8600": ("Tài chính", "Bất động sản"),
    "8700": ("Tài chính", "Dịch vụ tài chính"),
    "9500": ("Công nghệ", "Công nghệ thông tin"),
}
EXCHANGE = {"HSX": "HOSE", "HNX": "HNX", "UPCOM": "UPCoM"}


def main():
    info = {x["symbol"]: x for x in vci.all_symbols()}
    vn30 = set(vci.group_symbols("VN30"))
    rows = []
    for t in vci.group_symbols(UNIVERSE):
        x = info[t]
        l1, l2 = ICB.get(x["icbCode2"], (None, None))
        rows.append({
            "ticker": t,
            "company_name": x["organName"],
            "exchange": EXCHANGE.get(x["board"], x["board"]),
            "icb_code_l2": x["icbCode2"],
            "industry_l1": l1,
            "industry_l2": l2,
            "is_vn30": t in vn30,
            "is_bank": x["icbCode2"] == "8300",
        })
    df = pd.DataFrame(rows)
    missing = df[df.industry_l1.isna()]
    assert missing.empty, f"Mã ngành chưa có trong bảng ICB: {missing[['ticker', 'icb_code_l2']].to_dict('records')}"
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_DIR / "stock_list.csv", index=False, encoding="utf-8-sig")
    print(f"{len(df)} mã {UNIVERSE} ({df.is_vn30.sum()} mã VN30, {df.is_bank.sum()} ngân hàng) -> stock_list.csv")


if __name__ == "__main__":
    main()
