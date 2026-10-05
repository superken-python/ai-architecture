# 01 · Kiến trúc v2 — POC tối giản

Bản v2 thay cho v1 theo góp ý của chủ dự án: **đơn giản hóa để làm POC**, chưa làm review/learning và auth, platform DB
là **PostgreSQL**, và **domain pack không phải "core = data agent"**: kỹ năng chung lấy lại từ các skill có sẵn của
**Data plugin** (Anthropic) và được nạp **trước** skill của domain khi khởi tạo agent object.

![Kiến trúc v2](assets/kien-truc-v2.svg)

## 1. Nguyên tắc cho POC

1. **Ít thành phần nhất có thể:** một tiến trình Python (AgentOS), một tiến trình DBHub, một container PostgreSQL.
2. **Không viết lại thứ đã có:** kỹ năng phân tích dữ liệu chung dùng lại từ Data plugin; AgentOS lo session, UI,
   tracing; DBHub lo kết nối và chế độ chỉ đọc.
3. **Domain pack = dữ liệu, không phải code:** thêm một domain là thêm một thư mục (`pack.yaml` + một skill); code khởi
   tạo agent dùng chung cho mọi pack.
4. **Mỗi bước POC chạy được và đo được** trước khi thêm bước sau (xem [Checklist POC](../CHECKLIST.md)).

## 2. Thành phần

| Thành phần | Vai trò trong POC | Công nghệ |
|---|---|---|
| Client | Chọn agent, chat, xem trace; script chạy eval | AgentOS UI, REST/SSE, script Python |
| AgentOS | Chứa danh sách agent, API chạy agent, session, tracing | `agno[os]` 3.1 (FastAPI) |
| Agent object | Một agent cho mỗi domain pack: model + instructions ngắn + **skills** + **tools DBHub** + db | `agno.agent.Agent`; tùy chọn `agents.Agent` (OpenAI Agents SDK) qua adapter |
| Skill dùng chung | Workflow phân tích, viết SQL, khám phá và kiểm tra dữ liệu | `vendor/data-plugin/` — bản sao thư mục `data` của Data plugin (Apache-2.0) |
| Domain pack | Thuật ngữ, bộ lọc chuẩn, metric, mô tả bảng của một miền; nguồn dữ liệu DBHub; câu hỏi eval | `packs/<domain>/` |
| DBHub | Cổng MCP tới dữ liệu: `execute_sql_<source>` (readonly), `search_objects_<source>` | `@bytebase/dbhub` 1.4 |
| PostgreSQL | DB `agentos` (sessions, runs, traces, spans) + DB dữ liệu mẫu `timesheet`, `finance` | PostgreSQL 17 (docker) |

## 3. Khởi tạo agent object (init process)

Khi `app.py` khởi động, mỗi domain pack tạo ra **một agent object**. Kỹ năng được nạp theo thứ tự cố định:
**① skill chung từ Data plugin → ② skill của domain**. Agno giữ thứ tự này trong danh mục skill đưa vào prompt; nếu hai skill
trùng tên, loader sau (domain) ghi đè loader trước.

```mermaid
sequenceDiagram
    autonumber
    participant Dev as Lập trình viên
    participant App as app.py
    participant FS as Thư mục repo<br/>vendor/data-plugin, packs/*
    participant SK as agno Skills
    participant OS as AgentOS
    participant PG as PostgreSQL (agentos)
    participant HUB as DBHub (MCP)
    Dev->>App: uv run python app.py
    App->>App: đọc .env (OPENAI_API_KEY, DATABASE_URL, DBHUB_URL)
    App->>PG: PostgresDb(db_url)
    App->>FS: đọc packs/*/pack.yaml
    loop mỗi pack (timesheet, finance)
        App->>SK: ① LocalSkills("vendor/data-plugin/skills/<tên>", validate=False) cho từng tên trong data_skills
        App->>SK: ② LocalSkills("packs/<id>/skills")
        SK->>FS: đọc frontmatter (name, description) + nội dung SKILL.md, liệt kê references/
        Note over SK: trùng tên → skill của domain ghi đè (có cảnh báo)
        App->>App: MCPTools(transport="streamable-http", url=DBHUB_URL,<br/>include_tools=[execute_sql_<src>, search_objects_<src>])
        App->>App: Agent(id, model, instructions, skills, tools, db)
    end
    App->>OS: AgentOS(agents=[...], db=PostgresDb, tracing=True)
    OS->>PG: tạo bảng sessions, runs, traces, spans nếu chưa có
    OS->>HUB: lifespan: kết nối MCPTools, list_tools
    HUB-->>OS: execute_sql_timesheet, search_objects_timesheet, ...
    OS-->>Dev: http://localhost:7777 sẵn sàng (kết nối từ AgentOS UI)
```

Ghi chú:

- `validate=False` là bắt buộc với skill của Data plugin: frontmatter của chúng có `argument-hint` / `user-invocable`
  (trường riêng của Claude) mà validator của Agno không chấp nhận — chi tiết ở
  [02 · Tái sử dụng skill của Data plugin](02-tai-su-dung-skill-data-plugin.md).
- Mỗi pack chọn skill chung nào cần qua `data_skills` trong `pack.yaml` (mặc định 6 skill chỉ-hướng-dẫn).
- Agent **không** nạp `data-context-extractor`; skill đó chỉ dùng offline để sinh skill của domain.

## 4. Một lần chạy (run process)

```mermaid
sequenceDiagram
    autonumber
    actor U as Người dùng
    participant OS as AgentOS
    participant A as timesheet-agent (Agno)
    participant LLM as Model
    participant HUB as DBHub
    participant DATA as PostgreSQL (timesheet)
    participant PG as PostgreSQL (agentos)
    U->>OS: POST /agents/timesheet-agent/runs {message, session_id}
    OS->>A: arun(message, session_id, user_id)
    A->>PG: đọc lịch sử session
    A->>LLM: system = instructions + danh mục skill (① Data → ② domain) + định nghĩa tool
    LLM-->>A: get_skill_instructions("timesheet-data-analyst")
    A-->>LLM: SKILL.md của domain (thuật ngữ, bộ lọc chuẩn, metric)
    LLM-->>A: get_skill_instructions("analyze")
    A-->>LLM: workflow: hiểu câu hỏi → lấy dữ liệu → kiểm tra → trình bày
    opt chưa chắc tên bảng/cột
        LLM-->>A: get_skill_reference("timesheet-data-analyst", "tables.md") hoặc search_objects_timesheet
    end
    LLM-->>A: execute_sql_timesheet(sql)
    A->>HUB: MCP call_tool
    HUB->>DATA: SELECT (readonly, tối đa 500 dòng)
    DATA-->>HUB: rows
    HUB-->>A: {"success": true, "data": {"statements": [...]}}
    A-->>LLM: kết quả truy vấn
    Note over LLM: tự kiểm tra (bước 4 của analyze, validate-data),<br/>sai thì sửa SQL và chạy lại
    LLM-->>A: câu trả lời + SQL đã chạy
    A->>PG: lưu run + session
    A--)PG: spans agent / model / tool (tracing)
    OS-->>U: SSE stream
```

- Prompt ban đầu chỉ có **tên + mô tả** của skill; nội dung đầy đủ chỉ được tải khi model gọi `get_skill_instructions` —
  nhờ vậy nạp 6 skill chung không làm phình prompt.
- An toàn dữ liệu trong POC dựa vào DBHub `readonly = true` + `max_rows` + user PostgreSQL chỉ có quyền SELECT.

## 5. Biến thể OpenAI Agents SDK (POC-3, tùy chọn)

Dùng **cùng** `pack.yaml` và **cùng** thư mục skill. Khác biệt: OpenAI Agents SDK không có skill native ngoài sandbox, nên
danh mục skill được chèn vào instructions và nội dung skill đọc qua function tool `load_skill`; agent được đưa vào AgentOS
qua adapter `BaseExternalAgent`; trace ghi về cùng PostgreSQL. Lý do và phạm vi: [ADR-001](04-adr-openai-agents-sdk.md).

```mermaid
sequenceDiagram
    autonumber
    participant App as app.py
    participant TP as PgTraceProcessor
    participant AD as OpenAIAgentsAdapter
    participant OA as agents.Agent
    participant MS as MCPServerStreamableHttp
    participant OS as AgentOS
    participant PG as PostgreSQL (agentos)
    Note over App,PG: Khởi tạo
    App->>TP: set_trace_processors([PgTraceProcessor(db)]) — không gửi trace lên OpenAI
    App->>App: đọc cùng pack.yaml + cùng thư mục skill (① Data → ② domain)
    App->>OA: Agent(instructions = nền + danh mục skill, tools=[load_skill], mcp_servers=[MS])
    App->>AD: OpenAIAgentsAdapter(id="finance-openai", agent=OA, db)
    App->>OS: AgentOS(agents=[..., AD], lifespan=kết nối MS)
    OS->>MS: connect() lúc khởi động
    Note over App,PG: Chạy
    OS->>AD: arun(message, session_id)
    AD->>PG: đọc lịch sử session
    AD->>OA: Runner.run(OA, lịch sử + message)
    OA->>OA: load_skill("finance-data-analyst"), load_skill("analyze")
    OA->>MS: execute_sql_finance(sql)
    OA-->>AD: final_output
    AD->>PG: lưu run + session
    TP->>PG: upsert_trace + create_spans (cùng bảng với Agno)
```

## 6. Triển khai POC

```mermaid
flowchart LR
    ui[AgentOS UI / curl / script eval] --> app["app.py — AgentOS<br/>uv run · cổng 7777"]
    app -- "MCP streamable-http" --> hub["DBHub 1.4<br/>npx · cổng 8080"]
    app -- "sessions, runs, traces" --> pg[("PostgreSQL 17<br/>docker · cổng 5432")]
    hub -- "user chỉ SELECT" --> pg
    app <-- HTTPS --> llm[(OpenAI API)]
```

`docker compose up -d` (PostgreSQL), `npx @bytebase/dbhub@1.4.0 --transport http --port 8080 --config dbhub.toml`, rồi
`uv run python app.py`. App và DBHub chạy trực tiếp (không container) để sửa và chạy lại nhanh; DBHub cần Node ≥ 22.5.

## 7. So với diagram v0 và thiết kế v1

| Hạng mục | v0 (diagram gốc) | v1 (đã bỏ) | v2 (POC) |
|---|---|---|---|
| Kỹ năng chung | không nêu | pack `core` tự viết | **dùng lại skill của Data plugin**, nạp trước |
| Domain pack | 6 loại asset | 10 loại file YAML/Markdown | `pack.yaml` + một skill sinh theo template `data-context-extractor` + `evals.yaml` |
| Agent Registry | có | `agents.yaml` + version | danh sách agent của AgentOS, sinh từ `packs/*` |
| Orchestrator | có | router cascade + workflow báo cáo | người dùng chọn agent trên UI; để sau POC |
| Auth & RBAC | có | JWT + RBAC dữ liệu | **bỏ** trong POC |
| Data Gateway | không | kiểm SQL, PII, evidence | **bỏ**; dựa vào DBHub readonly + user chỉ SELECT |
| Review & learning | không | có | **bỏ** trong POC |
| Observability | có | trace 2 runtime + evidence + eval gate | `tracing=True` → PostgreSQL; eval bằng script đơn giản |
| Platform DB | không nêu | Postgres/SQLite | **PostgreSQL** |
| OpenAI Agents SDK | ngang hàng Agno | runtime phụ + triage/handoff | runtime phụ, **một agent**, POC-3 tùy chọn |
| Report templates, dashboard | có | Jinja + workflow | để sau POC (cần tool ghi file) |
