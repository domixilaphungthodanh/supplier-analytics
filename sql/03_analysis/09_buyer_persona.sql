-- =============================================================================
-- MẢNG 9: Chân dung người mua (theo nhóm nghề nghiệp)
-- Câu hỏi: Nhóm nghề nào mua nhiều nhất? Chi bao nhiêu? Có liên quan
--          tới chuỗi cung ứng không?
--
-- LƯU Ý (gap G15): cột Job là nhiễu ngẫu nhiên -> kết quả gần như phẳng.
-- Riêng nhóm Supply Chain / Procurement đáng chú ý về mặt nghiệp vụ:
-- nếu nhóm này mua nhiều, đó là tín hiệu "mua sắm nội bộ".
-- =============================================================================
SELECT
    c.job_family,
    COUNT(DISTINCT c.customer_key)  AS customers,
    COUNT(p.purchase_id)            AS order_count,
    ROUND(SUM(p.purchase_price), 2) AS total_spend,
    ROUND(AVG(p.purchase_price), 2) AS avg_order_value,
    ROUND(AVG(p.quantity), 2)       AS avg_quantity,
    SUM(p.quantity)                 AS units,
    SUM(p.is_high_value)            AS high_value_orders,
    ROUND(SUM(p.is_high_value) * 100.0 / COUNT(*), 2) AS high_value_pct,
    COUNT(DISTINCT p.supplier_id)   AS distinct_suppliers,
    COUNT(DISTINCT p.product_id)    AS distinct_products
FROM dim_customer   c
JOIN fact_purchases p ON p.customer_key = c.customer_key
GROUP BY c.job_family
ORDER BY total_spend DESC;
