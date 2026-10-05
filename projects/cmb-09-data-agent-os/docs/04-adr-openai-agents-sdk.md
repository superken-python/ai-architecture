# ADR-001 · OpenAI Agents SDK trong POC và cách nạp skill trong luồng OpenAI

- **Trạng thái:** đề xuất (v2) — chờ chủ dự án duyệt
- **Ngày:** 2026-10-05
- **Phiên bản đã xem xét:** `agno` 3.1.1, `openai-agents` 0.23.1

## Bối cảnh

Diagram v0 đặt Agno SDK và OpenAI Agents SDK ngang nhau trong Agent Runtime. Yêu cầu: agent khi khởi tạo phải lấy skill của
data agent (v2: các skill dùng lại từ Data plugin) trước, và *"nếu đi theo flow OpenAI Agents SDK thì xem có cần không"*.
POC phải đơn giản nhất có thể.

Sự thật kỹ thuật (đã kiểm tra mã nguồn):

- AgentOS là sản phẩm của Agno. Agent Agno được hỗ trợ đầy đủ (session, UI, tracing, kết nối MCP). Agent của framework khác vào
  AgentOS qua `agno.agents.base.BaseExternalAgent`; Agno có sẵn adapter cho Claude Agent SDK, LangGraph, DSPy nhưng **chưa có
  cho OpenAI Agents SDK**.
- Agno có **Skills native**: nạp thư mục SKILL.md, đưa tên + mô tả vào prompt, tải nội dung khi cần. Skill của Data plugin nạp
  được bằng `LocalSkills(..., validate=False)` (đã thử).
- OpenAI Agents SDK chỉ có skill qua `SandboxAgent` + capability `Skills` (mount thư mục skill vào sandbox) hoặc skill của
  `ShellTool` — đều cần môi trường sandbox/shell.
- Tracing của OpenAI Agents SDK mặc định gửi lên nền tảng OpenAI; thay được bằng `set_trace_processors([...])`.

## Quyết định

1. **POC-1 và POC-2 chỉ dùng Agno.** Một agent Agno cho mỗi domain pack. Không cần adapter, không cần processor tracing riêng.
2. **POC-3 (tùy chọn, phục vụ nghiên cứu): thêm đúng một agent OpenAI Agents SDK** (`finance-openai`) cho cùng pack `finance`,
   đưa vào AgentOS qua `OpenAIAgentsAdapter(BaseExternalAgent)`, để so sánh hai runtime trên cùng `evals.yaml`.
   **Không** làm agent điều phối/handoff và **không** dùng `SandboxAgent` trong POC.
3. **Trong luồng OpenAI, skill vẫn cần — và nạp cùng thứ tự ① Data plugin → ② domain.** Thiếu skill chung thì agent mất workflow
   phân tích và kiểm tra kết quả; thiếu skill domain thì không biết bộ lọc chuẩn, metric. Cách nạp: chèn danh mục skill (tên +
   mô tả) vào instructions và thêm function tool `load_skill(name)` đọc **cùng file SKILL.md** — giống cơ chế
   `get_skill_instructions` của Agno, không cần sandbox.
4. **Trace của agent OpenAI ghi vào cùng PostgreSQL** (`agno.agno_traces`, `agno.agno_spans`) bằng một `TracingProcessor` tự
   viết; tắt bộ xuất mặc định để dữ liệu không rời hệ thống.

## Phương án đã cân nhắc

| Phương án | Vì sao không chọn cho POC |
|---|---|
| Hai runtime ngang hàng ngay từ đầu | gấp đôi việc trước khi biết Agno đã đủ hay chưa; trái mục tiêu POC đơn giản |
| `SandboxAgent` + capability `Skills` cho luồng OpenAI | đúng cơ chế "native" của SDK nhưng cần dựng sandbox (local/Docker); các skill dùng trong POC chỉ là hướng dẫn, không có script phải chạy |
| Agent điều phối + handoff sang agent domain | POC chỉ cần người dùng chọn agent trên UI; handoff thêm một lượt gọi model và phải xử lý skill cho từng agent |
| Bỏ hẳn OpenAI Agents SDK | mất câu trả lời cho câu hỏi nghiên cứu "runtime nào tốt hơn cho data agent"; giữ ở mức tùy chọn là đủ |

## Hệ quả

- POC-1/2 chạy được chỉ với Agno; POC-3 thêm ba phần tự viết: adapter, tool `load_skill`, trace processor (test được không cần
  API key bằng `agents.testing.ScriptedModel`).
- Một nguồn skill duy nhất trên đĩa cho cả hai runtime; khác biệt chỉ nằm ở cách đưa skill vào agent.
- Cần một hàm dùng chung `resolve_skill_files(pack)` trả về danh sách file SKILL.md theo đúng thứ tự ①→②, để hai runtime không
  lệch nhau.

## Điều kiện xem lại

- Sau POC-3: nếu agent OpenAI không tốt hơn Agno ở độ chính xác, chi phí hoặc độ trễ → dừng runtime OpenAI.
- Khi cần `build-dashboard` / `create-viz` (ghi file, chạy Python) → cân nhắc `SandboxAgent` hoặc tool chạy code của Agno.
- Agno phát hành adapter chính thức cho OpenAI Agents SDK → thay adapter tự viết.
