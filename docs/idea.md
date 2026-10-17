# IDEA — Supplier & Supply-Chain Analytics

**Trạng thái:** v0.3 — scope đã chốt
**Stack:** Python (pandas) + SQLite (SQL thuần cho phần phân tích)
**Ngôn ngữ:** tài liệu tiếng Việt; tên bảng, tên cột và code dùng tiếng Anh

---

## 1. Tóm tắt ý tưởng

Dự án **Data Analytics end-to-end** về hiệu quả chuỗi cung ứng / nhà cung cấp.

- **Phía CẦU (demand - dữ liệu thật):** dataset *Ecommerce Purchases* (Kaggle) — 10.000 giao dịch của người mua.
- **Phía CUNG (supply - synthetic, có ghi chú rõ):** lớp nhà cung cấp được thêm vào
  (suppliers, products, shipments) để có thể tính được các chỉ số KPI của supplier.
- **Lưu trữ:** SQLite warehouse (`supply_chain.db`), chia lớp `raw → staging → dim/fact → mart`.
- **Xử lý:** Python cho ETL, SQL cho phân tích.
- **Output:** các **mảng phân tích tách riêng**, mỗi mảng ghi ra 1 bảng `mart_*` + CSV + chart PNG.

**Mục tiêu:** chứng minh kỹ năng *data modeling + ETL + SQL analytics* trên một bài toán
chuỗi cung ứng — chứ không chỉ là EDA một file CSV.

---

## 2. Các quyết định đã chốt

| # | Quyết định | Lựa chọn |
|---|---|---|
| D1 | Nguồn dữ liệu supplier | **Giữ file gốc làm phía DEMAND; thêm lớp SUPPLY synthetic** |
| D2 | Mục đích dự án | Học tập / portfolio (được dùng dữ liệu synthetic, kèm disclaimer) |
| D3 | Hình thức thực thi | **Cả hai** — package Python tái sử dụng trong `src/` + notebook cho EDA & trình bày |
| D4 | Output cuối | SQL + CSV + chart PNG |
| D5 | Ngôn ngữ | Docs tiếng Việt; tên bảng/cột + code tiếng Anh |

### Vì sao chọn D1 (phần quan trọng)

Dataset gốc **không có entity nhà cung cấp**. Cột `Company` là **công ty của người mua**,
tức nó thuộc phía cầu. Coi `Company` là supplier sẽ là **sai logic**.

Thay vào đó:

```
10.000 dòng gốc  ->  fact_purchases   (demand, giữ nguyên)
                     + dim_product    (mỗi product -> đúng 1 primary supplier)
                     + dim_supplier   (synthetic)
                     + fact_shipments (synthetic: ngày giao, delay, defect)
```

Cách này giữ nguyên dữ liệu thật, đồng thời dùng `Company` **đúng nghĩa**
như một dimension khách hàng B2B, mà vẫn có đủ dữ liệu để phân tích supplier.

---

## 3. Nguồn dữ liệu

Notebook bro gửi: <https://www.kaggle.com/code/peiranliu/ecommerce-purchases-analysis>

Notebook chạy trên dataset **"Ecommerce Purchases"** (có nhiều mirror trên Kaggle):

- `utkarsharya/ecommerce-purchases`
- `vladmarascu/ecommerce-purchases-csv`
- `ahmedashrafahmed/ecommerce-purchases`

| Thuộc tính | Giá trị |
|---|---|
| Số dòng | 10.000 |
| Số cột | 14 |
| Dung lượng | ~2.75 MB (CSV) |
| Bản chất | **Dữ liệu tổng hợp (synthetic), không phải giao dịch thật** |
| License | Unknown |

Danh sách cột:
`Address`, `Lot`, `AM or PM`, `Browser Info`, `Company`, `Credit Card`,
`CC Exp Date`, `CC Security Code`, `CC Provider`, `Email`, `Job`,
`IP Address`, `Language`, `Purchase Price`

### ✅ Đã tải & kiểm tra thực tế (2026-10-17)

File đã có tại `data/raw/Ecommerce Purchases.csv` (tải từ mirror GitHub, không cần tài khoản Kaggle).
Kết quả kiểm tra khớp mong đợi: **10.000 dòng × 14 cột, 0 null**.
Ba phát hiện làm thay đổi thiết kế — chi tiết ở `docs/data_dictionary.md`:

1. **`Purchase Price` chỉ 0.00 – 99.99** (mean 50.35), không phải 0–1000 như giả định ban đầu.
2. **`Address` xuống 2 dòng** trong 1 ô CSV; dòng 2 là `City, ST ZIP` → quy tắc parse đã chốt.
3. **Mọi cột gốc phân bố đều (uniform)** — dữ liệu là nhiễu ngẫu nhiên, không có
   tương quan thật. Vì vậy các mảng chỉ dùng dữ liệu gốc sẽ ra biểu đồ phẳng;
   đó là kết quả trung thực, không phải lỗi.

---

## 4. Mổ xẻ từng cột

| Cột | Ý nghĩa thật | Dùng được cho supply chain? |
|---|---|---|
| `Company` | **Công ty nơi người mua làm việc** — KHÔNG phải nhà cung cấp | Có, nhưng như một **tài khoản khách hàng B2B** |
| `Email` | Email người mua; domain là free mail hoặc domain công ty | Yếu; domain **không khớp** với `Company` |
| `Job` | Chức danh người mua | Có -> **persona / vai trò mua hàng** |
| `Address` | Địa chỉ free text (có city/state/zip) | Có -> **địa lý** (cần parse) |
| `Purchase Price` | Giá trị đơn hàng | Có -> **spend / monetary** |
| `AM or PM` | Buổi mua hàng | Có -> **pattern theo thời điểm** |
| `CC Provider` | JCB / Discover / Mastercard / Visa | Có -> **kênh thanh toán & rủi ro** |
| `Browser Info` | User agent | Có -> **kênh / thiết bị** |
| `Language` | en, fr, pt... | Ít giá trị |
| `IP Address` | Địa chỉ IP | Ít giá trị (trừ khi geo-IP) |
| `Lot` | Chuỗi ngẫu nhiên (9.822/10.000 unique) | Không — nhiễu |
| `Credit Card`, `CC Exp Date`, `CC Security Code` | **Dữ liệu thẻ (PII)** | **Không — phải drop / mask** |

> **Kết luận thẳng thắn:** file này không chứa bất kỳ dữ liệu nhà cung cấp nào.
> Không có `supplier_id`, không product, không ngày giao hàng, không lead time, không tồn kho.
> Vì vậy các khoảng trống ở mục 5 là bắt buộc phải xử lý.

---

## 5. Gap analysis — các khuyết điểm & cách bù

| # | Khuyết điểm | Ảnh hưởng | Cách xử lý |
|---|---|---|---|
| G1 | Không có entity supplier | Thiếu phần cốt lõi của dự án | Tạo `dim_supplier` synthetic |
| G2 | Không có product / SKU | Không map được "mua cái gì -> từ supplier nào" | Tạo `dim_product` synthetic; phân bổ product theo phân khúc `Purchase Price` để mô hình có ý nghĩa |
| G3 | Không có ngày giao dịch (chỉ có `AM or PM`) | Không làm được time series, seasonality, lead time, OTD | Sinh `order_date` synthetic (ví dụ 2023–2025) |
| G4 | Không có quantity / cost price | Không tính được margin, không đánh giá hiệu quả chi phí | Sinh `quantity` + `unit_cost`; `margin = price - qty*unit_cost` |
| G5 | Không có shipment / logistics | Không đo được on-time, defect, fill rate | Tạo `fact_shipments` (delivery_date, status, delay_days) |
| G6 | Không có đánh giá supplier | Không làm được scorecard / ranking | Tính KPI: `on_time_rate`, `defect_rate`, `avg_lead_time` |
| G7 | Dữ liệu synthetic, license "Unknown" | Không thể kết luận về thị trường thật | Thêm **disclaimer** trong README và mọi report |
| G8 | PII: credit card, IP, email | Rủi ro pháp lý / đạo đức nếu publish | Drop 3 cột thẻ; hash/mask email và IP ở tầng staging |
| G9 | `Address` là free text | Không group theo địa lý được | Parse regex -> `city`, `state`, `zip`; tạo `dim_location` |
| G10 | `Company` ≠ email domain | Dễ phân tích sai nếu nhầm | Ghi rõ trong data dictionary; chỉ coi `Company` là buyer org |
| G11 | Trùng lặp & nhiễu (`Lot`, số thẻ lặp) | Sai lệch khi count | Data quality report + quy tắc dedupe ở staging |
| G12 | Chỉ 1 bảng phẳng | Chưa phải data warehouse | Chuẩn hoá thành star schema (mục 6) |
| G13 | Không có test / kiểm soát chất lượng | Pipeline dễ hỏng âm thầm | Thêm `src/etl/validate.py` (check null, range, row count) |
| G14 | Không phân tách được các "mảng" | Mục tiêu "phân tích riêng từng mảng" không đạt | Mỗi mảng phân tích có 1 bảng `mart_*` riêng |
| G15 | **Mọi cột gốc phân bố đều (uniform)** — dữ liệu là nhiễu ngẫu nhiên, không có tương quan thật | ~4/9 mảng chỉ dùng dữ liệu gốc (Payment, Channel, Time, Language) sẽ ra **biểu đồ phẳng** | Ghi rõ trong report; tách "mảng có tín hiệu" (dùng lớp supply synthetic) vs "mảng không có tín hiệu" |
| G16 | `Company` có nhóm trùng nhưng **yếu** — công ty nhiều đơn nhất chỉ 15 đơn / 10.000 | Mảng B2B không đủ mạnh để kết luận | Hạ kỳ vọng mảng B2B xuống mức "mô tả", không đưa ra kết luận |

---

## 6. Thiết kế dữ liệu (SQLite star schema)

```
-- Dimension
dim_date(date_sk, order_date, day, month, quarter, year, is_weekend)
dim_location(location_sk, city, state, zip)
dim_customer(customer_sk, company_name, email_masked, job_title, job_family, language)
dim_product(product_sk, product_name, category, unit_cost, list_price, primary_supplier_id)
dim_supplier(supplier_sk, supplier_name, country, tier, category_focus, contract_start, is_dual_source)

-- Fact
fact_purchases(purchase_id, customer_sk, product_sk, supplier_sk, date_sk, location_sk,
               purchase_price, quantity, am_pm, cc_provider, browser_family, device_type)
fact_shipments(shipment_id, purchase_id, supplier_sk, ship_date, delivery_date,
               delay_days, status, defect_flag, units_shipped)

-- Mart (mỗi mảng phân tích 1 bảng)
mart_supplier_scorecard(supplier_id, on_time_rate, defect_rate, avg_lead_time,
                        total_spend, order_count, abc_class, xyz_class)
mart_supplier_concentration(supplier_id, spend_share, category_count, single_source_risk)
mart_product_supplier(category, supplier_id, spend, order_count, dependency_ratio)
mart_b2b_customer(company_name, order_count, total_spend, avg_order_value, segment)
mart_geo_demand(state, city, order_count, total_spend, supplier_count)
mart_payment_profile(cc_provider, order_count, avg_price, high_value_share)
mart_channel_mix(browser_family, device_type, order_count, avg_price)
mart_time_pattern(am_pm, day_of_week, order_count, total_spend)
mart_buyer_persona(job_family, order_count, total_spend, avg_order_value)
mart_data_quality(rule_name, total_rows, failed_rows, pass_rate)
```

**Nguyên tắc:** `stg_*` giữ nguyên 10.000 dòng gốc và mọi thống kê của nó.
Lớp synthetic chỉ **thêm** bảng/cột — **không bao giờ** ghi đè giá trị gốc.
Điều này giữ cho dự án trung thực khi trình bày.

### Giả định khi sinh dữ liệu synthetic (chi tiết ở `docs/assumptions.md`)

- 35–40 suppliers thuộc nhiều category; mỗi product có 1 primary supplier,
  một số có thêm secondary supplier (dual-source).
- Đơn hàng thừa hưởng supplier của product tương ứng.
- Lead time và delay được sinh theo tier của supplier; supplier tier thấp có
  on-time / defect kém hơn — nhờ vậy scorecard mới có sự phân hoá để phân tích.
- Mọi dữ liệu synthetic đều được đánh dấu (`is_synthetic` hoặc prefix `synth_`).

---

## 7. Các mảng phân tích

1. **Supplier Performance** 🟢 — scorecard: on-time rate, defect rate, lead time, ABC/XYZ.
2. **Supplier Spend & Concentration** 🟢 — Pareto, rủi ro phụ thuộc 1 supplier (single-source risk).
3. **Product–Supplier Mapping** 🟢 — category nào phụ thuộc supplier nào.
4. **B2B Customer Accounts** 🟡 — `Company`: top tài khoản, giá trị đơn trung bình (tín hiệu yếu).
5. **Geographic Demand vs Supply** 🟡 — bang nào cầu lớn nhưng ít supplier phục vụ.
6. **Payment & Risk** ⚪ — phân bố `CC Provider`, tỷ trọng đơn giá cao.
7. **Channel & Time Pattern** ⚪ — `Browser Info` + `AM or PM`.
8. **Buyer Persona** ⚪ — `Job`: nhóm chức danh nào mua gì.
9. **Data Quality Report** 📋 — minh bạch điểm yếu của dữ liệu.

**Chú thích mức tín hiệu:**

| Ký hiệu | Nghĩa |
|---|---|
| 🟢 | Có tín hiệu thật — phân tích ra kết luận được (nhờ lớp supply synthetic) |
| 🟡 | Tín hiệu yếu — chỉ nên mô tả, không kết luận |
| ⚪ | **Không có tín hiệu** — cột gốc phân bố đều, biểu đồ sẽ phẳng. Vẫn làm để minh hoạ phương pháp và thể hiện sự trung thực |
| 📋 | Báo cáo kiểm tra chất lượng |

> Vì mọi cột gốc là nhiễu ngẫu nhiên (gap G15), 3 mảng ⚪ sẽ ra kết quả
> "không có gì đặc biệt". **Đó chính là kết luận đúng** — và việc dám báo cáo
> điều đó tốt hơn là bịa ra insight không tồn tại.

---

## 8. Cấu trúc thư mục

```
supplier-analytics/
├── docs/
│   ├── idea.md                 <- file này
│   ├── data_dictionary.md
│   └── assumptions.md          (giả định sinh dữ liệu synthetic)
├── data/
│   ├── raw/                    (Ecommerce Purchases.csv — không commit)
│   └── processed/              (supply_chain.db)
├── sql/
│   ├── schema.sql
│   ├── 01_staging.sql
│   ├── 02_marts.sql
│   └── 03_analysis/*.sql       (mỗi mảng 1 file)
├── src/
│   ├── etl/
│   │   ├── load_raw.py
│   │   ├── clean.py
│   │   ├── synth_supply.py
│   │   ├── build_db.py
│   │   └── validate.py
│   └── analysis/
│       └── run_marts.py
├── notebooks/                  (EDA + trình bày)
├── reports/figures/
└── README.md
```

---

## 9. Roadmap

| Phase | Việc | Output |
|---|---|---|
| 0 | Chốt scope + tải dataset | `data/raw/*.csv` |
| 1 | ETL: làm sạch, parse address, mask PII | `stg_*` |
| 2 | Sinh lớp supply + kiểm tra chất lượng | `dim_*`, `fact_*` |
| 3 | Viết SQL marts | `mart_*` |
| 4 | 9 mảng phân tích + chart | CSV + PNG trong `reports/` |
| 5 | README + data dictionary + disclaimer | repo hoàn chỉnh |

---

## 10. Việc còn để ngỏ

- [ ] Tải `Ecommerce Purchases.csv` vào `data/raw/` (cần đăng nhập Kaggle).
- [ ] Xác nhận các giả định sinh dữ liệu trong `docs/assumptions.md`.
- [ ] Cân nhắc Phase 2: so sánh với một dataset supply chain thật
      (ví dụ DataCo Smart Supply Chain).
