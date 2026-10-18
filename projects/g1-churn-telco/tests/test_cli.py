"""Các lệnh `make` chạy thật từ đầu tới cuối (tiến trình con, dữ liệu nhỏ ở thư mục tạm): train → eval → score →
MLflow → báo cáo. Bắt lỗi kiểu "chạy từng hàm thì được, ghép lại thì hỏng"."""

import json
import subprocess
import sys

import pytest


def run(small, *args: str) -> str:
    out = subprocess.run([sys.executable, "-m", *args], env=small.env, capture_output=True, text=True, timeout=600)
    assert out.returncode == 0, out.stderr[-3000:]
    return out.stdout + out.stderr


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_make_targets_end_to_end(small):
    assert "LightGBM v1" in run(small, "churn_telco.train", "--feature-set", "v1")
    table = run(small, "churn_telco.evaluate", "--n-boot", "50")
    assert "LightGBM v1" in table and "LightGBM v2" in table and "Luật CSKH hiện tại" in table
    assert "gọi" in run(small, "churn_telco.score")
    assert list((small.data / "outputs").glob("call_list_2026-01-01.*"))
    tracked = run(small, "churn_telco.tracking", str(small.root / "models" / "lgbm-v1"))
    assert "run" in tracked and (small.root / "mlruns" / "mlflow.db").exists()
    report = run(small, "churn_telco.report")
    assert "Báo cáo 1 trang" in report
    assert (small.root / "reports" / "profit_curve.png").exists()
    results = json.loads((small.root / "reports" / "eval_test.json").read_text())
    assert {r["model"] for r in results} >= {"Logistic", "LightGBM v1", "LightGBM v2"}
