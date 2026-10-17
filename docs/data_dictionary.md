# Data Dictionary — Ecommerce Purchases (dataset gốc)

Nguồn: Kaggle *Ecommerce Purchases* (~10.000 dòng, 14 cột, dữ liệu synthetic).
File thực tế: `data/raw/Ecommerce Purchases.csv`.

---

## ✅ Hồ sơ dữ liệu thực tế (đã kiểm tra ngày 2026-10-17)

| Chỉ số | Kết quả |
|---|---|
| Shape | **(10.000, 14)** — đúng như mong đợi |
| Null | **0** trên mọi cột |
| `Purchase Price` | **0.00 – 99.99**, mean 50.35, std 29.02 (phân bố **đều**, không phải 0–1000) |
| `AM or PM` | PM 5.068 / AM 4.932 (~50/50) |
| `CC Provider` | 10 giá trị, gần như đều (767 – 1.716) |
| `Language` | 9 giá trị, gần như đều (~1.086 – 1.155) |
| `Company` | 8.653 unique — công ty trùng nhiều nhất chỉ **15 đơn** |
| `Job` | 623 unique |
| `Lot` | 9.822 unique (nhiễu) |
| `Address`, `Credit Card`, `IP Address` | 10.000 unique (không trùng) |

### ⚠️ Phát hiện quan trọng: dữ liệu gần như **ngẫu nhiên đều**

Mọi cột gốc đều phân bố **uniform** — không có tương quan thật giữa
giá tiền, ngôn ngữ, loại thẻ, thời điểm mua hay chức danh.
Hệ quả:

1. **Các mảng phân tích chỉ dùng dữ liệu gốc (Payment, Language, Channel,
   AM/PM) sẽ ra biểu đồ phẳng** — vì bản chất là nhiễu ngẫu nhiên.
2. Đây là **phát hiện trung thực cần ghi vào report**, không phải lỗi code.
3. Các mảng có ý nghĩa thực sự là những mảng dùng **lớp supply chain synthetic**
   (Supplier Performance, Concentration, Product–Supplier, Geographic).
4. `Company` có nhóm trùng nhưng **yếu** (nhiều nhất 15 đơn/công ty)
   → mảng B2B cần đặt kỳ vọng thấp.

### Định dạng `Address` (quan trọng khi parse)

Địa chỉ **xuống 2 dòng** trong 1 ô CSV:

```
16629 Pace Camp Apt. 448\nAlexisborough, NE 77130-7478
9374 Jasmine Spurs Suite 508\nSouth John, TN 84355-4179
Unit 0065 Box 5052\nDPO AP 27450          <- địa chỉ quân sự, không có ZIP 5 số
```

→ **Dòng 2 luôn là `City, ST ZIP`** (trừ địa chỉ quân sự dạng `DPO AP 27450`).
Quy tắc parse: tách theo `\n`, lấy dòng cuối, regex `^(?P<city>.+), (?P<state>[A-Z]{2}) (?P<zip>\d{5}(-\d{4})?)$`.

### Định dạng `Email`

- ~48,6% là free mail: `hotmail.com` 1.638, `yahoo.com` 1.616, `gmail.com` 1.605
- Còn lại là domain công ty **sinh ngẫu nhiên từ họ người** (smith.com, williams.com...)
  → **không liên quan** đến cột `Company`. Xác nhận lại lần nữa: `Company` là phía người mua.

| # | Cột | Kiểu (dự kiến) | Ý nghĩa | Giữ? | Ghi chú |
|---|---|---|---|---|---|
| 1 | `Address` | text | Địa chỉ người mua, **xuống 2 dòng**: dòng 2 là `City, ST ZIP` | Có | Phải parse thành `city`, `state`, `zip` (xem quy tắc ở trên) |
| 2 | `Lot` | text | Chuỗi ký tự ngẫu nhiên | Không | 9.822 unique / 10.000 dòng -> gần như nhiễu |
| 3 | `AM or PM` | text | Mua buổi sáng hay chiều | Có | ~51% PM / ~49% AM |
| 4 | `Browser Info` | text | Chuỗi user-agent đầy đủ | Có | Parse thành browser family + OS + device type |
| 5 | `Company` | text | **Công ty nơi người mua làm việc** — KHÔNG phải supplier | Có | 8.653 unique / 10.000 -> dùng làm buyer org B2B |
| 6 | `Credit Card` | text/number | Số thẻ | **Không — PII** | Drop ngay |
| 7 | `CC Exp Date` | text | `MM/YY` | **Không — PII** | Drop ngay |
| 8 | `CC Security Code` | number | CVV | **Không — PII** | Drop ngay |
| 9 | `CC Provider` | text | JCB 16 digit / Discover / Mastercard / Visa... | Có | Phân tích kênh thanh toán & rủi ro |
| 10 | `Email` | text | Email người mua | Mask | Giữ bản đã hash + domain email |
| 11 | `Job` | text | Chức danh người mua | Có | Suy ra `job_family` |
| 12 | `IP Address` | text | IP người mua | Mask | Hash; giá trị phân tích thấp |
| 13 | `Language` | text | Mã ngôn ngữ (en, fr, pt...) | Có | Giá trị thấp |
| 14 | `Purchase Price` | float | Giá trị đơn hàng | Có | Chỉ số monetary cốt lõi |

## Các trường dẫn xuất

| Trường | Dẫn xuất từ | Quy tắc |
|---|---|---|
| `city`, `state`, `zip` | `Address` | Regex: `..., <City>, <ST> <ZIP>` |
| `browser_family`, `os`, `device_type` | `Browser Info` | Match keyword trong chuỗi UA |
| `email_domain`, `email_masked` | `Email` | Tách theo `@`; hash phần local |
| `job_family` | `Job` | Map theo từ khoá (engineer, manager, sales...) |
| `price_tier` | `Purchase Price` | Chia quantile 4 mức (bronze / silver / gold / platinum) |
| `is_high_value` | `Purchase Price` | Ngưỡng **`> 85`** (top ~15%) — **KHÔNG dùng 1000** vì giá tối đa chỉ 99.99 |

## Các trường synthetic (do dự án này sinh thêm)

| Trường | Bảng | Ý nghĩa |
|---|---|---|
| `supplier_id` | `dim_supplier` | Khoá supplier (synthetic) |
| `product_id` | `dim_product` | Khoá product (synthetic); mỗi product có 1 primary supplier |
| `quantity` | `fact_purchases` | Số lượng mua (synthetic) |
| `unit_cost` | `dim_product` | Giá vốn / đơn vị từ supplier (synthetic) |
| `order_date` | `fact_purchases` | Ngày đặt hàng (synthetic, ví dụ trong 2023–2025) |
| `delay_days`, `status`, `defect_flag` | `fact_shipments` | Kết quả logistics (synthetic) |

> Mỗi bảng synthetic đều mang cờ `is_synthetic` (hoặc prefix `synth_`)
> để không bao giờ bị nhầm lẫn giữa dữ liệu thật và dữ liệu sinh thêm.
