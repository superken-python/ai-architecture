# Dự án G9 · Video dạy chữ cái tiếng Việt. Gõ `make` để xem lệnh.
# Thứ tự thường dùng: make setup → make assets → make preview → make video → make qa
# Đổi nhân vật: chép video vào assets/nhan-vat/nguon/, sửa `characters` trong kịch bản → make sprites
UV ?= uv

.DEFAULT_GOAL := help
.PHONY: help setup assets sprites voice preview video clip qa test lint format check clean

help: ## Hiện danh sách lệnh
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup: ## Cài môi trường đúng theo uv.lock (cần thêm ffmpeg của hệ điều hành)
	$(UV) sync --locked
	@command -v ffmpeg >/dev/null || echo "→ Chưa có ffmpeg: macOS 'brew install ffmpeg', Ubuntu 'sudo apt install ffmpeg'"

assets: ## Tải font, hình minh họa, giọng đọc, model nghe lại vào .cache/ (~150 MB, một lần)
	$(UV) run python -m chu_cai_video assets --asr

sprites: ## Tách nhân vật khỏi video gốc → assets/nhan-vat/*.webp (chỉ khi đổi nhân vật; tải ~350 MB mô hình lần đầu)
	$(UV) run --group sprites python -m chu_cai_video sprites

voice: ## Đọc mọi câu của kịch bản, in độ dài từng câu so với khúc nhạc
	$(UV) run python -m chu_cai_video voice

preview: ## Vẽ vài khung hình xem thử → out/khung-*.png (vài giây)
	$(UV) run python -m chu_cai_video frame

video: ## Dựng cả video 3 phút → media/video-chu-cai.mp4 + poster.jpg + chuong.vtt + phu-de.vtt (~3 phút)
	$(UV) run python -m chu_cai_video render

clip: ## Dựng thử 15 giây đầu → out/thu.mp4
	$(UV) run python -m chu_cai_video render --end 15 --out out/thu.mp4

qa: ## Máy nghe lại từng câu (ASR) → reports/kiem-tra-giong.md
	$(UV) run python -m chu_cai_video qa

test: ## Test (không cần mạng, không cần model)
	$(UV) run pytest

lint: ## Kiểm tra code style
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format: ## Tự sửa code style
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

check: lint test ## Lint + test

clean: ## Xoá khung hình và âm thanh trung gian (giữ .cache/ và media/)
	rm -rf out .pytest_cache .ruff_cache
