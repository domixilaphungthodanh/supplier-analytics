-- =============================================================================
-- MẢNG 6: Hồ sơ thanh toán & rủi ro theo nhà cung cấp thẻ
-- Câu hỏi: Nhà cung cấp thẻ nào phổ biến? Thẻ nào gắn với đơn giá trị cao?
--
-- LƯU Ý (gap G15): dữ liệu gốc phân bố đều -> các chỉ số ở đây gần như phẳng.
-- Đây là kết quả TRUNG THỰC, không phải lỗi.
-- =============================================================================
SELECT
    cc_provider,
    COUNT(*)                                            AS order_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM fact_purchases), 2) AS order_share_pct,
    ROUND(SUM(purchase_price), 2)                       AS total_spend,
    ROUND(AVG(purchase_price), 2)                       AS avg_order_value,
    ROUND(MIN(purchase_price), 2)                       AS min_price,
    ROUND(MAX(purchase_price), 2)                       AS max_price,
    SUM(is_high_value)                                  AS high_value_orders,
    ROUND(SUM(is_high_value) * 100.0 / COUNT(*), 2)     AS high_value_pct,
    COUNT(DISTINCT supplier_id)                         AS distinct_suppliers
FROM fact_purchases
GROUP BY cc_provider
ORDER BY total_spend DESC;
