-- Star schema cho dự án VN stock analysis (PostgreSQL).
-- Chạy lại an toàn: xóa rồi tạo lại toàn bộ bảng. load_to_db.py tự chạy file này trước khi nạp.
-- Thiết kế: docs/schema.md.

DROP TABLE IF EXISTS fact_financials, fact_price, fact_index_price, dim_date, dim_stock CASCADE;

CREATE TABLE dim_stock (
    ticker           VARCHAR(10) PRIMARY KEY,
    company_name     VARCHAR(255) NOT NULL,
    exchange         VARCHAR(10)  NOT NULL,
    icb_code_l2      CHAR(4)      NOT NULL,
    industry_l1      VARCHAR(50)  NOT NULL,
    industry_l2      VARCHAR(50)  NOT NULL,
    is_vn30          BOOLEAN      NOT NULL,
    is_bank          BOOLEAN      NOT NULL,
    fs_template      VARCHAR(12)  NOT NULL CHECK (fs_template IN ('thuong', 'ngan_hang', 'chung_khoan', 'bao_hiem')),
    first_trade_date DATE         NOT NULL
);

CREATE TABLE dim_date (
    date           DATE PRIMARY KEY,
    year           SMALLINT NOT NULL,
    quarter        SMALLINT NOT NULL,
    month          SMALLINT NOT NULL,
    week           SMALLINT NOT NULL,
    day_of_week    SMALLINT NOT NULL,
    is_trading_day BOOLEAN  NOT NULL,
    market_regime  VARCHAR(20)
);

CREATE TABLE fact_price (
    ticker        VARCHAR(10)   NOT NULL REFERENCES dim_stock (ticker),
    date          DATE          NOT NULL REFERENCES dim_date (date),
    open          NUMERIC(14,2) NOT NULL,
    high          NUMERIC(14,2) NOT NULL,
    low           NUMERIC(14,2) NOT NULL,
    close         NUMERIC(14,2) NOT NULL,
    volume        BIGINT        NOT NULL,
    value_mil_vnd NUMERIC(18,3) NOT NULL,
    crawled_at    TIMESTAMP     NOT NULL,
    PRIMARY KEY (ticker, date)
);
CREATE INDEX ix_fact_price_date ON fact_price (date);

CREATE TABLE fact_index_price (
    index_code    VARCHAR(10)   NOT NULL,
    date          DATE          NOT NULL REFERENCES dim_date (date),
    open          NUMERIC(14,2) NOT NULL,
    high          NUMERIC(14,2) NOT NULL,
    low           NUMERIC(14,2) NOT NULL,
    close         NUMERIC(14,2) NOT NULL,
    volume        BIGINT        NOT NULL,
    value_mil_vnd NUMERIC(18,3) NOT NULL,
    crawled_at    TIMESTAMP     NOT NULL,
    PRIMARY KEY (index_code, date)
);

CREATE TABLE fact_financials (
    ticker            VARCHAR(10) NOT NULL REFERENCES dim_stock (ticker),
    fiscal_year       SMALLINT    NOT NULL,
    available_date    DATE        NOT NULL,
    revenue           NUMERIC(18,3),
    profit_before_tax NUMERIC(18,3),
    net_income        NUMERIC(18,3),
    net_income_parent NUMERIC(18,3),
    total_assets      NUMERIC(18,3),
    total_liabilities NUMERIC(18,3),
    total_equity      NUMERIC(18,3),
    eps               NUMERIC(12,2),
    roe               NUMERIC(12,6),
    roa               NUMERIC(12,6),
    pe                NUMERIC(12,6),
    pb                NUMERIC(12,6),
    gross_margin      NUMERIC(12,6),
    net_margin        NUMERIC(12,6),
    debt_to_equity    NUMERIC(12,6),
    PRIMARY KEY (ticker, fiscal_year)
);

COMMENT ON COLUMN fact_price.close IS 'Giá đóng cửa đã điều chỉnh (cổ tức, chia tách), đơn vị đồng';
COMMENT ON COLUMN fact_price.value_mil_vnd IS 'Giá trị giao dịch, triệu đồng = close * volume / 1e6 (không dùng số của API vì lệch đơn vị trước 2025); dùng giá điều chỉnh nên quá khứ thấp hơn thực tế vài %';
COMMENT ON COLUMN fact_financials.available_date IS 'Ngày công bố BCTC (publicDate từ API), dùng để tránh look-ahead bias';
COMMENT ON COLUMN fact_financials.revenue IS 'Tỷ đồng. Ngân hàng: tổng thu nhập hoạt động; bảo hiểm: doanh thu phí bảo hiểm';
COMMENT ON COLUMN fact_financials.eps IS 'Lãi cơ bản trên cổ phiếu, đồng';
COMMENT ON COLUMN fact_financials.roe IS 'Tỷ lệ thập phân (0.287 = 28,7%)';
COMMENT ON COLUMN dim_stock.fs_template IS 'Mẫu BCTC theo API: thuong / ngan_hang / chung_khoan / bao_hiem';
