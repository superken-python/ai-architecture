.PHONY: help setup test test-e2e eval bench smoke clean tls models up down pdf up-listen models-listen clean-models

help:
	@echo "Available commands:"
	@echo "  make setup     - Install dependencies for ai and web"
	@echo "  make tls       - Generate local TLS certs for nginx (requires mkcert)"
	@echo "  make models    - Download required AI models (Silero VAD & GGUF)"
	@echo "  make test      - Run unit & integration tests for ai and web"
	@echo "  make test-e2e  - Run Playwright E2E browser tests for web"
	@echo "  make eval      - Run golden set evaluation metrics"
	@echo "  make bench     - Run profile benchmark"
	@echo "  make smoke     - Run WebSocket smoke test against live server"
	@echo "  make pdf       - Convert Technical Design markdown to PDF with Mermaid diagrams"
	@echo "  make up        - Start all services (AI + Web) via docker compose"
	@echo "  make up-listen - Start listen-only stack (speech to text, no translation, 8 GB GPU)"
	@echo "  make models-listen - Prepare listen-only models (Silero VAD, PhoWhisper-large CT2, large-v3-turbo)"
	@echo "  make clean-models  - List models the listen-only stack does not use (add YES=1 to delete)"
	@echo "  make down      - Stop all services"

tls:
	@echo "Generating local TLS certificates..."
	mkdir -p config/tls
	mkcert -key-file config/tls/key.pem -cert-file config/tls/cert.pem localhost 127.0.0.1 ::1 $$( (hostname -I 2>/dev/null || ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $$2}') | tr '\n' ' ')

models:
	./scripts/download_models.sh

switch-qwen7b:
	./scripts/switch_to_qwen7b.sh

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

up-listen:
	./start.sh --listen

models-listen:
	./scripts/prepare_listen_models.sh

clean-models:
	./scripts/remove_unused_models.sh $(if $(YES),--yes,)

up-cpu:
	./start.sh --cpu

down:
	./docker/stop.sh

status:
	./start.sh --status

logs:
	./start.sh --logs
