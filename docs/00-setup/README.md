# 00 · Setup — chuẩn bị môi trường trước khi học

Làm phần này **một lần** trước khi bắt đầu bất kỳ kỹ năng nào. Mục tiêu: mọi người trong nhóm có môi trường
giống hệt nhau, chạy lại được kết quả của nhau, và không ai vô tình làm lộ khóa bí mật hay dữ liệu thật.

## Bắt đầu nhanh (khoảng 15 phút)

```bash
# 1. Cài Git và uv (chi tiết theo hệ điều hành: 01-cong-cu-can-cai.md)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Lấy mã nguồn
git clone https://github.com/superken-python/ai-architecture.git
cd ai-architecture

# 3. Tạo môi trường (uv tự tải Python 3.12 nếu máy chưa có) + cài git hooks
make setup

# 4. Tạo file khóa bí mật từ mẫu (chỉ cần khi bắt đầu học LLM)
cp .env.example .env

# 5. Kiểm tra
make doctor     # môi trường
make check      # lint + test + catalog — phải xanh
```

Máy không có `make` (Windows ngoài WSL)? Mỗi lệnh `make x` tương ứng một dòng trong [Makefile](../../Makefile),
ví dụ `make setup` = `uv sync --inexact` rồi `uv run pre-commit install`.

## Các bước chi tiết

| # | Tài liệu | Nội dung | Khi nào cần |
|---|---|---|---|
| 1 | [Công cụ cần cài](01-cong-cu-can-cai.md) | Hệ điều hành, Git, uv, VS Code, Docker | Ngay từ đầu |
| 2 | [Môi trường Python](02-moi-truong-python.md) | uv, nhóm phụ thuộc theo nhóm bài toán, notebook | Ngay từ đầu |
| 3 | [API key và bí mật](03-api-key-va-bi-mat.md) | `.env`, giới hạn chi tiêu, quy tắc dữ liệu công ty | Trước khi học LLM (Nhóm 5–7) |
| 4 | [GPU và tài nguyên tính toán](04-gpu-va-tinh-toan.md) | GPU máy nhà, Colab, Kaggle, Apple Silicon | Trước Nhóm 5 và deep learning |
| 5 | [Dữ liệu luyện tập](05-du-lieu-luyen-tap.md) | Bộ dữ liệu cho 8 dự án luyện tập và cách tải | Trước mỗi dự án |
| 6 | [Xử lý sự cố](06-xu-ly-su-co.md) | Lỗi thường gặp: Windows, tiếng Việt, CUDA, proxy | Khi gặp lỗi |

## Danh sách kiểm tra "đã setup xong"

- [ ] `git --version`, `uv --version` chạy được; đã đặt `git config --global user.name/user.email`
- [ ] `make setup` thành công, thư mục `.venv/` được tạo
- [ ] `make doctor` không còn dòng ✗
- [ ] `make check` xanh
- [ ] VS Code mở repo, nhận đúng interpreter `.venv` và cài các extension được gợi ý
- [ ] (Khi học LLM) `.env` có khóa, đã đặt giới hạn chi tiêu trên trang nhà cung cấp
- [ ] (Khi học deep learning) đã chọn được nơi chạy GPU: máy nhà, Colab hoặc Kaggle

## Yêu cầu phần cứng tối thiểu

| | Tối thiểu | Khuyên dùng |
|---|---|---|
| RAM | 8 GB | 16 GB trở lên |
| Ổ trống | 20 GB (dev + core + 1–2 nhóm) | 60 GB (cài đủ các nhóm, có PyTorch và dữ liệu) |
| GPU | Không bắt buộc | NVIDIA ≥ 8 GB VRAM, hoặc dùng Colab/Kaggle |
| Hệ điều hành | Windows 10/11 (qua WSL2), macOS 13+, Ubuntu 22.04+ | Ubuntu hoặc WSL2 Ubuntu |

Tiếp theo sau khi setup: đọc [bản đồ bài toán](../01-problem-map/README.md) rồi [bản đồ kỹ năng](../02-skill-map/README.md).
