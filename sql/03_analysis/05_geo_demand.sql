-- =============================================================================
-- MẢNG 5: Nhu cầu theo địa lý vs độ phủ nhà cung cấp
-- Câu hỏi: Bang nào cầu lớn? Bang nào cầu lớn mà ít supplier phục vụ?
--
-- LƯU Ý: cột is_military đánh dấu địa chỉ DPO/APO/FPO. Đây KHÔNG phải thành
-- phố thật — nếu không lọc, chúng sẽ đứng đầu bảng xếp hạng một cách vô nghĩa.
-- =============================================================================
SELECT
    l.state,
    MAX(l.is_military)                              AS is_military,
    COUNT(DISTINCT l.city)                          AS cities,
    COUNT(p.purchase_id)                            AS order_count,
    ROUND(SUM(p.purchase_price), 2)                 AS total_spend,
    ROUND(AVG(p.purchase_price), 2)                 AS avg_order_value,
    COUNT(DISTINCT p.supplier_id)                   AS suppliers_serving,
    COUNT(DISTINCT p.product_id)                    AS distinct_products,
    ROUND(SUM(p.purchase_price) / COUNT(DISTINCT p.supplier_id), 2) AS spend_per_supplier,
    ROUND(COUNT(p.purchase_id) * 100.0
          / (SELECT COUNT(*) FROM fact_purchases), 2) AS order_share_pct
FROM fact_purchases p
JOIN dim_location   l ON l.location_key = p.location_key
GROUP BY l.state
ORDER BY total_spend DESC;
