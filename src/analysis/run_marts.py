"""Giai đoạn 6 — Chạy 9 mảng phân tích, ghi CSV + vẽ chart.

Mỗi file trong sql/03_analysis/ là 1 mảng phân tích:
  - được chạy thành bảng `mart_*` trong SQLite
  - xuất ra reports/... CSV trong data/processed/
  - vẽ chart PNG trong reports/figures/

Chạy:
    python -m src.analysis.run_marts
"""

from __future__ import annotations

import sqlite3

import matplotlib

matplotlib.use("Agg")  # không cần màn hình

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle

from ..etl.config import DATA_PROCESSED, DB_PATH, FIGURES, PROJECT_ROOT
from ..etl.util import force_utf8_stdout

MART_DIR = PROJECT_ROOT / "sql" / "03_analysis"

# Đặc tả chart cho từng mart.
#   kind      : bar | barh | line | scatter
#   x / y     : cột trục hoành / trục tung
#   agg_by    : gộp nhóm trước khi vẽ
#   label_cols: ghép nhiều cột thành nhãn
#   hue       : tô màu theo nhóm
#   size      : kích thước điểm (scatter)
#   top       : chỉ lấy N giá trị lớn nhất
#   query     : lọc bằng pandas query
#   period    : ghép year+month thành trục thời gian
CHART_SPECS: dict[str, list[dict]] = {
    "mart_supplier_scorecard": [
        {
            "kind": "barh", "x": "supplier_name", "y": "total_spend", "hue": "tier",
            "top": 15, "fname": "01_supplier_top_spend",
            "title": "Top 15 suppliers by total spend (colored by tier)",
        },
        {
            "kind": "scatter", "x": "on_time_pct", "y": "defect_pct",
            "size": "total_spend", "hue": "tier", "fname": "02_supplier_quality_map",
            "title": "Supplier quality map: on-time % vs defect % (bubble = spend)",
        },
    ],
    "mart_supplier_concentration": [
        {
            "kind": "barh", "label_cols": ["category", "supplier_name"],
            "y": "category_share_pct", "top": 12, "fname": "03_category_dependency",
            "title": "Highest category dependency (top supplier share of category spend)",
        },
    ],
    "mart_product_supplier": [
        {
            "kind": "bar", "agg_by": "category", "y": "spend", "agg_func": "sum",
            "fname": "04_spend_by_category",
            "title": "Total spend by product category",
        },
        {
            "kind": "barh", "x": "product_name", "y": "margin_pct", "hue": "category",
            "top": 15, "fname": "05_product_margin",
            "title": "Top 15 products by gross margin %",
        },
    ],
    "mart_b2b_customer": [
        {
            "kind": "barh", "x": "company_name", "y": "total_spend", "hue": "account_segment",
            "top": 15, "fname": "06_top_b2b_accounts",
            "title": "Top 15 B2B accounts by spend (colored by segment)",
        },
    ],
    "mart_geo_demand": [
        {
            "kind": "barh", "x": "state", "y": "total_spend", "hue": "is_military",
            "top": 15, "fname": "07_top_states",
            "title": "Top 15 states by spend (hue = military address)",
        },
        {
            "kind": "scatter", "x": "suppliers_serving", "y": "total_spend",
            "size": "order_count", "hue": "is_military", "query": "order_count >= 50",
            "fname": "08_state_coverage",
            "title": "Supplier coverage vs demand by state (bubble = orders)",
        },
    ],
    "mart_payment_profile": [
        {
            "kind": "bar", "x": "cc_provider", "y": "order_count",
            "fname": "09_card_provider",
            "title": "Orders by card provider",
        },
    ],
    "mart_channel_mix": [
        {
            "kind": "bar", "x": "browser_family", "y": "order_count",
            "fname": "10_browser",
            "title": "Orders by browser",
        },
        {
            "kind": "bar", "agg_by": "device_type", "y": "order_count", "agg_func": "sum",
            "fname": "11_device_type",
            "title": "Orders by device type",
        },
    ],
    "mart_time_pattern": [
        {
            "kind": "line", "period": True, "y": "order_count", "hue": "am_pm",
            "fname": "12_monthly_seasonality",
            "title": "Monthly orders by time of day (synthetic seasonality)",
        },
    ],
    "mart_buyer_persona": [
        {
            "kind": "barh", "x": "job_family", "y": "total_spend",
            "fname": "13_job_family_spend",
            "title": "Total spend by job family",
        },
    ],
    "mart_data_quality": [
        {
            "kind": "barh", "x": "rule_name", "y": "pass_rate_pct",
            "query": "severity != 'info'", "fname": "14_data_quality",
            "title": "Data quality checks - pass rate %",
        },
    ],
}


def mart_name_from_path(path) -> str:
    """01_supplier_scorecard.sql -> mart_supplier_scorecard"""
    return "mart_" + path.stem.split("_", 1)[1]


def build_mart(conn: sqlite3.Connection, name: str, sql_path) -> pd.DataFrame:
    sql = sql_path.read_text(encoding="utf-8").strip().rstrip(";")
    conn.execute(f"DROP TABLE IF EXISTS {name}")
    conn.execute(f"CREATE TABLE {name} AS {sql}")
    conn.commit()
    return pd.read_sql_query(f"SELECT * FROM {name}", conn)


def make_chart(df: pd.DataFrame, spec: dict, out_path) -> None:
    d = df.copy()

    if spec.get("query"):
        d = d.query(spec["query"])
    if "pass_rate" in d.columns:
        d["pass_rate_pct"] = d["pass_rate"] * 100

    if spec.get("period"):
        d["period"] = d["year"].astype(str) + "-" + d["month"].astype(str).str.zfill(2)
        xcol = "period"
    elif spec.get("agg_by"):
        d = d.groupby(spec["agg_by"], as_index=False)[spec["y"]].agg(
            spec.get("agg_func", "sum")
        )
        xcol = spec["agg_by"]
    elif spec.get("label_cols"):
        d["_label"] = d[spec["label_cols"]].astype(str).agg(" / ".join, axis=1)
        xcol = "_label"
    else:
        xcol = spec["x"]

    y = spec["y"]
    if spec.get("top"):
        d = d.nlargest(spec["top"], y)

    kind = spec["kind"]
    hue = spec.get("hue")

    fig, ax = plt.subplots(figsize=(11, 6))

    if kind == "line":
        if hue:
            for key, g in d.groupby(hue):
                g = g.sort_values(xcol)
                ax.plot(g[xcol], g[y], marker="o", label=str(key))
            ax.legend(title=hue)
        else:
            d = d.sort_values(xcol)
            ax.plot(d[xcol], d[y], marker="o")
        ax.tick_params(axis="x", rotation=45)

    elif kind == "scatter":
        if hue:
            for key, g in d.groupby(hue):
                s = g[spec["size"]] if spec.get("size") else None
                ss = (s / s.max() * 400 + 30) if s is not None else 60
                ax.scatter(g[xcol], g[y], s=ss, alpha=0.7, label=f"{hue}={key}")
            ax.legend(title=hue)
        else:
            s = d[spec["size"]] if spec.get("size") else None
            ss = (s / s.max() * 400 + 30) if s is not None else 60
            ax.scatter(d[xcol], d[y], s=ss, alpha=0.7)

    elif kind == "barh":
        d = d.sort_values(y)
        if hue:
            cats = sorted(d[hue].unique(), key=str)
            cmap = plt.get_cmap("tab10")
            colors = [cmap(cats.index(v) % 10) for v in d[hue]]
            ax.barh(d[xcol], d[y], color=colors)
            handles = [Rectangle((0, 0), 1, 1, color=cmap(i % 10)) for i in range(len(cats))]
            ax.legend(handles, [f"{hue}={c}" for c in cats], title=hue)
        else:
            ax.barh(d[xcol], d[y])

    else:  # bar
        d = d.sort_values(y, ascending=False)
        ax.bar(d[xcol].astype(str), d[y])
        ax.tick_params(axis="x", rotation=45)

    ax.set_title(spec["title"], fontsize=13, fontweight="bold")
    ax.set_ylabel(y)
    ax.grid(axis="x" if kind == "barh" else "y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=110)
    plt.close(fig)


def headline_findings(conn: sqlite3.Connection) -> None:
    """In các phát hiện chính."""
    print("\n" + "=" * 78)
    print("PHÁT HIỆN CHÍNH")
    print("=" * 78)

    print("\n[1] Danh bạ nhà cung cấp")
    q = """
        SELECT COUNT(*)                                  AS suppliers_total,
               SUM(is_active)                            AS active,
               SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) AS dormant,
               ROUND(SUM(total_spend), 2)                AS total_spend
        FROM mart_supplier_scorecard
    """
    print(pd.read_sql_query(q, conn).to_string(index=False))
    q = """
        SELECT supplier_id, supplier_name, tier, category_focus, products_assigned
        FROM mart_supplier_scorecard WHERE is_active = 0
    """
    dormant = pd.read_sql_query(q, conn)
    if len(dormant):
        print("    Supplier không hoạt động (có trong danh bạ, chưa gán sản phẩm nào):")
        print("    " + dormant.to_string(index=False).replace("\n", "\n    "))

    print("\n[2] Supplier giao trễ nhất (on-time thấp nhất)")
    q = """
        SELECT supplier_name, tier, country, shipment_count, on_time_pct, defect_pct
        FROM mart_supplier_scorecard WHERE is_active = 1
        ORDER BY on_time_pct ASC LIMIT 3
    """
    print(pd.read_sql_query(q, conn).to_string(index=False))

    print("\n[3] Supplier đáng tin nhất (on-time cao nhất)")
    q = """
        SELECT supplier_name, tier, country, shipment_count, on_time_pct, defect_pct
        FROM mart_supplier_scorecard WHERE is_active = 1
        ORDER BY on_time_pct DESC LIMIT 3
    """
    print(pd.read_sql_query(q, conn).to_string(index=False))

    print("\n[4] Phân loại ABC theo chi tiêu")
    q = """
        SELECT abc_class,
               COUNT(*)                        AS suppliers,
               ROUND(SUM(total_spend), 2)      AS spend,
               ROUND(SUM(total_spend) * 100.0
                     / (SELECT SUM(total_spend) FROM mart_supplier_scorecard), 2) AS spend_pct
        FROM mart_supplier_scorecard GROUP BY abc_class ORDER BY abc_class
    """
    print(pd.read_sql_query(q, conn).to_string(index=False))

    print("\n[5] Rủi ro phụ thuộc 1 nhà cung cấp (>50% chi tiêu của category)")
    q = """
        SELECT category, supplier_name, tier, category_share_pct,
               suppliers_in_category, products_without_backup
        FROM mart_supplier_concentration
        WHERE is_single_source_risk = 1
        ORDER BY category_share_pct DESC
    """
    risk = pd.read_sql_query(q, conn)
    print(risk.to_string(index=False) if len(risk) else "    Không có category nào bị phụ thuộc >50%")

    q = "SELECT COUNT(*) AS n FROM mart_product_supplier WHERE is_dual_source = 0"
    print(f"\n    Tổng category bị rủi ro     : {len(risk)}")
    print(f"    Sản phẩm không có dự phòng  : {pd.read_sql_query(q, conn)['n'][0]}/120")

    print("\n[6] Tài khoản B2B lớn nhất")
    q = """
        SELECT company_name, customers, order_count, total_spend, account_segment
        FROM mart_b2b_customer LIMIT 3
    """
    print(pd.read_sql_query(q, conn).to_string(index=False))
    q = "SELECT account_segment, COUNT(*) AS accounts FROM mart_b2b_customer GROUP BY account_segment ORDER BY accounts DESC"
    print("\n    Phân bố tài khoản:")
    print(pd.read_sql_query(q, conn).to_string(index=False).replace("\n", "\n    "))

    print("\n[7] Mùa vụ (order_date là cột SYNTHETIC theo giả định A3)")
    q = """
        SELECT ROUND(SUM(CASE WHEN quarter = 4 THEN order_count ELSE 0 END) * 100.0
                     / SUM(order_count), 2) AS q4_share_pct,
               ROUND(SUM(CASE WHEN quarter <> 4 THEN order_count ELSE 0 END) * 100.0
                     / SUM(order_count), 2) AS other_share_pct
        FROM mart_time_pattern
    """
    print(pd.read_sql_query(q, conn).to_string(index=False))
    q = """
        SELECT year, ROUND(SUM(CASE WHEN am_pm = 'PM' THEN order_count ELSE 0 END) * 100.0
                           / SUM(order_count), 2) AS pm_share_pct
        FROM mart_time_pattern GROUP BY year ORDER BY year
    """
    print(pd.read_sql_query(q, conn).to_string(index=False))

    print("\n[8] Kiểm chứng dữ liệu gốc là nhiễu ngẫu nhiên (gap G15)")
    q = """
        SELECT MIN(order_share_pct) AS min_share, MAX(order_share_pct) AS max_share,
               ROUND(AVG(avg_order_value), 2) AS avg_order_value
        FROM mart_payment_profile
    """
    r = pd.read_sql_query(q, conn).iloc[0]
    print(f"    Tỷ trọng đơn theo loại thẻ : {r['min_share']}% - {r['max_share']}%"
          f"  (lệch rất nhỏ -> phân bố đều)")
    print(f"    Giá trị đơn trung bình     : ${r['avg_order_value']}")
    q = "SELECT MIN(avg_order_value) AS lo, MAX(avg_order_value) AS hi FROM mart_buyer_persona"
    r = pd.read_sql_query(q, conn).iloc[0]
    print(f"    Đơn TB theo nhóm nghề      : ${r['lo']} - ${r['hi']}  (gần như bằng nhau)")


def main() -> None:
    force_utf8_stdout()

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Chưa có database: {DB_PATH}\nChạy trước: python -m src.etl.build_db"
        )

    FIGURES.mkdir(parents=True, exist_ok=True)

    mart_files = sorted(MART_DIR.glob("*.sql"))
    line = "=" * 78

    conn = sqlite3.connect(DB_PATH)
    try:
        print(line)
        print(f"CHẠY {len(mart_files)} MẢNG PHÂN TÍCH (GIAI ĐOẠN 6)")
        print(line)

        total_charts = 0
        for i, path in enumerate(mart_files, start=1):
            name = mart_name_from_path(path)
            df = build_mart(conn, name, path)
            df.to_csv(DATA_PROCESSED / f"{name}.csv", index=False)

            specs = CHART_SPECS.get(name, [])
            for spec in specs:
                make_chart(df, spec, FIGURES / f"{spec['fname']}.png")
            total_charts += len(specs)

            print(f"\n[{i}/{len(mart_files)}] {name}")
            print(f"    {len(df):,} dòng x {df.shape[1]} cột  |  {len(specs)} chart")

        # Chart riêng cho bảng chất lượng dữ liệu
        dq = pd.read_sql_query("SELECT * FROM mart_data_quality", conn)
        for spec in CHART_SPECS.get("mart_data_quality", []):
            make_chart(dq, spec, FIGURES / f"{spec['fname']}.png")
            total_charts += 1

        headline_findings(conn)

        print("\n" + line)
        print(f"TỔNG KẾT: {len(mart_files)} bảng mart, {total_charts} chart")
        print(line)
    finally:
        conn.close()

    print(f"\nCSV  : {DATA_PROCESSED}")
    print(f"Chart: {FIGURES}")


if __name__ == "__main__":
    main()
