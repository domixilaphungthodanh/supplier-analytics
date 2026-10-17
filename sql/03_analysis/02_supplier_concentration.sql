-- =============================================================================
-- MẢNG 2: Tập trung chi tiêu & rủi ro phụ thuộc nhà cung cấp
-- Câu hỏi: Có đang phụ thuộc quá nhiều vào 1 supplier trong 1 category không?
--          Category nào có nhiều sản phẩm không có supplier dự phòng?
-- =============================================================================
WITH cat_supplier AS (
    SELECT pr.category,
           p.supplier_id,
           COUNT(*)              AS order_count,
           SUM(p.purchase_price) AS spend,
           SUM(p.quantity)       AS units
    FROM fact_purchases p
    JOIN dim_product   pr ON pr.product_id = p.product_id
    GROUP BY pr.category, p.supplier_id
),
cat_total AS (
    SELECT category, SUM(spend) AS category_spend
    FROM cat_supplier
    GROUP BY category
)
SELECT
    cs.category,
    cs.supplier_id,
    s.supplier_name,
    s.tier,
    s.country,
    cs.order_count,
    cs.units,
    ROUND(cs.spend, 2)                                     AS spend,
    ROUND(ct.category_spend, 2)                            AS category_spend,
    ROUND(cs.spend * 100.0 / ct.category_spend, 2)         AS category_share_pct,
    (SELECT COUNT(*) FROM cat_supplier x WHERE x.category = cs.category)
                                                           AS suppliers_in_category,
    -- Rủi ro: 1 supplier chiếm > 50% chi tiêu của category
    CASE WHEN cs.spend * 1.0 / ct.category_spend > 0.50 THEN 1 ELSE 0 END
                                                           AS is_single_source_risk,
    (SELECT COUNT(*) FROM dim_product d
      WHERE d.category = cs.category AND d.is_dual_source = 0)
                                                           AS products_without_backup,
    (SELECT COUNT(*) FROM dim_product d
      WHERE d.category = cs.category)
                                                           AS products_in_category
FROM cat_supplier cs
JOIN cat_total    ct ON ct.category = cs.category
JOIN dim_supplier s  ON s.supplier_id = cs.supplier_id
ORDER BY cs.category, category_share_pct DESC;
