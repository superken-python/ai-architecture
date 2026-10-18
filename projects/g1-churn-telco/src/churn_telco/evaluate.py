"""Harness đánh giá một lệnh (A3 · BIZ-02): `make eval` = mọi baseline + mọi model đã train, trên CÙNG bộ đánh giá đóng
băng, kèm khoảng tin cậy bootstrap và chênh lệch cặp so với baseline tham chiếu.

    uv run python -m churn_telco.evaluate                  # tập test đóng băng → reports/eval.md + reports/eval.json
    uv run python -m churn_telco.evaluate --split valid    # tập valid (dùng khi phát triển)
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from churn_telco import baselines, config, features, metrics, split

log = logging.getLogger(__name__)
REFERENCE = "Logistic"  # baseline tham chiếu: model phải vượt nó mới đáng thêm độ phức tạp

Scorer = Callable[[pd.DataFrame], np.ndarray]


def candidates(train: pd.DataFrame, models_dir: Path = config.MODELS) -> dict[str, Scorer]:
    """Baseline (học lại mỗi lần chạy, vài giây) + mọi model đã lưu trong models/*/bundle.json."""
    logistic = baselines.fit_logistic(train)
    scorers: dict[str, Scorer] = dict(baselines.RULES)
    scorers[REFERENCE] = lambda df: logistic.predict_proba(df[logistic.feature_names_in_])[:, 1]
    bundles = sorted(models_dir.glob("*/bundle.json"))
    if bundles:  # model LightGBM có từ A5; trước đó harness chỉ chấm baseline
        from churn_telco import train as training

        for path in bundles:
            bundle = training.load(path.parent)
            scorers[bundle.meta["name"]] = bundle.score
    return scorers


def run(
    which: str = "test",
    n_boot: int = 1000,
    processed: Path = config.PROCESSED,
    manifest: Path = split.MANIFEST,
    models_dir: Path = config.MODELS,
) -> pd.DataFrame:
    df = features.load(processed)
    if not manifest.exists():  # lần chạy đầu tiên: đóng băng trước khi nhìn bất kỳ kết quả nào
        log.warning("Chưa có %s — đóng băng tập test ngay bây giờ: %s", manifest, split.freeze(df, manifest))
    parts = split.split(df)
    frame = split.frozen_test(df, manifest) if which == "test" else parts[which]
    scores = {name: score(frame) for name, score in candidates(parts["train"], models_dir).items()}
    return metrics.bootstrap(scores, frame, n_boot=n_boot, reference=REFERENCE)


def save(results: pd.DataFrame, which: str, out: Path = config.REPORTS) -> str:
    out.mkdir(parents=True, exist_ok=True)
    text = f"Tập: **{which}** · KTC 95% bootstrap theo khách · tham chiếu: {REFERENCE}\n\n{metrics.table(results)}\n"
    (out / f"eval_{which}.md").write_text(text, encoding="utf-8")
    (out / f"eval_{which}.json").write_text(results.to_json(orient="records", force_ascii=False, indent=1), "utf-8")
    return text


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--split", choices=["valid", "test"], default="test")
    parser.add_argument("--n-boot", type=int, default=1000)
    args = parser.parse_args(argv)
    print(save(run(args.split, args.n_boot), args.split))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
