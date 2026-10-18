"""A2: dữ liệu thô "bẩn" đúng như mô tả, và mỗi quy tắc làm sạch xử lý đúng một loại lỗi."""

import unicodedata

import pandas as pd
import pytest

from churn_telco import clean, simulate


def test_simulation_is_reproducible():
    cfg = simulate.SimConfig(n_initial=300, new_per_month=10, months=6)
    a, b = simulate.simulate(cfg), simulate.simulate(cfg)
    for name in a:
        pd.testing.assert_frame_equal(a[name], b[name])


def test_raw_data_has_the_documented_problems(small):
    raw = small.tables
    customers = raw["customers"]
    assert customers["customer_id"].duplicated().any()  # export trùng
    assert (customers["date_of_birth"] == pd.Timestamp("1900-01-01")).any()  # ngày sinh mặc định
    assert customers["channel"].isna().any()
    assert any(p != unicodedata.normalize("NFC", p) for p in customers["province"])  # chuỗi NFD
    tickets = raw["tickets"]
    assert (tickets["logged_at"].dt.normalize() > tickets["created_at"].dt.normalize()).any()  # ticket vào hệ thống trễ
    assert (raw["cancellations"]["status"] == "Đã hoàn tác").any()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("TP.HCM", "TP. Hồ Chí Minh"),
        ("Ho Chi Minh", "TP. Hồ Chí Minh"),
        ("HN", "Hà Nội"),
        ("TP. Hà Nội", "Hà Nội"),
        ("Khánh Hoà", "Khánh Hòa"),  # dấu đặt kiểu cũ
        (unicodedata.normalize("NFD", "Đà Nẵng"), "Đà Nẵng"),  # cùng chữ, khác byte
        ("Huế", "Thừa Thiên Huế"),
    ],
)
def test_normalize_province(raw, expected):
    assert clean.normalize_province(raw) == expected


def test_unknown_province_is_kept_not_guessed():
    assert clean.normalize_province("Sao Hỏa") == "Sao Hỏa"


def test_clean_customers(small):
    customers = small.clean["customers"]
    assert not set(clean.PII_COLUMNS) & set(customers.columns)
    assert customers["customer_id"].is_unique
    assert not (customers["date_of_birth"] == pd.Timestamp("1900-01-01")).any()
    assert customers["channel"].notna().all()
    assert clean.unknown_values(small.clean) == {"province": [], "category": []}


def test_dedup_keeps_latest_update():
    raw = pd.DataFrame(
        {
            "customer_id": ["KH1", "KH1"],
            "full_name": ["A", "A"],
            "phone": ["0", "0"],
            "email": ["x", "x"],
            "province": ["HN", "Hà Nội"],
            "channel": ["Online", "Online"],
            "date_of_birth": pd.to_datetime(["1990-01-15", "1990-01-15"]),
            "updated_at": pd.to_datetime(["2025-12-01", "2024-01-01"]),
        }
    )
    out = clean.clean_customers(raw)
    assert len(out) == 1 and out.loc[0, "updated_at"] == pd.Timestamp("2025-12-01")


def test_clean_invoices_flags_adjustments_and_drops_exact_duplicates(small):
    invoices = small.clean["invoices"]
    assert invoices["invoice_id"].is_unique
    assert (invoices.loc[invoices["is_adjustment"], "amount"] < 0).all()
