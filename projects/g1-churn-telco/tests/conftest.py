"""Fixture dùng chung: chạy TOÀN BỘ pipeline trên một nhà mạng thu nhỏ (≈ 3.000 khách) trong thư mục tạm.

Mất vài giây, chạy một lần cho cả phiên test. Test không đụng tới data/ và models/ thật của dự án.
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from churn_telco import clean, features, marketing, simulate, split, train

SMALL = simulate.SimConfig(n_initial=3000, new_per_month=80)


def env_for(root: Path) -> dict[str, str]:
    """Biến môi trường trỏ mọi đường dẫn của config sang thư mục tạm — cho test chạy lệnh/lab ở tiến trình con."""
    paths = {"CHURN_DATA": "data", "CHURN_MODELS": "models", "CHURN_EVAL_DIR": "eval", "CHURN_REPORTS": "reports"}
    return {**os.environ, **{k: str(root / v) for k, v in paths.items()}, "CHURN_MLRUNS": str(root / "mlruns")}


@pytest.fixture(scope="session")
def small(tmp_path_factory: pytest.TempPathFactory) -> SimpleNamespace:
    root = tmp_path_factory.mktemp("churn")
    data = root / "data"
    tables = simulate.simulate(SMALL)
    simulate.write_raw(tables, data / "raw")
    cleaned = clean.clean_all(data / "raw", data / "interim")
    base = features.build_all(data / "interim", data / "processed")
    promos = marketing.read_promotions(data / "marketing" / "competitor_promotions.csv")
    marketing.build(base, promos).to_parquet(data / "processed" / "features_marketing.parquet", index=False)
    df = features.load(data / "processed")
    split.freeze(df, root / "eval" / "manifest.json")
    train.save(train.train(df, "v1"), root / "models" / "lgbm-v1")  # model của A5 (lab A5, A6 cần)
    bundle = train.train(df, "v2")
    train.save(bundle, root / "models" / "lgbm-v2")
    return SimpleNamespace(
        root=root,
        data=data,
        raw=data / "raw",
        interim=data / "interim",
        processed=data / "processed",
        tables=tables,
        clean=cleaned,
        df=df,
        promos=promos,
        bundle=bundle,
        env=env_for(root),
    )
