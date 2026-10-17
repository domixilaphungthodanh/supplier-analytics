# Supplier & Supply-Chain Analytics

Dự án phân tích chuỗi cung ứng / nhà cung cấp end-to-end, xây trên dataset
*Ecommerce Purchases* (Kaggle) và mở rộng thêm một lớp dữ liệu supply chain.
Stack: **Python + SQLite**.

> **Miễn trừ trách nhiệm (Disclaimer)**
> Dataset gốc là **dữ liệu tổng hợp (synthetic)** và **không chứa thông tin nhà cung cấp**.
> Toàn bộ dữ liệu supplier / product / shipment trong dự án này được **sinh ra cho mục
> đích minh hoạ**. Kết quả thể hiện *phương pháp phân tích*, không phải insight thị trường thật.
> Xem phân tích chi tiết tại `docs/idea.md` mục 5.

## Trạng thái

- [x] Khởi tạo khung dự án
- [x] Chốt scope (`docs/idea.md` mục 2)
- [x] Tải dataset vào `data/raw/` (từ mirror GitHub — không cần tài khoản Kaggle)
- [x] ETL: làm sạch + che dữ liệu PII
- [x] Sinh lớp dữ liệu supply chain (synthetic)
- [x] Build SQLite warehouse
- [x] Kiểm tra chất lượng dữ liệu (`validate.py`) — 20/20 quy tắc ĐẠT
- [x] Viết 9 mảng phân tích
- [x] Vẽ chart + viết report — 14 chart

## Tải và chạy trên máy khác

Yêu cầu Python 3.10 trở lên. Mở terminal tại thư mục có `run_all.py`.

```bash
python -m pip install -r requirements.txt
```

Tải dataset theo [hướng dẫn](docs/getting_data.md), đặt tên file là
`data/raw/Ecommerce Purchases.csv`. Dữ liệu thô và database không được đóng gói;
database được tạo khi chạy pipeline.

## Chạy dự án

```bash
python run_all.py
```

Chạy lần lượt: làm sạch -> sinh supply layer -> dựng database -> kiểm tra -> 9 mảng phân tích.

## Kết quả

Xem **`docs/findings.md`** để đọc báo cáo kết quả đầy đủ.

| Output | Đường dẫn |
|---|---|
| Database | `data/processed/supply_chain.db` |
| 9 bảng phân tích + CSV | `data/processed/mart_*.csv` |
| 14 chart | `reports/figures/*.png` |

## Cấu trúc

Xem `docs/idea.md` mục 8.

## Cài đặt

```bash
pip install -r requirements.txt
```

## Tài liệu

| File | Nội dung |
|---|---|
| `docs/00_START_HERE.md` | Bản đồ đọc tài liệu (mở file này trước) |
| `docs/idea.md` | Ý tưởng, scope, gap analysis, data model, roadmap |
| `docs/data_dictionary.md` | Ý nghĩa từng cột của dataset gốc |
| `docs/assumptions.md` | Giả định dùng để sinh lớp dữ liệu supply chain |
| `docs/getting_data.md` | 4 cách tải dataset |
| `docs/findings.md` | **Báo cáo kết quả phân tích** |
