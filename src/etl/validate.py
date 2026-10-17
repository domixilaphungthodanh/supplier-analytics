"""Giai đoạn 5 — Kiểm tra chất lượng dữ liệu.

Chạy ~20 quy tắc kiểm tra trên database, ghi kết quả vào:
  - bảng `mart_data_quality` trong SQLite
  - file data/processed/mart_data_quality.csv
  - bảng `mart_synthetic_disclosure` (công bố tỷ lệ dữ liệu synthetic)

Mỗi quy tắc là 1 câu SQL trả về 2 cột: (failed_rows, total_rows).

Chạy:
    python -m src.etl.validate
"""

from __future__ import annotations

import sqlite3

import pandas as pd

from .config import DATA_PROCESSED, DB_PATH
from .util import force_utf8_stdout

# (tên quy tắc, nhóm, mức độ, câu SQL trả về (failed_rows, total_rows), ghi chú)
CHECKS: list[tuple[str, str, str, str, str]] = [
    # --- Đầy đủ dữ liệu ------------------------------------------------------
    (
        "row_count_stg_purchases", "completeness", "high",
        "SELECT ABS(COUNT(*) - 10000), COUNT(*) FROM stg_purchases",
        "Bảng staging phải đúng 10.000 dòng (không mất dòng khi làm sạch)",
    ),
    (
        "row_count_fact_purchases", "completeness", "high",
        "SELECT ABS(COUNT(*) - 10000), COUNT(*) FROM fact_purchases",
        "Bảng đơn hàng phải đúng 10.000 dòng",
    ),
    (
        "row_count_fact_shipments", "completeness", "high",
        "SELECT ABS(COUNT(*) - 10000), COUNT(*) FROM fact_shipments",
        "Mỗi đơn hàng phải có đúng 1 shipment",
    ),
    (
        "no_null_critical_fields", "completeness", "high",
        """
        SELECT COUNT(*), (SELECT COUNT(*) FROM fact_purchases)
        FROM fact_purchases
        WHERE purchase_price IS NULL OR quantity IS NULL OR product_id IS NULL
           OR supplier_id IS NULL OR order_date IS NULL OR customer_key IS NULL
           OR location_key IS NULL
        """,
        "Các cột khoá và cột đo lường không được NULL",
    ),
    (
        "dim_date_covers_all_orders", "completeness", "high",
        """
        SELECT COUNT(*), (SELECT COUNT(*) FROM fact_purchases)
        FROM fact_purchases f
        LEFT JOIN dim_date d ON d.date = f.order_date
        WHERE d.date IS NULL
        """,
        "Mọi order_date phải có trong dim_date (nếu thiếu, join theo thời gian sẽ mất dòng)",
    ),

    # --- Bảo toàn dữ liệu gốc ------------------------------------------------
    (
        "purchase_price_unchanged", "integrity", "high",
        """
        SELECT COUNT(*), (SELECT COUNT(*) FROM fact_purchases)
        FROM fact_purchases f
        JOIN stg_purchases s ON s.purchase_id = f.purchase_id
        WHERE ABS(f.purchase_price - s.purchase_price) > 0.001
        """,
        "QUAN TRỌNG: purchase_price phải giống hệt dữ liệu gốc, không được sửa",
    ),

    # --- Khoá duy nhất -------------------------------------------------------
    (
        "purchase_id_unique", "uniqueness", "high",
        "SELECT COUNT(*) - COUNT(DISTINCT purchase_id), COUNT(*) FROM fact_purchases",
        "purchase_id là khoá chính",
    ),
    (
        "shipment_id_unique", "uniqueness", "high",
        "SELECT COUNT(*) - COUNT(DISTINCT shipment_id), COUNT(*) FROM fact_shipments",
        "shipment_id là khoá chính",
    ),
    (
        "dim_customer_key_unique", "uniqueness", "high",
        "SELECT COUNT(*) - COUNT(DISTINCT customer_key), COUNT(*) FROM dim_customer",
        "customer_key là khoá chính (lỗi cũ: dùng email_masked làm gộp 9.954 -> 4.907)",
    ),
    (
        "dim_location_key_unique", "uniqueness", "high",
        "SELECT COUNT(*) - COUNT(DISTINCT location_key), COUNT(*) FROM dim_location",
        "location_key là khoá chính",
    ),

    # --- Miền giá trị --------------------------------------------------------
    (
        "quantity_in_range", "validity", "high",
        "SELECT COUNT(*), (SELECT COUNT(*) FROM fact_purchases) FROM fact_purchases WHERE quantity < 1 OR quantity > 20",
        "quantity phải trong [1, 20]",
    ),
    (
        "purchase_price_in_range", "validity", "high",
        "SELECT COUNT(*), (SELECT COUNT(*) FROM fact_purchases) FROM fact_purchases WHERE purchase_price < 0 OR purchase_price > 100",
        "purchase_price (dữ liệu gốc) nằm trong [0, 100]",
    ),
    (
        "shipment_status_valid", "validity", "high",
        """
        SELECT COUNT(*), (SELECT COUNT(*) FROM fact_shipments)
        FROM fact_shipments
        WHERE status NOT IN ('delivered', 'delayed', 'in_transit', 'cancelled')
        """,
        "status chỉ nhận 4 giá trị hợp lệ",
    ),
    (
        "defect_flag_binary", "validity", "medium",
        "SELECT COUNT(*), (SELECT COUNT(*) FROM fact_shipments) FROM fact_shipments WHERE defect_flag NOT IN (0, 1)",
        "defect_flag chỉ là 0 hoặc 1",
    ),
    (
        "delay_days_non_negative", "validity", "high",
        "SELECT COUNT(*), (SELECT COUNT(*) FROM fact_shipments) FROM fact_shipments WHERE delay_days < 0",
        "delay_days không được âm",
    ),
    (
        "delivery_date_consistency", "validity", "medium",
        """
        SELECT COUNT(*), (SELECT COUNT(*) FROM fact_shipments)
        FROM fact_shipments
        WHERE (status = 'cancelled' AND delivery_date IS NOT NULL)
           OR (status <> 'cancelled' AND delivery_date IS NULL)
        """,
        "Đơn huỷ không có ngày giao; đơn khác phải có ngày giao",
    ),
    (
        "ship_before_delivery", "validity", "high",
        """
        SELECT COUNT(*), (SELECT COUNT(*) FROM fact_shipments)
        FROM fact_shipments
        WHERE delivery_date IS NOT NULL AND delivery_date < ship_date
        """,
        "Ngày giao phải sau hoặc bằng ngày gửi",
    ),

    # --- Tính nhất quán giữa các bảng ---------------------------------------
    (
        "order_supplier_matches_product", "consistency", "high",
        """
        SELECT COUNT(*), (SELECT COUNT(*) FROM fact_purchases)
        FROM fact_purchases f
        JOIN dim_product pr ON pr.product_id = f.product_id
        WHERE f.supplier_id <> pr.primary_supplier_id
          AND (pr.secondary_supplier_id IS NULL
               OR f.supplier_id <> pr.secondary_supplier_id)
        """,
        "Supplier của đơn phải là primary hoặc secondary supplier của product",
    ),
    (
        "shipment_supplier_matches_order", "consistency", "high",
        """
        SELECT COUNT(*), (SELECT COUNT(*) FROM fact_shipments)
        FROM fact_shipments sh
        JOIN fact_purchases f ON f.purchase_id = sh.purchase_id
        WHERE sh.supplier_id <> f.supplier_id
        """,
        "Supplier của shipment phải trùng supplier của đơn hàng",
    ),
    (
        "units_shipped_matches_quantity", "consistency", "medium",
        """
        SELECT COUNT(*), (SELECT COUNT(*) FROM fact_shipments)
        FROM fact_shipments sh
        JOIN fact_purchases f ON f.purchase_id = sh.purchase_id
        WHERE sh.units_shipped <> f.quantity
        """,
        "Số đơn vị gửi phải bằng số lượng đặt",
    ),

    # --- Đặc điểm dữ liệu gốc (thông tin, không phải lỗi) ---------------------
    (
        "source_am_pm_is_balanced", "source_data_profile", "info",
        """
        SELECT CASE WHEN ABS(
                   AVG(CASE WHEN am_pm = 'PM' THEN 1.0 ELSE 0.0 END) - 0.5) <= 0.05
                THEN 0 ELSE 1 END,
               COUNT(*)
        FROM stg_purchases
        """,
        "THÔNG TIN: AM/PM gần 50/50 -> dữ liệu gốc là nhiễu ngẫu nhiên (gap G15)",
    ),
    (
        "source_price_is_uniform", "source_data_profile", "info",
        "SELECT CASE WHEN AVG(purchase_price) BETWEEN 45 AND 55 THEN 0 ELSE 1 END, COUNT(*) FROM stg_purchases",
        "THÔNG TIN: giá trung bình ~50 trên miền 0-100 -> phân bố đều",
    ),
    (
        "source_language_is_uniform", "source_data_profile", "info",
        """
        SELECT CASE WHEN MAX(cnt) * 1.0 / SUM(cnt) <= 0.15 THEN 0 ELSE 1 END, SUM(cnt)
        FROM (SELECT COUNT(*) AS cnt FROM stg_purchases GROUP BY language)
        """,
        "THÔNG TIN: không ngôn ngữ nào chiếm >15% -> phân bố đều",
    ),
]

SYNTHETIC_DISCLOSURE_SQL = """
SELECT 'dim_supplier'    AS object_name, COUNT(*) AS rows_total, 1 AS is_synthetic FROM dim_supplier
UNION ALL SELECT 'dim_product',   COUNT(*), 1 FROM dim_product
UNION ALL SELECT 'fact_shipments', COUNT(*), 1 FROM fact_shipments
UNION ALL SELECT 'dim_customer',  COUNT(*), 0 FROM dim_customer
UNION ALL SELECT 'dim_location',  COUNT(*), 0 FROM dim_location
UNION ALL SELECT 'dim_date',      COUNT(*), 0 FROM dim_date
UNION ALL SELECT 'stg_purchases', COUNT(*), 0 FROM stg_purchases
UNION ALL SELECT 'fact_purchases', COUNT(*), 0 FROM fact_purchases
"""


def run_checks(conn: sqlite3.Connection) -> pd.DataFrame:
    rows = []
    for name, category, severity, sql, note in CHECKS:
        failed, total = conn.execute(sql).fetchone()
        pass_rate = 1.0 if total == 0 else (total - failed) / total
        rows.append(
            {
                "rule_name": name,
                "category": category,
                "severity": severity,
                "total_rows": int(total),
                "failed_rows": int(failed),
                "pass_rate": round(pass_rate, 6),
                "note": note,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    force_utf8_stdout()

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Chưa có database: {DB_PATH}\nChạy trước: python -m src.etl.build_db"
        )

    conn = sqlite3.connect(DB_PATH)
    try:
        df = run_checks(conn)

        df.to_sql("mart_data_quality", conn, if_exists="replace", index=False)
        conn.execute("CREATE INDEX idx_mart_dq_category ON mart_data_quality(category)")

        disclosure = pd.read_sql_query(SYNTHETIC_DISCLOSURE_SQL, conn)
        disclosure.to_sql("mart_synthetic_disclosure", conn, if_exists="replace", index=False)
        conn.commit()

        df.to_csv(DATA_PROCESSED / "mart_data_quality.csv", index=False)
        disclosure.to_csv(DATA_PROCESSED / "mart_synthetic_disclosure.csv", index=False)

        # --- Báo cáo ---
        line = "=" * 78
        print(line)
        print("BÁO CÁO CHẤT LƯỢNG DỮ LIỆU (GIAI ĐOẠN 5)")
        print(line)

        real_checks = df[df["severity"] != "info"]
        info_checks = df[df["severity"] == "info"]

        print(f"\n[1] Quy tắc nghiêm ngặt ({len(real_checks)} quy tắc)")
        print(f"    {'QUY TẮC':<38} {'MỨC':<7} {'LỖI':>6} {'TỔNG':>8} {'ĐẠT':>7}")
        for _, r in real_checks.iterrows():
            flag = "OK" if r["failed_rows"] == 0 else "LỖI"
            print(f"    {r['rule_name']:<38} {r['severity']:<7} "
                  f"{r['failed_rows']:>6,} {r['total_rows']:>8,} {r['pass_rate']:>6.2%} {flag}")

        n_fail = int((real_checks["failed_rows"] > 0).sum())
        print(f"\n    => {len(real_checks) - n_fail}/{len(real_checks)} quy tắc ĐẠT"
              f"{'  ✅' if n_fail == 0 else f'  ❌ {n_fail} quy tắc lỗi'}")

        print(f"\n[2] Nhận xét về dữ liệu gốc ({len(info_checks)} mục — không phải lỗi)")
        for _, r in info_checks.iterrows():
            print(f"    - {r['note']}")

        print("\n[3] Công bố dữ liệu synthetic")
        for _, r in disclosure.iterrows():
            mark = "SYNTHETIC" if r["is_synthetic"] else "nguồn gốc"
            print(f"    {r['object_name']:<16} {r['rows_total']:>7,} dòng   [{mark}]")

        # --- Kiểm tra khoá ngoại (không dùng SQL thường được) ---
        fk = conn.execute("PRAGMA foreign_key_check").fetchall()
        print(f"\n[4] Vi phạm khoá ngoại: {len(fk)}  {'OK' if not fk else fk[:3]}")
        print(line)
    finally:
        conn.close()

    print(f"\nĐã ghi: mart_data_quality ({len(CHECKS)} quy tắc) vào database và CSV")


if __name__ == "__main__":
    main()
