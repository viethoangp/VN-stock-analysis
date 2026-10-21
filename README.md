# Phân tích thị trường chứng khoán Việt Nam (VN100)

> Thu thập giá giao dịch và báo cáo tài chính của các cổ phiếu VN100 giai đoạn 2021-2026, lưu theo star schema trên PostgreSQL, phân tích bằng Python/SQL, phân cụm bằng K-Means và trình bày qua Excel + Power BI.

🚧 **Đang thực hiện.**

<!-- Ảnh dashboard nổi bật nhất sẽ đặt ở đây (dashboard/screenshots/) -->

## Câu hỏi kinh doanh

| # | Câu hỏi |
|---|---|
| Q1 | Ngành nào có lợi suất điều chỉnh theo rủi ro tốt nhất, và thứ hạng thay đổi ra sao qua các giai đoạn thị trường? |
| Q2 | Các chỉ số cơ bản (ROE, P/E, P/B, tăng trưởng lợi nhuận) có liên hệ gì với hiệu suất giá năm sau? |
| Q3 | Những cặp cổ phiếu nào có tương quan thấp, giúp đa dạng hóa danh mục? |
| Q4 | Có thể chia cổ phiếu thành các nhóm đặc trưng nào (tăng trưởng, giá trị, phòng thủ, đầu cơ)? |
| Q5 | Nhóm VN30 khác phần còn lại của VN100 thế nào về rủi ro, thanh khoản và lợi suất? |

## Insight chính

_Sẽ cập nhật sau khi phân tích._

## Dữ liệu

| Mục | Giá trị |
|---|---|
| Nguồn | Thư viện [`vnstock`](https://github.com/thinh-vu/vnstock) |
| Rổ cổ phiếu | VN100 (thử nghiệm trên VN30) |
| Giai đoạn | 01/01/2021 → 30/09/2026 (ngày chốt cố định) |
| Quy mô ước tính | ~120.000 dòng giá, ~500 dòng chỉ số tài chính |

## Phương pháp và công cụ

Python (pandas, scikit-learn) · PostgreSQL · Excel · Power BI · Git

```
vnstock → data/raw → clean (Python) → PostgreSQL (star schema) → SQL / Notebook / Excel / Power BI → Insight
```

## Hạn chế

- Survivorship bias: dùng danh sách VN100 hiện tại.
- Ngày công bố BCTC là giả định (01/04 năm sau).
- Chưa tính phí giao dịch và thuế.
- Tương quan không phải nhân quả.
- Dự án mang tính học tập, không phải khuyến nghị đầu tư.

## Cách chạy lại

```bash
git clone https://github.com/viethoangp/VN-stock-analysis.git
cd VN-stock-analysis
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # rồi điền mật khẩu DB
```

_Các lệnh chạy pipeline sẽ bổ sung khi viết xong script._

## Cấu trúc thư mục

```
├── data/raw, data/processed   # dữ liệu (không đưa lên Git)
├── src/                       # pipeline Python
├── notebooks/                 # phân tích, ML
├── sql/                       # schema + truy vấn phân tích
├── excel/                     # báo cáo Excel
└── dashboard/                 # Power BI + ảnh chụp
```
