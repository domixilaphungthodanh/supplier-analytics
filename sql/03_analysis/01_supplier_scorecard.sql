-- =============================================================================
-- MẢNG 1: Hiệu suất nhà cung cấp (Supplier Performance Scorecard)
-- Câu hỏi: Supplier nào giao đúng hạn? Ai lỗi nhiều? Ai đáng tin nhất?
--
-- Phân loại ABC theo tổng chi tiêu (A <= 80% lũy kế, B <= 95%, C còn lại)
-- Phân loại XYZ theo độ biến động lead time (X ổn định -> Z thất thường)
--
-- LƯU Ý: dùng LEFT JOIN để giữ cả supplier trong danh bạ nhưng KHÔNG có đơn
-- hàng nào (is_active = 0). Nếu dùng INNER JOIN sẽ âm thầm mất 2/35 supplier.
-- =============================================================================
WITH orders AS (
    SELECT supplier_id,
           COUNT(*)                     AS order_count,
           SUM(purchase_price)          AS total_spend,
           AVG(purchase_price)          AS avg_order_value,
           SUM(quantity)                AS units_sold,
           COUNT(DISTINCT product_id)   AS product_count,
           COUNT(DISTINCT customer_key) AS customer_count,
           MIN(order_date)              AS first_order,
           MAX(order_date)              AS last_order
    FROM fact_purchases
    GROUP BY supplier_id
),
ships AS (
    SELECT supplier_id,
           COUNT(*)                                               AS shipment_count,
           SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END)   AS cancelled_count,
           AVG(CASE WHEN status IN ('delivered', 'delayed')
                    THEN CASE WHEN delay_days = 0 THEN 1.0 ELSE 0.0 END END) AS on_time_rate,
           AVG(defect_flag)                                        AS defect_rate,
           AVG(CASE WHEN status IN ('delivered', 'delayed')
                    THEN actual_lead_days END)                     AS avg_lead_days,
           AVG(CASE WHEN status IN ('delivered', 'delayed')
                    THEN actual_lead_days * actual_lead_days END)  AS avg_lead_sq,
           MAX(delay_days)                                         AS max_delay_days
    FROM fact_shipments
    GROUP BY supplier_id
),
joined AS (
    SELECT s.supplier_id,
           s.supplier_name,
           s.country,
           s.tier,
           s.category_focus,
           s.is_dual_source,
           COALESCE(o.order_count, 0)      AS order_count,
           COALESCE(o.total_spend, 0.0)    AS total_spend,
           COALESCE(o.avg_order_value, 0.0) AS avg_order_value,
           COALESCE(o.units_sold, 0)       AS units_sold,
           COALESCE(o.product_count, 0)    AS product_count,
           COALESCE(o.customer_count, 0)   AS customer_count,
           o.first_order,
           o.last_order,
           COALESCE(sh.shipment_count, 0)  AS shipment_count,
           COALESCE(sh.cancelled_count, 0) AS cancelled_count,
           sh.on_time_rate,
           sh.defect_rate,
           sh.avg_lead_days,
           sh.max_delay_days,
           -- Số sản phẩm được GÁN cho supplier (khác với số sản phẩm đã bán)
           (SELECT COUNT(*) FROM dim_product d
             WHERE d.primary_supplier_id   = s.supplier_id
                OR d.secondary_supplier_id = s.supplier_id) AS products_assigned,
           -- Hệ số biến động (CV) = độ lệch chuẩn / trung bình
           CASE WHEN COALESCE(sh.avg_lead_days, 0) > 0
                THEN SQRT(MAX(sh.avg_lead_sq - sh.avg_lead_days * sh.avg_lead_days, 0.0))
                     / sh.avg_lead_days
           END AS lead_time_cv
    FROM dim_supplier s
    LEFT JOIN orders o  ON o.supplier_id  = s.supplier_id
    LEFT JOIN ships  sh ON sh.supplier_id = s.supplier_id
),
ranked AS (
    SELECT *,
           SUM(total_spend) OVER (
               ORDER BY total_spend DESC
               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
           ) / NULLIF(SUM(total_spend) OVER (), 0) AS cum_spend_share
    FROM joined
)
SELECT
    supplier_id,
    supplier_name,
    country,
    tier,
    category_focus,
    is_dual_source,
    CASE WHEN order_count > 0 THEN 1 ELSE 0 END AS is_active,
    products_assigned,
    order_count,
    product_count,
    customer_count,
    units_sold,
    ROUND(total_spend, 2)                                   AS total_spend,
    ROUND(avg_order_value, 2)                               AS avg_order_value,
    ROUND(total_spend * 100.0 / SUM(total_spend) OVER (), 2) AS spend_share_pct,
    CASE WHEN cum_spend_share IS NULL THEN 'C'
         WHEN cum_spend_share <= 0.80 THEN 'A'
         WHEN cum_spend_share <= 0.95 THEN 'B'
         ELSE 'C' END                                       AS abc_class,
    ROUND(on_time_rate * 100, 2)                            AS on_time_pct,
    ROUND((1 - on_time_rate) * 100, 2)                      AS late_pct,
    ROUND(defect_rate * 100, 2)                             AS defect_pct,
    ROUND(avg_lead_days, 2)                                 AS avg_lead_days,
    max_delay_days,
    ROUND(lead_time_cv, 3)                                  AS lead_time_cv,
    CASE WHEN lead_time_cv IS NULL THEN '?'
         WHEN lead_time_cv <= 0.15 THEN 'X'
         WHEN lead_time_cv <= 0.30 THEN 'Y'
         ELSE 'Z' END                                       AS xyz_class,
    cancelled_count,
    shipment_count,
    first_order,
    last_order
FROM ranked
ORDER BY total_spend DESC, supplier_id;
