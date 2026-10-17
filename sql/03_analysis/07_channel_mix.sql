-- =============================================================================
-- MẢNG 7: Kênh truy cập & thiết bị
-- Câu hỏi: Khách dùng trình duyệt nào? Thiết bị nào? Đơn giá có khác nhau không?
--
-- LƯU Ý (gap G15): dữ liệu gốc phân bố đều -> kết quả gần như phẳng.
-- =============================================================================
SELECT
    browser_family,
    device_type,
    COUNT(*)                                            AS order_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM fact_purchases), 2) AS order_share_pct,
    ROUND(SUM(purchase_price), 2)                       AS total_spend,
    ROUND(AVG(purchase_price), 2)                       AS avg_order_value,
    ROUND(AVG(quantity), 2)                             AS avg_quantity,
    SUM(is_high_value)                                  AS high_value_orders,
    ROUND(SUM(is_high_value) * 100.0 / COUNT(*), 2)     AS high_value_pct,
    COUNT(DISTINCT supplier_id)                         AS distinct_suppliers,
    COUNT(DISTINCT product_id)                          AS distinct_products
FROM fact_purchases
GROUP BY browser_family, device_type
ORDER BY total_spend DESC;
