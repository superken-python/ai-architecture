"""Chấm điểm hằng tháng (A6 · A7): ngày chấm điểm MỚI (chưa có nhãn) → danh sách gọi kèm 3 lý do cho CSKH.

Dữ liệu lịch sử tới 2025-12-31, nên lần chấm điểm "thật" đầu tiên là t = 2026-01-01: dựng feature as-of tại t bằng
đúng code của bảng học, chấm điểm, xếp theo giá trị kỳ vọng, giữ tối đa 500 khách có EV > 0, sinh lý do.
File kết quả chỉ có mã khách — CSKH tra số điện thoại trong CRM (có phân quyền), dữ liệu cá nhân không rời hệ nguồn.

    uv run python -m churn_telco.score --t 2026-01-01      # → data/outputs/call_list_2026-01-01.{csv,parquet}
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from churn_telco import config, decision, explain, features, marketing, schemas, train
from churn_telco.features import KEYS, LABEL, META

log = logging.getLogger(__name__)

OUTPUTS = config.DATA / "outputs"
COLUMNS = ["t", "rank", "customer_id", "p", "value", "ev", "province", "plan_code"]


def build_features(
    t: pd.Timestamp, interim: Path = config.INTERIM, promotions: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Feature tại một ngày chấm điểm — cùng SQL với bảng học, nên train và chấm điểm không lệch nhau."""
    df = features.build(features.connect(interim), [t]).drop(columns=[LABEL, *META])  # tương lai chưa có nhãn
    schemas.FEATURES.remove_columns([LABEL]).validate(df, lazy=True)
    if promotions is not None:
        df = df.merge(marketing.build(df, promotions), on=KEYS, how="left", validate="one_to_one")
    return df


def call_list(bundle: train.Bundle, df: pd.DataFrame, capacity: int = config.CALL_CAPACITY) -> pd.DataFrame:
    calls = decision.call_list(df, bundle.proba(df), capacity)
    top = calls[calls["call"]].sort_values("rank")
    return top[COLUMNS].join(explain.reasons(bundle, top))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Chấm điểm một ngày và xuất danh sách gọi cho CSKH")
    parser.add_argument("--t", type=pd.Timestamp, default=pd.Timestamp("2026-01-01"))
    parser.add_argument("--model", type=Path, default=config.MODELS / "lgbm-v2")
    parser.add_argument("--capacity", type=int, default=config.CALL_CAPACITY)
    args = parser.parse_args(argv)
    bundle = train.load(args.model)
    promos = marketing.read_promotions() if "competitor_promo_30d" in bundle.features else None
    df = build_features(args.t, promotions=promos)
    out = call_list(bundle, df, args.capacity)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    stem = OUTPUTS / f"call_list_{args.t:%Y-%m-%d}"
    out.to_parquet(stem.with_suffix(".parquet"), index=False)
    out.to_csv(stem.with_suffix(".csv"), index=False, encoding="utf-8-sig")  # utf-8-sig: Excel mở đúng tiếng Việt
    log.info(
        "%s: chấm %d khách, gọi %d (EV trung bình %.0f đ, xác suất trung bình %.1f%%) → %s.csv",
        f"{args.t:%Y-%m-%d}",
        len(df),
        len(out),
        out["ev"].mean(),
        100 * out["p"].mean(),
        stem,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
