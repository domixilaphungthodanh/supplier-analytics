"""Giai đoạn 3 — Sinh lớp dữ liệu supply chain (SYNTHETIC).

Đầu vào : data/processed/stg_purchases.csv   (10.000 dòng đã làm sạch)
Đầu ra  : data/processed/
            dim_supplier.csv, dim_product.csv, dim_customer.csv,
            dim_location.csv, dim_date.csv,
            fact_purchases.csv, fact_shipments.csv

Thông số khớp với docs/assumptions.md:
  - 35 suppliers, 3 tier (on-time 96% / 90% / 80%)
  - 120 products / 10 category, mỗi product 1 primary supplier, 20% có secondary
  - order_date trong 2023-2025, Q4 cao hơn 30%
  - Purchase Price KHÔNG BAO GIỜ bị sửa

Chạy:
    python -m src.etl.synth_supply
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DATA_PROCESSED, RANDOM_SEED, STG_PURCHASES_CSV
from .util import force_utf8_stdout

# --- Thông số sinh dữ liệu ---------------------------------------------------

N_SUPPLIERS = 35
N_PER_CATEGORY = 12          # 10 category x 12 = 120 products
DUAL_SOURCE_SHARE = 0.20     # 20% product có secondary supplier
SECONDARY_USED_RATE = 0.15   # 15% đơn dùng secondary supplier
P_CANCELLED = 0.012          # 1.2% đơn bị huỷ
PROMISED_IN_TRANSIT_START = "2025-12-01"   # đơn từ mốc này coi như đang vận chuyển

# Phạm vi sinh: 2023-01-01 .. 2025-12-31
DATE_START = "2023-01-01"
DATE_END = "2025-12-31"

# Q4 cao hơn 30% so với các quý khác: 3x + 1.3x = 1  ->  x = 0.2325
QUARTER_WEIGHTS = np.array([0.2325, 0.2325, 0.2325, 0.3025])

# Hiệu suất theo tier (khớp docs/assumptions.md A1)
SUPPLIER_TIERS = {
    1: {"on_time_rate": 0.96, "defect_rate": 0.005, "promised_lead_days": 10, "min_lead_days": 5},
    2: {"on_time_rate": 0.90, "defect_rate": 0.015, "promised_lead_days": 16, "min_lead_days": 10},
    3: {"on_time_rate": 0.80, "defect_rate": 0.040, "promised_lead_days": 25, "min_lead_days": 18},
}
TIER_PROBS = [0.34, 0.37, 0.29]

COUNTRY_PROBS = {
    "United States": 0.45,
    "China": 0.20,
    "Vietnam": 0.10,
    "Germany": 0.10,
    "India": 0.05,
    "Mexico": 0.05,
    "Japan": 0.05,
}

SUPPLIER_PREFIXES = [
    "Delta", "Vertex", "Northwind", "Apex", "Blue Ridge", "Orion", "Pacific",
    "Summit", "Atlas", "Zenith", "Crescent", "Ironwood", "Lighthouse",
    "Meridian", "Nova", "Pioneer", "Redwood", "Silverline", "Titan", "Upland",
    "Vanguard", "Westfield", "Yellowstone", "Aurora", "Beacon", "Cobalt",
    "Driftwood", "Everest", "Falcon", "Granite", "Harbor", "Ivory", "Juniper",
    "Keystone", "Larkspur",
]
SUPPLIER_SUFFIXES = [
    "Components", "Trading Co.", "Industries", "Supply Group", "Logistics",
    "Manufacturing", "Traders", "Global Sourcing", "Materials", "Distribution",
]

# 10 category x 12 sản phẩm
CATEGORY_PRODUCTS: dict[str, list[str]] = {
    "Electronics": [
        "Wireless Keyboard", "Bluetooth Speaker", "USB-C Hub",
        "Noise-Cancelling Headphones", "Portable Charger", "Webcam 1080p",
        "Mechanical Mouse", "SSD 1TB", "Monitor Stand", "Smart Plug",
        "Laptop Sleeve", "HDMI Cable",
    ],
    "Apparel": [
        "Cotton T-Shirt", "Denim Jacket", "Running Shorts", "Wool Socks",
        "Rain Jacket", "Baseball Cap", "Fleece Hoodie", "Chino Trousers",
        "Leather Belt", "Linen Shirt", "Puffer Vest", "Canvas Sneakers",
    ],
    "Home": [
        "Ceramic Mug Set", "Bamboo Cutting Board", "Table Lamp",
        "Throw Blanket", "Storage Basket", "Wall Clock", "Cushion Cover",
        "Floor Mat", "Spice Rack", "Laundry Hamper", "Picture Frame",
        "Scented Candle",
    ],
    "Office": [
        "A4 Notebook", "Gel Pen Pack", "Desk Organiser", "Stapler",
        "Whiteboard Marker", "Filing Box", "Ergonomic Footrest",
        "Label Printer", "Paper Shredder", "Desk Pad", "Binder Set",
        "Sticky Notes",
    ],
    "Beauty": [
        "Face Cleanser", "Moisturising Cream", "Lip Balm", "Hair Shampoo",
        "Body Lotion", "Sunscreen SPF50", "Nail Care Kit", "Beard Oil",
        "Facial Serum", "Hand Cream", "Makeup Brush Set", "Bath Salts",
    ],
    "Sports": [
        "Yoga Mat", "Resistance Bands", "Water Bottle 1L", "Jump Rope",
        "Dumbbell Set", "Foam Roller", "Cycling Gloves", "Gym Bag",
        "Tennis Balls", "Football", "Swim Goggles", "Fitness Tracker",
    ],
    "Toys": [
        "Building Blocks", "Puzzle 1000pc", "Remote Control Car",
        "Plush Teddy Bear", "Board Game", "Art & Craft Kit", "Toy Train Set",
        "Action Figure", "Science Kit", "Play Dough Set", "Doll House", "Kite",
    ],
    "Auto": [
        "Engine Oil 5W-30", "Car Vacuum", "Phone Mount", "Tyre Inflator",
        "Microfibre Cloths", "Jump Starter", "Seat Cover", "Dash Cam",
        "Windscreen Cover", "Car Wax", "Funnel Set", "Tyre Pressure Gauge",
    ],
    "Grocery": [
        "Olive Oil 1L", "Basmati Rice 5kg", "Coffee Beans 1kg",
        "Green Tea Box", "Honey Jar", "Pasta Pack", "Almonds 500g",
        "Dark Chocolate Bar", "Tomato Sauce", "Breakfast Cereal",
        "Peanut Butter", "Sparkling Water 12pk",
    ],
    "Books": [
        "Business Strategy Guide", "Cookbook", "Sci-Fi Novel",
        "Self-Help Handbook", "History Atlas", "Children's Storybook",
        "Programming Manual", "Travel Guide", "Poetry Collection",
        "Photography Guide", "Language Workbook", "Puzzle Book",
    ],
}

CATEGORIES = list(CATEGORY_PRODUCTS.keys())


# --- Sinh dimension ---------------------------------------------------------


def build_suppliers(rng: np.random.Generator) -> pd.DataFrame:
    """35 suppliers. 10 supplier đầu được gán cứng 1 category để đảm bảo
    mọi category đều có ít nhất 1 supplier."""
    tiers = rng.choice([1, 2, 3], size=N_SUPPLIERS, p=TIER_PROBS)
    countries = rng.choice(
        list(COUNTRY_PROBS.keys()), size=N_SUPPLIERS, p=list(COUNTRY_PROBS.values())
    )

    focuses: list[str] = []
    for i in range(N_SUPPLIERS):
        if i < len(CATEGORIES):
            focuses.append(CATEGORIES[i])
        else:
            focuses.append(CATEGORIES[rng.integers(0, len(CATEGORIES))])

    contract_start = pd.to_datetime("2018-01-01") + pd.to_timedelta(
        rng.integers(0, 1826, size=N_SUPPLIERS), unit="D"
    )

    df = pd.DataFrame(
        {
            "supplier_id": [f"SUP-{i:03d}" for i in range(1, N_SUPPLIERS + 1)],
            "supplier_name": [
                f"{SUPPLIER_PREFIXES[i]} {SUPPLIER_SUFFIXES[i % len(SUPPLIER_SUFFIXES)]}"
                for i in range(N_SUPPLIERS)
            ],
            "country": countries,
            "tier": tiers,
            "category_focus": focuses,
            "contract_start": contract_start.strftime("%Y-%m-%d"),
            "is_dual_source": 0,
            "is_synthetic": 1,
        }
    )
    return df


def build_products(rng: np.random.Generator, suppliers: pd.DataFrame) -> pd.DataFrame:
    """120 products, mỗi product có 1 primary supplier, 20% có secondary."""
    rows = []
    pid = 1
    for category, names in CATEGORY_PRODUCTS.items():
        pool = suppliers.loc[suppliers["category_focus"] == category, "supplier_id"].tolist()
        if not pool:  # phòng trường hợp category chưa có supplier
            pool = suppliers["supplier_id"].tolist()

        for name in names[:N_PER_CATEGORY]:
            primary = pool[rng.integers(0, len(pool))]
            has_dual = rng.random() < DUAL_SOURCE_SHARE
            secondary = None
            if has_dual:
                other = [s for s in pool if s != primary]
                if not other:
                    # category chỉ có 1 supplier -> lấy supplier khác bất kỳ
                    other = [s for s in suppliers["supplier_id"] if s != primary]
                if other:
                    secondary = other[rng.integers(0, len(other))]
                else:
                    has_dual = False

            list_price = round(float(rng.uniform(3.0, 45.0)), 2)
            unit_cost = round(list_price * float(rng.uniform(0.60, 0.80)), 2)

            rows.append(
                {
                    "product_id": f"PRD-{pid:03d}",
                    "product_name": name,
                    "category": category,
                    "list_price": list_price,
                    "unit_cost": unit_cost,
                    "primary_supplier_id": primary,
                    "secondary_supplier_id": secondary,
                    "is_dual_source": int(has_dual),
                    "is_synthetic": 1,
                }
            )
            pid += 1
    return pd.DataFrame(rows)


def build_order_dates(rng: np.random.Generator, n: int) -> pd.Series:
    """order_date trong 2023-2025, Q4 cao hơn 30%."""
    quarters = pd.period_range("2023Q1", "2025Q4", freq="Q")
    p = np.tile(QUARTER_WEIGHTS, len(quarters) // 4)
    p = p / p.sum()

    starts = quarters.start_time.values.astype("datetime64[D]")
    ends = quarters.end_time.values.astype("datetime64[D]")
    days_in_q = (ends - starts).astype("int64") + 1

    q = rng.choice(len(quarters), size=n, p=p)
    offsets = rng.integers(0, days_in_q[q])
    return pd.Series(starts[q] + offsets.astype("timedelta64[D]")).dt.normalize()


# --- Sinh fact --------------------------------------------------------------


def build_facts(
    rng: np.random.Generator,
    stg: pd.DataFrame,
    suppliers: pd.DataFrame,
    products: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sinh fact_purchases và fact_shipments."""
    n = len(stg)

    # 1. Chọn product sao cho list_price <= purchase_price (để quantity >= 1)
    #    Sắp xếp theo giá tăng dần rồi dùng searchsorted -> chọn ngẫu nhiên trong
    #    tập ứng viên.
    prod_sorted = products.sort_values("list_price").reset_index(drop=True)
    lp = prod_sorted["list_price"].to_numpy()
    prices = stg["purchase_price"].to_numpy()

    n_candidates = np.searchsorted(lp, prices, side="right")
    pick = rng.integers(0, np.maximum(n_candidates, 1))
    pick = np.where(n_candidates > 0, pick, 0)          # giá < 3 -> lấy rẻ nhất
    chosen = prod_sorted.iloc[pick].reset_index(drop=True)

    # 2. Số lượng: quantity * list_price ~ purchase_price, kẹp [1, 20]
    quantity = np.clip(np.round(prices / chosen["list_price"].to_numpy()), 1, 20).astype(int)

    # 3. Ngày đặt hàng
    order_date = build_order_dates(rng, n)

    # 4. Supplier của đơn: primary, 15% dùng secondary nếu có
    supplier_ids = chosen["primary_supplier_id"].to_numpy().copy()
    has_secondary = chosen["secondary_supplier_id"].notna().to_numpy()
    use_secondary = has_secondary & (rng.random(n) < SECONDARY_USED_RATE)
    supplier_ids[use_secondary] = chosen.loc[use_secondary, "secondary_supplier_id"].to_numpy()

    # 5. Thông số tier theo supplier của từng đơn
    sup = suppliers.set_index("supplier_id")
    tier = sup.loc[supplier_ids, "tier"].to_numpy()

    def tier_arr(field: str) -> np.ndarray:
        return np.array([SUPPLIER_TIERS[t][field] for t in tier])

    promised = tier_arr("promised_lead_days")
    min_lead = tier_arr("min_lead_days")
    on_time_rate = tier_arr("on_time_rate")
    defect_rate = tier_arr("defect_rate")

    # 6. Shipment
    ship_date = order_date + pd.to_timedelta(rng.integers(0, 4, size=n), unit="D")

    is_on_time = rng.random(n) < on_time_rate
    actual_lead = np.where(
        is_on_time,
        rng.integers(min_lead, promised + 1),           # giao trong hạn
        promised + rng.integers(1, 11),                 # trễ 1-10 ngày
    )
    delay_days = np.maximum(0, actual_lead - promised)

    delivery_date = ship_date + pd.to_timedelta(actual_lead, unit="D")

    # 7. Status
    cancelled = rng.random(n) < P_CANCELLED
    in_transit = order_date >= pd.Timestamp(PROMISED_IN_TRANSIT_START)

    status = np.where(delay_days == 0, "delivered", "delayed")
    status = np.where(in_transit, "in_transit", status)
    status = np.where(cancelled, "cancelled", status)

    delivery_date = delivery_date.where(~cancelled)
    actual_lead_out = np.where(cancelled, np.nan, actual_lead)
    delay_out = np.where(cancelled, np.nan, delay_days)

    defect_flag = (rng.random(n) < defect_rate).astype(int)
    defect_flag = np.where(cancelled, 0, defect_flag)

    # 8. Bảng fact
    fact_purchases = pd.DataFrame(
        {
            "purchase_id": stg["purchase_id"].to_numpy(),
            "is_synthetic": 0,
            "product_id": chosen["product_id"].to_numpy(),
            "supplier_id": supplier_ids,
            "order_date": order_date.dt.strftime("%Y-%m-%d").to_numpy(),
            "purchase_price": prices,
            "quantity": quantity,
            "am_pm": stg["am_pm"].to_numpy(),
            "cc_provider": stg["cc_provider"].to_numpy(),
            "browser_family": stg["browser_family"].to_numpy(),
            "device_type": stg["device_type"].to_numpy(),
            "price_tier": stg["price_tier"].to_numpy(),
            "is_high_value": stg["is_high_value"].to_numpy(),
            "customer_key": stg["customer_key"].to_numpy(),
            "location_key": (stg["city"] + "|" + stg["state"]).to_numpy(),
        }
    )

    fact_shipments = pd.DataFrame(
        {
            "shipment_id": [f"SHP-{i:05d}" for i in range(1, n + 1)],
            "is_synthetic": 1,
            "purchase_id": stg["purchase_id"].to_numpy(),
            "supplier_id": supplier_ids,
            "ship_date": ship_date.dt.strftime("%Y-%m-%d").to_numpy(),
            "delivery_date": pd.Series(delivery_date).dt.strftime("%Y-%m-%d").to_numpy(),
            "promised_lead_days": promised,
            "actual_lead_days": actual_lead_out,
            "delay_days": delay_out,
            "status": status,
            "defect_flag": defect_flag,
            "units_shipped": quantity,
        }
    )

    return fact_purchases, fact_shipments


def build_dim_customer(stg: pd.DataFrame) -> pd.DataFrame:
    """Khách hàng = `customer_key` (hash của email gốc).

    Lưu ý: KHÔNG dùng `email_masked` làm khoá — nó chỉ để hiển thị.
    """
    dim = (
        stg.sort_values("purchase_id")
        .drop_duplicates(subset=["customer_key"], keep="first")
        [["customer_key", "email_masked", "email_domain", "company_name",
          "job_title", "job_family", "language"]]
        .reset_index(drop=True)
    )
    return dim


def build_dim_location(stg: pd.DataFrame) -> pd.DataFrame:
    """Vị trí ở cấp THÀNH PHỐ (city, state).

    Không dùng (city, state, zip) vì zip là duy nhất cho mỗi dòng
    (9.879/10.000) -> dimension sẽ vô nghĩa.

    `is_military` đánh dấu các địa chỉ DPO/APO/FPO — đây KHÔNG phải thành phố
    thật, nếu không đánh dấu thì phân tích địa lý sẽ bị chúng chi phối.
    """
    MILITARY_STATES = {"AA", "AE", "AP"}
    MILITARY_CITIES = {"DPO", "APO", "FPO"}

    dim = stg[["city", "state"]].drop_duplicates().reset_index(drop=True)
    dim["location_key"] = dim["city"] + "|" + dim["state"]
    dim["is_military"] = (
        dim["state"].isin(MILITARY_STATES) | dim["city"].isin(MILITARY_CITIES)
    ).astype(int)
    return dim[["location_key", "city", "state", "is_military"]]


def build_dim_date(dates: pd.Series) -> pd.DataFrame:
    full = pd.date_range(dates.min(), dates.max(), freq="D")
    df = pd.DataFrame({"date": full})
    df["date_sk"] = df["date"].dt.strftime("%Y%m%d").astype(int)
    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%b")
    df["day"] = df["date"].dt.day
    df["day_of_week"] = df["date"].dt.day_name()
    df["is_weekend"] = (df["date"].dt.dayofweek >= 5).astype(int)
    return df[["date_sk", "date", "year", "quarter", "month", "month_name",
               "day", "day_of_week", "is_weekend"]]


# --- Main -------------------------------------------------------------------


def main() -> None:
    force_utf8_stdout()
    rng = np.random.default_rng(RANDOM_SEED)

    stg = pd.read_csv(STG_PURCHASES_CSV)
    print(f"Đọc stg_purchases: {len(stg):,} dòng")

    suppliers = build_suppliers(rng)
    products = build_products(rng, suppliers)
    fact_purchases, fact_shipments = build_facts(rng, stg, suppliers, products)

    # Cập nhật is_dual_source cho supplier nào có đóng vai secondary
    dual_ids = set(products["secondary_supplier_id"].dropna())
    suppliers["is_dual_source"] = suppliers["supplier_id"].isin(dual_ids).astype(int)

    dim_customer = build_dim_customer(stg)
    dim_location = build_dim_location(stg)

    all_dates = pd.concat(
        [fact_purchases["order_date"], fact_shipments["delivery_date"].dropna()]
    )
    dim_date = build_dim_date(pd.to_datetime(all_dates))

    tables = {
        "dim_supplier": suppliers,
        "dim_product": products,
        "dim_customer": dim_customer,
        "dim_location": dim_location,
        "dim_date": dim_date,
        "fact_purchases": fact_purchases,
        "fact_shipments": fact_shipments,
    }

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        path = DATA_PROCESSED / f"{name}.csv"
        df.to_csv(path, index=False)
        print(f"  -> {name:<16} {len(df):>7,} dòng x {df.shape[1]:>2} cột")

    # --- Báo cáo kiểm tra ---
    line = "=" * 68
    print()
    print(line)
    print("BÁO CÁO SINH DỮ LIỆU SUPPLY CHAIN (GIAI ĐOẠN 3)")
    print(line)

    print("\n[1] Supplier theo tier")
    for t, g in suppliers.groupby("tier"):
        print(f"    Tier {t}: {len(g):>2} supplier  (on-time mục tiêu "
              f"{SUPPLIER_TIERS[t]['on_time_rate']:.0%}, defect {SUPPLIER_TIERS[t]['defect_rate']:.1%})")

    print("\n[2] Product theo category")
    print(f"    {products['category'].nunique()} category, {len(products)} product, "
          f"{products['is_dual_source'].sum()} dual-source ({products['is_dual_source'].mean():.0%})")

    print("\n[3] Status shipment")
    for k, v in fact_shipments["status"].value_counts().items():
        print(f"    {k:<12} {v:>6,}  ({v/len(fact_shipments):.1%})")

    shipped = fact_shipments.merge(
        suppliers[["supplier_id", "tier"]], on="supplier_id", how="left"
    )
    shipped = shipped[shipped["status"].isin(["delivered", "delayed"])]
    score = shipped.groupby("tier").agg(
        on_time_rate=("delay_days", lambda s: (s == 0).mean()),
        defect_rate=("defect_flag", "mean"),
        avg_lead=("actual_lead_days", "mean"),
        orders=("shipment_id", "count"),
    )
    print("\n[4] Hiệu suất THỰC TẾ sinh ra theo tier (đối chiếu mục A1)")
    print(score.to_string(float_format=lambda x: f"{x:,.4f}"))

    merged = fact_purchases.merge(products[["product_id", "list_price", "unit_cost"]], on="product_id")
    merged["revenue"] = merged["quantity"] * merged["list_price"]
    merged["cost"] = merged["quantity"] * merged["unit_cost"]
    margin = 1 - merged["cost"].sum() / merged["revenue"].sum()
    print("\n[5] Kiểm tra tính hợp lý")
    print(f"    quantity: min {fact_purchases['quantity'].min()}, "
          f"max {fact_purchases['quantity'].max()}, "
          f"mean {fact_purchases['quantity'].mean():.2f}")
    print(f"    Sai lệch |qty*list - price| / price: trung vị "
          f"{np.median(np.abs(merged['revenue'] - merged['purchase_price']) / merged['purchase_price']):.1%}")
    print(f"    Margin gộp toàn hệ thống: {margin:.1%}")

    print("\n[6] Bảo toàn dữ liệu gốc")
    same = (fact_purchases["purchase_price"].to_numpy() == stg["purchase_price"].to_numpy()).all()
    print(f"    purchase_price giữ nguyên: {'OK' if same else 'SAI!'}")
    print(f"    Tổng doanh thu gốc: {stg['purchase_price'].sum():,.2f}")
    print(f"    Tổng doanh thu fact: {fact_purchases['purchase_price'].sum():,.2f}")

    print("\n[7] Phân bố theo năm")
    print(fact_purchases.assign(y=pd.to_datetime(fact_purchases['order_date']).dt.year)
          .groupby("y").size().to_string())
    print(line)


if __name__ == "__main__":
    main()
