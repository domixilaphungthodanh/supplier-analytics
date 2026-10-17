# Giả định — Lớp dữ liệu supply chain (synthetic)

**Trạng thái:** DRAFT — cần xác nhận trước khi làm Phase 2.
Toàn bộ con số dưới đây là **do mình tự đặt để minh hoạ**. Chúng được chọn sao cho
các KPI của supplier có **sự phân hoá hợp lý** (không phải supplier nào cũng giống nhau,
cũng không phải ai cũng hoàn hảo) — đó là điều làm cho phần phân tích trở nên có ý nghĩa.

**Nguyên tắc vàng:** lớp synthetic chỉ **thêm** bảng và cột.
Nó **không bao giờ** sửa hay thay thế bất kỳ giá trị gốc nào của `Ecommerce Purchases.csv`.
Mọi bảng synthetic đều được đánh dấu (`is_synthetic = 1`).

---

## A1. Suppliers

- Số lượng: **35 suppliers**.
- Trường: `supplier_name`, `country`, `tier` (1–3, 1 là tốt nhất), `category_focus`,
  `contract_start`, `is_dual_source`.
- Phân bổ quốc gia (ước lượng): 45% US, 20% China, 10% Vietnam, 10% Germany, 15% khác.
- Tier quyết định hiệu suất:
  - Tier 1: on-time ~96%, defect ~0.5%
  - Tier 2: on-time ~90%, defect ~1.5%
  - Tier 3: on-time ~80%, defect ~4.0%

## A2. Products & ánh xạ supplier

- Số lượng: **120 products** thuộc **10 categories**
  (Electronics, Apparel, Home, Office, Beauty, Sports, Toys, Auto, Grocery, Books).
- Mỗi product -> **đúng 1 primary supplier**.
- **~20%** product có thêm **secondary supplier** (dual sourcing) để phần phân tích
  "single-source risk" có ý nghĩa.
- `list_price` (giá bán đề xuất) sinh trong khoảng **[3.00 – 45.00]** — tức **nhỏ hơn**
  `Purchase Price` là mức giá trị đơn hàng, để có thể chia ra được số lượng > 1.
- `unit_cost` (giá vốn) `≈ 0.60–0.80 × list_price` → margin gộp ~20–40%.
- Product gán cho mỗi giao dịch dựa theo category và phân khúc giá, sao cho
  `quantity × list_price ≈ Purchase Price` (xem A3).

> Ràng buộc từ dữ liệu thật: `Purchase Price` chỉ trong **0.00 – 99.99**
> (đã kiểm tra, xem `docs/data_dictionary.md`). Vì vậy `list_price` phải nhỏ
> để quantity còn lớn hơn 1 được.

## A3. Orders (nối phía cầu với phía cung)

- `order_date`: ngày ngẫu nhiên trong **2023-01-01 … 2025-12-31**, nhưng có trọng số
  để **Q4 cao hơn 30%** so với các quý khác (mùa lễ hội).
- `AM or PM` của dòng gốc được **giữ nguyên**; `order_date` không cần nhất quán với
  trường nào khác (vì dữ liệu gốc không có chiều thời gian).
- `quantity`: tính bằng `round(Purchase Price / list_price)`, kẹp trong **[1, 20]**.
  Vì `list_price ≤ 45` nên đa số đơn có quantity 1–5, một số ít lên tới 20.
- **`Purchase Price` không bao giờ bị thay đổi** — nó là *tổng giá trị đơn hàng*.
  `list_price` và `quantity` được chọn sao cho `quantity × list_price ≈ Purchase Price`.
  Với đơn có `Purchase Price < 3` hoặc `= 0`, đặt `quantity = 1`.
- Supplier của đơn = primary supplier của product
  (dùng secondary supplier ~15% số lần với các product dual-sourced).

## A4. Shipments

- Mỗi dòng purchase tương ứng 1 shipment.
- `ship_date` = `order_date` + 0–3 ngày.
- `lead_time_days` sinh theo profile tier của supplier
  (Tier 1: ~5–10 ngày, Tier 2: ~10–18, Tier 3: ~18–30).
- `delivery_date` = `ship_date` + `lead_time_days` (+ delay ngẫu nhiên).
- `status` ∈ {`delivered`, `in_transit`, `delayed`, `cancelled`} — đa số là `delivered`.
- `defect_flag` được bật với xác suất = defect rate của supplier.
- `delay_days` = max(0, lead time thực tế − lead time cam kết).

## A5. Tính ngẫu nhiên & khả năng tái lập

- Dùng **random seed cố định** để dataset sinh ra là tái lập được.
- Giá trị seed: **42** (chỉ đổi nếu muốn một kết quả ngẫu nhiên khác).

## A6. Nguyên tắc trung thực

1. Mọi chart/report có dùng dữ liệu synthetic đều phải ghi rõ điều đó.
2. `README.md` luôn có disclaimer cố định.
3. Bảng `mart_data_quality` phải báo cáo cả vấn đề chất lượng của dữ liệu gốc
   **và** việc lớp supply là dữ liệu synthetic.

---

## ✅ Câu hỏi đã chốt (2026-10-17)

- [x] Quy mô: **35 suppliers / 120 products** (giữ nguyên)
- [x] Con số hiệu suất theo tier (A1): **giữ nguyên** (on-time 96/90/80%, defect 0.5/1.5/4.0%)
- [x] `order_date`: **2023-01-01 … 2025-12-31** (chọn phương án "mới" thay vì mốc 2020)
