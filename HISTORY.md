# Lịch sử công việc

Ghi lại **những gì đã làm**, mới nhất ở trên. Việc **sắp làm** nằm trong [CHECKLIST.md](CHECKLIST.md).

Quy ước khi thêm một mục:

- Tiêu đề: `## YYYY-MM-DD · <tên công việc>` (kèm link PR nếu có).
- Ghi: **Đã làm** (kết quả cụ thể), **Quyết định** (đã chọn gì, vì sao), **Còn mở** (chuyển sang CHECKLIST).
- Khi một mục trong CHECKLIST hoàn thành: đánh dấu `[x]` ở CHECKLIST và thêm một dòng tóm tắt vào đây.

---

## 2026-10-17 · Harness agent: Agno → LangChain, cải tiến theo Claude Code + lab LLM-05 đầu tiên

**Đã làm**

- `docs/agent-radar/02-harness-agno-sang-langchain.md`: một run của Agno 3.1.3 đi qua những bước nào (có dẫn mã
  nguồn), 6 hành vi đã đo bằng thí nghiệm, bảng 5 run; ánh xạ sang LangChain 1.4.6 / LangGraph 1.2.16; toàn bộ code
  từng mảnh; 8 lớp cải tiến theo Claude Code và bộ đo vàng.
- `labs/llm-05-trung-cap-harness-langchain/`: lab đầu tiên của repo. Package `harness/` (model kịch bản + model thật,
  tool server + tool client qua `interrupt()`, instructions động, cửa sổ N run, memory theo user, giới hạn, người
  duyệt; `improved.py`: file luật, đọc trước khi ghi có dấu vân tay, kiểm chứng sau khi ghi, `<system-reminder>`,
  quyền theo vai trò, subagent, todo, tóm tắt/xoá kết quả tool cũ), `demo.py`, `eval_golden.py`.
- 39 test (24 hành vi + 15 đồng bộ tài liệu–code), chạy bằng `uv run --no-project --with ...` — không thêm gói vào
  lockfile chung.

**Quyết định**

- Code trong tài liệu sinh nguyên văn từ file của lab; `test_doc_sync.py` đỏ khi hai bên lệch.
- Sửa có chủ ý so với Agno: thiếu `user_id` thì không đọc/ghi memory (Agno dùng `"default"` chung); trần số bước
  dừng hẳn (`exit_behavior="end"`) và có thêm trần số lượt model.
- **Ưu tiên:** tập trung agent harness và workflow agent trước; AG-UI và API để sau (khớp
  `docs/self-practices` mục 10). Tài liệu 02 có phần Tóm tắt và bảng thứ tự học harness → workflow → AG-UI.

**Còn mở** (chuyển sang CHECKLIST)

- Chạy `eval_golden.py` với model thật; workflow agent bằng `StateGraph` (tiếp theo); test resume nhiều interrupt
  cùng lúc; endpoint AG-UI (để sau).

## 2026-10-14 · Radar agent — so sánh cơ chế agent của 4 framework

- `docs/agent-radar/01-co-che-agent.md`: vòng lặp tool, dừng và kết quả có cấu trúc, điểm can thiệp (hook, middleware,
  guardrail), tạm dừng/chạy tiếp, nhiều agent, bộ nhớ — Agno 3.1.3, OpenAI Agents SDK 0.23.1, LangGraph 1.2.15 +
  LangChain 1.4.5, Pydantic AI 2.56.0; đối chiếu trên mã nguồn từng gói.

## 2026-10-14 · Radar agent cho Nhóm 7 — tài liệu sống, cập nhật hằng tháng

**Đã làm**

- `docs/agent-radar/README.md`: kết luận theo nhu cầu, 8 tiêu chí (điều hướng, duyệt người, chạy bền, OTel, MCP, A2A,
  AG-UI, eval), xu hướng 2026 kèm bằng chứng, kiến trúc tham chiếu cho agent Nhóm 7, cách tự đo bằng golden set, quy
  trình cập nhật và quy tắc vòng radar.
- `catalog/agent_landscape.yaml`: 19 framework + 18 công cụ hỗ trợ (giao thức, quan sát, eval, chạy bền, bộ nhớ, sandbox),
  mỗi mục có vòng Adopt/Trial/Assess/Hold, mức kiểm chứng (source/docs/secondary), ngày review.
- `src/aiarch/landscape.py` + `make landscape-refresh` / `make landscape`: kéo số liệu PyPI/npm (+ GitHub khi có token)
  vào `catalog/agent_landscape.snapshot.json`, sinh `docs/agent-radar/generated/bang-so-sanh.md`, gắn cờ gói lâu không
  phát hành, lên major sau lần review, repo archive, mục quá hạn review. Test `tests/test_landscape.py`.
- Workflow `.github/workflows/agent-landscape.yml`: ngày 1 hằng tháng kéo số liệu và mở PR nếu có thay đổi.

**Quyết định**

- Adopt: Agno/AgentOS (đang dùng ở CMB-10, CMB-09). Trial: LangGraph, Pydantic AI, DSPy. Hold: AutoGen/Semantic Kernel
  (đã vào Microsoft Agent Framework), smolagents cho production, OpenAI Agents SDK khi cần AG-UI.
- Lớp chung: MCP cho tool, AG-UI cho giao diện, OTel → Langfuse cho trace, golden set riêng cho eval.

**Còn mở**

- Nhiều mục ở mức `secondary` — cần đọc tài liệu/mã nguồn trước khi dựa vào; chưa có số sao GitHub (môi trường làm bản
  này không gọi được GitHub API — workflow hằng tháng sẽ bổ sung).
- Cần bật quyền "Allow GitHub Actions to create and approve pull requests" để workflow mở PR.

## 2026-10-13 · CMB-10 — POC 0.2: quay lại agent Agno, công cụ Excel chạy ở add-in, Office add-in cho Excel thật ([#6](https://github.com/superken-python/ai-architecture/pull/6))

**Đã làm**

- Bỏ OpenAI Agents SDK và adapter tự viết; agent là một `Agent` Agno phục vụ qua interface AGUI của AgentOS, model
  `OpenAIResponses(gpt-5-mini, reasoning low, store=false)`.
- Công cụ Excel do giao diện khai báo qua AG-UI (`excel_get_context`, `excel_find_rows`, `excel_read_rows`,
  `excel_set_values`, `excel_append_rows`): run tạm dừng → giao diện chạy công cụ (tool ghi có xem trước + xác nhận,
  đọc lại sheet trước khi ghi) → gửi kết quả → run chạy tiếp.
- Một khung chat, hai host: web POC (bảng mô phỏng, file trên server) và **task pane Office add-in** (Office.js, Excel
  Table, giữ số 0 đầu, chèn file xuất vào workbook) + `addin/manifest.xml`, icon, `make addin-certs`, `make dev-https`,
  `make addin-manifest`.
- Chế độ offline và test dùng OpenAI Responses API giả lập trong tiến trình (luật cố định / kịch bản) — cùng đường code
  Agno như khi có key; từ chối `function_call_output` không khớp lời gọi hàm như OpenAI.
- Lệnh `/search`, `/datasets`, `/help` chuyển sang `POST /api/v1/commands` (không gọi model); `/search` mới dùng cột đang
  chọn, agent tự chọn cột khi tìm.
- 47 test unit + integration (tạm dừng/tiếp tục qua AgentOS thật, gpt-5-mini giả lập gọi song song tool server + tool
  Excel) + 2 test e2e (web POC; task pane với Office.js giả lập). Viết lại tài liệu 06, thêm ADR-09.

**Quyết định**

- ADR-09 (theo yêu cầu chủ dự án): quay lại agent Agno vì add-in cần frontend tools; thay ADR-08. Một Agent, không Team:
  đọc mã nguồn Agno 3.1.3 thấy thành viên Team nhận `dependencies` nhưng không nhận công cụ của client.

**Còn mở**

- Chưa chạy với gpt-5-mini thật và chưa chạy trên Excel thật (môi trường làm POC chặn `api.openai.com`, không có Excel).

## 2026-10-13 · CMB-10 — POC 0.1: AgentOS + AG-UI + OpenAI Agents SDK, chat → file Excel, /search → ghi vào cột ([#6](https://github.com/superken-python/ai-architecture/pull/6))

**Đã làm**

- `projects/cmb-10-excel-agent-addin/`: POC Python theo
  [best practice cấu trúc dự án](projects/python-ai-project-structure-best-practices.md) (`src/` layout, tầng API/service/
  schema/agent, prompt YAML tách khỏi code, uv + Makefile).
- Agent viết bằng **OpenAI Agents SDK** 0.23.1: `Điều phối` (triage) handoff sang `Excel Report Agent` (`export_excel`) và
  `Data Search Agent` (`search_data`); model mặc định `gpt-5-mini`; chưa có key thì chạy model offline (luật cố định).
- **AgentOS** (Agno 3.1.3) chỉ làm runtime: adapter tự viết `OpenAIAgentsAdapter` đổi sự kiện stream của SDK sang sự kiện
  AgentOS → AG-UI; session lưu SQLite.
- API dữ liệu giả lập (`/datasets`, `/search`, `/export` → `.xlsx`); workbook service lưu theo phiên bản, xem trước, ghi cột
  / thêm dòng có kiểm chứng (kiểu, phạm vi, trùng mã, `expected_version`), hoàn tác.
- Giao diện web (JS thuần, client AG-UI): khung chat + thẻ file → bấm xem dữ liệu; `/search` (theo cột chọn trên bảng hoặc
  `Cột: từ khóa`) → tích kết quả → **Ghi vào cột** / **Thêm thành dòng mới** → xác nhận.
- 38 test unit + integration (AG-UI qua AgentOS thật, `ScriptedModel` mô phỏng gpt-5-mini gọi tool) + 1 test e2e Chromium;
  hướng dẫn: `docs/06-poc-huong-dan-su-dung.md`.

**Quyết định**

- ADR-08 (chủ dự án chọn): agent và tool viết bằng OpenAI Agents SDK, không viết agent bằng Agno; thay ADR-06. Ghi dữ liệu
  theo mẫu *agent đề xuất → người dùng xác nhận trên giao diện → API ghi xác định*, không cần frontend tools.

**Còn mở**

- Chưa chạy với gpt-5-mini thật (chưa có key; môi trường làm POC chặn `api.openai.com`).
- Adapter chưa hỗ trợ frontend tools (tạm dừng/tiếp tục) — chỉ cần khi agent phải tự đọc sheet giữa run.

## 2026-10-13 · CMB-10 — ADR-07 chọn runtime agent cho Excel add-in ([#6](https://github.com/superken-python/ai-architecture/pull/6))

**Đã làm**

- So sánh AgentOS/Agno với Pydantic AI, Microsoft Agent Framework, LangGraph, Mastra, Google ADK, OpenAI Agents SDK và nền
  tảng low-code theo 6 tiêu chí, đọc mã nguồn phần AG-UI của từng framework và giấy phép trong metadata gói →
  `projects/cmb-10-excel-agent-addin/docs/05-adr-runtime-agent.md`.

**Quyết định** (đề xuất, chờ duyệt)

- Giữ AgentOS/Agno (Apache-2.0): duy nhất có sẵn frontend tools + tạm dừng/tiếp tục lưu ở server, xác thực, session, trace,
  MCP, skill, và dùng chung runtime với CMB-09. AG-UI là giao kèo để backend thay được.
- Dự phòng theo thứ tự: Pydantic AI → Microsoft Agent Framework → LangGraph (server `langgraph-api` là Elastic-2.0).

**Còn mở**

- Control plane của AgentOS (os.agno.com) trả phí khi nối AgentOS chạy thật — add-in không cần, nhưng CMB-09 cần tính nếu
  dùng AgentOS UI ở production.

## 2026-10-13 · Bài toán mới CMB-10 — trợ lý AI trong Excel nối với agent của hệ thống (chỉ tài liệu, [#6](https://github.com/superken-python/ai-architecture/pull/6))

**Đã làm**

- Phân loại: Nhóm 7 + Nhóm 6 → thêm tổ hợp **CMB-10** vào `catalog/combinations.yaml` (11 kỹ năng, 3 kỹ năng keo, 5 bẫy,
  metric end-to-end); thêm ví dụ vào Nhóm 7 (`problems.yaml`) và CMB-10 vào hướng "LLM ứng dụng & Agent"
  (`roadmap.yaml`); `make catalog` sinh lại 5 trang; số tổ hợp 9 → 10 trong README; thêm ví dụ phân rã vào bản đồ bài toán.
- `projects/cmb-10-excel-agent-addin/`: README (framing theo mẫu + kết luận nhanh) và 4 tài liệu nghiên cứu — mô tả bài
  toán và phân loại; giải pháp và kiến trúc (4 phương án, kết nối AG-UI, bộ công cụ Excel, bảo mật, triển khai, ADR);
  41 tính năng mở rộng; đánh giá khả thi (14 bằng chứng có nguồn, 12 rủi ro, ước lượng công sức, kế hoạch POC + go/no-go).
- Kiểm chứng: requirement set Excel (mới nhất ExcelApi 1.21) và API tìm/chèn/gộp hoàn tác trong `@types/office-js`
  1.0.611; mã nguồn `agno` 3.1.1 và 3.1.3 (AG-UI frontend tools + tạm dừng/tiếp tục run, REST, MCP, JWT); phiên bản npm
  của AG-UI client, CopilotKit, MSAL.js; tài liệu Claude for Excel và Microsoft Graph Excel API.

**Quyết định** (đề xuất, chờ duyệt)

- Không thêm nhóm thứ 9: "plugin trong Excel" là kênh giao diện, bài toán là tổ hợp G7 + G6.
- Phương án A (tự xây add-in React + Office.js, nối AgentOS qua AG-UI, cổng ghi đặt ở add-in) làm hướng chính; phương án B
  (Claude for Excel/Copilot + agent hệ thống qua MCP) chỉ chạy thử song song nếu công ty đã có license.
- "Code tìm và tính, LLM chọn tham số"; mọi lệnh ghi qua kiểm chứng + xem trước + xác nhận + một bước hoàn tác.

**Còn mở**

- 9 câu hỏi mở (agent hệ thống nào, phiên bản Excel, tenant/admin, license, chính sách dữ liệu, hệ thống nghiệp vụ,
  workbook mẫu, mạng, nhân lực) → [CHECKLIST.md](CHECKLIST.md).
- `learn.microsoft.com` bị chặn trong môi trường nghiên cứu nên đã đọc bản Markdown gốc trên GitHub của Microsoft; chưa
  chạy thử trên Excel thật.

## 2026-10-09 · Kế hoạch dự án Realtime Voice Translate (chỉ tài liệu)

**Đã làm**

- `projects/realtime-voice-translate/`: README (framing theo mẫu dự án) và
  [kế hoạch triển khai chi tiết](projects/realtime-voice-translate/docs/01-ke-hoach-trien-khai.md) cho web điện thoại dịch
  hội thoại trực tiếp Nhật ⇄ Anh ⇄ Việt: SLO, kiến trúc, chọn model cho GPU 8 GB, pipeline realtime, UI chia đôi, cấu trúc
  thư mục theo best practice, Docker hai phần + HTTPS nội bộ, triển khai trên máy GPU, eval, kế hoạch P0–P6, rủi ro, ADR.

**Quyết định** (đề xuất, chờ P0 đo)

- Cascade Silero VAD → Whisper `large-v3-turbo` (LID giới hạn ja/en/vi + prior theo nửa màn hình) → Hy-MT2-1.8B qua
  llama.cpp; ước tính 4,5–5 GB VRAM.
- WebSocket thay vì WebRTC cho MVP: chưa phát âm thanh (TTS) nên chưa cần WebRTC.
- Chỉ triển khai trên máy GPU (chủ dự án chốt): `make deploy` build image tại chỗ theo commit → chạy → smoke → tự
  rollback khi lỗi; không dùng GitHub Actions để deploy.
- Tạm bỏ ngrok (chủ dự án chốt): chỉ dùng trong mạng nội bộ; nginx phục vụ HTTPS bằng chứng chỉ mkcert vì điện thoại cần
  HTTPS để dùng micro; giao diện, REST và WebSocket cùng một origin.

**Còn mở**

- Yêu cầu số 7 còn trống; GPU cụ thể; có tên miền riêng để làm HTTPS nội bộ không; có bật CI kiểm thử riêng không
  → [CHECKLIST.md](CHECKLIST.md).

## 2026-10-08 · Trang web lộ trình cho GitHub Pages

**Đã làm**

- `catalog/roadmap.yaml`: chuyển lộ trình theo tuần từ Markdown sang dữ liệu — 4 giai đoạn (A Nền tảng, B GenAI,
  C Chuyên sâu, **D Nâng cao · Production** mới), 25 bước (việc cần làm, sản phẩm nộp, kỹ năng + mức mục tiêu),
  5 hướng chuyên sâu, thanh ngang chữ T, thói quen xuyên suốt. Thêm câu hỏi nhận diện bài toán vào `problems.yaml`.
- Bộ kiểm tra lộ trình: kỹ năng tiên quyết phải xuất hiện ở bước trước, mức mục tiêu không giảm, lộ trình phủ đủ
  65/65 kỹ năng, chặn trường lạ (lỗi YAML do dấu phẩy chưa đặt trong ngoặc kép — đã gặp và sửa trong lúc làm).
- Sinh `docs/02-skill-map/generated/lo-trinh.md`; thẻ kỹ năng có thêm dòng "Trong lộ trình"; `04-lo-trinh-hoc.md` rút
  gọn còn nguyên tắc + liên kết.
- `web/` + `src/aiarch/site.py`: trang một trang (HTML/CSS/JS thuần) gồm Tổng quan, Lộ trình, Nhóm bài toán (quiz 30 giây,
  lộ trình 3 chặng mỗi nhóm), Kỹ năng (tìm không dấu, lọc), Ma trận + bản đồ nhiệt, Tổ hợp, Tiến độ (lưu trình duyệt,
  xuất/nhập JSON); sáng/tối; vừa màn hình điện thoại.
- `.github/workflows/pages.yml` triển khai lên Pages khi `main` đổi; CI thêm job kiểm thử trang bằng Chromium thật
  (`scripts/smoke_site.py`, 23 trang × 2 cỡ màn hình); `make site`, `make site-serve`, `make site-test`.

**Quyết định**

- Không dùng framework/bundler: trang tĩnh thuần, dữ liệu nhúng vào `index.html` nên mở file trực tiếp cũng chạy.
- Tiến độ chỉ lưu trong trình duyệt người xem (không backend); chuyển máy bằng file JSON.
- Giai đoạn D là đề xuất thêm để có mức Nâng cao (lộ trình gốc dừng ở tháng 6) — cần chủ dự án duyệt.

**Còn mở**

- Bật Pages trong Settings (Source: GitHub Actions) — chỉ chủ repo làm được.
- Review nội dung từng bước trong `catalog/roadmap.yaml`.

## 2026-10-05 · CMB-09 Data Agent OS — thiết kế v2 cho POC tối giản ([#4](https://github.com/superken-python/ai-architecture/pull/4))

**Đã làm**

- Vẽ lại kiến trúc v2 (`docs/assets/kien-truc-v2.svg`) và thêm sequence diagram cho **khởi tạo agent object**, **một lần chạy**,
  biến thể OpenAI Agents SDK.
- Đánh giá tái sử dụng 10 skill của Data plugin (`anthropics/knowledge-work-plugins`, thư mục `data`, commit `8444efc`,
  Apache-2.0): chạy validator của Agno (9/10 lỗi vì `argument-hint`/`user-invocable`), nạp được cả 10 bằng `validate=False`.
- Viết lại chi tiết kỹ thuật thành tài liệu POC, ADR-001 v2, checklist POC (P0 → POC-1/2/3). Xóa tài liệu chỉ dùng cho v1.

**Quyết định (đề xuất, chờ duyệt)**

- Bỏ khỏi POC: review/learning, auth/RBAC, Data Gateway, router, workflow báo cáo. Platform DB là PostgreSQL.
- Không còn pack `core` tự viết: skill chung lấy từ Data plugin (6 skill chỉ-hướng-dẫn), nạp **trước** skill domain.
- Domain pack = `pack.yaml` + một skill sinh bằng `data-context-extractor` + `evals.yaml`.
- POC-1/2 chỉ dùng Agno; OpenAI Agents SDK là POC-3 tùy chọn (một agent, skill qua tool `load_skill`, không sandbox).

**Còn mở**

- Bản Data plugin 20 skill mà chủ dự án đang cài không có trong repo công khai — cần file thật để kiểm tra lại (P0-02).

## 2026-10-05 · Thiết kế dự án nghiên cứu CMB-09 Data Agent OS ([#3](https://github.com/superken-python/ai-architecture/pull/3), đã merge)

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
