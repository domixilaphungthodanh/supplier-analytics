"""Cấu hình đường dẫn và hằng số dùng chung cho toàn bộ pipeline.

Mọi module khác import từ đây, không hard-code đường dẫn.
"""

from __future__ import annotations

from pathlib import Path

# --- Đường dẫn ---------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
REPORTS = PROJECT_ROOT / "reports"
FIGURES = REPORTS / "figures"

RAW_CSV = DATA_RAW / "Ecommerce Purchases.csv"
STG_PURCHASES_CSV = DATA_PROCESSED / "stg_purchases.csv"
DB_PATH = DATA_PROCESSED / "supply_chain.db"

# --- Quy tắc làm sạch --------------------------------------------------------

# 3 cột thẻ tín dụng: PII, xoá hoàn toàn, không bao giờ ghi ra output
PII_COLUMNS = ["Credit Card", "CC Exp Date", "CC Security Code"]

# Cột nhiễu, không mang thông tin (9.822 unique / 10.000 dòng)
DROP_COLUMNS = ["Lot"]

# Ngưỡng "đơn giá trị cao". Lưu ý: Purchase Price thực tế chỉ 0.00 - 99.99
HIGH_VALUE_THRESHOLD = 85.0

PRICE_TIER_LABELS = ["bronze", "silver", "gold", "platinum"]

# --- Sinh dữ liệu ------------------------------------------------------------

RANDOM_SEED = 42
