"""Giai đoạn 2 — Làm sạch dữ liệu gốc.

Đầu vào : data/raw/Ecommerce Purchases.csv   (10.000 dòng, 14 cột)
Đầu ra  : data/processed/stg_purchases.csv

Nguyên tắc bất di bất dịch:
  1. KHÔNG sửa giá trị gốc (purchase_price, am_pm, cc_provider, language...).
  2. XOÁ hoàn toàn 3 cột thẻ tín dụng (PII).
  3. MASK email và IP (hash), không giữ bản gốc.
  4. CHỈ THÊM cột dẫn xuất, không ghi đè.

Chạy:
    python -m src.etl.clean
"""

from __future__ import annotations

import hashlib
import re

import pandas as pd

from .config import (
    DROP_COLUMNS,
    HIGH_VALUE_THRESHOLD,
    PII_COLUMNS,
    PRICE_TIER_LABELS,
    RAW_CSV,
    STG_PURCHASES_CSV,
)
from .util import force_utf8_stdout

# --- Regex dùng lại nhiều lần (compile 1 lần cho nhanh) ----------------------

# Địa chỉ dòng cuối: "Alexisborough, NE 77130-7478"
_ADDRESS_RE = re.compile(r"^(?P<city>.+?), (?P<state>[A-Z]{2}) (?P<zip>\d{5}(?:-\d{4})?)$")
# Dự phòng cho địa chỉ quân sự: "DPO AE 61496-4172" (không có dấu phẩy)
_ADDRESS_FALLBACK_RE = re.compile(r"^(?P<city>.+?) (?P<state>[A-Z]{2}) (?P<zip>\d{5}(?:-\d{4})?)$")

# Mã "bang" hợp lệ theo USPS: 50 bang + DC + lãnh thổ + địa chỉ quân sự
US_STATE_CODES = set(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT "
    "NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY "
    "DC PR VI GU AS MP PW MH FM AA AE AP".split()
)

# Thứ tự QUAN TRỌNG: Edge phải đứng trước Chrome, Opera trước Chrome,
# Chrome trước Safari (vì UA của Chrome có chứa token "Safari/").
_BROWSER_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"Edg[ea]?/|Edge/"), "Edge"),
    (re.compile(r"OPR/|Opera[/ ]"), "Opera"),
    (re.compile(r"Firefox/"), "Firefox"),
    (re.compile(r"Chrome/|CriOS/"), "Chrome"),
    (re.compile(r"Safari/"), "Safari"),
    (re.compile(r"MSIE |Trident/"), "Internet Explorer"),
]

_OS_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"Android"), "Android"),
    (re.compile(r"iPhone|iPad|iPod"), "iOS"),
    (re.compile(r"Windows"), "Windows"),
    (re.compile(r"Macintosh|Mac OS X"), "macOS"),
    (re.compile(r"Linux|X11"), "Linux"),
]

# Map chức danh -> nhóm nghề. Duyệt theo thứ tự, dừng ở match đầu tiên.
# Thứ tự quan trọng: quy tắc CỤ THỂ phải đứng trước quy tắc CHUNG.
_JOB_FAMILY_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"supply|logistic|warehouse|transport|distribution"), "Supply Chain"),
    (re.compile(r"buyer|purchas|procurement|sourcing"), "Procurement"),
    (re.compile(r"software|developer|programmer|web |full.?stack|devops|network|multimedia|\bit consultant|systems? (admin|engineer|analyst)"), "IT & Software"),
    (re.compile(r"data|analyst|statistic|actuar"), "Data & Analysis"),
    (re.compile(r"scientist|research|lab|biolog|chemist|physic|geolog|hydrolog|genetic|technologist|radiation"), "Science & Research"),
    (re.compile(r"engineer"), "Engineering"),
    (re.compile(r"surveyor|planning|geomatics|cartograph|minerals|building|estates"), "Surveying & Planning"),
    (re.compile(r"nurse|doctor|clinical|health|medical|pharmac|therap|surgeon|dental|physio|psycholog|psychotherap|occupational|chiropodist|dietitian|optometrist|orthoptist|paramedic|radiograph"), "Healthcare"),
    (re.compile(r"editor|journalist|magazine|broadcast|producer|presenter|television|film|video|musician|printmaker|media|writer|author|\barts?\b"), "Media & Publishing"),
    (re.compile(r"chief|director|head of|manager|management|ceo|cto|board"), "Management"),
    (re.compile(r"sales|business development|account manager|retail"), "Sales & BD"),
    (re.compile(r"market|advertis|public relations|\bpr\b|brand|communication"), "Marketing"),
    (re.compile(r"financ|account|audit|bank|tax|treasur|credit|insurance|broker|trader|claims"), "Finance & Accounting"),
    (re.compile(r"teach|lectur|education|training|tutor|professor|academic"), "Education & Training"),
    (re.compile(r"lawyer|legal|solicitor|barrister|paralegal|judge"), "Legal"),
    (re.compile(r"social work|counsell?or|care|support worker|youth|charit|fundrais|community|advice worker|warden|ranger|development worker|volunteer"), "Social & Care"),
    (re.compile(r"design|artist|creative|\bart\b|architect|illustrat|conservator|restorer|curator|museum|conservation"), "Design & Creative"),
    (re.compile(r"officer|administrat|secretary|assistant|receptionist|clerk|coordinator"), "Administration"),
    (re.compile(r"police|fire|security|army|military"), "Public & Safety"),
]


# --- Các bước biến đổi -------------------------------------------------------


def load_raw(path=RAW_CSV) -> pd.DataFrame:
    """Đọc CSV gốc."""
    if not path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file dữ liệu: {path}\n"
            "Xem docs/getting_data.md để biết cách tải."
        )
    return pd.read_csv(path)


def parse_address(addr: str) -> tuple[str | None, str | None, str | None]:
    """Tách địa chỉ 2 dòng thành (city, state, zip).

    Dòng cuối của Address luôn có dạng `City, ST ZIP`.
    Trả về (None, None, None) nếu không parse được.
    """
    lines = [ln.strip() for ln in str(addr).split("\n") if ln.strip()]
    if not lines:
        return None, None, None

    last = lines[-1]
    m = _ADDRESS_RE.match(last) or _ADDRESS_FALLBACK_RE.match(last)
    if not m:
        return None, None, None
    return m.group("city"), m.group("state"), m.group("zip")


def parse_browser(ua: str) -> tuple[str, str, str]:
    """Tách user-agent thành (browser_family, os, device_type)."""
    ua = str(ua)

    browser = "Other"
    for pattern, name in _BROWSER_PATTERNS:
        if pattern.search(ua):
            browser = name
            break

    os_name = "Other"
    for pattern, name in _OS_PATTERNS:
        if pattern.search(ua):
            os_name = name
            break

    if re.search(r"iPad|Tablet", ua):
        device = "tablet"
    elif re.search(r"Mobile|Android|iPhone|iPod|Windows Phone", ua):
        device = "mobile"
    else:
        device = "desktop"

    return browser, os_name, device


def map_job_family(job: str) -> str:
    """Gom 623 chức danh thành các nhóm nghề."""
    text = str(job).lower()
    for pattern, family in _JOB_FAMILY_RULES:
        if pattern.search(text):
            return family
    return "Other"


def mask_email(email: str) -> tuple[str, str | None]:
    """Trả về (email_masked, email_domain). Không giữ lại email gốc."""
    text = str(email).strip()
    if "@" not in text:
        return "invalid", None
    local, _, domain = text.partition("@")
    masked = (local[0] + "***") if local else "***"
    return f"{masked}@{domain}", domain


def hash_ip(ip: str) -> str:
    """Băm IP thành chuỗi 12 ký tự. Không thể dịch ngược."""
    return "iph_" + hashlib.sha256(str(ip).encode("utf-8")).hexdigest()[:12]


def hash_email(email: str) -> str:
    """Khoá khách hàng = băm email gốc.

    KHÔNG dùng `email_masked` làm khoá: `p***@yahoo.com` khớp với hàng nghìn
    người khác nhau, sẽ gộp 9.954 khách thành ~4.900.
    """
    text = str(email).strip().lower().encode("utf-8")
    return "cus_" + hashlib.sha256(text).hexdigest()[:12]


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Áp dụng toàn bộ quy tắc làm sạch, trả về bảng stg_purchases."""
    out = pd.DataFrame(index=df.index)

    # 1. Khoá chính giả + cờ đánh dấu dữ liệu thật
    out["purchase_id"] = range(1, len(df) + 1)
    out["is_synthetic"] = 0

    # 2. Giữ NGUYÊN các cột gốc có giá trị phân tích
    out["am_pm"] = df["AM or PM"]
    out["cc_provider"] = df["CC Provider"]
    out["language"] = df["Language"]
    out["purchase_price"] = df["Purchase Price"]
    out["company_name"] = df["Company"]
    out["job_title"] = df["Job"]

    # 3. Cột dẫn xuất từ Address
    parsed = df["Address"].map(parse_address)
    out["city"] = [p[0] for p in parsed]
    out["state"] = [p[1] for p in parsed]
    out["zip"] = [p[2] for p in parsed]

    # 4. Cột dẫn xuất từ Browser Info
    browsers = df["Browser Info"].map(parse_browser)
    out["browser_family"] = [b[0] for b in browsers]
    out["os"] = [b[1] for b in browsers]
    out["device_type"] = [b[2] for b in browsers]

    # 5. Mask PII (email, IP) — bản gốc bị bỏ
    emails = df["Email"].map(mask_email)
    out["email_masked"] = [e[0] for e in emails]
    out["email_domain"] = [e[1] for e in emails]
    out["customer_key"] = df["Email"].map(hash_email)
    out["ip_hash"] = df["IP Address"].map(hash_ip)

    # 6. Cột dẫn xuất từ Job
    out["job_family"] = df["Job"].map(map_job_family)

    # 7. Phân khúc theo giá
    out["price_tier"] = pd.qcut(
        df["Purchase Price"], q=4, labels=PRICE_TIER_LABELS, duplicates="drop"
    ).astype(str)
    out["is_high_value"] = (df["Purchase Price"] > HIGH_VALUE_THRESHOLD).astype(int)

    return out


def report(raw: pd.DataFrame, stg: pd.DataFrame) -> None:
    """In báo cáo kiểm tra ra màn hình."""
    line = "=" * 68

    print(line)
    print("BÁO CÁO LÀM SẠCH (GIAI ĐOẠN 2)")
    print(line)

    print(f"\n[1] Kích thước")
    print(f"    Gốc : {raw.shape[0]:,} dòng x {raw.shape[1]} cột")
    print(f"    Sạch: {stg.shape[0]:,} dòng x {stg.shape[1]} cột")

    print(f"\n[2] Cột bị XOÁ")
    for c in PII_COLUMNS:
        print(f"    - {c}   (PII - thẻ tín dụng)")
    for c in DROP_COLUMNS:
        print(f"    - {c}   (nhiễu, không mang thông tin)")

    print(f"\n[3] Kiểm tra giá trị gốc có bị thay đổi không")
    same_price = (raw["Purchase Price"].values == stg["purchase_price"].values).all()
    same_ampm = (raw["AM or PM"].values == stg["am_pm"].values).all()
    print(f"    purchase_price giữ nguyên : {'OK' if same_price else 'SAI!'}")
    print(f"    am_pm giữ nguyên          : {'OK' if same_ampm else 'SAI!'}")

    print(f"\n[4] Parse Address")
    fail_addr = stg["city"].isna().sum()
    print(f"    Parse được : {len(stg) - fail_addr:,} / {len(stg):,}")
    print(f"    Thất bại   : {fail_addr}")
    print(f"    Số bang khác nhau: {stg['state'].nunique()}")
    bad_state = stg["state"].dropna()
    bad_state = bad_state[~bad_state.isin(US_STATE_CODES)]
    if len(bad_state):
        print(f"    Mã bang KHÔNG hợp lệ: {len(bad_state)} -> {bad_state.unique()[:6].tolist()}")
    else:
        print(f"    Mã bang hợp lệ 100% (so với danh sách USPS)")
    zip5 = stg["zip"].dropna().str[:5]
    valid_zip = zip5.str.match(r"^\d{5}$").sum()
    print(f"    ZIP 5 số hợp lệ: {valid_zip:,} / {len(zip5):,}")

    print(f"\n[5] Parse Browser")
    print(f"    browser_family: {stg['browser_family'].value_counts().to_dict()}")
    print(f"    os            : {stg['os'].value_counts().to_dict()}")
    print(f"    device_type   : {stg['device_type'].value_counts().to_dict()}")

    print(f"\n[6] Nhóm nghề (job_family)")
    for k, v in stg["job_family"].value_counts().items():
        print(f"    {k:<22} {v:>6,}")

    print(f"\n[7] Phân khúc giá")
    for k, v in stg["price_tier"].value_counts().sort_index().items():
        print(f"    {k:<10} {v:>6,}")
    print(f"    Đơn giá trị cao (>{HIGH_VALUE_THRESHOLD}): {stg['is_high_value'].sum():,}")

    print(f"\n[8] Mask PII")
    print(f"    Email ví dụ  : {stg['email_masked'].iloc[0]}")
    print(f"    customer_key : {stg['customer_key'].iloc[0]}")
    print(f"    IP hash ví dụ: {stg['ip_hash'].iloc[0]}")
    print(f"    Domain email top 3: {stg['email_domain'].value_counts().head(3).to_dict()}")
    print(f"    Số khách hàng (customer_key): {stg['customer_key'].nunique():,}"
          f"   <- phải gần bằng 9.954, KHÔNG dùng email_masked ({stg['email_masked'].nunique():,})")

    print(f"\n[9] Ví dụ 1 dòng trước -> sau")
    print(f"    GỐC : Address={raw['Address'].iloc[0]!r}")
    print(f"          Job={raw['Job'].iloc[0]!r}")
    print(f"          Email={raw['Email'].iloc[0]!r}")
    print(f"          Price={raw['Purchase Price'].iloc[0]}")
    print(f"    SẠCH: city={stg['city'].iloc[0]!r} state={stg['state'].iloc[0]!r} zip={stg['zip'].iloc[0]!r}")
    print(f"          job_title={stg['job_title'].iloc[0]!r} -> job_family={stg['job_family'].iloc[0]!r}")
    print(f"          email={stg['email_masked'].iloc[0]!r} | browser={stg['browser_family'].iloc[0]!r} "
          f"os={stg['os'].iloc[0]!r} device={stg['device_type'].iloc[0]!r}")
    print(f"          price_tier={stg['price_tier'].iloc[0]!r} purchase_price={stg['purchase_price'].iloc[0]}")
    print(line)


def main() -> None:
    force_utf8_stdout()
    raw = load_raw()
    stg = clean(raw)

    STG_PURCHASES_CSV.parent.mkdir(parents=True, exist_ok=True)
    stg.to_csv(STG_PURCHASES_CSV, index=False)

    report(raw, stg)
    print(f"\nĐã ghi: {STG_PURCHASES_CSV}")


if __name__ == "__main__":
    main()
