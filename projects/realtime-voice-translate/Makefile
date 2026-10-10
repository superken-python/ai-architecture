.PHONY: help setup test test-e2e eval bench smoke clean tls up down pdf

help:
	@echo "Available commands:"
	@echo "  make setup     - Install dependencies for ai and web"
	@echo "  make tls       - Generate local TLS certs for nginx (requires mkcert)"
	@echo "  make test      - Run unit & integration tests for ai and web"
	@echo "  make test-e2e  - Run Playwright E2E browser tests for web"
	@echo "  make eval      - Run golden set evaluation metrics"
	@echo "  make bench     - Run profile benchmark"
	@echo "  make smoke     - Run WebSocket smoke test against live server"
	@echo "  make pdf       - Convert Technical Design markdown to PDF with Mermaid diagrams"
	@echo "  make up        - Start all services (AI + Web) via docker compose"
	@echo "  make down      - Stop all services"

tls:
	@echo "Generating local TLS certificates..."
	mkdir -p config/tls
	mkcert -install
	mkcert -key-file config/tls/key.pem -cert-file config/tls/cert.pem localhost 127.0.0.1 ::1 $$(hostname -I 2>/dev/null | awk '{print $$1}' || echo "127.0.0.1")

setup:
	cd ai && uv sync
	cd web && npm install

test:
	cd ai && uv run pytest tests
	cd web && npm test

test-e2e:
	cd web && npx playwright test

eval:
	PYTHONPATH=ai/src uv run python eval/run_eval.py

bench:
	PYTHONPATH=ai/src uv run python eval/bench_models.py

smoke:
	PYTHONPATH=ai/src uv run python scripts/smoke_ws.py

pdf:
	node scripts/convert_md_to_pdf.js

up:
	./start.sh

up-gpu:
	./start.sh --gpu

up-cpu:
	./start.sh --cpu

down:
	./docker/stop.sh

status:
	./start.sh --status

logs:
	./start.sh --logs
