-- =============================================================================
-- Schema: supply_chain.db
-- Kiến trúc: raw -> staging -> dim/fact -> mart
--
-- Quy ước:
--   * Bảng dim_* và fact_* = lớp phân tích
--   * Bảng stg_*          = lớp làm sạch (dữ liệu gốc, chưa mô hình hoá)
--   * Bảng mart_*         = kết quả phân tích, sinh bởi sql/03_analysis/
--   * Ngày tháng lưu dạng TEXT 'YYYY-MM-DD' (chuẩn SQLite/ISO 8601)
-- =============================================================================

PRAGMA foreign_keys = ON;

-- --- Xoá theo thứ tự ngược khoá ngoại ---------------------------------------
DROP TABLE IF EXISTS fact_shipments;
DROP TABLE IF EXISTS fact_purchases;
DROP TABLE IF EXISTS stg_purchases;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_supplier;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_location;

-- =============================================================================
-- STAGING
-- =============================================================================

CREATE TABLE stg_purchases (
    purchase_id     INTEGER PRIMARY KEY,
    is_synthetic    INTEGER NOT NULL DEFAULT 0,
    am_pm           TEXT    NOT NULL,
    cc_provider     TEXT    NOT NULL,
    language        TEXT    NOT NULL,
    purchase_price  REAL    NOT NULL,
    company_name    TEXT    NOT NULL,
    job_title       TEXT    NOT NULL,
    city            TEXT,
    state           TEXT,
    zip             TEXT,
    browser_family  TEXT    NOT NULL,
    os              TEXT    NOT NULL,
    device_type     TEXT    NOT NULL,
    email_masked    TEXT    NOT NULL,
    email_domain    TEXT,
    customer_key    TEXT    NOT NULL,
    ip_hash         TEXT    NOT NULL,
    job_family      TEXT    NOT NULL,
    price_tier      TEXT    NOT NULL,
    is_high_value   INTEGER NOT NULL
);

-- =============================================================================
-- DIMENSION
-- =============================================================================

CREATE TABLE dim_supplier (
    supplier_id     TEXT    PRIMARY KEY,
    supplier_name   TEXT    NOT NULL,
    country         TEXT    NOT NULL,
    tier            INTEGER NOT NULL,
    category_focus  TEXT    NOT NULL,
    contract_start  TEXT    NOT NULL,
    is_dual_source  INTEGER NOT NULL,
    is_synthetic    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE dim_product (
    product_id            TEXT    PRIMARY KEY,
    product_name          TEXT    NOT NULL,
    category              TEXT    NOT NULL,
    list_price            REAL    NOT NULL,
    unit_cost             REAL    NOT NULL,
    primary_supplier_id   TEXT    NOT NULL REFERENCES dim_supplier(supplier_id),
    secondary_supplier_id TEXT             REFERENCES dim_supplier(supplier_id),
    is_dual_source        INTEGER NOT NULL,
    is_synthetic          INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE dim_customer (
    customer_key  TEXT PRIMARY KEY,
    email_masked  TEXT NOT NULL,
    email_domain  TEXT,
    company_name  TEXT NOT NULL,
    job_title     TEXT NOT NULL,
    job_family    TEXT NOT NULL,
    language      TEXT NOT NULL
);

-- Vị trí ở cấp thành phố. is_military = 1 cho địa chỉ DPO/APO/FPO
-- (không phải thành phố thật).
CREATE TABLE dim_location (
    location_key TEXT PRIMARY KEY,
    city         TEXT    NOT NULL,
    state        TEXT    NOT NULL,
    is_military  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE dim_date (
    date_sk     INTEGER PRIMARY KEY,
    date        TEXT    NOT NULL UNIQUE,
    year        INTEGER NOT NULL,
    quarter     INTEGER NOT NULL,
    month       INTEGER NOT NULL,
    month_name  TEXT    NOT NULL,
    day         INTEGER NOT NULL,
    day_of_week TEXT    NOT NULL,
    is_weekend  INTEGER NOT NULL
);

-- =============================================================================
-- FACT
-- =============================================================================

CREATE TABLE fact_purchases (
    purchase_id     INTEGER PRIMARY KEY REFERENCES stg_purchases(purchase_id),
    is_synthetic    INTEGER NOT NULL DEFAULT 0,
    product_id      TEXT    NOT NULL REFERENCES dim_product(product_id),
    supplier_id     TEXT    NOT NULL REFERENCES dim_supplier(supplier_id),
    order_date      TEXT    NOT NULL REFERENCES dim_date(date),
    customer_key    TEXT    NOT NULL REFERENCES dim_customer(customer_key),
    location_key    TEXT    NOT NULL REFERENCES dim_location(location_key),
    purchase_price  REAL    NOT NULL,
    quantity        INTEGER NOT NULL CHECK (quantity >= 1),
    am_pm           TEXT    NOT NULL,
    cc_provider     TEXT    NOT NULL,
    browser_family  TEXT    NOT NULL,
    device_type     TEXT    NOT NULL,
    price_tier      TEXT    NOT NULL,
    is_high_value   INTEGER NOT NULL
);

-- Lưu ý: delivery_date / actual_lead_days / delay_days = NULL khi đơn bị huỷ
CREATE TABLE fact_shipments (
    shipment_id        TEXT    PRIMARY KEY,
    is_synthetic       INTEGER NOT NULL DEFAULT 1,
    purchase_id        INTEGER NOT NULL REFERENCES fact_purchases(purchase_id),
    supplier_id        TEXT    NOT NULL REFERENCES dim_supplier(supplier_id),
    ship_date          TEXT    NOT NULL,
    delivery_date      TEXT,
    promised_lead_days INTEGER NOT NULL,
    actual_lead_days   INTEGER,
    delay_days         INTEGER,
    status             TEXT    NOT NULL
        CHECK (status IN ('delivered', 'delayed', 'in_transit', 'cancelled')),
    defect_flag        INTEGER NOT NULL,
    units_shipped      INTEGER NOT NULL
);

-- =============================================================================
-- INDEX
-- =============================================================================

CREATE INDEX idx_stg_purchases_customer   ON stg_purchases(customer_key);
CREATE INDEX idx_stg_purchases_state      ON stg_purchases(state);
CREATE INDEX idx_stg_purchases_job_family ON stg_purchases(job_family);

CREATE INDEX idx_product_category         ON dim_product(category);
CREATE INDEX idx_supplier_tier            ON dim_supplier(tier);
CREATE INDEX idx_location_state           ON dim_location(state);

CREATE INDEX idx_fact_purchases_supplier  ON fact_purchases(supplier_id);
CREATE INDEX idx_fact_purchases_product   ON fact_purchases(product_id);
CREATE INDEX idx_fact_purchases_date      ON fact_purchases(order_date);
CREATE INDEX idx_fact_purchases_customer  ON fact_purchases(customer_key);
CREATE INDEX idx_fact_purchases_location  ON fact_purchases(location_key);

CREATE INDEX idx_fact_shipments_supplier  ON fact_shipments(supplier_id);
CREATE INDEX idx_fact_shipments_status    ON fact_shipments(status);
CREATE INDEX idx_fact_shipments_ship_date ON fact_shipments(ship_date);
