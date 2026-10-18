"""Khối feature marketing (A6): lịch khuyến mãi của đối thủ theo tỉnh — nguồn dữ liệu MỚI tìm ra nhờ phân tích lỗi.

Phòng marketing theo dõi các đợt khuyến mãi của đối thủ (data/marketing/competitor_promotions.csv). Dữ liệu này
không nằm trong CRM/billing nên bảng học ban đầu không có. Feature vẫn phải as-of: chỉ tính đợt đã BẮT ĐẦU trước t.

    uv run python -m churn_telco.marketing     # → data/processed/features_marketing.parquet (features.load tự ghép)
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

from churn_telco import config
from churn_telco.features import KEYS

log = logging.getLogger(__name__)

PROMO = ["competitor_promo_30d"]

PROMO_SQL = """
SELECT b.t, b.customer_id, (count(m.province) > 0)::DOUBLE AS competitor_promo_30d
FROM base b LEFT JOIN promotions m
    ON m.province = b.province
    AND m.start_date < b.t                         -- đợt đã bắt đầu trước t (biết được tại t)
    AND m.end_date >= b.t - INTERVAL 30 DAY        -- và còn chạy trong 30 ngày trước t
GROUP BY ALL
ORDER BY b.t, b.customer_id                        -- thứ tự cố định: file ra giống hệt mỗi lần (mã băm dữ liệu ổn định)
"""


def read_promotions(path: Path = config.DATA / "marketing" / "competitor_promotions.csv") -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["start_date", "end_date"])


def build(base: pd.DataFrame, promotions: pd.DataFrame) -> pd.DataFrame:
    """base: bảng có (t, customer_id, province) — thường là bảng học của features.build."""
    con = duckdb.connect()
    con.register("base", base[[*KEYS, "province"]].astype({"province": str}))
    con.register("promotions", promotions)
    df = con.execute(PROMO_SQL).df()
    df["t"] = pd.to_datetime(df["t"])
    return df


def build_all(processed: Path = config.PROCESSED) -> pd.DataFrame:
    base = pd.read_parquet(processed / "features.parquet", columns=[*KEYS, "province"])
    df = build(base, read_promotions())
    df.to_parquet(processed / "features_marketing.parquet", index=False)
    log.info(
        "features_marketing.parquet: %d dòng, %.1f%% dòng có khuyến mãi đối thủ", len(df), 100 * df[PROMO[0]].mean()
    )
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    build_all()
