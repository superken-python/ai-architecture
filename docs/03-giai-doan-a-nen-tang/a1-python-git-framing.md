# A1 · Python, Git và framing bài toán

**Tuần 1** · Kỹ năng: [PY-01](../02-skill-map/generated/mang/py.md#py-01) Cơ bản,
[PY-02](../02-skill-map/generated/mang/py.md#py-02) Cơ bản, [BIZ-01](../02-skill-map/generated/mang/biz.md#biz-01) Cơ bản ·
Lab: [`labs/biz-01-co-ban-framing-churn/`](../../labs/biz-01-co-ban-framing-churn/README.md) ·
Sản phẩm: repo chạy được bằng một lệnh setup + framing 1 trang

Trước khi viết một dòng code ML, ta phải trả lời được: *model này thay đổi quyết định nào, đáng bao nhiêu tiền, và cần
đúng tới đâu?* Bài này trả lời các câu đó cho Sóng Xanh bằng con số. Song song, ta dựng khung dự án Python tái lập
được, dùng cho cả 7 bài sau.

**Sau bài này bạn làm được:**

- Viết lại "giảm churn" thành một bài toán đo được: *precision@500 mỗi tháng cho đội CSKH*, kèm ngưỡng hoà vốn.
- Tính giá trị kỳ vọng của một hành động (cuộc gọi) từ các giả định nghiệp vụ, bằng tay và bằng code.
- Dựng dự án `uv` theo cấu trúc `src/ tests/`, có lockfile, `.gitignore` chặn dữ liệu và secret, một `Makefile`.
- Viết module Python có type hints, `dataclass`, `pathlib`, `argparse`.

---

## 1 · Lý thuyết: framing — từ mục tiêu mơ hồ tới bài toán đo được

### 1.1 Bắt đầu từ quyết định, không phải từ model

"Giảm churn" là một **mục tiêu**, chưa phải **bài toán**. Model chỉ có giá trị khi nó làm thay đổi một quyết định
cụ thể của một người cụ thể. Ở Sóng Xanh, quyết định đó là:

> Đầu mỗi tháng, đội CSKH chọn **500 khách** để gọi giữ chân. Chọn ai?

Từ câu này suy ra mọi thứ khác:

| Câu hỏi framing | Trả lời cho Sóng Xanh |
|---|---|
| Quyết định nào thay đổi? | Danh sách 500 khách được gọi mỗi tháng (thay danh sách "sắp hết hợp đồng") |
| Ai dùng, dùng thế nào, bao lâu một lần? | Đội CSKH, đầu mỗi tháng nhận file danh sách + lý do; gọi trong tháng |
| KPI nghiệp vụ | Số khách giữ được mỗi tháng; lợi nhuận ròng của chương trình gọi |
| Metric kỹ thuật tương ứng | **precision@500 theo tháng** — trong 500 người được gọi có bao nhiêu người thật sự sắp rời |
| Loại sai nào đắt hơn? | Bỏ sót một khách sắp rời (mất ~1,5 triệu đ lợi nhuận) đắt hơn nhiều so với gọi nhầm (25.000 đ) |
| Cách làm hiện tại | Luật: sắp hết hợp đồng → gọi trước; hay báo lỗi mạng → gọi tiếp |
| Có cần AI không? | Thử luật trước (bài A3). Chỉ dùng model nếu nó vượt luật một cách có ý nghĩa thống kê |
| Ràng buộc | 500 cuộc/tháng; dữ liệu khách là dữ liệu cá nhân; danh sách cần trước ngày 1 hằng tháng |

Đây là bài toán **xếp hạng có năng lực giới hạn**, thuộc Nhóm 1 · dữ liệu bảng trong
[bản đồ bài toán](../01-problem-map/README.md). Ta không cần biết chắc *ai* sẽ rời. Ta cần **thứ tự**: 500 người
đứng đầu danh sách phải là những người đáng gọi nhất.

### 1.2 Hai loại sai và cái giá của chúng

Với mỗi khách trong danh sách gọi có hai khả năng sai:

- **Gọi nhầm** (false positive): khách không định rời. Ta mất 25.000 đ thời gian nhân viên, và có thể làm phiền khách.
- **Bỏ sót** (false negative): khách sắp rời nhưng không nằm trong danh sách. Ta mất cơ hội giữ một khách đáng khoảng
  1,5 triệu đ lợi nhuận (tính ở mục 1.3).

Vì vậy **accuracy là metric sai** cho bài toán này. Chỉ khoảng 2% khách rời mạng mỗi tháng. Một "model" đoán *không
ai rời cả* đúng 98% nhưng không giúp được ai (bài A2 tính con số này từ dữ liệu). Năng lực gọi cố định là 500 cuộc,
nên câu hỏi đúng là: **trong 500 người được gọi, bao nhiêu người thật sự sắp rời?** Đó chính là precision@500.

### 1.3 Giá trị kỳ vọng của một cuộc gọi — làm bằng tay

Phòng CSKH và phòng tài chính cung cấp các giả định sau (ghi vào `config.py`, mục A1.3):

| Giả định | Giá trị | Nguồn |
|---|---|---|
| Chi phí một cuộc gọi | 25.000 đ | thời gian nhân viên + tổng đài |
| Tỷ lệ khách sắp rời đồng ý ở lại khi được gọi | 30% | chiến dịch thử năm 2024 |
| Ưu đãi tặng khách đồng ý ở lại | 150.000 đ | chính sách CSKH |
| Khách giữ được ở thêm trung bình | 12 tháng | tài chính |
| Biên lợi nhuận gộp trên cước | 45% | tài chính |

**Giá trị của một khách giữ được** = cước tháng × 12 tháng × 45%. Ví dụ khách gói SX300 trả 320.000 đ/tháng:

    giá trị = 320.000 × 12 × 0,45 = 1.728.000 đ

Gọi một khách có xác suất rời mạng là **p**. Có ba trường hợp:

- Khách sắp rời (xác suất p) và đồng ý ở lại (30%): ta giữ được 1.728.000 đ, trả ưu đãi 150.000 đ.
- Khách sắp rời nhưng vẫn đi: ta chỉ mất phí cuộc gọi.
- Khách không định rời: ta chỉ mất phí cuộc gọi.

Gộp lại thành **giá trị kỳ vọng (EV)** của một cuộc gọi:

    EV(p) = p × 0,30 × (1.728.000 − 150.000) − 25.000
          = p × 473.400 − 25.000

Cuộc gọi có lãi khi EV > 0, tức **p > 25.000 / 473.400 ≈ 5,3%**. Đây là **xác suất hoà vốn**. Gói cước càng cao thì
khách càng đáng giữ, nên ngưỡng hoà vốn càng thấp.

Suy ra yêu cầu cho model. Nếu trung bình mỗi người trong danh sách 500 người có xác suất rời trên ~5%, tức
**precision@500 ≥ ~5%**, chương trình gọi mới hoà vốn. Tỷ lệ churn nền khoảng 2%, nên gọi ngẫu nhiên chắc chắn lỗ.
Model phải xếp hạng tốt hơn ngẫu nhiên ít nhất 2,5 lần mới bắt đầu có ích.

> **Ghi nhớ:** con số kỹ thuật (precision@500) luôn đi kèm con số tiền (lợi nhuận/tháng). Bài A8 sẽ trình bày kết
> quả bằng con số tiền; con số kỹ thuật dùng để so model với nhau.

### 1.4 Khi nào không cần ML?

Trước khi train bất cứ gì, hãy viết **cách làm hiện tại thành code** để có một baseline. Ở đây cách làm hiện tại là
luật CSKH "sắp hết hợp đồng → gọi". Nếu luật đã đạt precision@500 cao hơn mức cần, có khi không cần ML. Bài A3 đo
luật này: nó chỉ trúng **7,5%**, vừa đủ hoà vốn. Đó là lý do đáng thử một model.

---

## 2 · Lý thuyết: một dự án Python tái lập được

### 2.1 Vì sao `src/` + `tests/`, không phải một notebook dài

Notebook rất tốt để khám phá, nhưng tệ cho thứ phải chạy lại mỗi tháng: thứ tự ô có thể sai, khó test, khó review.
Quy ước trong khoá học:

- **Code dùng lại** nằm trong package `src/churn_telco/`. Mỗi bước pipeline là một module có hàm thuần (đầu vào → đầu
  ra), cộng một khối `if __name__ == "__main__":` để chạy bằng `python -m churn_telco.<bước>`.
- **Khám phá và thí nghiệm** nằm trong `labs/`, viết dạng script có ô `# %%`. Script này chạy được cả file lẫn từng ô
  trong VS Code.
- **Test** nằm trong `tests/`, chạy bằng `pytest`.

Layout `src/` buộc bạn *cài* package (`uv sync` cài ở chế độ editable) rồi mới import được. Nhờ vậy lỗi "chạy được trên
máy tôi vì tôi đứng đúng thư mục" không xảy ra.

### 2.2 `uv`, `pyproject.toml` và lockfile

- `pyproject.toml` khai báo **ý định**: cần những thư viện nào, phiên bản tối thiểu bao nhiêu.
- `uv.lock` ghi **kết quả**: phiên bản chính xác của *mọi* thư viện, kể cả thư viện gián tiếp, kèm mã băm.
  Lockfile **phải commit**. Máy khác chạy `uv sync --locked` sẽ ra môi trường giống hệt.
- Nhóm phụ thuộc (`[dependency-groups]`) tách thứ chỉ cần khi phát triển (pytest, ruff) hay khi phân tích (shap,
  mlflow) khỏi thứ cần khi chạy thật. Image Docker ở bài A7 chỉ cài nhóm lõi.

### 2.3 Git: commit gì, không commit gì

| Commit | KHÔNG BAO GIỜ commit |
|---|---|
| code, test, cấu hình, `uv.lock`, `Makefile` | dữ liệu khách (kể cả "chỉ là file thử") |
| `.env.example` (tên biến, không có giá trị thật) | `.env`, khoá API, mật khẩu |
| manifest bộ đánh giá (`eval/manifest.json`) | model đã train, `mlruns/` (sinh lại được bằng lệnh) |
| báo cáo kết quả nhỏ (`reports/`) | output notebook chứa dữ liệu |

Một file đã commit thì vẫn nằm trong **lịch sử Git** kể cả khi bạn xoá nó ở commit sau. Vì vậy `.gitignore` phải có
**trước** commit đầu tiên. Bài A7 có script rà cả lịch sử.

### 2.4 Python cho dữ liệu — năm thói quen dùng suốt khoá học

1. **`pathlib.Path`** thay cho chuỗi đường dẫn: `config.RAW / "customers.csv"` đúng trên mọi hệ điều hành.
2. **Type hints** cho mọi hàm: `def break_even(fee: float, a: Assumptions) -> float`. Người đọc biết ngay hàm nhận gì,
   trả gì, và công cụ kiểm tra bắt được lỗi sớm.
3. **`@dataclass(frozen=True)`** cho nhóm giá trị đi cùng nhau (các giả định nghiệp vụ). `frozen` để không ai lỡ tay
   sửa giữa chừng; muốn đổi thì `replace(a, save_rate=0.15)` tạo bản mới.
4. **Một chỗ cho hằng số**: đường dẫn, ngày, giả định nằm trong `config.py`, không rải rác trong code.
5. **CLI bằng `argparse`** và **`logging`** thay cho `print` trong code của package.

---

## 3 · Lab A1 — dựng khung dự án và quy bài toán ra tiền

### A1.1 Tạo dự án

```bash
mkdir -p projects/g1-churn-telco/src/churn_telco projects/g1-churn-telco/tests
cd projects/g1-churn-telco
echo '"""Dự đoán churn cho nhà mạng — real case của Giai đoạn A."""' > src/churn_telco/__init__.py
echo "3.12" > .python-version
git init    # nếu bạn làm trong repo riêng
```

Viết `pyproject.toml`. Ta khai báo **một lần** đủ thư viện cho cả 8 tuần, để không phải sửa file này ở mỗi bài:

**File: `pyproject.toml`**

```toml
[project]
name = "churn-telco"
version = "0.1.0"
description = "Real case Giai đoạn A: dự đoán khách rời mạng trong 30 ngày tới cho nhà mạng Sóng Xanh (dữ liệu mô phỏng)"
readme = "README.md"
requires-python = ">=3.12,<3.14"
# Phụ thuộc lõi = đủ để dựng dữ liệu, train và PHỤC VỤ model (image Docker chỉ cài nhóm này).
dependencies = [
  "numpy>=2.0",
  "pandas>=2.2",
  "pyarrow>=17",
  "duckdb>=1.1",
  "scikit-learn>=1.5",
  "lightgbm>=4.5",
  "pandera>=0.24",
  "fastapi>=0.115",
  "uvicorn>=0.30",
]

[dependency-groups]
# Phân tích và theo dõi thực nghiệm: dùng khi học/làm, KHÔNG cần trong container phục vụ.
research = ["shap>=0.46", "matplotlib>=3.9", "mlflow>=3.0"]
dev = ["pytest>=8", "httpx>=0.27", "ruff>=0.16,<0.17"]  # ruff cùng phiên bản với repo gốc

[tool.uv]
default-groups = ["research", "dev"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/churn_telco"]

[tool.ruff]
line-length = 120
target-version = "py312"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
filterwarnings = [
  # starlette mới khuyên đổi httpx → httpx2 cho TestClient; chưa ảnh hưởng hành vi
  "ignore:Using `httpx` with `starlette.testclient`:UserWarning",
]
```

Đọc file theo từng khối:

- **`dependencies`** — nhóm lõi, đủ để dựng dữ liệu, train và *phục vụ* model: numpy/pandas/pyarrow (bảng), duckdb
  (SQL tại máy), scikit-learn (baseline, hiệu chỉnh), lightgbm (model chính), pandera (kiểm tra dữ liệu), fastapi +
  uvicorn (API). Mỗi dòng có phiên bản tối thiểu (`>=`). `uv.lock` mới là nơi chốt phiên bản chính xác.
- **`[dependency-groups]`** — `research` (shap vẽ biểu đồ, matplotlib, mlflow) và `dev` (pytest, httpx cho test API,
  ruff). `default-groups` cài cả hai khi bạn chạy `uv sync`; Docker thì bỏ qua (`--no-default-groups`).
- **`ruff>=0.16,<0.17`** — cùng phiên bản với repo gốc, để định dạng code ở hai nơi giống nhau.
- **`[build-system]` + `packages = ["src/churn_telco"]`** — biến thư mục thành package cài được.
- **`[tool.ruff]`**, **`[tool.pytest.ini_options]`** — lint và test dùng chung cấu hình cho mọi người trong nhóm.
  `filterwarnings` tắt đúng một cảnh báo đã biết, không tắt hết.

Cài môi trường và tạo lockfile:

```bash
uv lock          # giải phiên bản → uv.lock
uv sync          # tạo .venv/, cài thư viện + package churn_telco (editable)
uv run python -c "import churn_telco, lightgbm; print(lightgbm.__version__)"
```

```text
4.7.0
```

### A1.2 Chặn dữ liệu và secret khỏi Git — trước commit đầu tiên

**File: `.gitignore`**

```gitignore
# Sinh ra khi chạy — KHÔNG commit (dữ liệu khách, dù mô phỏng, model và lịch sử thí nghiệm ở ngoài Git)
data/
models/
mlruns/
.env
```

`data/` chứa dữ liệu khách (kể cả mô phỏng — ta luyện thói quen như với dữ liệu thật). `models/` và `mlruns/` sinh lại
được bằng `make`, nên không cần lưu. `.env` chứa secret.

Secret (khoá API ở bài A7) được đọc từ biến môi trường. Repo chỉ chứa **mẫu** để người khác biết cần đặt biến gì:

**File: `.env.example`**

```bash
# Sao chép thành .env rồi đổi khoá (file .env KHÔNG commit — đã có trong .gitignore):
#   python -c "import secrets; print(secrets.token_urlsafe(32))"
CHURN_API_KEY=doi-khoa-nay-truoc-khi-chay
```

### A1.3 `config.py` — một chỗ cho đường dẫn, mốc thời gian và giả định

**File: `src/churn_telco/config.py`**

```python
"""Hằng số dùng chung: đường dẫn, mốc thời gian, giả định nghiệp vụ. Sửa một chỗ, mọi bước dùng theo.

Giả định nghiệp vụ (A1 — framing) do phòng CSKH và tài chính cung cấp; A8 phân tích độ nhạy của kết luận theo chúng.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]  # thư mục projects/g1-churn-telco
DATA = Path(os.getenv("CHURN_DATA", ROOT / "data"))
RAW = DATA / "raw"  # bảng thô như export từ hệ thống nguồn — không sửa
INTERIM = DATA / "interim"  # bảng đã làm sạch
PROCESSED = DATA / "processed"  # bảng feature + nhãn để học
MODELS = Path(os.getenv("CHURN_MODELS", ROOT / "models"))
EVAL_DIR = Path(os.getenv("CHURN_EVAL_DIR", ROOT / "eval"))  # manifest của bộ đánh giá đã đóng băng (có commit)
REPORTS = Path(os.getenv("CHURN_REPORTS", ROOT / "reports"))
# Biến môi trường CHURN_* cho phép test và lab chạy trên dữ liệu nhỏ ở thư mục tạm mà không đụng dữ liệu thật.

# ---------------------------------------------------------------- mốc thời gian
HISTORY_START = pd.Timestamp("2024-01-01")  # dữ liệu nguồn có từ ngày này
HISTORY_END = pd.Timestamp("2025-12-31")
EXPORT_DATE = pd.Timestamp("2026-01-05")  # ngày export CRM: cột "trạng thái hiện tại" phản ánh ngày này
HORIZON_DAYS = 30  # nhãn: khách gửi yêu cầu hủy trong 30 ngày sau ngày chấm điểm

# Ngày chấm điểm (snapshot) = ngày 1 mỗi tháng. Cần >= 6 tháng lịch sử để tính feature.
SNAPSHOTS = list(pd.date_range("2024-07-01", "2025-12-01", freq="MS"))
TRAIN_END = pd.Timestamp("2025-06-01")  # train: 2024-07 .. 2025-06
VALID_END = pd.Timestamp("2025-09-01")  # valid: 2025-07 .. 2025-09 (chọn model, ngưỡng)
# test (bộ đánh giá đóng băng): 2025-10 .. 2025-12 — chỉ dùng để báo cáo, không dùng để chọn gì

# ---------------------------------------------------------------- giả định nghiệp vụ
CALL_CAPACITY = 500  # đội giữ chân khách gọi được 500 khách mỗi tháng
CALL_COST = 25_000  # VND mỗi cuộc gọi (thời gian nhân viên + hạ tầng)
SAVE_RATE = 0.30  # gọi đúng khách sắp rời: 30% đồng ý ở lại (kết quả chiến dịch thử năm 2024)
OFFER_COST = 150_000  # VND ưu đãi tặng khách đồng ý ở lại
VALUE_MONTHS = 12  # một khách giữ được ở lại thêm trung bình 12 tháng
MARGIN = 0.45  # biên lợi nhuận gộp trên cước
SEED = 42
```

Đọc theo khối:

- **Đường dẫn.** `ROOT = Path(__file__).resolve().parents[2]` tìm thư mục dự án từ vị trí file. Lệnh chạy ở đâu thì
  đường dẫn vẫn đúng. Mỗi đường dẫn đọc được từ biến môi trường `CHURN_*`: test và lab chạy trên dữ liệu nhỏ trong
  thư mục tạm mà không đụng dữ liệu thật (bài A6).
- **Ba tầng dữ liệu.** `raw` là bản export gốc, không bao giờ sửa (là bằng chứng). `interim` là bản đã làm sạch.
  `processed` là bảng học. Sai ở bước nào thì chạy lại từ bước đó.
- **Mốc thời gian.** Lịch sử có từ 2024-01-01 tới 2025-12-31. `EXPORT_DATE = 2026-01-05` là ngày export CRM, cột
  "trạng thái hiện tại" trong CRM phản ánh ngày này (bài A4 sẽ thấy vì sao điều đó nguy hiểm). Ngày chấm điểm là ngày
  1 mỗi tháng. `TRAIN_END` và `VALID_END` chia lịch sử thành train / valid / test theo thời gian (bài A3).
- **Giả định nghiệp vụ.** Chính là bảng ở mục 1.3. Đặt ở đây để bài A8 thay giả định và xem kết luận có đổi không.

### A1.4 `Makefile` — bản đồ lệnh của cả khoá học

Mỗi bước pipeline có một lệnh `make`, và mỗi lệnh ghi bước học sinh ra nó. Hôm nay mới chạy được `setup`. Các lệnh
khác sẽ chạy được khi bạn viết tới module tương ứng.

**File: `Makefile`**

```makefile
# Dự án G1 · Churn nhà mạng Sóng Xanh — real case của Giai đoạn A. Gõ `make` để xem lệnh.
# Mỗi lệnh ghi bước học (A1–A8) sinh ra nó; lệnh của bước sau chỉ chạy được khi đã làm tới bước đó.
UV ?= uv
PORT ?= 8000

.DEFAULT_GOAL := help
.PHONY: help setup data clean-data features eval eval-valid train marketing train-v2 score track mlflow-ui serve \
	docker-up docker-down report all test lint format check clean

help: ## Hiện danh sách lệnh
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## (A1) Cài môi trường đúng theo uv.lock + tạo .env từ mẫu
	$(UV) sync --locked
	@test -f .env || (cp .env.example .env && echo "→ Đã tạo .env — đổi CHURN_API_KEY trước khi chạy API")

data: ## (A2) Sinh dữ liệu thô của các hệ nguồn → data/raw/ (cố định theo seed)
	$(UV) run python -m churn_telco.simulate

clean-data: ## (A2) Làm sạch data/raw/ → data/interim/
	$(UV) run python -m churn_telco.clean

features: clean-data ## (A4) Bảng học as-of + kiểm tra schema → data/processed/features.parquet
	$(UV) run python -m churn_telco.features

eval: ## (A3) Mọi baseline + model trên bộ đánh giá đóng băng, kèm KTC bootstrap → reports/eval_test.md
	$(UV) run python -m churn_telco.evaluate

eval-valid: ## (A3) Như eval, trên tập valid (dùng khi phát triển)
	$(UV) run python -m churn_telco.evaluate --split valid

train: ## (A5) LightGBM v1 → models/lgbm-v1/
	$(UV) run python -m churn_telco.train --feature-set v1

marketing: ## (A6) Feature khuyến mãi của đối thủ → data/processed/features_marketing.parquet
	$(UV) run python -m churn_telco.marketing

train-v2: marketing ## (A6) LightGBM v2 = v1 + feature marketing → models/lgbm-v2/
	$(UV) run python -m churn_telco.train --feature-set v2

score: ## (A6) Danh sách gọi tháng 01/2026 kèm 3 lý do → data/outputs/
	$(UV) run python -m churn_telco.score

track: ## (A7) Ghi mọi model trong models/ vào MLflow (mlruns/)
	$(UV) run python -m churn_telco.tracking $(wildcard models/*)

mlflow-ui: ## (A7) Giao diện MLflow tại http://127.0.0.1:5000
	$(UV) run mlflow ui --backend-store-uri sqlite:///mlruns/mlflow.db --port 5000

serve: ## (A7) API tại http://127.0.0.1:$(PORT) (khoá đọc từ .env)
	$(UV) run --env-file .env uvicorn churn_telco.api:create_app --factory --port $(PORT)

docker-up: ## (A7) Build image + chạy API trong Docker (cần .env, models/, data/outputs/)
	docker compose up --build -d
	@echo "→ http://127.0.0.1:8000/docs · 'docker compose ps' phải thấy (healthy) sau ~30 giây"

docker-down: ## (A7) Dừng container
	docker compose down

report: ## (A8) Báo cáo 1 trang → reports/README.md
	$(UV) run python -m churn_telco.report

all: data features train train-v2 eval score track report ## Chạy cả quy trình từ đầu (~2 phút)

test: ## Test (tự sinh dữ liệu nhỏ, không cần make data)
	$(UV) run pytest

lint: ## Kiểm tra code style
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format: ## Tự sửa code style
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

check: lint test ## Lint + test

clean: ## Xoá dữ liệu sinh ra, model, mlruns (giữ eval/manifest.json và reports/)
	rm -rf data models mlruns .pytest_cache .ruff_cache
```

- `make` (không tham số) in danh sách lệnh: dòng `help` đọc chú thích `## ...` sau mỗi target. Thêm lệnh mới là
  tài liệu tự cập nhật.
- `setup` dùng `uv sync --locked`: nếu `pyproject.toml` và `uv.lock` lệch nhau thì báo lỗi, không lặng lẽ cài phiên
  bản khác.
- `all` nối các bước theo đúng thứ tự phụ thuộc. Bài A8 dùng nó để chứng minh dự án tái lập được từ con số 0.

```bash
make setup
make            # xem danh sách lệnh
```

```text
  help         Hiện danh sách lệnh
  setup        (A1) Cài môi trường đúng theo uv.lock + tạo .env từ mẫu
  data         (A2) Sinh dữ liệu thô của các hệ nguồn → data/raw/ (cố định theo seed)
  clean-data   (A2) Làm sạch data/raw/ → data/interim/
  features     (A4) Bảng học as-of + kiểm tra schema → data/processed/features.parquet
  eval         (A3) Mọi baseline + model trên bộ đánh giá đóng băng, kèm KTC bootstrap → reports/eval_test.md
  ...
```

### A1.5 Lab: quy giả định ra tiền

Script của lab dùng chính `config.py` vừa viết. Lab nằm ngoài package nhưng chạy bằng môi trường của dự án
(`uv run --project`):

**File: `labs/biz-01-co-ban-framing-churn/value_calc.py`**

```python
"""Lab A1 · BIZ-01: quy bài toán churn ra tiền TRƯỚC khi có model — một cuộc gọi đáng bao nhiêu, cần đúng bao nhiêu.

Chưa cần dữ liệu: chỉ dùng giả định nghiệp vụ trong config.py (CSKH và tài chính cung cấp). Kết quả trả lời ba câu
mà framing 1 trang phải có: giá trị của một khách giữ được, xác suất hoà vốn của một cuộc gọi, và precision@500 cần
đạt để dự án đáng làm.

    cd labs/biz-01-co-ban-framing-churn
    uv run --project ../../projects/g1-churn-telco python value_calc.py
    uv run --project ../../projects/g1-churn-telco python value_calc.py --save-rate 0.15   # giả định xấu hơn
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace

from churn_telco import config

PLAN_FEES = {
    "SX50": 198_000,
    "SX150": 269_000,
    "SX300": 320_000,
    "SX150TV": 290_000,
    "SX300TV": 365_000,
    "COMBO": 450_000,
}


@dataclass(frozen=True)
class Assumptions:
    """Giả định nghiệp vụ — gom vào một chỗ để đổi một giá trị là thấy kết luận đổi theo."""

    call_cost: float = config.CALL_COST
    save_rate: float = config.SAVE_RATE
    offer_cost: float = config.OFFER_COST
    value_months: int = config.VALUE_MONTHS
    margin: float = config.MARGIN
    capacity: int = config.CALL_CAPACITY


def customer_value(fee: float, a: Assumptions) -> float:
    """Lợi nhuận gộp giữ lại được nếu khách ở thêm `value_months` tháng."""
    return fee * a.value_months * a.margin


def call_ev(p: float, fee: float, a: Assumptions) -> float:
    """Giá trị kỳ vọng của MỘT cuộc gọi tới khách có xác suất rời mạng p."""
    return p * a.save_rate * (customer_value(fee, a) - a.offer_cost) - a.call_cost


def break_even(fee: float, a: Assumptions) -> float:
    """p tối thiểu để cuộc gọi không lỗ: giải call_ev(p) = 0."""
    return a.call_cost / (a.save_rate * (customer_value(fee, a) - a.offer_cost))


def monthly_profit(precision: float, fee: float, a: Assumptions) -> float:
    """Lợi nhuận ròng một tháng khi gọi đủ `capacity` khách và `precision` trong số đó thật sự sắp rời."""
    hits = precision * a.capacity
    return hits * a.save_rate * (customer_value(fee, a) - a.offer_cost) - a.capacity * a.call_cost


def vnd(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".") + " đ"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Quy bài toán churn ra tiền")
    parser.add_argument("--save-rate", type=float, default=config.SAVE_RATE, help="tỷ lệ khách đồng ý ở lại")
    parser.add_argument("--capacity", type=int, default=config.CALL_CAPACITY, help="số cuộc gọi mỗi tháng")
    args = parser.parse_args(argv)
    a = replace(Assumptions(), save_rate=args.save_rate, capacity=args.capacity)
    print(f"Giả định: {a}\n")

    print(f"{'Gói':8} {'Cước/tháng':>12} {'Giá trị 1 khách':>16} {'p hoà vốn':>10}")
    for plan, fee in PLAN_FEES.items():
        print(f"{plan:8} {vnd(fee):>12} {vnd(customer_value(fee, a)):>16} {break_even(fee, a):>10.1%}")

    fee = sum(PLAN_FEES.values()) / len(PLAN_FEES)  # cước trung bình (đơn giản hoá cho framing)
    # precision cần đạt = xác suất hoà vốn: trung bình mỗi người trong danh sách phải "đáng" một cuộc gọi
    print(f"\nCước trung bình {vnd(fee)} → precision@{a.capacity} phải ≥ {break_even(fee, a):.1%} mới hoà vốn")
    print(f"\n{'Kịch bản':16} {'precision':>9} {'gọi trúng':>10} {'giữ được':>9} {'lợi nhuận/tháng':>17}")
    for label, precision in [("Ngẫu nhiên", 0.02), ("Cách hiện tại?", 0.07), ("Mục tiêu", 0.15), ("Rất tốt", 0.30)]:
        hits = precision * a.capacity
        profit = monthly_profit(precision, fee, a)
        print(f"{label:16} {precision:>9.0%} {hits:>10.0f} {hits * a.save_rate:>9.0f} {vnd(profit):>17}")


if __name__ == "__main__":
    main()
```

Giải thích:

- **`Assumptions`** là `dataclass(frozen=True)`, giá trị mặc định lấy từ `config`. `replace(Assumptions(),
  save_rate=0.15)` tạo một bản giả định mới, không sửa bản gốc. Đây là cách thử "nếu giả định sai thì sao".
- **`customer_value`, `call_ev`, `break_even`, `monthly_profit`** là đúng các công thức ở mục 1.3, mỗi công thức một
  hàm nhỏ có type hints. Hàm nhỏ thì dễ test và dễ dùng lại: bài A5 viết lại chúng trong `decision.py` cho cả bảng.
- **`main(argv=None)`** nhận tham số dòng lệnh qua `argparse`. Truyền `argv` là một danh sách (thay vì đọc
  `sys.argv`) giúp test gọi được `main(["--save-rate", "0.15"])`.

Chạy với giả định gốc:

```bash
cd labs/biz-01-co-ban-framing-churn
uv run --project ../../projects/g1-churn-telco python value_calc.py
```

```text
Giả định: Assumptions(call_cost=25000, save_rate=0.3, offer_cost=150000, value_months=12, margin=0.45, capacity=500)

Gói        Cước/tháng  Giá trị 1 khách  p hoà vốn
SX50        198.000 đ      1.069.200 đ       9.1%
SX150       269.000 đ      1.452.600 đ       6.4%
SX300       320.000 đ      1.728.000 đ       5.3%
SX150TV     290.000 đ      1.566.000 đ       5.9%
SX300TV     365.000 đ      1.971.000 đ       4.6%
COMBO       450.000 đ      2.430.000 đ       3.7%

Cước trung bình 315.333 đ → precision@500 phải ≥ 5.4% mới hoà vốn

Kịch bản         precision  gọi trúng  giữ được   lợi nhuận/tháng
Ngẫu nhiên              2%         10         3      -7.841.600 đ
Cách hiện tại?          7%         35        10       3.804.400 đ
Mục tiêu               15%         75        22      22.438.000 đ
Rất tốt                30%        150        45      57.376.000 đ
```

Đọc kết quả:

- Dòng SX300 khớp phép tính tay ở mục 1.3: giá trị 1.728.000 đ, hoà vốn 5,3%. **Luôn kiểm code bằng một ví dụ tính
  tay.**
- Gọi ngẫu nhiên lỗ ~7,8 triệu đ/tháng. Danh sách hiện tại (~7%, ta sẽ đo thật ở bài A3) chỉ vừa có lãi. Nếu model
  đạt precision@500 khoảng 30%, chương trình lãi ~57 triệu đ/tháng.
- Thử giả định xấu hơn: `--save-rate 0.15`. Khi đó danh sách hiện tại **lỗ**, còn mức "mục tiêu" chỉ lãi khoảng 5
  triệu. Kết luận phụ thuộc mạnh vào tỷ lệ giữ chân, nên bài A8 sẽ đề nghị đo lại con số này.

### A1.6 Viết framing 1 trang

Chép bảng ở mục 1.1 vào phần **1 · ĐÚNG — framing** của `README.md` dự án (theo
[mẫu dự án](../../templates/project/README.md)). Thêm vào đó các con số vừa tính: ngưỡng hoà vốn ~5,4%, mục tiêu
precision@500 ≥ 15% so với ~7% hiện tại. Xem bản hoàn chỉnh ở
[README của dự án](../../projects/g1-churn-telco/README.md).

Một framing tốt phải trả lời được câu hỏi của người không làm ML: *"Nếu dự án thành công thì tháng sau có gì khác?"*
Ở đây câu trả lời là: đội CSKH gọi đúng 500 cuộc như cũ, nhưng trúng gấp nhiều lần số người sắp rời, và biết nói gì
với từng người.

### A1.7 Commit đầu tiên

```bash
git add .gitignore .env.example .python-version pyproject.toml uv.lock Makefile README.md src/
git status --short      # KHÔNG được thấy data/, models/, .env
git commit -m "feat(churn): khung dự án, config và framing"
```

---

## 4 · Kiểm tra kết quả

- [ ] Clone repo sang thư mục khác, chạy `make setup`: môi trường cài xong không cần sửa gì (`uv sync --locked`).
- [ ] `uv run python -c "from churn_telco import config; print(config.ROOT)"` in đúng thư mục dự án.
- [ ] `value_calc.py` cho SX300 ra 1.728.000 đ và 5,3%, khớp phép tính tay.
- [ ] README dự án có framing đủ 8 dòng ở mục 1.1, kèm metric precision@500/tháng và ngưỡng hoà vốn.
- [ ] `git log --all --name-only` không có `data/`, `.env` (bài A7 có script kiểm tra tự động).

## 5 · Lỗi thường gặp

| Triệu chứng | Nguyên nhân | Cách sửa |
|---|---|---|
| `ModuleNotFoundError: churn_telco` | chạy `python` của hệ thống thay vì môi trường dự án | luôn chạy qua `uv run ...` hoặc `make` |
| Máy bạn chạy, máy đồng nghiệp lỗi phiên bản | chưa commit `uv.lock` hoặc cài bằng `pip install` | commit `uv.lock`, dùng `uv sync --locked` |
| Đường dẫn sai khi chạy từ thư mục khác | dùng đường dẫn tương đối kiểu `"data/raw"` | dùng `config.RAW` (tính từ vị trí file) |
| Lỡ commit `.env` | thêm `.gitignore` sau commit đầu | đổi ngay khoá đó (coi như đã lộ), rồi mới dọn lịch sử |

## 6 · Bài tập

1. **(Cơ bản)** Thêm cột "EV nếu p = 20%" vào bảng theo gói trong `value_calc.py`. Gói nào đáng gọi nhất?
2. **(Cơ bản)** Đội CSKH đề xuất tăng ưu đãi lên 300.000 đ. Precision@500 tối thiểu thay đổi thế nào? Viết thành một
   câu cho trưởng phòng.
3. **(Trung cấp)** Viết `tests/test_value_calc.py` (tạm đặt trong thư mục lab) kiểm tra `break_even` bằng ví dụ tính
   tay, và kiểm tra `call_ev(break_even(...)) == 0`.
4. **(Mở rộng — BIZ-01 Trung cấp)** Gọi nhầm khách không định rời có thể làm họ *khó chịu*. Giả sử 2% khách bị gọi
   nhầm phàn nàn và cứ 10 lời phàn nàn thì mất 1 khách. Cập nhật công thức EV và cho biết kết luận có đổi không.

---

**Tiếp theo:** [A2 · SQL, pandas và thống kê mô tả](a2-sql-pandas-thong-ke.md). Ta sinh dữ liệu của 4 hệ thống nguồn,
đếm xem nó "bẩn" tới mức nào, làm sạch, và rút ra 5 nhận xét có số liệu.
