"""Lab A7 · OPS-08: rà soát trước khi push — repo không chứa secret, không chứa dữ liệu khách, output không lộ PII.

Bốn kiểm tra, mỗi cái in ✔ hoặc ✘; có ✘ thì thoát mã 1 (gắn được vào pre-commit hoặc CI):
1. File đang được Git theo dõi không chứa chuỗi giống khoá bí mật và không có file .env thật.
2. Lịch sử Git chưa từng chứa .env hay dữ liệu thô của dự án (xoá ở commit sau vẫn còn trong lịch sử!).
3. Thư mục dữ liệu, model, mlruns của dự án nằm trong .gitignore.
4. Bảng trung gian và danh sách gọi không có cột/giá trị PII (tên, số điện thoại, email).
Cuối cùng in bảng phân loại dữ liệu: cột nào được phép rời khỏi hệ thống, tới đâu.

    cd labs/ops-01-co-ban-dong-goi-api
    uv run --project ../../projects/g1-churn-telco python security_check.py
"""

import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
from churn_telco import config
from churn_telco.clean import PII_COLUMNS

REPO = config.ROOT.parents[1]
PROJECT = config.ROOT.relative_to(REPO).as_posix()
SECRET_PATTERNS = {
    "khoá riêng (private key)": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "OpenAI/Anthropic key": re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
}
PHONE = re.compile(r"(?<![\d.])0[35789]\d{8}(?!\d)")  # 10 số bắt đầu 03/05/07/08/09, không phải phần thập phân
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
problems: list[str] = []


def git(*args: str) -> list[str]:
    out = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


def check(ok: bool, message: str) -> None:
    print(f"   {'✔' if ok else '✘'} {message}")
    if not ok:
        problems.append(message)


# 1. File đang theo dõi
print("1) File Git đang theo dõi:")
tracked = git("ls-files")
env_files = [f for f in tracked if Path(f).name.startswith(".env") and not f.endswith(".env.example")]
check(not env_files, f"không có file .env thật ({env_files or 'không có'})")
hits = []
for name in tracked:
    path = REPO / name
    if path.suffix in {".png", ".jpg", ".parquet", ".lock", ".ico", ".pdf"} or not path.is_file():
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    hits += [f"{name}: {kind}" for kind, pattern in SECRET_PATTERNS.items() if pattern.search(text)]
check(not hits, f"không có chuỗi giống khoá bí mật trong {len(tracked)} file ({hits[:3] or 'sạch'})")

# 2. Lịch sử Git
print("2) Lịch sử Git (mọi commit, mọi nhánh):")
ever = set(git("log", "--all", "--name-only", "--format="))
bad = sorted(f for f in ever if (Path(f).name == ".env") or f.startswith(f"{PROJECT}/data/"))
check(not bad, f"chưa từng commit .env hay {PROJECT}/data/ ({bad[:3] or 'sạch'})")

# 3. .gitignore
print("3) .gitignore:")
for folder in ("data/raw/customers.csv", "models/lgbm-v2/model.txt", "mlruns/mlflow.db", ".env"):
    ignored = subprocess.run(["git", "check-ignore", "-q", f"{PROJECT}/{folder}"], cwd=REPO).returncode == 0
    check(ignored, f"{PROJECT}/{folder} bị Git bỏ qua")

# 4. PII trong dữ liệu đã xử lý và output
print("4) PII trong dữ liệu sau bước làm sạch:")
for path in sorted(config.INTERIM.glob("*.parquet")) + sorted(config.PROCESSED.glob("*.parquet")):
    columns = set(pd.read_parquet(path).columns)
    check(not columns & set(PII_COLUMNS), f"{path.relative_to(config.DATA)}: không có cột {PII_COLUMNS}")
for path in sorted((config.DATA / "outputs").glob("*.csv")):
    text = path.read_text(encoding="utf-8-sig")
    check(
        not (PHONE.search(text) or EMAIL.search(text)), f"{path.relative_to(config.DATA)}: không có số điện thoại/email"
    )

print("\nPhân loại dữ liệu — được phép đi đâu:")
print("   | Dữ liệu                         | Ví dụ                     | Được phép                              |")
print("   |---------------------------------|---------------------------|----------------------------------------|")
print("   | Định danh cá nhân (PII)         | tên, SĐT, email           | chỉ trong CRM, không vào pipeline ML   |")
print("   | Mã khách (bí danh)              | KH000113                  | nội bộ: pipeline, API, danh sách gọi   |")
print("   | Hành vi theo khách              | data dùng, ticket, cước   | nội bộ; KHÔNG gửi API bên ngoài (LLM)  |")
print("   | Số tổng hợp ≥ 50 khách mỗi ô    | tỷ lệ churn theo tỉnh     | báo cáo, slide, gửi đối tác            |")
print("   | Secret                          | CHURN_API_KEY             | chỉ biến môi trường / .env cục bộ      |")
if problems:
    print(f"\n✘ {len(problems)} vấn đề — sửa trước khi push")
    sys.exit(1)
print("\n✔ Sạch — có thể push")
