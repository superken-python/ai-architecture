"""Huấn luyện LightGBM (A5 · ML-02): early stopping trên valid, hiệu chỉnh Platt trên valid, lưu model dạng text.

Một "bundle" = thư mục models/<tên>/ gồm:
- model.txt  — cây LightGBM dạng văn bản (đọc được, không dùng pickle: nạp pickle từ nguồn lạ = chạy code lạ);
- bundle.json — mọi thứ cần để tái lập và phục vụ: danh sách feature, tham số, số vòng, hệ số hiệu chỉnh, metric trên
  valid, mã băm dữ liệu, phiên bản thư viện, commit git. API (A7) và MLflow (A7) đều chỉ đọc bundle này.

    uv run python -m churn_telco.train --feature-set v1     # → models/lgbm-v1/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import platform
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from churn_telco import config, decision, features, metrics, split
from churn_telco.features import CATEGORICAL, LABEL, NUMERIC

log = logging.getLogger(__name__)

FEATURE_SETS = {
    "v1": CATEGORICAL + NUMERIC,  # A5: dữ liệu CRM, billing, helpdesk, đo mạng
    "v2": CATEGORICAL + NUMERIC + ["competitor_promo_30d"],  # A6: thêm lịch khuyến mãi của đối thủ (marketing)
}
PARAMS = {
    "objective": "binary",
    "metric": "average_precision",  # early stopping theo PR-AUC trên valid
    "learning_rate": 0.03,
    "num_leaves": 31,
    "min_data_in_leaf": 100,  # lá phải có ≥ 100 dòng: churn hiếm, lá nhỏ là học thuộc nhiễu
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "lambda_l2": 1.0,
    "seed": config.SEED,
    "deterministic": True,
    "force_row_wise": True,
    "verbose": -1,
}


@dataclass
class Bundle:
    booster: lgb.Booster
    meta: dict

    @property
    def features(self) -> list[str]:
        return self.meta["features"]

    def score(self, df: pd.DataFrame) -> np.ndarray:
        """Xác suất thô của LightGBM — dùng để xếp hạng."""
        return self.booster.predict(df[self.features], num_iteration=self.meta["best_iteration"])

    def proba(self, df: pd.DataFrame) -> np.ndarray:
        """Xác suất đã hiệu chỉnh — dùng để tính giá trị kỳ vọng và chọn ngưỡng."""
        return decision.apply_platt(self.score(df), **self.meta["calibration"])


def file_sha256(*paths: Path) -> str:
    h = hashlib.sha256()
    for path in paths:
        h.update(path.read_bytes())
    return h.hexdigest()


def git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=config.ROOT)
        return out.stdout.strip() or None
    except OSError:
        return None


def train(df: pd.DataFrame, feature_set: str = "v1", params: dict = PARAMS, rounds: int = 3000) -> Bundle:
    cols = FEATURE_SETS[feature_set]
    parts = split.split(df)
    tr, va = parts["train"], parts["valid"]
    dtrain = lgb.Dataset(tr[cols], tr[LABEL])  # cột category của pandas → LightGBM tự xử lý biến phân loại
    dvalid = lgb.Dataset(va[cols], va[LABEL], reference=dtrain)
    booster = lgb.train(
        params,
        dtrain,
        num_boost_round=rounds,
        valid_sets=[dvalid],
        callbacks=[lgb.early_stopping(100, verbose=False), lgb.log_evaluation(0)],
    )
    raw_valid = booster.predict(va[cols], num_iteration=booster.best_iteration)
    meta = {
        "name": f"LightGBM {feature_set}",
        "feature_set": feature_set,
        "features": cols,
        "params": params,
        "best_iteration": booster.best_iteration,
        "calibration": decision.fit_platt(raw_valid, va[LABEL].to_numpy()),
        "valid": metrics.evaluate(metrics.rank(raw_valid, va[LABEL], va["t"])),
        "data": {
            "train_rows": len(tr),
            "valid_rows": len(va),
            "train_period": [f"{tr['t'].min():%Y-%m}", f"{tr['t'].max():%Y-%m}"],
            "valid_period": [f"{va['t'].min():%Y-%m}", f"{va['t'].max():%Y-%m}"],
        },
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "versions": {"python": platform.python_version(), "lightgbm": lgb.__version__, "pandas": pd.__version__},
        "git_commit": git_commit(),
    }
    return Bundle(booster, meta)


def save(bundle: Bundle, out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    bundle.booster.save_model(out / "model.txt", num_iteration=bundle.meta["best_iteration"])
    (out / "bundle.json").write_text(json.dumps(bundle.meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def load(path: Path) -> Bundle:
    meta = json.loads((path / "bundle.json").read_text(encoding="utf-8"))
    return Bundle(lgb.Booster(model_file=path / "model.txt"), meta)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Huấn luyện LightGBM cho churn 30 ngày")
    parser.add_argument("--feature-set", choices=list(FEATURE_SETS), default="v1")
    parser.add_argument("--out", type=Path, default=None, help="mặc định models/lgbm-<feature-set>")
    args = parser.parse_args(argv)
    df = features.load()
    bundle = train(df, args.feature_set)
    files = sorted(config.PROCESSED.glob("features*.parquet"))
    bundle.meta["data"]["features_sha256"] = file_sha256(*files)  # "phiên bản dữ liệu" của lần train này
    bundle.meta["data"]["files"] = [f.name for f in files]
    bundle.meta["version"] = f"{args.feature_set}-{bundle.meta['data']['features_sha256'][:8]}"
    out = save(bundle, args.out or config.MODELS / f"lgbm-{args.feature_set}")
    v = bundle.meta["valid"]
    log.info(
        "%s: %d vòng · valid AUC %.3f · PR-AUC %.3f · P@%d %.3f → %s",
        bundle.meta["name"],
        bundle.meta["best_iteration"],
        v["auc"],
        v["pr_auc"],
        config.CALL_CAPACITY,
        v["p@k"],
        out,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
