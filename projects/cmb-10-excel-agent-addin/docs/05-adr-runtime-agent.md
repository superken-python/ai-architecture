# 05 · ADR-07 · Runtime agent cho add-in: AgentOS/Agno hay framework open source khác?

- **Trạng thái:** đề xuất — chờ chủ dự án duyệt
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
