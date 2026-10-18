"""A4: bảng học đúng thời điểm. Test quan trọng nhất của dự án là `test_point_in_time`: dựng lại feature tại t từ dữ
liệu đã bị CẮT về đúng những gì hệ thống biết tại t — kết quả phải giống hệt bản dựng từ dữ liệu đầy đủ. Feature nào
lén dùng thông tin sau t sẽ cho giá trị khác và test đỏ.
"""

import pandas as pd
import pandera.pandas as pa
import pytest

from churn_telco import features, schemas
from churn_telco.features import KEYS, LABEL, META


def feature_part(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=[LABEL, *META]).set_index(KEYS).sort_index()


@pytest.mark.parametrize("t", ["2024-11-01", "2025-06-01", "2025-12-01"])
def test_point_in_time(small, t):
    t = pd.Timestamp(t)
    full = features.build(features.connect(small.interim), [t])
    as_of = features.build(features.connect_as_of(small.interim, t), [t])
    pd.testing.assert_frame_equal(feature_part(full), feature_part(as_of), check_categorical=False)


def test_point_in_time_catches_created_at_leak(small, monkeypatch):
    """Lọc ticket theo created_at (lúc khách gọi) thay vì logged_at (lúc vào hệ thống) — test phải bắt được."""
    monkeypatch.setattr(features, "FEATURE_SQL", features.FEATURE_SQL.replace("logged_at", "created_at"))
    t = pd.Timestamp("2025-06-01")
    full = features.build(features.connect(small.interim), [t])
    as_of = features.build(features.connect_as_of(small.interim, t), [t])
    with pytest.raises(AssertionError):
        pd.testing.assert_frame_equal(feature_part(full), feature_part(as_of), check_categorical=False)


def test_build_is_bit_for_bit_reproducible(small):
    a, b = (features.build(features.connect(small.interim)) for _ in range(2))
    pd.testing.assert_frame_equal(a, b, check_exact=True)


def test_population_and_keys(small):
    df, customers = small.df, small.clean["customers"].set_index("customer_id")
    assert not df.duplicated(KEYS).any()
    signup = customers.loc[df["customer_id"], "signup_date"].to_numpy()
    assert (signup < df["t"].to_numpy()).all()
    done = small.clean["cancellations"].query("status == 'Hoàn tất'").set_index("customer_id")["request_date"]
    gone = df["customer_id"].map(done)
    assert not (gone < df["t"]).any()  # không ai còn trong bảng sau khi đã gửi yêu cầu hủy


def test_label_matches_cancellations(small):
    done = small.clean["cancellations"].query("status == 'Hoàn tất'")[["customer_id", "request_date"]]
    df = small.df[KEYS + [LABEL]].merge(done, on="customer_id", how="left")
    in_window = (df["request_date"] >= df["t"]) & (df["request_date"] < df["t"] + pd.Timedelta(days=30))
    assert (in_window.astype(int) == df[LABEL]).all()


def test_revoked_cancellation_is_not_churn(small):
    revoked = small.clean["cancellations"].query("status == 'Đã hoàn tác'")["customer_id"]
    finished = small.clean["cancellations"].query("status == 'Hoàn tất'")["customer_id"]
    only_revoked = set(revoked) - set(finished)
    assert only_revoked
    assert small.df.loc[small.df["customer_id"].isin(only_revoked), LABEL].sum() == 0


def test_cancel_request_tickets_are_not_features(small):
    """tickets_30d không đếm ticket "Yêu cầu hủy" — nếu đếm, đó là proxy của nhãn."""
    t = pd.Timestamp("2025-06-01")
    tickets = small.clean["tickets"]
    window = tickets[(tickets["logged_at"] < t) & (tickets["logged_at"] >= t - pd.Timedelta(days=30))]
    got = small.df[small.df["t"] == t].set_index("customer_id")["tickets_30d"]
    expected = window[window["category"] != "Yêu cầu hủy"].groupby("customer_id").size()
    pd.testing.assert_series_equal(got, expected.reindex(got.index, fill_value=0).astype(float), check_names=False)


def test_schema_rejects_duplicated_rows(small):
    broken = pd.concat([small.df.head(100), small.df.head(1)], ignore_index=True)  # như một JOIN nhân đôi dòng
    with pytest.raises(pa.errors.SchemaErrors):
        schemas.FEATURES.validate(broken, lazy=True)


def test_schema_rejects_out_of_range_values(small):
    broken = small.df.head(100).copy()
    broken.loc[broken.index[0], "fee_change_90d"] = 3.0  # giá tăng 300%: gần như chắc chắn là lỗi dữ liệu
    with pytest.raises(pa.errors.SchemaErrors, match="fee_change_90d"):
        schemas.FEATURES.validate(broken, lazy=True)


def test_snapshot_check_detects_missing_month_of_data(small):
    df = small.df
    last = df["t"].max()
    broken = df[(df["t"] != last) | (df["customer_id"] < "KH001000")]  # tháng cuối mất 2/3 khách
    with pytest.raises(schemas.DataQualityError, match=f"{last:%Y-%m}"):
        schemas.check_snapshots(broken)


def test_validate_clean_rejects_pii(small, tmp_path):
    for name in schemas.CLEAN:
        pd.read_parquet(small.interim / f"{name}.parquet").to_parquet(tmp_path / f"{name}.parquet")
    customers = pd.read_parquet(tmp_path / "customers.parquet").assign(phone="0900000000")
    customers.to_parquet(tmp_path / "customers.parquet")
    with pytest.raises(schemas.DataQualityError, match="PII"):
        schemas.validate_clean(tmp_path)


def test_marketing_feature_is_as_of(small):
    """Đợt khuyến mãi HCM bắt đầu 2025-06-15: tại t = 2025-06-01 chưa biết, tại 2025-07-01 đã biết."""
    rows = small.df[small.df["province"] == "TP. Hồ Chí Minh"].groupby("t")["competitor_promo_30d"].mean()
    assert rows[pd.Timestamp("2025-06-01")] == 0
    assert rows[pd.Timestamp("2025-07-01")] == 1
    assert rows[pd.Timestamp("2025-11-01")] == 0  # kết thúc 2025-09-30, quá 30 ngày
