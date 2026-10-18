"""Mọi lab của Giai đoạn A (thư mục labs/ ở gốc repo) chạy hết từ đầu tới cuối trên nhà mạng thu nhỏ.

Lab là code người học chép và chạy theo bài — lab hỏng là bài học hỏng, nên lab cũng có test như code dự án.
"""

import socket
import subprocess
import sys
import time

import httpx
import pytest

from churn_telco import config

LABS = config.ROOT.parents[1] / "labs"
SCRIPTS = {
    "biz-01-co-ban-framing-churn/value_calc.py": "precision@500 phải",
    "data-01-co-ban-kham-pha-du-lieu/eda.py": "Năm nhận xét",
    "stat-02-co-ban-bootstrap/bootstrap_lab.py": "chênh lệch cặp",
    "data-03-trung-cap-ro-ri-du-lieu/leakage_lab.py": "Backtest gốc",
    "stat-05-trung-cap-nguong-chi-phi/threshold_lab.py": "xếp theo EV",
    "biz-03-trung-cap-phan-tich-loi/error_analysis.py": "SHAP",
    "ops-01-co-ban-dong-goi-api/security_check.py": "Phân loại dữ liệu",
    "biz-04-co-ban-trinh-bay/sensitivity.py": "câu chuyện 3 phút",
}


def run_lab(env: dict[str, str], script: str, *args: str) -> str:
    out = subprocess.run(
        [sys.executable, str(LABS / script), *args], env=env, capture_output=True, text=True, timeout=900
    )
    assert out.returncode == 0, f"{script}\n{out.stdout[-2000:]}\n{out.stderr[-3000:]}"
    return out.stdout


@pytest.mark.parametrize("script", list(SCRIPTS))
def test_lab_runs(small, script):
    assert SCRIPTS[script] in run_lab(small.env, script)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_api_lab_against_a_real_server(small):
    port = free_port()
    env = {**small.env, "CHURN_API_KEY": "khoa-lab", "CHURN_MODEL_DIR": str(small.root / "models" / "lgbm-v2")}
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "churn_telco.api:create_app", "--factory", "--port", str(port)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(60):
            try:
                if httpx.get(f"http://127.0.0.1:{port}/health", timeout=1, trust_env=False).status_code == 200:
                    break
            except httpx.TransportError:
                time.sleep(0.5)
        url = f"http://127.0.0.1:{port}"
        out = run_lab(env, "ops-01-co-ban-dong-goi-api/call_api.py", "--url", url, "--n-latency", "5")
    finally:
        server.terminate()
        server.wait(timeout=10)
    assert "Không có khoá: 401" in out and "request × 500 khách" in out
