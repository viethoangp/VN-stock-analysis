-- Kiểm tra toàn vẹn sau khi nạp. load_to_db.py tự chạy và in kết quả.
-- Khóa trùng và mã/ngày lạ đã bị khóa chính / khóa ngoại chặn khi nạp.

-- 1. Số dòng ngoài phạm vi ngày (kỳ vọng 0)
SELECT
    (SELECT COUNT(*) FROM fact_price WHERE date NOT BETWEEN '2021-01-01' AND '2026-09-30') AS price_out_of_range,
    (SELECT COUNT(*) FROM fact_index_price WHERE date NOT BETWEEN '2021-01-01' AND '2026-09-30') AS index_out_of_range;

-- 2. Số phiên giao dịch trong dim_date khớp VNINDEX (kỳ vọng bằng nhau)
SELECT
    (SELECT COUNT(*) FROM dim_date WHERE is_trading_day) AS trading_days,
    (SELECT COUNT(*) FROM fact_index_price WHERE index_code = 'VNINDEX') AS vnindex_sessions;

-- 3. Giá vô lý (kỳ vọng 0)
SELECT COUNT(*) AS bad_price_rows
FROM fact_price
WHERE low > high OR close NOT BETWEEN low AND high OR close <= 0 OR volume < 0;

-- 4. Mã có dưới 80% số phiên của VN-Index trong năm (2026 chỉ có 9 tháng nên so tương đối)
WITH s AS (
    SELECT ticker, EXTRACT(YEAR FROM date)::INT AS year, COUNT(*) AS sessions
    FROM fact_price GROUP BY 1, 2
), idx AS (
    SELECT EXTRACT(YEAR FROM date)::INT AS year, COUNT(*) AS sessions
    FROM fact_index_price WHERE index_code = 'VNINDEX' GROUP BY 1
)
SELECT s.year, idx.sessions AS vnindex_sessions, COUNT(*) AS stocks_below_80pct,
       STRING_AGG(s.ticker || ' (' || s.sessions || ')', ', ' ORDER BY s.ticker) AS tickers
FROM s JOIN idx USING (year)
WHERE s.sessions < 0.8 * idx.sessions
GROUP BY s.year, idx.sessions ORDER BY s.year;

-- 5. Số mã có BCTC theo năm và mẫu BCTC
SELECT f.fiscal_year, s.fs_template, COUNT(*) AS stocks
FROM fact_financials f JOIN dim_stock s USING (ticker)
GROUP BY 1, 2 ORDER BY 1, 2;

-- 6. Ô trống của chỉ số tài chính theo mẫu BCTC
SELECT s.fs_template, COUNT(*) AS rows,
       COUNT(*) - COUNT(f.roe) AS roe_null, COUNT(*) - COUNT(f.pe) AS pe_null,
       COUNT(*) - COUNT(f.gross_margin) AS gross_margin_null
FROM fact_financials f JOIN dim_stock s USING (ticker)
GROUP BY 1 ORDER BY 1;

-- 7. BCTC công bố muộn (sau 30/04 năm sau): available_date quan trọng cho Q2
SELECT ticker, fiscal_year, available_date
FROM fact_financials
WHERE available_date > MAKE_DATE(fiscal_year + 1, 4, 30)
ORDER BY available_date;

-- 8. Đối chiếu tay với BCTC đã công bố (FPT LNST 2024 = 9.427 tỷ, VCB LNTT 2024 = 42.236 tỷ)
SELECT ticker, fiscal_year, revenue, profit_before_tax, net_income, roe, pe
FROM fact_financials
WHERE ticker IN ('FPT', 'VCB') AND fiscal_year = 2024;
