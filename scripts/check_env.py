#!/usr/bin/env python3
"""Kiểm tra môi trường học tập — chỉ dùng thư viện chuẩn, chạy được cả trước khi cài gì.

    python scripts/check_env.py      # hoặc: make doctor

Không bao giờ in giá trị của khóa bí mật, chỉ in "đã đặt"/"chưa đặt".
"""

from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

OK, WARN, FAIL = "✓", "!", "✗"

# Nhóm phụ thuộc trong pyproject.toml → gói đại diện để kiểm tra đã cài chưa.
GROUP_PROBES = {
    "core": ["numpy", "pandas", "sklearn", "duckdb"],
    "tabular": ["lightgbm", "xgboost", "catboost", "shap"],
    "timeseries": ["statsforecast", "mlforecast"],
    "anomaly": ["pyod", "networkx"],
    "recsys": ["implicit", "faiss"],
    "vision": ["torch", "ultralytics", "cv2", "onnxruntime"],
    "llm": ["anthropic", "openai", "sentence_transformers", "underthesea"],
    "agent": ["langgraph", "mcp"],
    "optimization": ["ortools", "pulp", "dowhy"],
    "mlops": ["fastapi", "mlflow"],
}

SECRET_KEYS = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "HF_TOKEN", "LANGFUSE_SECRET_KEY"]


def line(status: str, label: str, detail: str = "") -> None:
    print(f"  {status} {label:<28} {detail}")


def tool_version(cmd: list[str]) -> str | None:
    if not shutil.which(cmd[0]):
        return None
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (out.stdout or out.stderr).strip().splitlines()
    return text[0] if text else ""


def read_dotenv_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    keys = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw and not raw.startswith("#") and "=" in raw:
            key, value = raw.split("=", 1)
            if value.strip().strip("\"'"):
                keys.add(key.strip())
    return keys


def main() -> int:
    problems = 0
    print(f"\nHệ điều hành: {platform.system()} {platform.release()} ({platform.machine()})")

    print("\n[1] Python")
    v = sys.version_info
    if (3, 11) <= (v.major, v.minor) < (3, 14):
        line(OK, "Python", platform.python_version())
    else:
        line(FAIL, "Python", f"{platform.python_version()} — cần 3.11–3.13 (khuyên dùng 3.12)")
        problems += 1
    in_venv = sys.prefix != sys.base_prefix
    line(OK if in_venv else WARN, "Môi trường ảo", sys.prefix if in_venv else "chưa ở trong venv — dùng `uv run ...`")

    print("\n[2] Công cụ dòng lệnh")
    for name, cmd, required in [
        ("git", ["git", "--version"], True),
        ("uv", ["uv", "--version"], True),
        ("make", ["make", "--version"], False),
        ("docker", ["docker", "--version"], False),
    ]:
        ver = tool_version(cmd)
        if ver is not None:
            line(OK, name, ver)
        else:
            line(FAIL if required else WARN, name, "chưa cài" + ("" if required else " (tùy chọn)"))
            problems += required

    print("\n[3] GPU")
    smi = tool_version(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"])
    if smi:
        line(OK, "NVIDIA GPU", smi)
    elif platform.system() == "Darwin" and platform.machine() == "arm64":
        line(OK, "Apple Silicon", "PyTorch dùng backend MPS")
    else:
        line(WARN, "GPU", "không thấy — đủ cho Nhóm 1–4, 6–8; Nhóm 5 nên dùng Colab/Kaggle")

    print("\n[4] Nhóm phụ thuộc đã cài (make setup-<tên>)")
    for group, modules in GROUP_PROBES.items():
        found = [m for m in modules if importlib.util.find_spec(m) is not None]
        if len(found) == len(modules):
            line(OK, group, "đủ")
        elif found:
            missing = ", ".join(sorted(set(modules) - set(found)))
            line(WARN, group, f"thiếu: {missing}")
        else:
            line(" ", group, "chưa cài")

    print("\n[5] Khóa bí mật (chỉ kiểm tra có/không, không in giá trị)")
    dotenv = ROOT / ".env"
    file_keys = read_dotenv_keys(dotenv)
    line(OK if dotenv.exists() else WARN, ".env", "có" if dotenv.exists() else "chưa có — `cp .env.example .env`")
    for key in SECRET_KEYS:
        where = "biến môi trường" if os.environ.get(key) else ".env" if key in file_keys else None
        line(OK if where else " ", key, f"đã đặt ({where})" if where else "chưa đặt")

    print("\n[6] An toàn Git")
    tracked = tool_version(["git", "-C", str(ROOT), "ls-files", ".env"])
    if tracked:
        line(FAIL, ".env bị commit", "XÓA khỏi Git ngay và đổi khóa!")
        problems += 1
    else:
        line(OK, ".env không bị theo dõi", "")

    print()
    if problems:
        print(f"{FAIL} Có {problems} vấn đề cần xử lý — xem docs/00-setup/06-xu-ly-su-co.md")
        return 1
    print(f"{OK} Môi trường sẵn sàng.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
