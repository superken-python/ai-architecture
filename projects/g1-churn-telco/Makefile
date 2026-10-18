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
