# ADR-001 · Vai trò của OpenAI Agents SDK và việc nạp kỹ năng core trong luồng OpenAI

- **Trạng thái:** đề xuất — chờ chủ dự án duyệt
- **Ngày:** 2026-10-05
- **Phiên bản đã xem xét:** `agno` 3.1.1, `openai-agents` 0.23.1

## Bối cảnh

Diagram v0 đặt Agno SDK và OpenAI Agents SDK ngang nhau trong Agent Runtime. Yêu cầu: agent khi khởi tạo phải lấy kỹ năng của
data agent (pack `core`) trước, và *"nếu đi theo flow OpenAI Agents SDK thì xem có cần không"*. Có hai câu hỏi tách biệt:

1. Dự án có cần runtime OpenAI Agents SDK không, và ở vai trò nào?
2. Trong luồng OpenAI Agents SDK, có cần nạp kỹ năng core trước không — cho agent nào, bằng cơ chế gì?

Sự thật kỹ thuật liên quan (đã kiểm tra mã nguồn):

- AgentOS là sản phẩm của Agno: agent Agno được hỗ trợ đầy đủ (session, memory, tracing, UI, scheduler, JWT). Agent của
  framework khác vào AgentOS qua `BaseExternalAgent`; Agno có sẵn adapter cho Claude Agent SDK, LangGraph, DSPy nhưng
  **chưa có cho OpenAI Agents SDK** → phải tự viết (hai hook, ~150 dòng).
- Agno có **Skills native** (SKILL.md, progressive disclosure, validator). OpenAI Agents SDK chỉ có skills qua
  `SandboxAgent` + capability `Skills` hoặc `ShellTool` — tức là cần môi trường sandbox/shell để agent đọc file skill.
- Khi **handoff**, agent nhận tiếp quản hội thoại nhưng chạy bằng instructions và tools **của chính nó**; instructions/tools
  của agent chuyển giao không đi theo.
- Tracing của OpenAI Agents SDK mặc định gửi lên nền tảng OpenAI; thay được bằng `set_trace_processors`.

## Câu hỏi 1 — Có cần OpenAI Agents SDK không?

| Phương án | Ưu | Nhược |
|---|---|---|
| A. Chỉ Agno | một runtime, ít code nhất, tích hợp AgentOS trọn vẹn | không trả lời được câu hỏi nghiên cứu "runtime nào tốt hơn cho data agent"; không dùng được tính năng riêng của OpenAI |
| **B. Agno chính + OpenAI SDK phụ qua adapter** | giữ được so sánh hai runtime trên cùng pack/eval; mở đường cho handoff, guardrail, sandbox, hosted tools của OpenAI khi cần | thêm adapter + trace processor phải bảo trì; hai cách khai báo tool |
| C. OpenAI SDK chính | hệ sinh thái OpenAI (Evals, hosted tools) | lệch khỏi AgentOS (UI, session, scheduler đều là của Agno); skills phải qua sandbox; trace mặc định ra ngoài |

**Quyết định: B.** Agno là runtime mặc định cho mọi agent. OpenAI Agents SDK là runtime **tùy chọn theo từng agent**
(`runtime: openai` trong `config/agents.yaml`), chỉ bật khi có ít nhất một lý do sau:

1. **So sánh nghiên cứu:** chạy cùng pack + golden set trên hai runtime để đo độ chính xác, chi phí, độ trễ (mục tiêu chính
   của dự án nghiên cứu này).
2. Cần **handoff** giữa nhiều agent chuyên trách theo mô hình của OpenAI, hoặc **guardrail** chạy song song với model.
3. Cần **SandboxAgent** để chạy script của skill (ví dụ phân tích pandas/vẽ biểu đồ trên kết quả truy vấn).
4. Cần **hosted tools** của OpenAI (code interpreter, file search, web search) hoặc Realtime/voice.

Nếu sau giai đoạn eval (P8 trong checklist) runtime OpenAI không hơn Agno ở tiêu chí nào và không có nhu cầu 2–4, giữ adapter ở
trạng thái `experimental` và không thêm agent mới trên runtime này.

## Câu hỏi 2 — Luồng OpenAI có cần nạp kỹ năng core trước không?

Luồng OpenAI dự kiến: `data-triage-openai` (điều phối) → handoff → `timesheet-openai` / `finance-openai` (chuyên trách).

| Agent trong luồng OpenAI | Cần kỹ năng core? | Lý do |
|---|---|---|
| Agent chuyên trách (domain) | **Có — bắt buộc**, cùng thứ tự `core → domain → learnings` như Agno | Sau handoff, chỉ instructions/tools của agent chuyên trách có hiệu lực; thiếu core thì mất quy tắc SQL an toàn, tự kiểm tra, trích nguồn |
| Agent điều phối (triage) | **Không** | Chỉ cần mô tả pack (`handoff_description`) để chọn; thêm skill core làm tốn token và khiến nó tự đi truy vấn thay vì chuyển giao. Agent này không có tool dữ liệu |
| `SandboxAgent` + capability `Skills` | **Không cần** mặc định | Skill của data agent là hướng dẫn (instruction-only); dữ liệu lấy qua tool của gateway, không cần shell. Chỉ dùng khi một skill có `scripts/` phải chạy |

**Cơ chế cho agent chuyên trách:** dùng **cùng Resolver** với Agno (cùng danh sách skill có thứ tự, cùng SKILL.md), nhưng
thay `Skills` của Agno bằng:

- danh mục skill (tên + mô tả) do Context Builder chèn vào instructions, theo đúng thứ tự core trước;
- function tool `load_skill(name)` trả nội dung SKILL.md (progressive disclosure, giống `get_skill_instructions` của Agno).

**Phương án đã cân nhắc và không chọn:** "core data agent làm tool" (`agent.as_tool()`) cho các agent domain. Bị loại vì
quy tắc nghiệp vụ và từ điển của domain phải định hình *chính câu SQL*; tách agent viết SQL (core) khỏi ngữ cảnh domain hoặc
làm mất ngữ cảnh đó, hoặc phải truyền lại toàn bộ — tốn gấp đôi token.

## Hệ quả

- Thêm hai thành phần phải bảo trì: `OpenAIAgentsAdapter` (`BaseExternalAgent`) và `AgnoDbTracingProcessor`; cả hai test
  được không cần API key nhờ `agents.testing.ScriptedModel`.
- Data tools định nghĩa một lần (`ToolSpec`), sinh ra cho hai SDK — không viết tool hai lần.
- Lịch sử hội thoại của agent OpenAI nằm trong session của AgentOS (adapter nạp `history`), không dùng Session riêng của
  OpenAI SDK.
- Trace của luồng OpenAI nằm cùng bảng với Agno; mặc định không gửi lên OpenAI (`DAGENT_OPENAI_TRACE_EXPORT=local`).
- Test bắt buộc: skill core xuất hiện **trước** skill domain trong instructions của agent chuyên trách; instructions của
  agent điều phối **không** chứa skill index.

## Điều kiện xem lại

- Agno phát hành adapter chính thức cho OpenAI Agents SDK → thay adapter tự viết.
- OpenAI Agents SDK hỗ trợ skills không cần sandbox → bỏ tool `load_skill` tự viết.
- Kết quả eval P8 cho thấy một runtime vượt trội rõ rệt → cân nhắc chỉ giữ một runtime.
