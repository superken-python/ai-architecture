# 6 · Xử lý sự cố thường gặp

| Triệu chứng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| `uv: command not found` sau khi cài | PATH chưa được nạp lại | Mở terminal mới hoặc `exec $SHELL`; kiểm tra `~/.local/bin` có trong PATH |
| `make: command not found` (Windows) | Windows không có make | Dùng WSL2, hoặc chạy lệnh tương ứng trong `Makefile` |
| Thư viện vừa cài bằng `pip install` biến mất | `uv sync` đưa môi trường về đúng lockfile | Thêm bằng `uv add --group <nhóm> <gói>` |
| Gói của nhóm khác bị gỡ sau `uv sync` | `uv sync` mặc định "chính xác" — gỡ gói không được yêu cầu | Dùng `make setup-<nhóm>` (đã có `--inexact`) |
| VS Code không thấy thư viện | Sai interpreter | *Python: Select Interpreter* → `.venv/bin/python` |
| Chữ tiếng Việt lỗi (`Ã¡`, `?`) khi đọc/ghi file | Không chỉ định encoding | Luôn `open(..., encoding="utf-8")`, `pd.read_csv(..., encoding="utf-8")`; trên Windows đặt biến môi trường `PYTHONUTF8=1` |
| Cùng một từ tiếng Việt nhưng tìm kiếm không khớp | Unicode dựng sẵn (NFC) vs tổ hợp (NFD) | `unicodedata.normalize("NFC", text)` cho mọi văn bản đầu vào (kỹ năng DATA-06) |
| Excel mở CSV tiếng Việt bị lỗi font | Excel cần BOM | Ghi bằng `encoding="utf-8-sig"` khi file dành cho Excel |
| `torch.cuda.is_available()` là `False` | Thiếu driver, driver cũ hơn bản CUDA của PyTorch, hoặc PyTorch bản CPU (Windows thuần) | `nvidia-smi` phải chạy được và `CUDA Version` ≥ `torch.version.cuda`; dùng WSL2/Linux; xem [04-gpu-va-tinh-toan.md](04-gpu-va-tinh-toan.md) |
| `CUDA out of memory` | Batch/ảnh quá lớn | Giảm batch size, dùng mixed precision, gradient accumulation (kỹ năng DL-01) |
| Lỗi chứng chỉ SSL / không tải được gói sau proxy công ty | Proxy chặn hoặc dùng CA riêng | Đặt `HTTPS_PROXY`; với CA riêng đặt `SSL_CERT_FILE` trỏ tới file CA của công ty (hỏi IT), không tắt kiểm tra SSL |
| API trả lỗi 429 | Vượt giới hạn tốc độ | Retry có backoff, giảm số request song song (kỹ năng PY-04) |
| API trả lỗi 401 | Khóa sai/hết hạn, hoặc chưa nạp `.env` | Kiểm tra bằng `make doctor`; gọi `load_dotenv()` trước khi tạo client |
| Pre-commit báo "files were modified by this hook" | Hook đã tự sửa format hoặc sinh lại tài liệu | `git add` các file vừa được sửa rồi commit lại |
| CI báo "Tài liệu sinh tự động đã cũ" | Sửa `catalog/*.yaml` nhưng chưa sinh lại | `make catalog` rồi commit thư mục `docs/02-skill-map/generated/` |

Vẫn chưa được? Chạy `make doctor`, chụp kết quả (đã không chứa khóa bí mật) và hỏi trong kênh của nhóm.
