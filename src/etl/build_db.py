"""Giai đoạn 4 — Dựng database SQLite từ các file CSV đã sinh.

Đầu vào : sql/schema.sql + data/processed/*.csv
Đầu ra  : data/processed/supply_chain.db

Chạy:
    python -m src.etl.build_db
"""

from __future__ import annotations

import sqlite3

import pandas as pd

from .config import DATA_PROCESSED, DB_PATH, PROJECT_ROOT
from .util import force_utf8_stdout

SCHEMA_SQL = PROJECT_ROOT / "sql" / "schema.sql"

# Thứ tự nạp phải tôn trọng khoá ngoại: dimension trước, fact sau.
LOAD_ORDER = [
    "dim_supplier",
    "dim_customer",
    "dim_location",
    "dim_date",
    "dim_product",       # FK -> dim_supplier
    "stg_purchases",
    "fact_purchases",    # FK -> dim_product, dim_supplier, dim_date, dim_customer, dim_location
    "fact_shipments",    # FK -> fact_purchases, dim_supplier
]


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL.read_text(encoding="utf-8"))
    conn.commit()


def table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]


def load_table(conn: sqlite3.Connection, table: str) -> int:
    """Nạp 1 file CSV vào bảng, tự sắp xếp lại cột theo đúng schema."""
    csv_path = DATA_PROCESSED / f"{table}.csv"
    df = pd.read_csv(csv_path)

    cols = table_columns(conn, table)
    missing = set(cols) - set(df.columns)
    if missing:
        raise ValueError(f"{table}: CSV thiếu cột {sorted(missing)}")

    # Sắp theo thứ tự bảng + đổi NaN của pandas thành NULL của SQLite
    df = df.reindex(columns=cols).astype(object)
    df = df.where(pd.notna(df), None)

    placeholders = ", ".join("?" * len(cols))
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
    conn.executemany(sql, list(df.itertuples(index=False, name=None)))
    conn.commit()
    return len(df)


def main() -> None:
    force_utf8_stdout()

    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Đã xoá database cũ: {DB_PATH.name}")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        create_schema(conn)
        print(f"Đã tạo schema từ {SCHEMA_SQL.name}\n")

        for table in LOAD_ORDER:
            n = load_table(conn, table)
            print(f"  -> {table:<16} {n:>7,} dòng")

        line = "=" * 68
        print()
        print(line)
        print("BÁO CÁO DATABASE (GIAI ĐOẠN 4)")
        print(line)

        # 1. Kiểm tra khoá ngoại
        print("\n[1] Kiểm tra khoá ngoại (foreign_key_check)")
        fk = conn.execute("PRAGMA foreign_key_check").fetchall()
        print(f"    Vi phạm: {len(fk)}  {'OK' if not fk else fk[:5]}")

        # 2. Kiểm tra integrity
        print("\n[2] Kiểm tra toàn vẹn (integrity_check)")
        print(f"    {conn.execute('PRAGMA integrity_check').fetchone()[0]}")

        # 3. Kích thước các bảng
        print("\n[3] Bảng trong database")
        rows = conn.execute(
            "SELECT name, type FROM sqlite_master "
            "WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY type, name"
        ).fetchall()
        for name, kind in rows:
            n = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            print(f"    {kind:<6} {name:<16} {n:>7,} dòng")

        # 4. Số index
        n_idx = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'index' AND name LIKE 'idx_%'"
        ).fetchone()[0]
        print(f"\n[4] Index đã tạo: {n_idx}")

        # 5. Truy vấn thử: top 5 supplier theo chi tiêu
        print("\n[5] Truy vấn thử — Top 5 supplier theo tổng chi tiêu")
        q = """
            SELECT s.supplier_id,
                   s.supplier_name,
                   s.tier,
                   s.country,
                   COUNT(*)                    AS orders,
                   ROUND(SUM(p.purchase_price), 2) AS total_spend
            FROM fact_purchases p
            JOIN dim_supplier  s ON s.supplier_id = p.supplier_id
            GROUP BY s.supplier_id
            ORDER BY total_spend DESC
            LIMIT 5
        """
        print(pd.read_sql_query(q, conn).to_string(index=False))

        # 6. Truy vấn thử: độ trễ trung bình theo tier
        print("\n[6] Truy vấn thử — Hiệu suất giao hàng theo tier")
        q2 = """
            SELECT s.tier,
                   COUNT(*)                                        AS shipments,
                   ROUND(AVG(f.actual_lead_days), 2)               AS avg_lead_days,
                   ROUND(AVG(CASE WHEN f.delay_days = 0 THEN 1.0 ELSE 0.0 END) * 100, 2) AS on_time_pct,
                   ROUND(AVG(f.defect_flag) * 100, 2)              AS defect_pct
            FROM fact_shipments f
            JOIN dim_supplier   s ON s.supplier_id = f.supplier_id
            WHERE f.status IN ('delivered', 'delayed')
            GROUP BY s.tier
            ORDER BY s.tier
        """
        print(pd.read_sql_query(q2, conn).to_string(index=False))
        print(line)
    finally:
        conn.close()

    print(f"\nĐã ghi: {DB_PATH}")


if __name__ == "__main__":
    main()
