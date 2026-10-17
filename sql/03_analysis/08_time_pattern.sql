-- =============================================================================
-- MẢNG 8: Mẫu hình theo thời gian (mùa vụ & buổi mua)
-- Câu hỏi: Tháng nào đông đơn nhất? Q4 có cao hơn thật không? Sáng hay chiều?
--
-- LƯU Ý: order_date là cột SYNTHETIC. Mùa vụ Q4 cao hơn 30% là do giả định
-- ở docs/assumptions.md A3, không phải phát hiện từ dữ liệu thật.
-- =============================================================================
SELECT
    d.year,
    d.quarter,
    d.month,
    d.month_name,
    p.am_pm,
    COUNT(*)                        AS order_count,
    ROUND(SUM(p.purchase_price), 2) AS total_spend,
    ROUND(AVG(p.purchase_price), 2) AS avg_order_value,
    SUM(p.quantity)                 AS units,
    COUNT(DISTINCT p.supplier_id)   AS distinct_suppliers
FROM fact_purchases p
JOIN dim_date       d ON d.date = p.order_date
GROUP BY d.year, d.quarter, d.month, d.month_name, p.am_pm
ORDER BY d.year, d.month, p.am_pm;
