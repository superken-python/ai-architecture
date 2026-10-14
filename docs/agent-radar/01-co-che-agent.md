# Cơ chế agent: Agno · OpenAI Agents SDK · LangGraph · Pydantic AI

| Thuộc tính | Chi tiết |
|---|---|
| Phạm vi | Chỉ **cơ chế agent**: vòng lặp gọi tool, điểm can thiệp, tạm dừng/chạy tiếp, nhiều agent, bộ nhớ. Không so runtime, giao thức, chi phí — xem [radar](README.md) |
| Phiên bản đã đọc mã nguồn | `agno` 3.1.3 · `openai-agents` 0.23.1 · `langgraph` 1.2.15 + `langchain` 1.4.5 (`create_agent`) · `pydantic-ai-slim` 2.56.0 |
| Ngày | 2026-10-14 |

Cả bốn chạy cùng một vòng lặp gốc: **gọi model → nếu model gọi tool thì chạy tool, đưa kết quả lại → gọi model tiếp →
dừng khi model trả lời không kèm tool, hoặc chạm giới hạn.** Khác nhau ở *ai giữ vòng lặp* và *chỗ nào cho ta can thiệp*.

## 1. Ai giữ vòng lặp

| | Agno | OpenAI Agents SDK | LangGraph | Pydantic AI |
|---|---|---|---|---|
| Vòng lặp nằm ở | Lớp `Model` (`models/base.py`), `Agent` bọc ngoài | `Runner.run` / `run_streamed`; `Agent` chỉ là cấu hình | **Đồ thị**: nút `model` ↔ nút `tools` nối bằng cạnh điều kiện (`create_agent` dựng sẵn, hoặc tự vẽ `StateGraph`) | **Đồ thị** `pydantic-graph` ẩn bên trong: UserPrompt → ModelRequest → CallTools → End |
| Đi từng bước | Stream sự kiện | Stream sự kiện | Stream theo nút / theo token; dừng ở nút bất kỳ | `agent.iter()` duyệt từng nút của đồ thị |
| Giới hạn | `tool_call_limit` (số lần gọi tool) | `max_turns` (số lượt gọi model) | `recursion_limit` (số bước đồ thị); middleware `ModelCallLimit`, `ToolCallLimit` | `UsageLimits`: số request, số tool call, token, **chi phí** |
| Chạy nhiều tool cùng lúc | Có (`asyncio.gather`) | Có | Có (`ToolNode`; `Send` để rẽ song song) | Có (`max_concurrency`; tool đánh dấu `sequential` chạy tuần tự) |

## 2. Dừng vòng lặp và kết quả có cấu trúc

| | Agno | OpenAI Agents SDK | LangGraph | Pydantic AI |
|---|---|---|---|---|
| Dừng ngay sau một tool | Cờ trên tool: `stop_after_tool_call`, `show_result` | `tool_use_behavior`: `stop_on_first_tool`, `StopAtTools([...])`, hàm tự viết | Cạnh của đồ thị quyết định; tool `return_direct` | `end_strategy` (`graceful` mặc định) |
| Kết quả có cấu trúc | `output_schema` (có thể dùng model phụ để parse) | `output_type` — chỉ dừng khi output đúng kiểu | `response_format` | `output_type` + output validator; sai thì bắt model làm lại |
| Chống gọi lặp một tool | — | `reset_tool_choice` | Tùy cạnh/middleware | `UsageLimits.tool_calls_limit` |

## 3. Điểm can thiệp

| | Agno | OpenAI Agents SDK | LangGraph | Pydantic AI |
|---|---|---|---|---|
| Quanh tool | `pre_hook`, `post_hook`, `tool_hooks` (middleware) | `RunHooks` / `AgentHooks`; **guardrail cho từng tool** (`tool_input_guardrails`, `tool_output_guardrails`) | **Middleware**: `wrap_tool_call`, `ToolRetry`, `ToolError`, `ToolCallLimit` | `prepare` (đổi/ẩn tool theo ngữ cảnh mỗi bước), `args_validator` |
| Quanh model | Hook trước/sau run | Guardrail đầu vào/đầu ra của agent | `before_model`, `after_model`, `wrap_model_call`, `ModelRetry`, `ModelFallback`, `Summarization`, `PII`, `LLMToolSelector` | `history_processors` |
| Lỗi tool → model sửa | Trả lỗi về model | `failure_error_function` | `handle_tool_errors`, `ToolErrorMiddleware` | **`ModelRetry`**: tool ném lỗi có hướng dẫn, model gọi lại (đếm theo `retries`) |
| Timeout tool | Tự làm | `timeout`, `timeout_behavior` | Middleware | `tool_timeout`, `timeout` trên từng tool |
| Lưu kết quả tool | `cache_results` | — | `cache` (cache nút) | — |

## 4. Tạm dừng giữa chừng (người duyệt, tool chạy ở client)

| | Agno | OpenAI Agents SDK | LangGraph | Pydantic AI |
|---|---|---|---|---|
| Cách dừng | 3 loại trên tool: `requires_confirmation`, `requires_user_input`, **`external_execution`** | `needs_approval` → run trả `interruptions` | `interrupt()` ở bất kỳ nút nào; `interrupt_before/after`; `HumanInTheLoopMiddleware` | `requires_approval` hoặc ném `ApprovalRequired` / `CallDeferred` → run kết thúc với `DeferredToolRequests` |
| Chạy tiếp | `continue_run(run_id, requirements)` | Nạp lại `RunState`, duyệt/từ chối, `Runner.run` lại | `Command(resume=...)` với cùng `thread_id` | Gọi lại `run` với `DeferredToolResults` + lịch sử tin nhắn |
| Trạng thái lưu ở đâu | **DB của Agno** (tự động) | Tự serialize `RunState` | **Checkpointer** (Postgres…) — tự động | **Không lưu**: người gọi giữ lịch sử và gửi lại |
| Tool do client chạy, trả kết quả | **Có loại riêng** (`external_execution`) | Không có loại riêng | Tự làm bằng `interrupt` | **Có** (`CallDeferred` / external toolset) |

## 5. Nhiều agent

| | Agno | OpenAI Agents SDK | LangGraph | Pydantic AI |
|---|---|---|---|---|
| Mô hình chính | **Team** — chế độ `coordinate`, `route`, `broadcast`, `tasks`; thành viên được gọi như tool | **Handoff** — chuyển hẳn quyền điều khiển (`transfer_to_…`); `agent.as_tool()` | **Đồ thị**: agent là nút/đồ thị con; `Command(goto=...)` để chuyển giao | Agent gọi agent qua tool (delegation); chuyển giao bằng code; `pydantic-graph` |
| Luồng do code định nghĩa | **Workflow** (bước, rẽ nhánh, vòng lặp) | Tự viết Python quanh `Runner` | **Chính là thế mạnh** | `pydantic-graph` |
| Lưu ý | Thành viên Team **không** nhận tool của client (frontend tools) | Agent mới nhận cả lịch sử (`input_filter` để cắt) | Tự quản state chung giữa các nút | Agent con tính chung `usage` với agent cha |

## 6. Bộ nhớ và ngữ cảnh

| | Agno | OpenAI Agents SDK | LangGraph | Pydantic AI |
|---|---|---|---|---|
| Lịch sử hội thoại | Tự lấy từ DB (`add_history_to_context`, `num_history_runs`) | `Session` (SQLite/Redis…) hoặc `previous_response_id` / `conversation_id` | Checkpointer theo `thread_id` | `message_history` do người gọi truyền vào |
| Bộ nhớ dài hạn | Memory manager, tóm tắt session, learning | — | `store` (bộ nhớ dài hạn theo namespace) | — |
| Tri thức / RAG | `knowledge` + vector DB | Tool `FileSearch` (lưu ở OpenAI) hoặc tự viết | Tự viết tool / retriever của LangChain | Tự viết tool |
| Ngữ cảnh động | Instructions là hàm nhận `run_context` | Instructions là hàm nhận `RunContextWrapper` | `context_schema` + middleware | `deps_type` + `RunContext[Deps]` có kiểu |

## 7. Kết luận

| Framework | Điểm mạnh về cơ chế | Chọn khi |
|---|---|---|
| **Agno** | Nhiều sẵn nhất: 3 kiểu tạm dừng có lưu DB, tool client, Team nhiều chế độ, Workflow, memory/knowledge | Agent nối giao diện cần tool chạy ở client (CMB-10); muốn ít tự làm |
| **OpenAI Agents SDK** | Gọn, kỷ luật quanh một agent: `tool_use_behavior`, guardrail từng tool, handoff tự nhiên | Agent dùng GPT, không cần tool client, ít code |
| **LangGraph** | **Kiểm soát cao nhất**: mọi bước là nút, `interrupt` ở đâu cũng được, checkpointer, middleware phong phú | Luồng nhiều nhánh cần audit, người duyệt, chạy bền |
| **Pydantic AI** | **Kiểu dữ liệu chặt** và **giới hạn chi tiết** (token, chi phí); `ModelRetry` để model tự sửa; deferred tools | Dịch vụ agent nhỏ, cần đầu ra đúng kiểu và kiểm soát chi phí |

Cách đọc bảng: thứ quyết định độ chính xác của agent vẫn là model, thiết kế tool và bộ eval. Cơ chế của framework quyết
định **ta chặn lỗi, dừng đúng chỗ và quan sát được vòng lặp tới đâu**. Muốn biết cái nào tốt hơn cho một bài toán, làm
phép thử ở [radar, mục 5](README.md#5-tự-đo-framework-nào-tốt-hơn-cho-dự-án-của-mình).
