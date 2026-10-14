<!-- FILE SINH TỰ ĐỘNG từ catalog/agent_landscape.yaml + agent_landscape.snapshot.json bằng `make landscape`. KHÔNG sửa tay. -->


# Radar framework agent · bảng so sánh

Dữ liệu duyệt: **2026-10-14** · số liệu registry: **2026-10-14** · 19 framework + 18 công cụ hỗ trợ. Cách đọc và quy trình cập nhật: [README](../README.md).

## 1. Radar

| Vòng | Framework |
|---|---|
| **Adopt** | [Agno + AgentOS](#agno) |
| **Trial** | [LangGraph](#langgraph) · [Pydantic AI](#pydantic-ai) · [DSPy](#dspy) |
| **Assess** | [Microsoft Agent Framework](#microsoft-agent-framework) · [Google Agent Development Kit (ADK)](#google-adk) · [Claude Agent SDK](#claude-agent-sdk) · [Strands Agents (AWS)](#strands-agents) · [CrewAI](#crewai) · [LlamaIndex (Agents / Workflows)](#llamaindex) · [Haystack (deepset)](#haystack) · [Mastra](#mastra) · [Vercel AI SDK](#vercel-ai-sdk) · [Hermes Agent (Nous Research)](#hermes-agent) · [Google Antigravity SDK](#google-antigravity) |
| **Hold** | [OpenAI Agents SDK](#openai-agents) · [AG2 (nhánh cộng đồng của AutoGen 0.2)](#ag2) · [AutoGen (Microsoft) / Semantic Kernel](#autogen) · [smolagents (Hugging Face)](#smolagents) |

## 2. Tính năng

✅ có · ◐ một phần / qua tích hợp · — không · ? chưa kiểm. Mức kiểm chứng: **source** đã đọc mã nguồn, **docs** tài liệu/registry chính thức, **secondary** bài viết thứ cấp — kiểm lại trước khi dựa vào.

| Framework | Vòng | Nhóm | routing | hitl | durable | otel | mcp | a2a | agui | eval | Kiểm chứng |
|---|---|---|---|---|---|---|---|---|---|---|---|
| [Agno + AgentOS](#agno) | Adopt | runtime | graph + llm | ✅ | ◐ | ✅ | ✅ | ✅ | ✅ | ✅ | source |
| [LangGraph](#langgraph) | Trial | orchestration | graph + llm | ✅ | ✅ | ◐ | ✅ | ◐ | ✅ | ◐ | source |
| [Pydantic AI](#pydantic-ai) | Trial | sdk | graph + llm | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | source |
| [Microsoft Agent Framework](#microsoft-agent-framework) | Assess | orchestration | graph + llm | ✅ | ◐ | ✅ | ✅ | ✅ | ✅ | ◐ | source |
| [Google Agent Development Kit (ADK)](#google-adk) | Assess | orchestration | graph + llm | ✅ | ◐ | ✅ | ✅ | ✅ | ✅ | ✅ | secondary |
| [OpenAI Agents SDK](#openai-agents) | Hold | vendor | llm | ✅ | ◐ | ◐ | ✅ | — | — | ◐ | source |
| [Claude Agent SDK](#claude-agent-sdk) | Assess | vendor | llm | ✅ | ◐ | ◐ | ✅ | — | ✅ | — | docs |
| [Strands Agents (AWS)](#strands-agents) | Assess | sdk | graph + llm | ◐ | ◐ | ✅ | ✅ | ✅ | ✅ | ? | secondary |
| [CrewAI](#crewai) | Assess | multi_agent | graph + llm | ◐ | ◐ | ✅ | ✅ | ◐ | ✅ | ◐ | secondary |
| [LlamaIndex (Agents / Workflows)](#llamaindex) | Assess | data | graph + llm | ✅ | ◐ | ◐ | ✅ | ? | ✅ | ✅ | secondary |
| [Haystack (deepset)](#haystack) | Assess | data | graph | ◐ | ? | ✅ | ✅ | ? | ? | ✅ | secondary |
| [DSPy](#dspy) | Trial | data | graph | — | — | ◐ | ✅ | — | — | ✅ | secondary |
| [Mastra](#mastra) | Assess | typescript | graph + llm | ✅ | ◐ | ✅ | ✅ | ✅ | ✅ | ✅ | secondary |
| [Vercel AI SDK](#vercel-ai-sdk) | Assess | typescript | llm | ◐ | — | ✅ | ✅ | — | ? | — | secondary |
| [AG2 (nhánh cộng đồng của AutoGen 0.2)](#ag2) | Hold | multi_agent | llm | ✅ | ? | ✅ | ✅ | ? | ✅ | ? | secondary |
| [AutoGen (Microsoft) / Semantic Kernel](#autogen) | Hold | multi_agent | llm | ◐ | ◐ | ✅ | ✅ | ? | — | ? | docs |
| [smolagents (Hugging Face)](#smolagents) | Hold | sdk | llm | — | — | ◐ | ✅ | — | — | — | secondary |
| [Hermes Agent (Nous Research)](#hermes-agent) | Assess | sdk | llm | ? | ? | ? | ? | ? | ? | ? | secondary |
| [Google Antigravity SDK](#google-antigravity) | Assess | vendor | ? | ? | ? | ? | ? | ? | ✅ | ? | docs |

**routing**: Điều hướng (graph = code định nghĩa nhánh; llm = model chọn agent/tool) · **hitl**: Tạm dừng chờ người duyệt / nhập liệu · **durable**: Chạy bền (resume sau lỗi, checkpoint lưu DB) · **otel**: Phát trace OpenTelemetry · **mcp**: Dùng MCP server làm tool · **a2a**: Giao thức A2A · **agui**: Giao thức AG-UI (frontend tools, stream sự kiện tới giao diện) · **eval**: Công cụ eval đi kèm

## 3. Số liệu registry

Major/12 tháng = số lần lên major trong 12 tháng trước ngày snapshot — đo tốc độ đổi API (gói 0.x đổi API ở bản minor nên ghi kèm `(0.x)`). Sao GitHub chỉ có khi chạy refresh với `GITHUB_TOKEN` (workflow hằng tháng).

| Framework | Gói | Phiên bản | Phát hành | Major/12 tháng | Giấy phép (registry) | Sao GitHub | Cờ |
|---|---|---|---|---|---|---|---|
| Agno + AgentOS | `agno` | `3.1.3` | 2026-10-12 | 1 | Apache Software License | — | — |
| LangGraph | `langgraph` | `1.2.15` | 2026-10-12 | 1 | MIT | — | — |
| Pydantic AI | `pydantic-ai-slim` | `2.56.0` | 2026-10-13 | 1 | MIT | — | — |
| Microsoft Agent Framework | `agent-framework` | `1.21.0` | 2026-10-08 | 0 | MIT License | — | — |
| Google Agent Development Kit (ADK) | `google-adk` | `2.12.0` | 2026-10-13 | 1 | Apache Software License | — | — |
| OpenAI Agents SDK | `openai-agents` | `0.23.1` | 2026-10-02 | 0 (0.x) | MIT | — | — |
| Claude Agent SDK | `claude-agent-sdk` | `0.2.166` | 2026-10-14 | 0 (0.x) | MIT License | — | — |
| Strands Agents (AWS) | `strands-agents` | `1.60.0` | 2026-10-12 | 0 | Apache Software License | — | — |
| CrewAI | `crewai` | `1.15.28` | 2026-10-14 | 1 | không khai báo | — | — |
| LlamaIndex (Agents / Workflows) | `llama-index-core` | `0.14.25` | 2026-09-21 | 0 (0.x) | MIT | — | — |
| Haystack (deepset) | `haystack-ai` | `3.3.0` | 2026-10-01 | 1 | Apache-2.0 | — | — |
| DSPy | `dspy` | `3.4.1` | 2026-10-12 | 0 | MIT License | — | — |
| Mastra | `@mastra/core` | `1.77.0` | 2026-10-14 | 1 | Apache-2.0 | — | — |
| Vercel AI SDK | `ai` | `7.0.140` | 2026-10-14 | 2 | Apache-2.0 | — | — |
| AG2 (nhánh cộng đồng của AutoGen 0.2) | `ag2` | `1.1.2` | 2026-10-03 | 1 | Apache-2.0 | — | — |
| AutoGen (Microsoft) / Semantic Kernel | `autogen-agentchat` | `0.7.5` | 2025-09-30 | 0 (0.x) | MIT License | — | ⚠ autogen-agentchat không phát hành 379 ngày |
| smolagents (Hugging Face) | `smolagents` | `1.26.0` | 2026-05-29 | 0 | không khai báo | — | — |
| Hermes Agent (Nous Research) | `hermes-agent` | `0.19.0` | 2026-07-20 | 0 (0.x) | MIT | — | — |
| Google Antigravity SDK | `google-antigravity` | `0.1.22` | 2026-10-13 | 0 (0.x) | Apache Software License | — | — |

## 4. Từng framework

<a id="agno"></a>

### Agno + AgentOS · Adopt

- **Nhóm:** Runtime đầy đủ — API, session, UI, trace đi kèm · **Ngôn ngữ:** python · **Repo:** [agno-agi/agno](https://github.com/agno-agi/agno)
- **Giấy phép:** SDK + runtime Apache-2.0; control plane os.agno.com trả phí (không bắt buộc)
- **Chọn khi:** Cần runtime đầy đủ nhanh, agent nối giao diện (add-in, web) qua AG-UI, dùng chung với CMB-09
- **Mạnh:** AgentOS có sẵn API/SSE, session lưu DB, JWT/RBAC, trace, MCP client + server, A2A, Skills; Frontend tools qua AG-UI chạy sẵn (run tạm dừng → client chạy tool → chạy tiếp), trạng thái lưu ở server; Workflows (bước, router, điều kiện, vòng lặp) cho luồng cố định; Team cho điều hướng bằng model
- **Yếu:** Đổi API nhanh (2.0 09/2025 → 3.0 08/2026) — cần khóa phiên bản và test hồi quy; Thành viên của Team không nhận frontend tools (3.1.3) — agent dùng tool phía client phải là agent chạy trực tiếp
- **Dùng trong repo:** CMB-10 (POC 0.2; ADR-09); CMB-09 (thiết kế)
- **Review:** 2026-10-14 · kiểm chứng: source

<a id="langgraph"></a>

### LangGraph · Trial

- **Nhóm:** Điều phối bằng đồ thị / workflow — luồng do code định nghĩa · **Ngôn ngữ:** python, typescript · **Repo:** [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)
- **Giấy phép:** Thư viện MIT; server langgraph-api là Elastic-2.0 (không phải OSI); LangSmith trả phí
- **Chọn khi:** Luồng nhiều bước, nhiều nhánh, cần audit và duyệt người (ngân hàng, bảo hiểm, đối soát)
- **Mạnh:** Luồng là đồ thị code định nghĩa — điều hướng chính xác, dễ kiểm toán; Checkpointer (PostgreSQL), interrupt chờ người duyệt, xem lại/quay lui từng bước — trưởng thành nhất; Cộng đồng và tài liệu lớn nhất; bản Python và TypeScript
- **Yếu:** Viết dài hơn SDK gọn; tracing/eval tốt nhất nằm ở LangSmith (thương mại); Frontend tools qua AG-UI phải tự nối vào state của graph
- **Review:** 2026-10-14 · kiểm chứng: source

<a id="pydantic-ai"></a>

### Pydantic AI · Trial

- **Nhóm:** SDK agent gọn — vòng lặp tool do model dẫn · **Ngôn ngữ:** python · **Repo:** [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai)
- **Giấy phép:** MIT; Logfire SDK MIT, backend Logfire là dịch vụ (có thể gửi OTel sang Langfuse thay thế)
- **Chọn khi:** Dịch vụ agent nhỏ, ưu tiên kiểu dữ liệu chặt và OTel; đội đã quen Pydantic/FastAPI
- **Mạnh:** Kiểu dữ liệu chặt (Pydantic), output có cấu trúc, lỗi rõ; OTel có sẵn; pydantic-evals; chạy bền qua Temporal/DBOS/Prefect; AGUIAdapter + ExternalToolset cho frontend tools
- **Yếu:** Là thư viện — API, xác thực, session phải tự dựng; Đổi major nhanh (1.0 09/2025 → 2.0 06/2026); client gửi lại toàn bộ lịch sử khi dùng AG-UI
- **Review:** 2026-10-14 · kiểm chứng: source

<a id="microsoft-agent-framework"></a>

### Microsoft Agent Framework · Assess

- **Nhóm:** Điều phối bằng đồ thị / workflow — luồng do code định nghĩa · **Ngôn ngữ:** python, dotnet · **Repo:** [microsoft/agent-framework](https://github.com/microsoft/agent-framework)
- **Giấy phép:** MIT; kế thừa AutoGen + Semantic Kernel; GA 1.0 tháng 4/2026
- **Chọn khi:** Công ty chuẩn hóa trên Azure/.NET/Microsoft 365
- **Mạnh:** Workflow có checkpoint; agent + workflow trong một SDK cho cả Python và .NET; OTel theo quy ước GenAI; AG-UI, MCP, A2A chính thức; Hợp hệ Azure / Microsoft 365 / Foundry
- **Yếu:** Kho trạng thái duyệt AG-UI mặc định trong bộ nhớ — chạy nhiều instance phải tự thay; Một số phần còn preview; mạnh nhất khi dùng cùng Azure
- **Review:** 2026-10-14 · kiểm chứng: source

<a id="google-adk"></a>

### Google Agent Development Kit (ADK) · Assess

- **Nhóm:** Điều phối bằng đồ thị / workflow — luồng do code định nghĩa · **Ngôn ngữ:** python, java, go, typescript · **Repo:** [google/adk-python](https://github.com/google/adk-python)
- **Giấy phép:** Apache-2.0
- **Chọn khi:** Dùng Google Cloud/Gemini, hoặc cần eval quỹ đạo ngay trong framework
- **Mạnh:** Eval có sẵn (`adk eval`), chấm cả quỹ đạo gọi tool; dev UI để debug; Agent tuần tự / song song / vòng lặp do code định nghĩa + chuyển giao bằng model; A2A do Google khởi xướng; nhiều ngôn ngữ
- **Yếu:** Mạnh nhất với Gemini/Vertex; 2.0 mới (2026) nên còn đổi API
- **Review:** 2026-10-14 · kiểm chứng: secondary

<a id="openai-agents"></a>

### OpenAI Agents SDK · Hold

- **Nhóm:** SDK của nhà cung cấp model · **Ngôn ngữ:** python, typescript · **Repo:** [openai/openai-agents-python](https://github.com/openai/openai-agents-python)
- **Giấy phép:** MIT; trace mặc định gửi lên nền tảng OpenAI (tắt được, đổi sang OTel qua processor)
- **Chọn khi:** Hệ thống dùng GPT là chính, không cần frontend tools, muốn ít code nhất
- **Mạnh:** Rất gọn: Agent, tool, handoff, guardrail; `needs_approval` + RunState cho duyệt người; Bản Python và TypeScript; dùng tốt nhất với model OpenAI (Responses API)
- **Yếu:** AG-UI chưa có (README AG-UI ghi "In Progress") — phải tự viết adapter, mất frontend tools; Handoff do model quyết định, kém chắc chắn hơn đồ thị
- **Dùng trong repo:** CMB-10 POC 0.1 (ADR-08; đã thay bằng Agno)
- **Review:** 2026-10-14 · kiểm chứng: source

<a id="claude-agent-sdk"></a>

### Claude Agent SDK · Assess

- **Nhóm:** SDK của nhà cung cấp model · **Ngôn ngữ:** python, typescript · **Repo:** [anthropics/claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python)
- **Giấy phép:** MIT; chạy với model Claude
- **Chọn khi:** Agent tự động hóa công việc trên file/repo/terminal, đã dùng Claude
- **Mạnh:** Vòng lặp agent của Claude Code: đọc/sửa file, chạy lệnh, subagent, skill, hook kiểm soát quyền; Có tích hợp AG-UI chính thức trong repo AG-UI
- **Yếu:** Gắn với model Claude; thiên về agent làm việc trên máy/repo hơn là agent nghiệp vụ nhiều hệ thống
- **Review:** 2026-10-14 · kiểm chứng: docs

<a id="strands-agents"></a>

### Strands Agents (AWS) · Assess

- **Nhóm:** SDK agent gọn — vòng lặp tool do model dẫn · **Ngôn ngữ:** python, typescript · **Repo:** [strands-agents/sdk-python](https://github.com/strands-agents/sdk-python)
- **Giấy phép:** Apache-2.0
- **Chọn khi:** Hạ tầng AWS, muốn SDK gọn có OTel
- **Mạnh:** Gọn, model-driven; graph/swarm cho đa agent; OTel có sẵn; Triển khai lên Amazon Bedrock AgentCore (có AG-UI chính thức)
- **Yếu:** Hợp nhất khi ở AWS; tính năng HITL/chạy bền chưa kiểm
- **Review:** 2026-10-14 · kiểm chứng: secondary

<a id="crewai"></a>

### CrewAI · Assess

- **Nhóm:** Đa agent theo vai trò / hội thoại · **Ngôn ngữ:** python · **Repo:** [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI)
- **Giấy phép:** MIT (repo); nền tảng CrewAI AMP trả phí
- **Chọn khi:** Nguyên mẫu đa agent nhanh; luồng sản xuất nên viết bằng Flows
- **Mạnh:** Đa agent theo vai trò viết nhanh; Flows (code định nghĩa) cho luồng chặt; Cộng đồng lớn, nhiều ví dụ
- **Yếu:** Crew (model tự phối hợp) khó kiểm soát và khó debug; nhiều lượt gọi model
- **Review:** 2026-10-14 · kiểm chứng: secondary

<a id="llamaindex"></a>

### LlamaIndex (Agents / Workflows) · Assess

- **Nhóm:** Agent xoay quanh dữ liệu, RAG, tối ưu prompt · **Ngôn ngữ:** python, typescript · **Repo:** [run-llama/llama_index](https://github.com/run-llama/llama_index)
- **Giấy phép:** MIT; LlamaCloud trả phí
- **Chọn khi:** Agent nặng RAG / xử lý tài liệu (Nhóm 6 + 7)
- **Mạnh:** Mạnh nhất khi agent xoay quanh tài liệu, RAG, trích xuất; Workflows hướng sự kiện
- **Yếu:** Phần agent tổng quát không phải thế mạnh chính
- **Review:** 2026-10-14 · kiểm chứng: secondary

<a id="haystack"></a>

### Haystack (deepset) · Assess

- **Nhóm:** Agent xoay quanh dữ liệu, RAG, tối ưu prompt · **Ngôn ngữ:** python · **Repo:** [deepset-ai/haystack](https://github.com/deepset-ai/haystack)
- **Giấy phép:** Apache-2.0
- **Chọn khi:** Pipeline RAG/agent cần cấu trúc rõ, chạy lâu dài
- **Mạnh:** Pipeline rõ ràng cho RAG/agent production; 3.0 (07/2026)
- **Yếu:** Ít dùng cho agent nhiều bước nối giao diện
- **Review:** 2026-10-14 · kiểm chứng: secondary

<a id="dspy"></a>

### DSPy · Trial

- **Nhóm:** Agent xoay quanh dữ liệu, RAG, tối ưu prompt · **Ngôn ngữ:** python · **Repo:** [stanfordnlp/dspy](https://github.com/stanfordnlp/dspy)
- **Giấy phép:** MIT
- **Chọn khi:** Đã có golden set và muốn tối ưu độ chính xác của một bước LLM (phân loại, trích xuất, chọn tool)
- **Mạnh:** Tối ưu prompt / few-shot tự động theo bộ eval — biến "viết prompt" thành bài toán đo được
- **Yếu:** Không phải runtime phục vụ; dùng kèm framework khác
- **Review:** 2026-10-14 · kiểm chứng: secondary

<a id="mastra"></a>

### Mastra · Assess

- **Nhóm:** Hệ TypeScript · **Ngôn ngữ:** typescript · **Repo:** [mastra-ai/mastra](https://github.com/mastra-ai/mastra)
- **Giấy phép:** Apache-2.0 (core); 1.0 tháng 1/2026
- **Chọn khi:** Backend agent viết bằng TypeScript / Next.js
- **Mạnh:** Runtime TypeScript đầy đủ: agent, workflow suspend/resume, memory, eval/scorer, tracing
- **Yếu:** Khác ngôn ngữ với các dự án Python trong repo
- **Review:** 2026-10-14 · kiểm chứng: secondary

<a id="vercel-ai-sdk"></a>

### Vercel AI SDK · Assess

- **Nhóm:** Hệ TypeScript · **Ngôn ngữ:** typescript · **Repo:** [vercel/ai](https://github.com/vercel/ai)
- **Giấy phép:** Apache-2.0
- **Chọn khi:** Giao diện chat trong ứng dụng web TypeScript
- **Mạnh:** Vòng lặp tool + stream UI tốt nhất cho ứng dụng React/Next.js; telemetry OTel
- **Yếu:** Là thư viện gọi model + UI, không phải runtime agent
- **Review:** 2026-10-14 · kiểm chứng: secondary

<a id="ag2"></a>

### AG2 (nhánh cộng đồng của AutoGen 0.2) · Hold

- **Nhóm:** Đa agent theo vai trò / hội thoại · **Ngôn ngữ:** python · **Repo:** [ag2ai/ag2](https://github.com/ag2ai/ag2)
- **Giấy phép:** Apache-2.0
- **Chọn khi:** Đã có code AutoGen 0.2 cần chạy tiếp
- **Mạnh:** Mẫu hội thoại đa agent quen thuộc của AutoGen; có AG-UI
- **Yếu:** Hội thoại do model dẫn khó kiểm soát; dễ nhầm với AutoGen của Microsoft (đang bảo trì)
- **Review:** 2026-10-14 · kiểm chứng: secondary

<a id="autogen"></a>

### AutoGen (Microsoft) / Semantic Kernel · Hold

- **Nhóm:** Đa agent theo vai trò / hội thoại · **Ngôn ngữ:** python, dotnet · **Repo:** [microsoft/autogen](https://github.com/microsoft/autogen)
- **Giấy phép:** MIT; Microsoft đưa hai dự án vào Microsoft Agent Framework
- **Chọn khi:** Không chọn cho việc mới
- **Mạnh:** Nhiều code mẫu cũ
- **Yếu:** autogen-agentchat không phát hành từ 09/2025 — dùng Microsoft Agent Framework cho việc mới
- **Review:** 2026-10-14 · kiểm chứng: docs

<a id="smolagents"></a>

### smolagents (Hugging Face) · Hold

- **Nhóm:** SDK agent gọn — vòng lặp tool do model dẫn · **Ngôn ngữ:** python · **Repo:** [huggingface/smolagents](https://github.com/huggingface/smolagents)
- **Giấy phép:** Apache-2.0
- **Chọn khi:** Nghiên cứu, thử model mở
- **Mạnh:** Agent viết code Python để gọi tool; gọn, hợp model mở
- **Yếu:** Chạy code do model sinh cần sandbox; nhịp phát hành chậm lại (bản cuối 05/2026)
- **Review:** 2026-10-14 · kiểm chứng: secondary

<a id="hermes-agent"></a>

### Hermes Agent (Nous Research) · Assess

- **Nhóm:** SDK agent gọn — vòng lặp tool do model dẫn · **Ngôn ngữ:** python · **Repo:** [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
- **Giấy phép:** MIT
- **Chọn khi:** Theo dõi ý tưởng "agent tự học skill"; chưa dùng cho production
- **Mạnh:** Agent tự tạo và cải thiện skill từ kinh nghiệm, có bộ nhớ lâu dài; tăng trưởng cộng đồng rất nhanh năm 2026
- **Yếu:** Còn 0.x; giống sản phẩm agent cá nhân hơn là framework cho quy trình doanh nghiệp — chưa kiểm
- **Review:** 2026-10-14 · kiểm chứng: secondary

<a id="google-antigravity"></a>

### Google Antigravity SDK · Assess

- **Nhóm:** SDK của nhà cung cấp model · **Ngôn ngữ:** python · **Repo:** [google-antigravity/antigravity-sdk-python](https://github.com/google-antigravity/antigravity-sdk-python)
- **Giấy phép:** Apache-2.0
- **Chọn khi:** Chỉ theo dõi
- **Mạnh:** SDK agent mới của Google, có AG-UI chính thức
- **Yếu:** Còn 0.1.x — chưa đủ ổn định để đánh giá
- **Review:** 2026-10-14 · kiểm chứng: docs

## 5. Lớp hỗ trợ: giao thức, quan sát, eval, chạy bền, bộ nhớ, sandbox

| Công cụ | Lớp | Vòng | Gói | Phiên bản | Phát hành | Giấy phép (registry) | Ghi chú |
|---|---|---|---|---|---|---|---|
| MCP (Model Context Protocol) SDK | protocol | Adopt | `mcp` | `2.3.0` | 2026-10-02 | MIT License | Chuẩn nối tool/dữ liệu vào agent; bản Python 2.x (2026) |
| A2A (Agent2Agent) SDK | protocol | Trial | `a2a-sdk` | `1.2.2` | 2026-10-05 | Apache-2.0 | Agent gọi agent qua mạng; 1.x từ 2026 |
| AG-UI protocol | protocol | Adopt | `ag-ui-protocol` | `1.0.0` | 2026-09-17 | MIT | Agent ↔ giao diện, frontend tools; 1.0 (09/2026); dùng ở CMB-10 |
| OpenTelemetry GenAI semantic conventions | protocol | Trial | `openinference-instrumentation` | `0.1.71` | 2026-10-07 | Apache-2.0 | Tên span invoke_agent / execute_tool; vẫn ở trạng thái Development — thuộc tính có thể đổi |
| Langfuse | observability | Adopt | `langfuse` | `4.18.0` | 2026-10-14 | MIT | Trace + prompt + eval, MIT, tự host được; nhận OTel từ mọi framework |
| Arize Phoenix | observability | Assess | `arize-phoenix` | `20.21.3` | 2026-10-14 | Elastic-2.0 | Trace + eval tốt; giấy phép Elastic-2.0 (không phải OSI) |
| Pydantic Logfire | observability | Assess | `logfire` | `5.2.0` | 2026-10-13 | MIT | SDK MIT dựa trên OTel; backend là dịch vụ |
| LangSmith | observability | Assess | `langsmith` | `0.14.8` | 2026-10-13 | MIT | Tốt nhất cho LangGraph; nền tảng thương mại |
| MLflow Tracing | observability | Assess | `mlflow` | `3.17.1` | 2026-10-13 | Apache Software License | Apache-2.0; hợp khi đã dùng MLflow cho ML cổ điển |
| OpenLLMetry (Traceloop) | observability | Assess | `traceloop-sdk` | `0.62.4` | 2026-09-29 | Apache-2.0 | Instrumentation OTel cho nhiều SDK LLM |
| DeepEval | eval | Trial | `deepeval` | `4.2.8` | 2026-10-02 | Apache Software License | Metric agent (task completion, tool correctness) + LLM-as-judge, chạy như pytest |
| Inspect AI (UK AISI) | eval | Trial | `inspect-ai` | `0.3.280` | 2026-10-14 | MIT License | Khung eval agent có sandbox, MIT; chấm quỹ đạo và kết quả |
| Ragas | eval | Assess | `ragas` | `0.4.3` | 2026-01-13 | Apache License | Metric RAG; nhịp phát hành chậm (bản cuối 01/2026) |
| Temporal | durable | Assess | `temporalio` | `1.34.0` | 2026-09-30 | MIT | Chạy bền cho luồng dài; tích hợp với Pydantic AI, OpenAI Agents SDK |
| DBOS | durable | Assess | `dbos` | `3.2.0` | 2026-09-29 | MIT License | Chạy bền dựa trên PostgreSQL, nhẹ hơn Temporal |
| Mem0 | memory | Assess | `mem0ai` | `2.2.1` | 2026-09-25 | Apache-2.0 | Bộ nhớ dài hạn cho agent |
| Letta | memory | Assess | `letta` | `0.34.12` | 2026-10-12 | Apache-2.0 | Agent có bộ nhớ tự quản (MemGPT cũ) |
| E2B | sandbox | Assess | `e2b` | `2.56.0` | 2026-10-13 | MIT | Sandbox cloud để agent chạy code an toàn |
