# 🚩 BẮT ĐẦU ĐỌC TỪ ĐÂY

File này là **bản đồ đọc tài liệu**. Mở file này trước, rồi đi theo đúng thứ tự bên dưới.

**Tổng thời gian: ~25 phút.** Đừng đọc như đọc sách — đọc để trả lời câu hỏi.

---

## TL;DR trong 60 giây

1. Dataset gốc (10.000 dòng mua hàng của **người mua**) **không có nhà cung cấp**.
2. Cột `Company` là **công ty của người mua**, không phải supplier.
3. Nên: giữ dữ liệu gốc làm **phía cầu**, tự sinh thêm **phía cung** (supplier/product/shipment).
4. Dự án gồm **9 mảng phân tích**, lưu trong SQLite, output là CSV + chart.
5. Còn **3 câu hỏi** cần bro chốt trước khi code (nằm ở file cuối cùng).

---

## Lộ trình đọc

### 🟢 Vòng 1 — Hiểu dự án là gì (5 phút)

| Bước | Đọc | Trả lời câu hỏi |
|---|---|---|
| 1 | `README.md` | Dự án này làm gì? Disclaimer nói gì? |
| 2 | `docs/idea.md` §1 | Tóm tắt ý tưởng |
| 3 | `docs/idea.md` §2 | 5 quyết định đã chốt — **bro có đồng ý không?** |

✅ Xong vòng 1 bro đã biết dự án làm gì và làm bằng gì.

---

### 🟡 Vòng 2 — Hiểu vấn đề & cách giải (12 phút)

Đây là **phần lõi**, đọc kỹ nhất.

| Bước | Đọc | Trả lời câu hỏi |
|---|---|---|
| 4 | `docs/idea.md` §3 | Dataset đến từ đâu, có gì |
| 5 | `docs/idea.md` §4 | 14 cột: cột nào dùng được, cột nào bỏ. **Bro có đồng ý cách xử lý không?** |
| 6 | `docs/idea.md` §5 | 14 khuyết điểm G1–G14 + cách bù ⭐ |
| 7 | `docs/idea.md` §6 | Sơ đồ bảng dữ liệu ⭐ — **nhìn có hợp lý không?** |

> ⚠️ Nếu chỉ đọc được 1 mục: đọc **§5** (gap analysis). Đó là phần mình bổ sung nhiều nhất.

---

### 🔵 Vòng 3 — Chi tiết & chốt (8 phút)

| Bước | Đọc | Trả lời câu hỏi |
|---|---|---|
| 8 | `docs/idea.md` §7 | 9 mảng phân tích — **có thiếu mảng nào bro muốn không?** |
| 9 | `docs/data_dictionary.md` | Nghĩa từng cột + quy tắc biến đổi |
| 10 | `docs/assumptions.md` | Số liệu synthetic cụ thể ⭐ |

---

## ✅ Sau khi đọc xong, bro cần trả lời 3 câu

Nằm ở **cuối `docs/assumptions.md`**:

1. Quy mô **35 suppliers / 120 products** đã hợp lý chưa?
2. Các con số hiệu suất theo tier (on-time 96/90/80%, defect 0.5/1.5/4%) có ổn không?
3. Khoảng `order_date` nên là **2023–2025** hay mốc 2020 như notebook gốc?

**Trả lời xong 3 câu này là mình bắt tay vào code ETL được ngay.**

---

## 📌 Mẹo đọc

- **Xem cho đẹp:** mở VS Code, bấm `Ctrl + Shift + V` để xem preview markdown.
- **Nhảy nhanh:** `Ctrl + F` rồi gõ `§5`, `§6` để tới đúng mục.
- **Đừng cố nhớ hết số liệu.** Chỉ cần nắm: *vấn đề là gì* (§5) và *giải thế nào* (§6).
- **Có gì không đồng ý thì ghi ra luôn**, mình sửa tài liệu trước khi viết code —
  sửa doc tốn 1 phút, sửa code tốn 1 tiếng.

---

## 🔜 Sau khi đọc xong, các bước tiếp theo

1. Bro chốt 3 câu hỏi -> mình cập nhật `assumptions.md`. ✅ (đã chốt 1A 2A 3A)
2. ~~Tải dataset vào `data/raw/`~~ ✅ **đã xong** — tải từ mirror GitHub, 10.000 × 14.
3. Mình viết `src/etl/` -> sinh database `supply_chain.db`.
4. Mình viết SQL cho 9 mảng phân tích -> CSV + chart trong `reports/`.
