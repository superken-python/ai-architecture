# POC CMB-10 · Excel agent: AgentOS + AG-UI + agent Agno + Office add-in. Gõ `make` để xem lệnh.
UV ?= uv
HOST ?= 127.0.0.1
PORT ?= 7777
CERT_DIR ?= $(HOME)/.office-addin-dev-certs
BASE_URL ?= https://localhost:$(PORT)

.DEFAULT_GOAL := help
.PHONY: help setup setup-e2e dev dev-https addin-certs addin-manifest data-api data test e2e lint format check clean

help: ## Hiện danh sách lệnh
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## Cài môi trường (uv) + tạo .env từ mẫu nếu chưa có
	$(UV) sync
	@test -f .env || cp .env.example .env

setup-e2e: ## Cài Playwright cho test giao diện (dùng Chromium có sẵn nếu có)
	$(UV) sync --group e2e

dev: ## Chạy server (AgentOS + AG-UI + UI + API giả lập) tại http://HOST:PORT
	$(UV) run uvicorn excel_agent.main:create_app --factory --host $(HOST) --port $(PORT) --reload --reload-dir src --reload-dir prompts

addin-certs: ## Tạo + tin cậy chứng chỉ HTTPS localhost cho Office add-in (cần Node.js, một lần)
	npx --yes office-addin-dev-certs install

dev-https: ## Chạy server qua HTTPS (https://localhost:PORT) để Excel nạp task pane
	$(UV) run uvicorn excel_agent.main:create_app --factory --host localhost --port $(PORT) --reload --reload-dir src --reload-dir prompts \
		--ssl-keyfile $(CERT_DIR)/localhost.key --ssl-certfile $(CERT_DIR)/localhost.crt

addin-manifest: ## Sinh var/manifest.xml trỏ tới BASE_URL (mặc định https://localhost:PORT)
	@mkdir -p var
	sed 's#https://localhost:7777#$(BASE_URL)#g' addin/manifest.xml > var/manifest.xml
	@echo "→ var/manifest.xml trỏ tới $(BASE_URL)"

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
