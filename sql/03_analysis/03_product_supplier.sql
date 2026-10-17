-- =============================================================================
-- MẢNG 3: Ánh xạ Sản phẩm - Nhà cung cấp
-- Câu hỏi: Sản phẩm nào lãi nhất? Category nào phụ thuộc supplier nào?
--          Sản phẩm nào KHÔNG có supplier dự phòng?
-- =============================================================================
SELECT
    pr.category,
    pr.product_id,
    pr.product_name,
    pr.list_price,
    pr.unit_cost,
    ROUND((pr.list_price - pr.unit_cost) * 100.0 / pr.list_price, 2) AS margin_pct,
    pr.primary_supplier_id,
    s1.supplier_name                       AS primary_supplier_name,
    s1.tier                                AS primary_tier,
    s1.country                             AS primary_country,
    pr.secondary_supplier_id,
    s2.supplier_name                       AS secondary_supplier_name,
    s2.tier                                AS secondary_tier,
    pr.is_dual_source,
    COUNT(p.purchase_id)                                   AS order_count,
    COALESCE(SUM(p.quantity), 0)                           AS units_sold,
    ROUND(COALESCE(SUM(p.purchase_price), 0), 2)           AS spend,
    ROUND(COALESCE(SUM(p.quantity * pr.unit_cost), 0), 2)  AS total_cost,
    ROUND(COALESCE(SUM(p.purchase_price), 0)
          - COALESCE(SUM(p.quantity * pr.unit_cost), 0), 2) AS gross_profit,
    ROUND(
        CASE WHEN COALESCE(SUM(p.purchase_price), 0) > 0
             THEN (COALESCE(SUM(p.purchase_price), 0)
                   - COALESCE(SUM(p.quantity * pr.unit_cost), 0))
                  * 100.0 / COALESCE(SUM(p.purchase_price), 0)
        END, 2)                                            AS realized_margin_pct
FROM dim_product pr
JOIN dim_supplier s1        ON s1.supplier_id = pr.primary_supplier_id
LEFT JOIN dim_supplier s2   ON s2.supplier_id = pr.secondary_supplier_id
LEFT JOIN fact_purchases p  ON p.product_id   = pr.product_id
GROUP BY pr.product_id
ORDER BY spend DESC, pr.product_id;
