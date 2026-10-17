-- =============================================================================
-- MẢNG 4: Tài khoản khách hàng B2B (từ cột Company)
-- Câu hỏi: Công ty nào mua nhiều nhất? Giá trị đơn trung bình bao nhiêu?
--
-- LƯU Ý (gap G16): cột Company có nhóm trùng nhưng YẾU — công ty nhiều đơn
-- nhất chỉ ~15/10.000 đơn. Vì vậy mảng này chỉ nên MÔ TẢ, không kết luận.
-- =============================================================================
SELECT
    c.company_name,
    COUNT(DISTINCT c.customer_key)  AS customers,
    COUNT(p.purchase_id)            AS order_count,
    ROUND(SUM(p.purchase_price), 2) AS total_spend,
    ROUND(AVG(p.purchase_price), 2) AS avg_order_value,
    SUM(p.quantity)                 AS units,
    SUM(p.is_high_value)            AS high_value_orders,
    COUNT(DISTINCT p.product_id)    AS distinct_products,
    COUNT(DISTINCT p.supplier_id)   AS distinct_suppliers,
    MIN(p.order_date)               AS first_order,
    MAX(p.order_date)               AS last_order,
    CASE WHEN COUNT(p.purchase_id) >= 5 THEN 'key_account'
         WHEN COUNT(p.purchase_id) >= 2 THEN 'repeat'
         ELSE 'one_off' END         AS account_segment
FROM dim_customer   c
JOIN fact_purchases p ON p.customer_key = c.customer_key
GROUP BY c.company_name
ORDER BY total_spend DESC;
