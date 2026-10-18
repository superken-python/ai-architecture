"""Ghi mỗi lần train vào MLflow (A7 · OPS-02): tham số, metric, phiên bản dữ liệu, commit và chính model.

Training (A5) đã ghi mọi thứ vào models/<tên>/bundle.json; module này chỉ "gửi" bundle đó lên MLflow, nên tracking
không làm rối code train và thay MLflow bằng công cụ khác chỉ phải sửa một file. Kho MLflow cục bộ: mlruns/ (SQLite +
thư mục artifact), xem bằng `make mlflow-ui`.

    uv run python -m churn_telco.tracking models/lgbm-v1 models/lgbm-v2
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")  # tắt dòng gợi ý in ra mỗi lần import mlflow

import mlflow  # noqa: E402

from churn_telco import config  # noqa: E402

MLRUNS = Path(os.getenv("CHURN_MLRUNS", config.ROOT / "mlruns"))
EXPERIMENT = "churn-30d"


def setup(store: Path = MLRUNS) -> str:
    store.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{store / 'mlflow.db'}")
    if mlflow.get_experiment_by_name(EXPERIMENT) is None:
        mlflow.create_experiment(EXPERIMENT, artifact_location=(store / "artifacts").as_uri())
    mlflow.set_experiment(EXPERIMENT)
    return mlflow.get_tracking_uri()


def log_bundle(path: Path, store: Path = MLRUNS, eval_report: Path | None = None) -> str:
    """Một run MLflow cho một bundle; trả về run_id."""
    setup(store)
    meta = json.loads((path / "bundle.json").read_text(encoding="utf-8"))
    with mlflow.start_run(run_name=meta["name"]) as run:
        mlflow.log_params({f"lgb.{k}": v for k, v in meta["params"].items()})
        mlflow.log_params({"feature_set": meta["feature_set"], "n_features": len(meta["features"])})
        mlflow.log_params(
            {"best_iteration": meta["best_iteration"], "train_period": "..".join(meta["data"]["train_period"])}
        )
        mlflow.log_metrics(
            {f"valid_{k.replace('@k', f'_at_{config.CALL_CAPACITY}')}": v for k, v in meta["valid"].items()}
        )
        mlflow.set_tags(
            {
                "data.features_sha256": meta["data"].get("features_sha256", "chưa ghi"),
                "git_commit": meta.get("git_commit") or "không có",
                "model_version": meta.get("version", meta["feature_set"]),
            }
        )
        mlflow.log_artifacts(str(path), artifact_path="bundle")  # model.txt + bundle.json: tải về là phục vụ được
        if eval_report and eval_report.exists():
            mlflow.log_artifact(str(eval_report))
        return run.info.run_id


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ghi bundle model vào MLflow")
    parser.add_argument("bundles", type=Path, nargs="+")
    args = parser.parse_args(argv)
    report = config.REPORTS / "eval_test.md"
    for path in args.bundles:
        print(f"{path.name}: run {log_bundle(path, eval_report=report)} → {mlflow.get_tracking_uri()}")


if __name__ == "__main__":
    main()
