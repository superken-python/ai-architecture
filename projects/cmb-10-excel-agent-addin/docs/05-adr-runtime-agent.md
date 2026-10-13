# 05 · ADR-07 · Runtime agent cho add-in: AgentOS/Agno hay framework open source khác?

- **Trạng thái:** phần *AgentOS làm runtime, AG-UI làm giao kèo* — giữ; phần *viết agent bằng Agno* — **được thay bởi
  [ADR-08](#bổ-sung--adr-08--agent-viết-bằng-openai-agents-sdk-agentos-chỉ-làm-runtime)** (chủ dự án chọn OpenAI Agents SDK)
- **Ngày:** 2026-10-13
- **Phiên bản đã xem xét** (đọc mã nguồn hoặc metadata gói trên PyPI/npm cùng ngày): `agno` 3.1.3 · `pydantic-ai-slim`
  2.55.0 · `agent-framework` 1.21.0 + `agent-framework-ag-ui` 1.5.1 · `langgraph` 1.2.15 + `ag-ui-langgraph` 0.0.47 +
  `langgraph-api` 0.16.0 · `@mastra/core` 1.76.0 · `google-adk` 2.11.0 + `ag-ui-adk` 0.9.0 · `openai-agents` 0.23.1

## Bối cảnh

Câu hỏi của chủ dự án: với Excel agent add-in, dùng AgentOS/Agno đã là tốt nhất chưa, hay có lựa chọn open source tốt hơn?

Backend của add-in phải đáp ứng (theo [tài liệu 02](02-giai-phap-kien-truc.md)):

| # | Tiêu chí | Mức |
|---|---|---|
| T1 | **Frontend tools qua AG-UI:** công cụ do add-in khai báo và chạy bằng Office.js; run tạm dừng chờ kết quả rồi chạy tiếp | bắt buộc |
| T2 | **Dùng lại hệ agent hiện có** (CMB-09: domain pack, skill `SKILL.md`, DBHub MCP, PostgreSQL) | rất quan trọng |
| T3 | **Hạ tầng runtime có sẵn:** API stream, session lưu ở server, xác thực, trace, MCP | quan trọng |
| T4 | **Giấy phép open source (OSI)** cho mọi phần cần chạy production | quan trọng |
| T5 | Độ trưởng thành, cộng đồng, tốc độ đổi API | quan trọng |
| T6 | Backend Python (đội và CMB-09 đều là Python); hợp hệ sinh thái Microsoft là điểm cộng | nên có |

## Các lựa chọn đã xem

| Lựa chọn | Giấy phép | T1 · Frontend tools qua AG-UI | Trạng thái khi tạm dừng | T3 · Hạ tầng có sẵn | T2 · Dùng lại CMB-09 |
|---|---|---|---|---|---|
| **Agno + AgentOS** | Apache-2.0 (SDK + runtime) | ✅ có sẵn: công cụ của client → `external_execution`, tạm dừng, `resume_paused_run` | lưu trong DB (PostgreSQL); session do server giữ, chặn ghi vào session người khác | ✅ REST/SSE, session, JWT/RBAC, trace, MCP client + server, A2A, Skills | ✅ trực tiếp |
| **Pydantic AI** | MIT | ✅ có sẵn: `AGUIAdapter`, công cụ của client → `ExternalToolset`; duyệt bằng AG-UI interrupt | không lưu: client gửi lại toàn bộ lịch sử mỗi lần | ⚠️ là thư viện: API, xác thực, session, triển khai phải tự dựng (chính tài liệu chuyển đổi Agno → Pydantic AI của họ xếp các phần này vào "application/infrastructure"); Skills qua Harness | ⚠️ phải viết lại phần nạp pack |
| **Microsoft Agent Framework** (GA 03/04/2026) | MIT | ✅ client tools gộp với server tools; duyệt bằng function approval | kho trạng thái duyệt mặc định **trong bộ nhớ** (`InMemoryAGUIApprovalStateStore`) | ⚠️ một phần: workflow có checkpoint, DevUI; hosting tự lo hoặc Azure; một số tính năng còn preview | ❌ viết lại |
| **LangGraph** | MIT (thư viện); **server `langgraph-api` = Elastic-2.0**, không phải OSI | ⚠️ được nhưng phải tự nối: adapter đưa công cụ của client vào state (`tools`, `copilotkit.actions`), graph phải tự bind và dừng | checkpointer (có Postgres) — HITL/durable trưởng thành nhất | ⚠️ server chuẩn không phải OSI → muốn thuần open source thì tự dựng | ❌ viết lại |
| **Mastra** (TypeScript) | Apache-2.0 | ✅ qua `@ag-ui/mastra` | workflow suspend/resume | ✅ khá đủ | ❌ khác ngôn ngữ với CMB-09 |
| **Google ADK** | Apache-2.0 (+ `ag-ui-adk` MIT) | ✅ qua middleware | session service | ⚠️ | ❌ |
| **OpenAI Agents SDK** | MIT | ❌ README của AG-UI ghi "In Progress" | — | — | — |
| Dify, n8n, Flowise, Langflow | khác nhau — n8n dùng Sustainable Use License (không phải OSI), Dify là Apache-2.0 kèm điều kiện | ❌ không có trong danh sách tích hợp AG-UI | — | — | — |

**Add-in Excel AI open source** (open-excel, office-agents, pi-for-excel): chạy vòng lặp agent ngay trong task pane với
API key của người dùng — không có backend doanh nghiệp, không quản trị tập trung, nên không thay được runtime. Có giá trị
**tham khảo cho lớp công cụ Office.js**; kiểm tra giấy phép trước khi dùng lại code.

**Điểm cần biết về Agno:** SDK và runtime AgentOS là Apache-2.0, nhưng **control plane (AgentOS UI tại os.agno.com) là
dịch vụ của nhà cung cấp**: miễn phí khi nối AgentOS chạy local, gói trả phí khi nối AgentOS chạy thật, bản tự host
control plane chỉ có ở gói Enterprise. Add-in là giao diện riêng nên **không cần** control plane; còn CMB-09 nếu muốn dùng
AgentOS UI ở production thì phải tính chi phí này.

## Quyết định

1. **Giữ AgentOS/Agno làm backend cho POC và MVP.** Không phải vì Agno tốt nhất mọi mặt, mà vì với bài toán này nó là lựa
   chọn duy nhất có đủ mọi thứ cần ngay trong hộp: frontend tools + tạm dừng/tiếp tục lưu ở server, xác thực, session,
   trace, MCP, skill. Thêm nữa, "agent của hệ thống" (CMB-09) đã chạy trên Agno, nên add-in dùng chung runtime, chung pack và
   chung trace. Giấy phép runtime là Apache-2.0.
2. **Giữ AG-UI làm giao kèo, đặt bộ công cụ Excel và lớp kiểm chứng ở add-in.** Như vậy đổi backend không phải sửa add-in.
   Đây là cách giảm rủi ro chính trước tốc độ đổi API của Agno (2.x → 3.x trong khoảng một năm).
3. **Phương án dự phòng, theo thứ tự:**
   - **Pydantic AI** — khi frontend tools của Agno qua AG-UI không ổn trong POC, hoặc khi muốn backend của add-in là một
     service nhỏ độc lập. Gọn, có kiểu dữ liệu chặt, hỗ trợ AG-UI tốt; đổi lại phải tự dựng API, xác thực, session.
     Lưu ý: server nhận lại toàn bộ lịch sử từ client, nên phải coi lịch sử đó là **dữ liệu không tin cậy** (client có thể
     sửa kết quả công cụ) — với agent được quyền ghi, đây là điểm trừ so với session do server giữ.
   - **Microsoft Agent Framework** — khi công ty chuẩn hóa trên Azure/.NET/Microsoft 365. Cần kho trạng thái duyệt bền
     vững thay cho bản trong bộ nhớ nếu chạy nhiều instance.
   - **LangGraph** — khi cần workflow dài, nhiều bước, durable, hoặc công ty đã chuẩn hóa trên LangChain. Muốn thuần open
     source thì không dùng `langgraph-api` (Elastic-2.0).
4. **Không chọn** Mastra (khác ngôn ngữ với CMB-09), Google ADK (không có lý do riêng cho bài toán này), OpenAI Agents SDK
   (chưa có AG-UI), nền tảng low-code (không có frontend tools tạm dừng/tiếp tục).

## Hệ quả

- Kiến trúc ở tài liệu 02 giữ nguyên.
- POC thêm một phép thử rẻ (tùy chọn, khoảng 1 ngày): dựng backend Pydantic AI tối giản với cùng 4 công cụ Excel, chạy cùng
  add-in và cùng `golden-v0`, so tỷ lệ đúng, độ trễ và lượng code backend. Làm được nhờ giao kèo AG-UI.
- Khóa phiên bản `agno` và `ag-ui-protocol`; giữ một bộ test hồi quy cho giao kèo công cụ (tên, schema, cách tạm dừng/tiếp
  tục) để nâng cấp không làm vỡ add-in.

## Điều kiện xem lại

- POC-1: tạm dừng/tiếp tục qua AG-UI của Agno lỗi hoặc mất trạng thái → chạy phép thử Pydantic AI, chọn lại.
- Agno đổi API lớn làm vỡ giao kèo công cụ.
- Công ty chọn một framework chuẩn khác cho toàn bộ hệ agent (Microsoft Agent Framework, LangGraph).
- CMB-09 không còn chạy trên Agno — khi đó lý do T2 mất đi, so lại từ đầu với bảng trên.

## Nguồn

- Mã nguồn đã đọc: `agno/os/interfaces/agui/` (Agno 3.1.3), `pydantic_ai/ui/ag_ui/` (Pydantic AI 2.55.0),
  `agent_framework_ag_ui/` (1.5.1), `ag_ui_langgraph/agent.py` (0.0.47); giấy phép lấy từ metadata của gói.
- [Agno pricing](https://www.agno.com/pricing) — gói của control plane.
- [Microsoft Agent Framework Version 1.0](https://devblogs.microsoft.com/agent-framework/microsoft-agent-framework-version-1-0/)
  · [AG-UI integration](https://learn.microsoft.com/agent-framework/integrations/ag-ui).
- [AG-UI — danh sách tích hợp](https://github.com/ag-ui-protocol/ag-ui).
- Add-in Excel AI open source: [open-excel](https://github.com/BuWH/open-excel),
  [office-agents](https://www.sourcepulse.org/projects/25972602), [pi-for-excel](https://www.sourcepulse.org/projects/25516876).

---

## Bổ sung · ADR-08 · Agent viết bằng OpenAI Agents SDK, AgentOS chỉ làm runtime

- **Trạng thái:** chấp nhận — chủ dự án chọn ngày 2026-10-13, áp dụng từ [POC 0.1](06-poc-huong-dan-su-dung.md)
- **Thay cho:** ADR-06 ([tài liệu 02](02-giai-phap-kien-truc.md#9-quyết-định-kiến-trúc)) và phần "viết agent bằng
  Agno" của ADR-07. Phần "AgentOS làm runtime, AG-UI làm giao kèo" của ADR-07 giữ nguyên.

### Bối cảnh

Yêu cầu của chủ dự án: stack là **AgentOS + AG-UI + OpenAI Agents SDK**; agent và tool viết bằng OpenAI Agents SDK, **không
viết agent bằng Agno SDK**; model **gpt-5-mini**; có **agent điều hướng** nếu cần.

ADR-07 loại OpenAI Agents SDK vì SDK chưa có AG-UI. Xem lại: AgentOS 3.1 có lớp `BaseExternalAgent` để bọc agent của
framework khác (Agno đã viết sẵn adapter cho Claude Agent SDK, LangGraph, DSPy). Bọc OpenAI Agents SDK bằng lớp này thì
AgentOS lo phần AG-UI, session, REST — lý do loại ở ADR-07 không còn là rào cản.

### Quyết định

1. **Agent, tool, handoff, model: OpenAI Agents SDK** (`Agent`, `function_tool`, `handoffs`, `Runner`). Agent `Điều phối`
   (triage) chuyển việc cho `Excel Report Agent` và `Data Search Agent`; model `gpt-5-mini`, reasoning `low`.
   `USE_TRIAGE=false` gộp thành một agent đủ tool khi muốn bớt một lượt gọi model.
2. **AgentOS chỉ làm runtime phục vụ:** endpoint AG-UI `/agui`, REST `/agents/{id}/runs`, lưu session (SQLite ở POC,
   PostgreSQL khi lên MVP). Không dùng `agno.agent.Agent`.
3. **Nối hai bên bằng `OpenAIAgentsAdapter`** (`src/excel_agent/agents/runtime/agentos_adapter.py`, khoảng 250 dòng): chạy
   `Runner.run_streamed`, đổi sự kiện của SDK sang sự kiện AgentOS — bảng đối chiếu ở
   [tài liệu 06 §2](06-poc-huong-dan-su-dung.md#2-kiến-trúc-poc).
4. **Ghi dữ liệu theo mẫu "agent đề xuất → người dùng xác nhận trên giao diện → API ghi xác định"**, không dùng frontend
   tools. Agent trả kết quả (file, danh sách tìm được) qua `TOOL_CALL_RESULT`; giao diện hiện xem trước; người dùng bấm
   xác nhận; lớp kiểm chứng ghi. Trạng thái giao diện (file, cột, dòng đang chọn) gửi lên qua `context` của AG-UI.

### Đánh đổi

| | Nội dung |
|---|---|
| Được | Agent là code OpenAI Agents SDK thuần, không phụ thuộc Agno — đổi runtime không phải viết lại agent |
| Được | Dùng sẵn handoff, guardrail, `needs_approval`, `RunState` của SDK; AgentOS vẫn lo AG-UI, session, REST |
| Được | Mẫu xác nhận trên giao diện đơn giản hơn tạm dừng/tiếp tục, và đặt cổng ghi ở nơi agent không vượt qua được (giữ tinh thần ADR-03) |
| Mất | **Frontend tools (tiêu chí T1):** adapter không đưa công cụ do client khai báo vào agent, không tạm dừng/tiếp tục run qua AG-UI. Agent không tự đọc sheet giữa run, chỉ thấy những gì giao diện gửi trong `context` |
| Mất | **Dùng lại trực tiếp agent Agno của CMB-09 (T2):** gọi CMB-09 qua API hoặc MCP như một tool, không chạy chung runtime |
| Phải tự làm | Bảo trì adapter khi Agno hoặc SDK đổi API: khóa phiên bản (`agno==3.1.3`, `openai-agents==0.23.1`), giữ test integration chạy qua AgentOS thật |
| Phải tự làm | Lịch sử hội thoại do AgentOS lưu; adapter đưa lại 20 message gần nhất vào input (kết quả tool cắt còn 1.500 ký tự), không dùng `Session` của SDK |
| Phải tự làm | Trace: tắt trace mặc định của SDK (không gửi lên OpenAI); trace của AgentOS không nhìn vào trong run của SDK → cần trace processor OpenTelemetry (`OPS-06`) ở MVP |

### Hệ quả cho add-in Excel thật

- Ghi vào sheet: add-in nhận kết quả agent, xem trước, người dùng xác nhận rồi ghi bằng Office.js (`TableRowCollection.add`,
  `Range.values`) — cùng mẫu với POC, không cần frontend tools.
- Đọc sheet: add-in gửi tóm tắt bảng đang mở (tên bảng, tiêu đề cột, vùng chọn, vài dòng mẫu) trong `context`. Tác vụ cần
  agent tự đọc thêm giữa run (ví dụ "so cột A với dữ liệu hệ thống rồi sửa các dòng lệch") chưa làm được.

### Điều kiện xem lại

- Có tác vụ quan trọng cần agent đọc sheet giữa run mà `context` không đủ → bổ sung tạm dừng/tiếp tục vào adapter (dựa trên
  `needs_approval` / `RunState` của SDK nối với cơ chế tạm dừng của AgentOS), hoặc quay về ADR-06.
- Agno ra adapter chính thức cho OpenAI Agents SDK → bỏ adapter tự viết.
- OpenAI Agents SDK có AG-UI chính thức → xem có còn cần AgentOS không (session, REST, xác thực).
