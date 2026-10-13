.PHONY: setup dev run lint format test eval help

help:
	@echo "Các lệnh khả dụng cho dự án gemini-excel-ai-agent:"
	@echo "  make setup   - Cài đặt thư viện bằng Poetry"
	@echo "  make dev     - Chạy dev server FastAPI & Office Add-in UI (reload)"
	@echo "  make format  - Định dạng mã nguồn bằng Ruff"
	@echo "  make lint    - Kiểm tra linter bằng Ruff"
	@echo "  make test    - Chạy bộ kiểm thử tự động pytest"

setup:
	poetry install

dev:
	poetry run uvicorn excel_agent.main:app --reload --host 0.0.0.0 --port 8000

run:
	poetry run python -m excel_agent.main

format:
	poetry run ruff format .

lint:
	poetry run ruff check .

test:
	poetry run pytest tests/ -v
