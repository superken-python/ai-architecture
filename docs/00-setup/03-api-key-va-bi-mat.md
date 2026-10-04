# 3 · API key, bí mật và quy tắc dữ liệu

Cần khi bắt đầu học LLM (Nhóm 5, 6, 7) hoặc dùng dịch vụ có khóa (Hugging Face, Kaggle, Langfuse).

## Lưu khóa đúng cách

```bash
cp .env.example .env     # .env đã nằm trong .gitignore
# mở .env, điền khóa của dịch vụ bạn dùng
```

Trong code, đọc khóa từ biến môi trường — **không bao giờ** viết khóa vào code, notebook, prompt hay log:

```python
from dotenv import load_dotenv  # gói python-dotenv, có trong nhóm core
import os

load_dotenv()
api_key = os.environ["ANTHROPIC_API_KEY"]  # SDK của các hãng cũng tự đọc biến này
```

Ba lớp bảo vệ đã có sẵn trong repo:

1. `.gitignore` bỏ qua `.env` và `.env.*` (trừ `.env.example`).
2. Hook pre-commit `no-env-file` chặn commit file `.env`.
3. `make doctor` báo lỗi nếu `.env` đang bị Git theo dõi.

**Lỡ commit/đẩy khóa lên GitHub:** coi như khóa đã lộ — thu hồi (revoke) ngay trên trang nhà cung cấp và
tạo khóa mới. Xóa khỏi lịch sử Git là chưa đủ.

## Lấy khóa ở đâu

| Dịch vụ | Biến | Nơi tạo |
|---|---|---|
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | Claude Console → API Keys |
| OpenAI | `OPENAI_API_KEY` | OpenAI Platform → API keys |
| Hugging Face | `HF_TOKEN` | huggingface.co → Settings → Access Tokens (chỉ cần quyền *read*) |
| Langfuse | `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` | Langfuse Cloud hoặc tự host bằng Docker |
| Kaggle | `KAGGLE_USERNAME`, `KAGGLE_KEY` | kaggle.com → Settings → API → Create New Token |

Chỉ cần **một** nhà cung cấp LLM để học. Tài liệu kỹ năng viết trung lập, không phụ thuộc hãng.

## Kiểm soát chi phí khi luyện tập

- Đặt **giới hạn chi tiêu** (spend limit / budget) trên trang quản trị của nhà cung cấp ngay khi tạo khóa.
- Dùng một khóa riêng cho việc học, tách khỏi khóa production.
- `LLM_DAILY_BUDGET_USD` trong `.env` là quy ước cho script luyện tập: script nên cộng dồn chi phí từ trường
  `usage` của response và dừng khi vượt ngưỡng (kỹ năng EFF-01).
- Chạy eval bằng Batch API khi không cần kết quả ngay (thường rẻ hơn khoảng một nửa — kỹ năng EFF-06).
- Bắt đầu thử nghiệm với golden set nhỏ (20–30 mẫu), chỉ chạy đủ ~100 mẫu khi đã ổn định.

## Quy tắc dữ liệu công ty (bắt buộc)

1. **Không** gửi dữ liệu khách hàng thật, tài liệu nội bộ hay mã nguồn công ty lên API bên ngoài khi chưa có
   chấp thuận bằng văn bản của người phụ trách dữ liệu/pháp chế.
2. Luyện tập bằng dữ liệu công khai (xem [05-du-lieu-luyen-tap.md](05-du-lieu-luyen-tap.md)) hoặc dữ liệu đã
   ẩn danh hóa (che tên, số điện thoại, CCCD, số tài khoản...).
3. Dữ liệu thật chỉ nằm trong `data/` trên máy được cấp quyền — không commit, không chép lên Drive cá nhân.
4. Việc xử lý dữ liệu cá nhân phải tuân thủ quy định về bảo vệ dữ liệu cá nhân của Việt Nam; hỏi pháp chế
   về văn bản đang có hiệu lực trước khi đưa dữ liệu vào bất kỳ hệ thống AI nào (kỹ năng OPS-08, LLM-06).

Tiếp theo: [4 · GPU và tài nguyên tính toán](04-gpu-va-tinh-toan.md).
