"""Hợp đồng dữ liệu (A4 · DATA-05): pipeline TỰ DỪNG với thông báo rõ ràng khi dữ liệu sai schema hoặc lệch mạnh.

Hai tầng kiểm tra:
- Schema (pandera): kiểu, khoảng giá trị, tập giá trị cho phép, khoá không trùng — kiểm tra từng dòng.
- Phân phối (`check_snapshots`): số khách và tỷ lệ churn từng tháng không được lệch bất thường — kiểm tra cả bảng.

Cột ngày giờ chỉ kiểm tra "là kiểu ngày giờ": pandas 3 giữ đơn vị của nguồn (ms/us/ns), ép một đơn vị là sai vặt.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pandera.pandas as pa

from churn_telco.clean import CANONICAL_PROVINCES, PII_COLUMNS, TICKET_CATEGORIES

PLAN_CODES = ["SX50", "SX150", "SX300", "SX150TV", "SX300TV", "COMBO"]
SEGMENTS = ["Hộ gia đình", "Doanh nghiệp nhỏ"]
CHANNELS = ["Cửa hàng", "Online", "Đại lý", "Không rõ"]
PAYMENTS = ["Tiền mặt tại điểm", "Chuyển khoản", "Ví điện tử", "Tự động trừ thẻ"]


class DataQualityError(ValueError):
    """Dữ liệu đầu vào không đạt — dừng pipeline thay vì train/chấm điểm trên dữ liệu hỏng."""


def _datetime(nullable: bool = False) -> pa.Column:
    is_dt = pa.Check(pd.api.types.is_datetime64_any_dtype, error="không phải kiểu ngày giờ")
    return pa.Column(checks=is_dt, nullable=nullable)


CUSTOMERS = pa.DataFrameSchema(
    {
        "customer_id": pa.Column(str, unique=True),  # sau khử trùng: mỗi khách một dòng
        "province": pa.Column(str, pa.Check.isin(CANONICAL_PROVINCES)),
        "segment": pa.Column(str, pa.Check.isin(SEGMENTS)),
        "channel": pa.Column(str, pa.Check.isin(CHANNELS)),
        "signup_date": _datetime(),
        "date_of_birth": _datetime(nullable=True),
    },
    checks=[
        pa.Check(lambda df: not set(PII_COLUMNS) & set(df.columns), error="còn cột PII (tên, điện thoại, email)"),
        pa.Check(lambda df: df["date_of_birth"].dropna().gt("1930-01-01").all(), error="còn ngày sinh mặc định 1900"),
    ],
    name="customers",
)
TICKETS = pa.DataFrameSchema(
    {
        "ticket_id": pa.Column(str, unique=True),
        "category": pa.Column(str, pa.Check.isin(TICKET_CATEGORIES)),
        "created_at": _datetime(),
        "logged_at": _datetime(),
        "csat": pa.Column(float, pa.Check.in_range(1, 5), nullable=True),
    },
    checks=pa.Check(lambda df: df["logged_at"] >= df["created_at"], error="ticket vào hệ thống trước khi được tạo"),
    name="tickets",
)
INVOICES = pa.DataFrameSchema(
    {"invoice_id": pa.Column(str, unique=True), "amount": pa.Column(float), "is_adjustment": pa.Column(bool)},
    checks=pa.Check(lambda df: (df["amount"] > 0) | df["is_adjustment"], error="hoá đơn thường có số tiền <= 0"),
    name="invoices",
)
USAGE = pa.DataFrameSchema(
    {"data_gb": pa.Column(float, pa.Check.gt(0)), "outage_minutes": pa.Column(float, pa.Check.ge(0))},
    unique=["customer_id", "month"],  # một khách một dòng mỗi tháng
    name="usage",
)
CLEAN = {"customers": CUSTOMERS, "tickets": TICKETS, "invoices": INVOICES, "usage": USAGE}


def validate_clean(interim: Path) -> None:
    """Kiểm tra các bảng đã làm sạch; gom MỌI lỗi (lazy=True) rồi mới báo, để sửa một lần."""
    for name, schema in CLEAN.items():
        try:
            schema.validate(pd.read_parquet(interim / f"{name}.parquet"), lazy=True)
        except pa.errors.SchemaErrors as err:
            raise DataQualityError(f"Bảng sạch '{name}' không đạt:\n{err.failure_cases.head(20)}") from err


FEATURES = pa.DataFrameSchema(
    {
        "t": _datetime(),
        "customer_id": pa.Column(str),
        "segment": pa.Column("category", pa.Check.isin(SEGMENTS)),
        "channel": pa.Column("category", pa.Check.isin(CHANNELS)),
        "province": pa.Column("category", pa.Check.isin(CANONICAL_PROVINCES)),
        "plan_code": pa.Column("category", pa.Check.isin(PLAN_CODES)),
        "payment_method": pa.Column("category", pa.Check.isin(PAYMENTS)),
        "tenure_days": pa.Column(float, pa.Check.ge(1)),  # khách vào mạng trước t ít nhất 1 ngày
        "age": pa.Column(float, pa.Check.in_range(16, 100), nullable=True),
        "monthly_fee": pa.Column(float, pa.Check.in_range(100_000, 1_000_000)),
        "fee_change_90d": pa.Column(float, pa.Check.in_range(-0.5, 0.5)),
        "contract_months": pa.Column(float, pa.Check.isin([0, 12, 24])),
        "days_to_contract_end": pa.Column(float, pa.Check.in_range(0, 730), nullable=True),
        "data_gb_m1": pa.Column(float, pa.Check.gt(0), nullable=True),
        "usage_ratio": pa.Column(float, pa.Check.gt(0), nullable=True),
        "outage_m1": pa.Column(float, pa.Check.ge(0), nullable=True),
        "tickets_30d": pa.Column(float, pa.Check.ge(0)),
        "open_tickets": pa.Column(float, pa.Check.ge(0)),
        "min_csat_90d": pa.Column(float, pa.Check.in_range(1, 5), nullable=True),
        "unpaid_at_t": pa.Column(float, pa.Check.ge(0)),
        "max_days_late_90d": pa.Column(float, pa.Check.ge(0), nullable=True),
        "churn_30d": pa.Column(int, pa.Check.isin([0, 1])),
    },
    unique=["t", "customer_id"],  # một khách chỉ có một dòng mỗi ngày chấm điểm — nếu trùng là JOIN sai
    name="features",
)


def check_snapshots(df: pd.DataFrame, max_size_change: float = 0.25, churn_range: tuple = (0.003, 0.15)) -> None:
    """Kiểm tra phân phối theo từng ngày chấm điểm: số khách và tỷ lệ churn nằm trong khoảng hợp lý."""
    per_t = df.groupby("t").agg(n=("customer_id", "size"), churn=("churn_30d", "mean"))
    size_dev = per_t["n"] / per_t["n"].median() - 1
    problems = [
        f"{t:%Y-%m}: {row.n} khách, lệch {dev:+.0%} so với trung vị"
        for (t, row), dev in zip(per_t.iterrows(), size_dev, strict=True)
        if abs(dev) > max_size_change
    ]
    problems += [
        f"{t:%Y-%m}: tỷ lệ churn {row.churn:.2%} ngoài khoảng {churn_range[0]:.1%}–{churn_range[1]:.0%}"
        for t, row in per_t.iterrows()
        if not churn_range[0] <= row.churn <= churn_range[1]
    ]
    if problems:
        raise DataQualityError("Bảng học lệch phân phối bất thường:\n  " + "\n  ".join(problems))
