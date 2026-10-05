# Lịch sử công việc

Ghi lại **những gì đã làm**, mới nhất ở trên. Việc **sắp làm** nằm trong [CHECKLIST.md](CHECKLIST.md).

Quy ước khi thêm một mục:

- Tiêu đề: `## YYYY-MM-DD · <tên công việc>` (kèm link PR nếu có).
- Ghi: **Đã làm** (kết quả cụ thể), **Quyết định** (đã chọn gì, vì sao), **Còn mở** (chuyển sang CHECKLIST).
- Khi một mục trong CHECKLIST hoàn thành: đánh dấu `[x]` ở CHECKLIST và thêm một dòng tóm tắt vào đây.

---

## 2026-10-05 · Thiết kế dự án nghiên cứu CMB-09 Data Agent OS

**Đã làm**

- Tạo `projects/cmb-09-data-agent-os/` (chỉ tài liệu thiết kế, chưa có code): kiến trúc v1 (sơ đồ SVG + các luồng Mermaid),
  review diagram v0 (13 điểm cần bổ sung), chi tiết kỹ thuật, ADR-001 về OpenAI Agents SDK, checklist triển khai 9 giai đoạn.
- Kiểm chứng API trên đúng phiên bản: `agno` 3.1.1 (AgentOS, `BaseExternalAgent`, Skills, tracing), `openai-agents` 0.23.1
  (`TracingProcessor`, skills chỉ qua sandbox, `ScriptedModel`), DBHub 1.4.0 + `mcp` 2.3.0 (chạy thử 2 nguồn SQLite), `sqlglot` 30.

**Quyết định (đề xuất, chờ duyệt)**

- Agno là runtime chính; OpenAI Agents SDK là runtime phụ qua adapter tự viết; trong luồng OpenAI, agent chuyên trách nạp skill
  core trước, agent điều phối thì không; không dùng SandboxAgent mặc định.
- Pack `core` (kỹ năng chung của data agent) luôn nạp trước mọi domain pack; skill an toàn bị khóa.
- Agent không gọi DBHub trực tiếp mà qua Data Gateway (kiểm quyền theo người dùng, chặn PII, ghi evidence).
- Trace của cả hai runtime lưu chung bảng `traces`/`spans` của AgentOS; mặc định không gửi trace lên OpenAI.

**Còn mở**

- Chủ dự án trả lời mục P0 trong `projects/cmb-09-data-agent-os/CHECKLIST.md` trước khi bắt đầu P1.

## 2026-10-04 · Thêm CHECKLIST và HISTORY

**Đã làm**

- Tạo `CHECKLIST.md` (việc sắp làm, chia theo giai đoạn, kèm các câu hỏi cần chủ dự án quyết định) và file
  lịch sử này.

**Còn mở**

- Chủ dự án review `CHECKLIST.md`: sửa thứ tự ưu tiên, trả lời mục "Cần quyết định".

## 2026-10-04 · Giai đoạn 2 — bản đồ kỹ năng + setup + cấu trúc dự án ([#1](https://github.com/superken-python/ai-architecture/pull/1), đã merge)

**Đã làm**

- `docs/00-setup/`: 6 tài liệu chuẩn bị môi trường (công cụ, uv và nhóm phụ thuộc, API key và quy tắc dữ liệu,
  GPU, dữ liệu luyện tập, xử lý sự cố) và `make doctor`.
- `docs/01-problem-map/`: bản Markdown của tài liệu giai đoạn 1, kèm file `.docx` gốc.
- `catalog/`: 8 nhóm, 2 họ bài toán, 65 kỹ năng trong 10 mảng (mỗi kỹ năng 3 mức), 9 tổ hợp.
- `src/aiarch/catalog.py`: kiểm tra catalog (gồm kiểm tra độ phủ so với ma trận giai đoạn 1) và sinh tài liệu
  `docs/02-skill-map/generated/`.
- `docs/02-skill-map/`: kiến trúc kỹ năng, kỹ năng kết hợp, tiết kiệm token mà vẫn chính xác, lộ trình 6 tháng.
- Hạ tầng: `pyproject.toml` + `uv.lock`, Makefile, pre-commit, CI, mẫu PR, mẫu kỹ năng/lab/dự án, test (52).

**Quyết định**

- YAML trong `catalog/` là nguồn dữ liệu duy nhất; tài liệu dạng bảng đều sinh tự động.
- Tầng kỹ năng (nền tảng / cầu nối / trong họ / chuyên biệt / bổ trợ) tính tự động từ mức sử dụng, không gán tay.
- Thêm 2 mảng so với giai đoạn 1: PY (lập trình nền tảng) và EFF (tiết kiệm token & độ tin cậy).
- Tài liệu trung lập nhà cung cấp LLM; số liệu giá/caching chỉ dùng làm ví dụ và ghi rõ thời điểm.

**Kết quả kiểm chứng**

- `make check` xanh; cả 10 nhóm phụ thuộc cài và import được trên Linux.
- Chưa kiểm chứng: setup trên Windows/macOS, Colab/Kaggle, lệnh tải dữ liệu Kaggle.

## 2026-10-04 · Giai đoạn 1 — bản đồ bài toán AI doanh nghiệp (v1)

**Đã làm**

- Tài liệu `ban-do-bai-toan-ai-doanh-nghiep_v1_20261004.docx`: 8 nhóm bài toán trong 4 khối, cây nhận diện
  30 giây, ma trận 8 mảng kỹ năng × 8 nhóm, chi tiết từng nhóm, quy trình ĐÚNG → NHANH → CHÍNH XÁC → THUYẾT PHỤC,
  lộ trình 6 tháng và bảng tự đánh giá.
