"""Chạy toàn bộ pipeline theo đúng thứ tự.

Cách dùng:
    python run_all.py

Bỏ qua bước 1 vì đó là việc tải dữ liệu thủ công (xem docs/getting_data.md).
"""

from __future__ import annotations

import os
import subprocess
import sys

from src.etl.util import force_utf8_stdout

STEPS = [
    ("Giai đoạn 2 — Làm sạch dữ liệu", "src.etl.clean"),
    ("Giai đoạn 3 — Sinh lớp dữ liệu supply chain", "src.etl.synth_supply"),
    ("Giai đoạn 4 — Dựng database SQLite", "src.etl.build_db"),
    ("Giai đoạn 5 — Kiểm tra chất lượng dữ liệu", "src.etl.validate"),
    ("Giai đoạn 6 — Chạy 9 mảng phân tích", "src.analysis.run_marts"),
]


def main() -> int:
    force_utf8_stdout()
    os.environ["PYTHONIOENCODING"] = "utf-8"

    raw = os.path.join("data", "raw", "Ecommerce Purchases.csv")
    if not os.path.exists(raw):
        print(f"THIẾU DỮ LIỆU: {raw}")
        print("Xem docs/getting_data.md để biết cách tải.")
        return 1

    for i, (label, module) in enumerate(STEPS, start=1):
        print("\n" + "#" * 78)
        print(f"# [{i}/{len(STEPS)}] {label}   (python -m {module})")
        print("#" * 78)
        result = subprocess.run([sys.executable, "-m", module])
        if result.returncode != 0:
            print(f"\nTHẤT BẠI ở bước: {label}")
            return result.returncode

    print("\n" + "#" * 78)
    print("# HOÀN TẤT TOÀN BỘ PIPELINE")
    print("#" * 78)
    print("\nKết quả:")
    print("  data/processed/supply_chain.db   <- database")
    print("  data/processed/mart_*.csv        <- 9 bảng phân tích")
    print("  reports/figures/*.png            <- 14 chart")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
