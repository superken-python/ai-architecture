# Các lệnh thường dùng. Gõ `make` hoặc `make help` để xem danh sách.
# Mọi lệnh Python chạy qua `uv run` để luôn dùng đúng môi trường của dự án.

UV ?= uv
GROUPS := core tabular timeseries anomaly recsys vision llm agent optimization mlops

.DEFAULT_GOAL := help
.PHONY: help setup setup-all $(addprefix setup-,$(GROUPS)) doctor catalog catalog-check site site-serve site-test lint format test check clean

help: ## Hiện danh sách lệnh
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
	@echo "  setup-<nhóm>     Cài thêm một nhóm phụ thuộc: $(GROUPS)"

# --inexact: chỉ cài thêm, không gỡ các nhóm đã cài trước đó.
# Muốn dọn môi trường về tối thiểu (chỉ dev): chạy `uv sync` (không có --inexact).
setup: ## Cài môi trường tối thiểu (dev) + git hooks
	$(UV) sync --inexact
	$(UV) run pre-commit install

setup-all: ## Cài TẤT CẢ nhóm phụ thuộc (nặng, nhiều GB)
	$(UV) sync --all-groups

# Mỗi nhóm luôn kèm `core` (numpy, pandas, scikit-learn...). Ví dụ: make setup-tabular setup-llm
$(addprefix setup-,$(GROUPS)): setup-%:
	$(UV) sync --inexact $(foreach g,$(sort core $*),--group $(g))

doctor: ## Kiểm tra môi trường (Python, công cụ, GPU, khóa bí mật)
	$(UV) run python scripts/check_env.py

catalog: ## Kiểm tra catalog/ và sinh lại docs/02-skill-map/generated/
	$(UV) run python -m aiarch.catalog build

catalog-check: ## Báo lỗi nếu tài liệu sinh tự động đã cũ (dùng trong CI)
	$(UV) run python -m aiarch.catalog build --check

site: ## Sinh trang web (GitHub Pages) vào _site/
	$(UV) run python -m aiarch.site build

site-serve: ## Sinh trang web rồi mở http://localhost:8000
	$(UV) run python -m aiarch.site serve

site-test: ## Kiểm thử trang web bằng Chromium thật (Playwright)
	$(UV) run --with playwright python scripts/smoke_site.py

lint: ## Kiểm tra code style
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format: ## Tự sửa code style
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

test: ## Chạy test
	$(UV) run pytest

check: lint test catalog-check ## Chạy mọi kiểm tra như CI

clean: ## Xóa file tạm
	rm -rf .pytest_cache .ruff_cache _site
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
