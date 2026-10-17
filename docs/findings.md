# Kết quả phân tích

Tài liệu này tóm tắt kết quả 9 mảng phân tích. Số liệu sinh ra từ
`python run_all.py` (random seed 42 nên tái lập được).

> ⚠️ **Nhắc lại một lần nữa:** dữ liệu supplier / product / shipment là **SYNTHETIC**
> (do dự án tự sinh theo `docs/assumptions.md`). Dataset gốc cũng là dữ liệu tổng hợp.
> Vì vậy **mọi con số ở đây minh hoạ PHƯƠNG PHÁP, không phải insight thị trường thật.**

---

## 0. Tóm tắt dữ liệu

| Hạng mục | Giá trị |
|---|---|
| Tổng chi tiêu | **$503,473.02** (giữ nguyên 100% từ dữ liệu gốc) |
| Đơn hàng | 10,000 |
| Shipment | 10,000 |
| Nhà cung cấp | 35 (33 hoạt động, 2 không hoạt động) |
| Sản phẩm | 120 (10 category × 12) |
| Khách hàng | 9,954 |
| Khoảng thời gian | 2023-01 → 2025-12 (synthetic) |
| Quy tắc chất lượng | **20/20 ĐẠT** |

---

## 1. Hiệu suất nhà cung cấp (Supplier Scorecard)

**Danh bạ 35 supplier, nhưng chỉ 33 đang hoạt động.** Hai supplier có trong danh bạ
nhưng chưa được gán sản phẩm nào: `Titan Materials` (Grocery), `Aurora Supply Group` (Home).

**Giao trễ nhất:**

| Supplier | Tier | Quốc gia | Shipment | On-time | Defect |
|---|---|---|---|---|---|
| Northwind Industries | 3 | China | 255 | **74.80%** | 3.53% |
| Ironwood Trading Co. | 3 | US | 116 | 75.23% | 4.31% |
| Harbor Components | 3 | China | 233 | 75.56% | 5.15% |

**Đáng tin nhất:**

| Supplier | Tier | Quốc gia | Shipment | On-time | Defect |
|---|---|---|---|---|---|
| Silverline Global Sourcing | 1 | Germany | 176 | **96.95%** | 1.14% |
| Everest Global Sourcing | 1 | China | 341 | 96.58% | 0.29% |
| Zenith Distribution | 2 | Germany | 109 | 96.23% | 1.83% |

→ **Kết luận:** tier dự đoán được chất lượng. Xem `02_supplier_quality_map.png`.

**Phân loại ABC theo chi tiêu:**

| Hạng | Số supplier | Chi tiêu | Tỷ trọng |
|---|---|---|---|
| A | 18 | $399,463.59 | **79.34%** |
| B | 9 | $72,793.84 | 14.46% |
| C | 8 | $31,215.59 | 6.20% |

→ 18/33 supplier (55%) chiếm 79% chi tiêu. Đây là **quy luật Pareto điển hình**.

---

## 2. Tập trung chi tiêu & rủi ro phụ thuộc

**5/10 category bị phụ thuộc >50% vào 1 nhà cung cấp:**

| Category | Supplier độc quyền | Tier | Thị phần |
|---|---|---|---|
| **Office** | Apex Supply Group | 2 | **95.76%** ⚠️ |
| Grocery | Atlas Materials | 1 | 76.26% |
| Auto | Summit Global Sourcing | 3 | 60.36% |
| Apparel | Driftwood Traders | 2 | 54.78% |
| Electronics | Redwood Traders | 2 | 54.52% |

→ **Rủi ro đáng chú ý nhất là Office:** gần như toàn bộ category phụ thuộc vào 1 supplier
tier 2, và 9/12 sản phẩm không có nguồn dự phòng. Nếu supplier này gặp sự cố,
category Office gần như tê liệt.

→ **94/120 sản phẩm (78%) không có supplier dự phòng.**

---

## 3. Sản phẩm & danh mục

- Chi tiêu trải đều trên 10 category (`04_spend_by_category.png`).
- Margin gộp toàn hệ thống: **~29.7%** (theo giả định `unit_cost = 60–80% list_price`).
- Top sản phẩm theo margin: xem `05_product_margin.png`.

---

## 4. Tài khoản khách hàng B2B

| Hạng mục | Giá trị |
|---|---|
| Tài khoản mua 1 lần (`one_off`) | 7,871 (91.4%) |
| Mua lặp lại (`repeat`) | 668 (7.8%) |
| Tài khoản chủ chốt (`key_account`) | 74 (0.9%) |
| Tài khoản lớn nhất | **Brown Ltd** — 15 khách, 16 đơn, $884.78 |

> ⚠️ **Hạn chế (gap G16):** tài khoản lớn nhất chỉ có **16 đơn / 10.000 đơn (0,16%)**.
> Nhóm B2B quá yếu để kết luận — chỉ nên xem như mô tả.

---

## 5. Địa lý: nhu cầu vs độ phủ

- 62 mã "bang" (50 bang + DC + lãnh thổ + địa chỉ quân sự).
- Top theo chi tiêu: xem `07_top_states.png`.
- **Phát hiện:** 5 "thành phố" đứng đầu bảng xếp hạng thực ra là `DPO / APO / FPO` —
  **địa chỉ quân sự, không phải thành phố thật**. Đã thêm cột `is_military` để lọc.
- Tương quan độ phủ vs nhu cầu: `08_state_coverage.png`.

---

## 6–8. Ba mảng KHÔNG có tín hiệu (kết quả trung thực)

Đây là các mảng chỉ dùng dữ liệu gốc — mà dữ liệu gốc là **nhiễu ngẫu nhiên** (gap G15):

| Mảng | Bằng chứng |
|---|---|
| **Payment** | Tỷ trọng đơn theo loại thẻ chỉ dao động **7.67% – 17.16%**, đơn TB $50.5 cho mọi loại thẻ |
| **Channel** | Trình duyệt/thtiết bị phân bố gần đều; 93.8% là desktop |
| **Buyer Persona** | Đơn TB theo nhóm nghề chỉ lệch **$39.0 – $55.07** |

→ **Đây là kết luận đúng, không phải lỗi.** Việc dám báo cáo "không có tín hiệu"
tốt hơn là bịa ra insight không tồn tại.

---

## 9. Mùa vụ (cột synthetic)

| Chỉ số | Giá trị |
|---|---|
| Tỷ trọng đơn Q4 | **30.25%** (các quý khác 69.75%) |
| Tỷ trọng PM | 50.42% – 50.89% mỗi năm |
| Đơn/ngày trung bình | ~9.1 |

→ Q4 cao hơn ~30% đúng như giả định A3. Xem `12_monthly_seasonality.png`.

**Lưu ý:** mùa vụ ở đây là **do mình cài vào**, không phải phát hiện từ dữ liệu.

---

## 10. Chất lượng dữ liệu

**20/20 quy tắc ĐẠT**, gồm các nhóm:
- Đầy đủ: số dòng đúng 10.000 ở cả 3 bảng fact/staging
- Bảo toàn: `purchase_price` không lệch một xu so với dữ liệu gốc
- Duy nhất: 4 khoá chính không trùng
- Miền giá trị: quantity ∈ [1,20], giá ∈ [0,100], status hợp lệ
- Nhất quán: supplier của đơn khớp với product, ngày gửi ≤ ngày giao

Xem `14_data_quality.png` và `data/processed/mart_data_quality.csv`.

---

## Danh sách file kết quả

### CSV (9 mảng + 2 file phụ)

```
data/processed/mart_supplier_scorecard.csv
data/processed/mart_supplier_concentration.csv
data/processed/mart_product_supplier.csv
data/processed/mart_b2b_customer.csv
data/processed/mart_geo_demand.csv
data/processed/mart_payment_profile.csv
data/processed/mart_channel_mix.csv
data/processed/mart_time_pattern.csv
data/processed/mart_buyer_persona.csv
data/processed/mart_data_quality.csv
data/processed/mart_synthetic_disclosure.csv
```

### Chart PNG (14)

| File | Nội dung |
|---|---|
| `01_supplier_top_spend.png` | Top 15 supplier theo chi tiêu (màu = tier) |
| `02_supplier_quality_map.png` | Bản đồ chất lượng: on-time vs defect |
| `03_category_dependency.png` | Mức phụ thuộc nhà cung cấp theo category |
| `04_spend_by_category.png` | Chi tiêu theo category |
| `05_product_margin.png` | Top sản phẩm theo margin |
| `06_top_b2b_accounts.png` | Top tài khoản B2B |
| `07_top_states.png` | Top bang theo chi tiêu |
| `08_state_coverage.png` | Độ phủ supplier vs nhu cầu |
| `09_card_provider.png` | Đơn theo loại thẻ |
| `10_browser.png` | Đơn theo trình duyệt |
| `11_device_type.png` | Đơn theo thiết bị |
| `12_monthly_seasonality.png` | Mùa vụ theo tháng (AM/PM) |
| `13_job_family_spend.png` | Chi tiêu theo nhóm nghề |
| `14_data_quality.png` | Tỷ lệ đạt các quy tắc chất lượng |

---

## Cách tái lập

```bash
python run_all.py
```
