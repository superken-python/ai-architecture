# POC CMB-10 · Excel agent: AgentOS + AG-UI + OpenAI Agents SDK. Gõ `make` để xem lệnh.
UV ?= uv
HOST ?= 127.0.0.1
PORT ?= 7777

.DEFAULT_GOAL := help
.PHONY: help setup setup-e2e dev data-api data test e2e lint format check clean

help: ## Hiện danh sách lệnh
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup: ## Cài môi trường (uv) + tạo .env từ mẫu nếu chưa có
	$(UV) sync
	@test -f .env || cp .env.example .env

setup-e2e: ## Cài Playwright cho test giao diện (dùng Chromium có sẵn nếu có)
	$(UV) sync --group e2e

dev: ## Chạy server (AgentOS + AG-UI + UI + API giả lập) tại http://HOST:PORT
	$(UV) run uvicorn excel_agent.main:create_app --factory --host $(HOST) --port $(PORT) --reload --reload-dir src --reload-dir prompts

data-api: ## Chạy riêng API dữ liệu giả lập ở cổng 8100 (khi MOUNT_MOCK_API=false)
	$(UV) run uvicorn excel_agent.mock_data_api.app:create_app --factory --host $(HOST) --port 8100

data: ## Sinh lại dữ liệu mẫu (cố định theo seed)
	$(UV) run python scripts/generate_sample_data.py

test: ## Test unit + integration (không cần API key, không cần mạng)
	$(UV) run pytest -m "not e2e"

e2e: ## Test giao diện bằng Chromium thật (sau `make setup-e2e`)
	$(UV) run --group e2e pytest -m e2e

lint: ## Kiểm tra code style
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format: ## Tự sửa code style
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

check: lint test ## Lint + test

clean: ## Xóa dữ liệu chạy thử (file Excel, SQLite) và cache
	rm -rf var .pytest_cache .ruff_cache test-results
