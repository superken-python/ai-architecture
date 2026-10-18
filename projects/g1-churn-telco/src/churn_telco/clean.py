"""Làm sạch bảng thô (A2): data/raw → data/interim. Mỗi quy tắc đều có lý do ghi ngay cạnh, và có test.

Nguyên tắc:
- Không sửa data/raw (bằng chứng gốc); mọi thay đổi nằm ở đây, chạy lại được.
- Bỏ PII (tên, số điện thoại, email) NGAY ở bước đầu tiên: model không cần, log và file trung gian không chứa (OPS-08).
- Không đoán bừa: giá trị không chuẩn hoá được thì giữ nguyên và báo ra, không ép vào nhóm gần nhất.

    uv run python -m churn_telco.clean        # data/raw → data/interim
"""

from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path

import pandas as pd

from churn_telco import config

PII_COLUMNS = ["full_name", "phone", "email"]
CANONICAL_PROVINCES = [
    "TP. Hồ Chí Minh",
    "Hà Nội",
    "Đà Nẵng",
    "Hải Phòng",
    "Cần Thơ",
    "Bình Dương",
    "Đồng Nai",
    "Khánh Hòa",
    "Thừa Thiên Huế",
    "Nghệ An",
]
PROVINCE_ALIASES = {"hcm": "TP. Hồ Chí Minh", "hochiminh": "TP. Hồ Chí Minh", "hn": "Hà Nội", "hue": "Thừa Thiên Huế"}
TICKET_CATEGORIES = ["Mất kết nối", "Mạng chậm", "Cước phí", "Chuyển địa điểm", "Yêu cầu hủy", "Khác"]


def ascii_key(text: str) -> str:
    """Khoá so khớp: NFC → bỏ dấu → chữ thường → bỏ tiền tố 'tp' và mọi ký tự không phải chữ số/chữ cái.

    'TP.HCM', 'TP HCM' → 'hcm'; 'Khánh Hoà' (dấu đặt kiểu cũ) và 'Khánh Hòa' → 'khanhhoa'.
    """
    text = unicodedata.normalize("NFD", unicodedata.normalize("NFC", text))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn").replace("đ", "d").replace("Đ", "D")
    text = re.sub(r"[^a-z0-9]", "", text.lower())
    return text.removeprefix("tp")


_PROVINCE_KEYS = {ascii_key(p): p for p in CANONICAL_PROVINCES} | PROVINCE_ALIASES
_TICKET_KEYS = {ascii_key(c): c for c in TICKET_CATEGORIES}


def normalize_province(value: str | float) -> str | float:
    if not isinstance(value, str):
        return value
    return _PROVINCE_KEYS.get(ascii_key(value), unicodedata.normalize("NFC", value.strip()))


def normalize_category(value: str) -> str:
    return _TICKET_KEYS.get(ascii_key(value), unicodedata.normalize("NFC", value.strip()))


def clean_customers(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.drop(columns=PII_COLUMNS)
    # export trùng: giữ bản cập nhật mới nhất của mỗi khách
    df = df.sort_values("updated_at").drop_duplicates("customer_id", keep="last")
    df["province"] = df["province"].map(normalize_province)
    df["channel"] = df["channel"].fillna("Không rõ")
    # 1900-01-01 là giá trị mặc định khi bỏ trống, không phải ngày sinh thật
    df.loc[df["date_of_birth"] == pd.Timestamp("1900-01-01"), "date_of_birth"] = pd.NaT
    # status/cancel_date là trạng thái TẠI NGÀY EXPORT: giữ lại để đối soát, KHÔNG dùng làm feature (A4)
    return df.sort_values("customer_id").reset_index(drop=True)


def clean_invoices(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.drop_duplicates()  # export lại: trùng nguyên dòng
    df = df.assign(is_adjustment=df["invoice_id"].str.endswith("-ADJ"))  # dòng điều chỉnh giảm cước, amount < 0
    return df.reset_index(drop=True)


def clean_tickets(raw: pd.DataFrame) -> pd.DataFrame:
    return raw.assign(category=raw["category"].map(normalize_category))


def read_raw(raw_dir: Path = config.RAW) -> dict[str, pd.DataFrame]:
    dates = {
        "customers": ["date_of_birth", "signup_date", "cancel_date", "updated_at"],
        "subscriptions": ["start_date", "end_date"],
        "plan_prices": ["effective_from"],
        "tickets": ["created_at", "logged_at", "resolved_at"],
        "cancellations": ["request_date", "effective_date"],
    }
    tables = {name: pd.read_csv(raw_dir / f"{name}.csv", parse_dates=cols) for name, cols in dates.items()}
    tables["plans"] = pd.read_csv(raw_dir / "plans.csv")
    tables["invoices"] = pd.read_parquet(raw_dir / "invoices.parquet")
    tables["usage"] = pd.read_parquet(raw_dir / "usage.parquet")
    return tables


def clean_all(raw_dir: Path = config.RAW, out_dir: Path = config.INTERIM) -> dict[str, pd.DataFrame]:
    raw = read_raw(raw_dir)
    clean = {
        **raw,
        "customers": clean_customers(raw["customers"]),
        "invoices": clean_invoices(raw["invoices"]),
        "tickets": clean_tickets(raw["tickets"]),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in clean.items():
        df.to_parquet(out_dir / f"{name}.parquet", index=False)
    return clean


def unknown_values(clean: dict[str, pd.DataFrame]) -> dict[str, list[str]]:
    """Giá trị chưa chuẩn hoá được — phải bằng rỗng trước khi đi tiếp (có test)."""
    provinces = set(clean["customers"]["province"].dropna()) - set(CANONICAL_PROVINCES)
    categories = set(clean["tickets"]["category"]) - set(TICKET_CATEGORIES)
    return {"province": sorted(provinces), "category": sorted(categories)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    log = logging.getLogger("churn_telco.clean")
    tables = clean_all()
    for name, df in tables.items():
        log.info("%-14s %8d dòng", name, len(df))
    unknown = unknown_values(tables)
    if any(unknown.values()):
        raise SystemExit(f"Còn giá trị chưa chuẩn hoá được: {unknown}")
