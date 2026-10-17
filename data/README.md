# Thư mục data/ KHÔNG được commit — xem .gitignore
#
# data/raw/       : file CSV gốc tải từ Kaggle, chứa PII (số thẻ, email, IP)
#                   => TUYỆT ĐỐI không đẩy lên git
# data/processed/ : database + CSV sinh ra bởi pipeline, tái tạo được bằng run_all.py
#
# Cách tạo lại:
#   1. Tải dataset: xem docs/getting_data.md
#   2. Chạy: python run_all.py
