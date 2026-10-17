# Hướng dẫn tải dataset

Mục tiêu: đưa file `Ecommerce Purchases.csv` (~2.75 MB, 10.000 dòng × 14 cột)
vào thư mục `data/raw/` của dự án.

Có 4 cách. **Cách 0 là cách đã dùng thành công** cho dự án này (không cần tài khoản Kaggle).

> ⚠️ Lưu ý trước: dataset này là **dữ liệu synthetic**, license ghi "Unknown".
> Chỉ dùng cho mục đích học tập/portfolio.

---

## Cách 0 — Mirror trên GitHub ✅ (đã dùng, không cần tài khoản)

Dataset này có bản sao trên GitHub, tải trực tiếp bằng 1 lệnh:

```powershell
Invoke-WebRequest `
  -Uri "https://raw.githubusercontent.com/anurags10/Ecommerce-purchases-dataset/main/Ecommerce%20Purchases" `
  -OutFile ".\data\raw\Ecommerce Purchases.csv"
```

Nguồn: <https://github.com/anurags10/Ecommerce-purchases-dataset>

**Kiểm tra:** file tải về phải ~2.62 MB. Đã xác nhận đúng **10.000 × 14**.

> Ưu điểm: không cần đăng nhập, không cần API token.
> Nhược điểm: không phải nguồn chính thức — nên đối chiếu lại nếu cần độ tin cậy tuyệt đối.

---

## Cách 1 — Tải thủ công bằng trình duyệt ⭐ (dễ nhất)

**Bước 1.** Đăng ký / đăng nhập Kaggle (miễn phí): <https://www.kaggle.com/account/login>

**Bước 2.** Mở một trong các link dataset sau:

| Link | File bên trong |
|---|---|
| <https://www.kaggle.com/datasets/vladmarascu/ecommerce-purchases-csv> | `Ecommerce Purchases.csv` |
| <https://www.kaggle.com/datasets/utkarsharya/ecommerce-purchases> | `Ecommerce Purchases` (không có đuôi .csv) |
| <https://www.kaggle.com/datasets/ahmedashrafahmed/ecommerce-purchases> | tương tự |

→ Nên dùng **link đầu tiên** vì file đã đúng đuôi `.csv`.

**Bước 3.** Bấm nút **Download** (góc phải, ký hiệu ⬇). Trình duyệt tải về file `.zip`.

**Bước 4.** Giải nén file zip đó ra.

**Bước 5.** Copy file `Ecommerce Purchases.csv` vào:

```
.\data\raw\
```

**Bước 6.** Kiểm tra lại (xem mục "Kiểm tra" ở cuối file này).

---

## Cách 2 — Dùng Kaggle CLI (tải bằng dòng lệnh)

Phù hợp nếu bro muốn tự động hoá, hoặc tải nhiều dataset.

**Bước 1.** Cài thư viện:

```bash
pip install kaggle
```

**Bước 2.** Lấy API token:

1. Vào <https://www.kaggle.com/settings>
2. Kéo xuống mục **API** → bấm **Create New Token**
3. Kaggle tải về file `kaggle.json`

**Bước 3.** Đặt file vào đúng chỗ trên Windows:

```
C:\Users\Dell XPS\.kaggle\kaggle.json
```

> Nếu thư mục `.kaggle` chưa có thì tạo mới.
> File `kaggle.json` chứa username + API key — **coi như mật khẩu, không chia sẻ, không commit lên git.**

**Bước 4.** Chạy lệnh tải:

```powershell
kaggle datasets download -d vladmarascu/ecommerce-purchases-csv `
  -p ".\data\raw" --unzip
```

Kiểm tra kết quả:

```powershell
Get-ChildItem ".\data\raw"
```

---

## Cách 3 — Dùng Python (`kagglehub`)

Cách mới nhất, gọn nhất nếu bro làm việc trong Python:

```bash
pip install kagglehub
```

```python
import kagglehub, shutil, os

# Tải về cache của kagglehub
path = kagglehub.dataset_download("vladmarascu/ecommerce-purchases-csv")
print("Đã tải về:", path)

# Copy sang data/raw của dự án
dest = r".\data\raw"
os.makedirs(dest, exist_ok=True)
for f in os.listdir(path):
    shutil.copy(os.path.join(path, f), dest)
    print("->", f)
```

> Cách này vẫn cần đăng nhập Kaggle ở lần dùng đầu tiên.

---

## Kiểm tra dữ liệu đã đúng

Sau khi có file trong `data/raw/`, chạy:

```powershell
python -c "import pandas as pd; df = pd.read_csv(r'.\data\raw\Ecommerce Purchases.csv'); print(df.shape); print(df.columns.tolist())"
```

**Kết quả mong đợi:**

```
(10000, 14)
['Address', 'Lot', 'AM or PM', 'Browser Info', 'Company', 'Credit Card',
 'CC Exp Date', 'CC Security Code', 'CC Provider', 'Email', 'Job',
 'IP Address', 'Language', 'Purchase Price']
```

- Nếu ra `(10000, 14)` → ✅ đúng file, sẵn sàng chạy ETL.
- Nếu số khác → gửi mình output, mình kiểm tra.

> Nếu chưa cài pandas: `pip install -r requirements.txt`

---

## Nếu bro không muốn tạo tài khoản Kaggle

Vẫn có phương án: mình **sinh một file CSV giả cùng đúng 14 cột và 10.000 dòng**,
đặt tên `Ecommerce Purchases.mock.csv`. Code ETL chạy y hệt.

Khi nào bro có file thật thì chỉ cần thay file vào `data/raw/` và chạy lại — **không phải sửa code**.

Nhược điểm: số liệu không giống dataset gốc, nên phần "data quality report"
sẽ phản ánh dữ liệu giả. Cần ghi rõ nếu đem đi showcase.
