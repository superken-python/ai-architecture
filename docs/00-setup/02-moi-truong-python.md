# 2 · Môi trường Python với uv

Dự án dùng [uv](https://docs.astral.sh/uv/) thay cho pip/venv/conda: một công cụ lo cả phiên bản Python,
môi trường ảo và thư viện, kèm **lockfile** (`uv.lock`) để mọi máy cài ra đúng cùng phiên bản.

## Ba file cần biết

| File | Vai trò | Ai sửa |
|---|---|---|
| `.python-version` | Phiên bản Python của dự án (3.12) | Hiếm khi đổi |
| `pyproject.toml` | Khai báo thư viện, chia theo **nhóm phụ thuộc** | Khi thêm/bớt thư viện |
| `uv.lock` | Phiên bản chính xác đã được giải — commit vào Git | uv tự sinh, không sửa tay |

## Nhóm phụ thuộc ↔ nhóm bài toán

Không cần cài tất cả (bản đầy đủ có PyTorch, nặng nhiều GB). Cài theo nhóm bài toán đang học — mỗi lệnh
`make setup-<nhóm>` **cài thêm** (không gỡ nhóm đã có) và luôn kèm nhóm `core`.

| Lệnh | Gói chính | Dùng cho |
|---|---|---|
| `make setup` | pytest, ruff, pre-commit, pyyaml | Bắt buộc — làm việc với repo |
| `make setup-core` | numpy, pandas, polars, duckdb, scipy, statsmodels, scikit-learn, jupyterlab, pydantic, httpx | Mọi nhóm |
| `make setup-tabular` | lightgbm, xgboost, catboost, shap, optuna | Nhóm 1 · Bảng (và 2, 3, 4, 8) |
| `make setup-timeseries` | statsforecast, mlforecast | Nhóm 2 · Thời gian |
| `make setup-anomaly` | pyod, networkx | Nhóm 3 · Bất thường |
| `make setup-recsys` | implicit, faiss-cpu | Nhóm 4 · Gợi ý |
| `make setup-vision` | torch, torchvision, ultralytics, opencv, onnxruntime, pymupdf, pdfplumber | Nhóm 5 · Ảnh/TL |
| `make setup-llm` | anthropic, openai, sentence-transformers, rank-bm25, qdrant-client, underthesea, langfuse | Nhóm 6 · LLM/RAG |
| `make setup-agent` | langgraph, mcp | Nhóm 7 · Agent |
| `make setup-optimization` | ortools, pulp, dowhy, econml | Nhóm 8 · Tối ưu & nhân quả |
| `make setup-mlops` | fastapi, uvicorn, mlflow, evidently | Triển khai (mọi nhóm) |
| `make setup-all` | tất cả | Khi máy đủ mạnh |

Ví dụ lộ trình 6 tháng: tháng 1–2 `make setup-tabular setup-mlops`, tháng 3–4 thêm `make setup-llm`,
tháng 5–6 thêm nhóm của bài toán chuyên sâu. Muốn dọn về tối thiểu: `uv sync` (không `--inexact`).

> Một số gói (PaddleOCR, VietOCR, vLLM, TensorRT...) phụ thuộc nhiều vào GPU/hệ điều hành nên **không**
> nằm trong lockfile chung. Cài chúng trong môi trường riêng của từng lab/dự án (xem `labs/README.md`).

## Lệnh uv hằng ngày

```bash
uv run python script.py            # chạy bằng môi trường dự án (không cần "activate")
uv run jupyter lab                 # mở notebook (cần nhóm core)
uv add --group llm tên-gói         # thêm thư viện vào một nhóm → cập nhật pyproject.toml + uv.lock
uv remove --group llm tên-gói      # gỡ
uv lock --upgrade-package tên-gói  # nâng một gói
uv run --with tên-gói lệnh         # dùng tạm một gói mà không thêm vào dự án (vd. kaggle CLI)
```

Quy tắc: thêm thư viện **luôn** qua `uv add` rồi commit cả `pyproject.toml` và `uv.lock` trong cùng PR.
Không `pip install` vào `.venv` — lần `uv sync` sau sẽ xóa mất và người khác không tái lập được.

## Notebook hay module?

- **Notebook** (`labs/.../*.ipynb`) để khám phá, vẽ biểu đồ, phân tích lỗi.
- **Module** (`src/`, `projects/.../src/`) cho code dùng lại, có test. Khi một đoạn code trong notebook được
  dùng lần thứ hai → chuyển nó sang module (kỹ năng PY-02).
- Xóa output notebook trước khi commit nếu output chứa dữ liệu thật.

## Kiểm tra

```bash
make doctor          # mục [4] liệt kê nhóm phụ thuộc đã cài
uv run python -c "import sklearn, pandas; print('ok')"   # sau make setup-core
```

Tiếp theo: [3 · API key và bí mật](03-api-key-va-bi-mat.md).
