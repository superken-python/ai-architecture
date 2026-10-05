# 03 · Chi tiết kỹ thuật POC

Đủ để bắt đầu code theo [Checklist POC](../CHECKLIST.md). Import và API dưới đây đã được kiểm tra trên đúng phiên bản (đọc mã
nguồn, import thử; DBHub chạy thử); các đoạn code là **phác thảo**, chưa chạy end-to-end.

## 1. Phiên bản

| Thành phần | Phiên bản | Ghi chú |
|---|---|---|
| `agno[os,mcp,postgres,openai]` | 3.1.1 | AgentOS, Agent, Skills, MCPTools, PostgresDb, tracing |
| `openai-agents` | 0.23.1 | chỉ cần ở POC-3 |
| DBHub | 1.4.0 (`npx @bytebase/dbhub@1.4.0`) | Node ≥ 22.5; đã chạy thử với 2 nguồn |
| PostgreSQL | 17 (docker) | một container, ba database |
| Model | `gpt-5.4-mini` (mặc định của Agno 3.1) | đổi trong `pack.yaml` |

## 2. Cấu trúc thư mục POC

```
projects/cmb-09-data-agent-os/
├── app.py                         # ~60 dòng: packs → agents → AgentOS
├── pyproject.toml · uv.lock       # môi trường riêng của dự án
├── docker-compose.yml             # chỉ PostgreSQL
├── dbhub.toml                     # nguồn timesheet, finance; execute_sql readonly
├── .env.example                   # OPENAI_API_KEY, DATABASE_URL, DBHUB_URL, TIMESHEET_DSN, FINANCE_DSN
├── db/init/                       # chạy tự động lần đầu container khởi động
│   ├── 01-databases.sql           # tạo DB timesheet, finance + user dbhub_ro
│   ├── 02-timesheet.sql           # bảng + dữ liệu mẫu + GRANT SELECT
│   └── 03-finance.sql
├── vendor/data-plugin/            # bản sao thư mục data của anthropics/knowledge-work-plugins
│   ├── LICENSE · NOTICE.md · CONNECTORS.md
│   └── skills/{analyze,write-query,sql-queries,explore-data,validate-data,statistical-analysis}/SKILL.md
├── packs/
│   ├── timesheet/
│   │   ├── pack.yaml
│   │   ├── skills/timesheet-data-analyst/{SKILL.md, references/}
│   │   └── evals.yaml
│   └── finance/ …
└── scripts/eval.py                # POC-2
```

## 3. `pack.yaml`

```yaml
id: timesheet
name: Timesheet
description: Giờ công, tỷ lệ billable, utilization, tuân thủ nộp timesheet.
dbhub_source: timesheet              # → tool execute_sql_timesheet, search_objects_timesheet
domain_skill: timesheet-data-analyst # tên skill trong packs/timesheet/skills/
data_skills:                         # skill dùng lại từ Data plugin, nạp TRƯỚC skill domain
  - analyze
  - write-query
  - sql-queries
  - explore-data
  - validate-data
  - statistical-analysis
model: gpt-5.4-mini
```

## 4. Skill domain (sinh bằng `data-context-extractor`, rồi chỉnh tay)

```markdown
---
name: timesheet-data-analyst
description: Ngữ cảnh dữ liệu timesheet của công ty (PostgreSQL) — thực thể, thuật ngữ, bộ lọc chuẩn và metric giờ công,
  billable, utilization. Dùng cho mọi câu hỏi về giờ công, dự án, billable, tuân thủ nộp timesheet.
---
# Timesheet — ngữ cảnh dữ liệu

## SQL dialect: PostgreSQL

## Phân biệt thực thể
"Giờ làm" có thể là giờ đã khai (mọi trạng thái) hoặc giờ đã duyệt (status = 'approved'). Mặc định: giờ đã duyệt.

## Bộ lọc chuẩn
- Tính giờ làm việc: `status = 'approved' AND activity <> 'leave'`
- Tuân thủ nộp timesheet: `status IN ('submitted', 'approved')`

## Metric chính
### Tỷ lệ billable
- Định nghĩa: giờ billable đã duyệt / tổng giờ làm việc đã duyệt (không tính nghỉ phép)
- Công thức: SUM(CASE WHEN p.billable THEN t.hours END) / SUM(t.hours), áp bộ lọc chuẩn
- Bảng: timesheet_entries t JOIN projects p ON p.project_id = t.project_id

## Tài liệu tham khảo
- references/tables.md — mô tả bảng, cột, quan hệ
- references/metrics.md — toàn bộ metric và lưu ý
```

## 5. `app.py` — khởi tạo agent object

```python
"""POC: mỗi domain pack → một Agno Agent; skill của Data plugin nạp trước skill domain."""

import os
from pathlib import Path

import yaml
from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.models.openai import OpenAIResponses
from agno.os import AgentOS
from agno.skills import LocalSkills, Skills
from agno.tools.mcp import MCPTools

ROOT = Path(__file__).parent
DATA_PLUGIN_SKILLS = ROOT / "vendor/data-plugin/skills"
db = PostgresDb(db_url=os.environ["DATABASE_URL"])  # postgresql+psycopg://dagent:...@localhost:5432/agentos

INSTRUCTIONS = """\
Bạn là data agent cho miền {name}. Trả lời bằng tiếng Việt.
- "data warehouse" trong các skill = tool execute_sql_{src} và search_objects_{src} của DBHub (PostgreSQL, chỉ đọc).
- Trước khi viết SQL, đọc skill {domain_skill}: thuật ngữ, bộ lọc chuẩn, định nghĩa metric của miền này.
- Câu hỏi số liệu: làm theo skill analyze; viết SQL theo sql-queries; kiểm tra kết quả theo validate-data.
- Chưa có công cụ vẽ biểu đồ hay ghi file: bỏ bước trực quan hóa, trình bày bằng bảng.
- Mọi con số phải lấy từ kết quả truy vấn; luôn kèm câu SQL đã chạy.
"""


def build_agent(pack_dir: Path) -> Agent:
    pack = yaml.safe_load((pack_dir / "pack.yaml").read_text(encoding="utf-8"))
    src = pack["dbhub_source"]
    loaders = [LocalSkills(str(DATA_PLUGIN_SKILLS / name), validate=False) for name in pack["data_skills"]]  # ①
    loaders.append(LocalSkills(str(pack_dir / "skills")))  # ② domain: nạp sau, trùng tên thì ghi đè
    return Agent(
        id=f"{pack['id']}-agent",
        name=pack["name"],
        model=OpenAIResponses(id=pack.get("model", "gpt-5.4-mini")),
        instructions=INSTRUCTIONS.format(name=pack["name"], src=src, domain_skill=pack["domain_skill"]),
        skills=Skills(loaders=loaders),
        tools=[
            MCPTools(
                transport="streamable-http",
                url=os.environ["DBHUB_URL"],  # http://localhost:8080/mcp
                include_tools=[f"execute_sql_{src}", f"search_objects_{src}"],
            )
        ],
        db=db,
        add_history_to_context=True,
        num_history_runs=3,
        markdown=True,
    )


agents = [build_agent(p.parent) for p in sorted(ROOT.glob("packs/*/pack.yaml"))]
agent_os = AgentOS(id="data-agent-os", agents=agents, db=db, tracing=True)
app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="app:app", reload=True)
```

Những gì Agno tự làm, không cần code thêm:

- Chèn danh mục skill (tên + mô tả, theo thứ tự nạp) vào system prompt và thêm 3 tool `get_skill_instructions`,
  `get_skill_reference`, `get_skill_script`.
- AgentOS kết nối mọi `MCPTools` của các agent lúc khởi động và đóng khi tắt (lifespan).
- `tracing=True`: OpenTelemetry → bảng `agno.agno_traces`, `agno.agno_spans`; session/run vào `agno.agno_sessions`, … trong DB
  `agentos`. Xem trên AgentOS UI (mục Traces) hoặc truy vấn trực tiếp.

## 6. DBHub và PostgreSQL

```toml
# dbhub.toml — ${VAR} được DBHub thay bằng biến môi trường
[[sources]]
id = "timesheet"
dsn = "${TIMESHEET_DSN}"   # postgres://dbhub_ro:...@localhost:5432/timesheet?sslmode=disable

[[sources]]
id = "finance"
dsn = "${FINANCE_DSN}"

[[tools]]
name = "execute_sql"
source = "timesheet"
readonly = true
max_rows = 500

[[tools]]
name = "search_objects"
source = "timesheet"

# … lặp lại hai khối [[tools]] cho source "finance"
```

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:17
    environment:
      POSTGRES_USER: dagent
      POSTGRES_PASSWORD: dagent
      POSTGRES_DB: agentos
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./db/init:/docker-entrypoint-initdb.d:ro
volumes:
  pgdata:
```

Dữ liệu mẫu (giả lập, vài chục dòng mỗi bảng) cố ý có "bẫy" để kiểm tra agent có đọc skill domain không:

| DB | Bảng | Bẫy |
|---|---|---|
| `timesheet` | `employees`, `projects`, `timesheet_entries` | dòng `draft`/`rejected` không được tính; `activity = 'leave'` không phải giờ làm việc; dự án nội bộ không billable |
| `finance` | `accounts`, `gl_entries`, `invoices` | doanh thu ghi **âm** trong sổ cái; bút toán đảo (`is_reversed`) phải loại; hóa đơn `void` |

User `dbhub_ro` chỉ có `CONNECT` + `SELECT` trên hai DB dữ liệu, không có quyền gì trên DB `agentos`.

## 7. Eval đơn giản (POC-2)

```yaml
# packs/timesheet/evals.yaml
- id: ts-01
  question: Tổng số giờ làm việc đã duyệt của tháng 8/2026 là bao nhiêu?
  expected_sql: >-
    SELECT SUM(hours) FROM timesheet_entries
    WHERE status = 'approved' AND activity <> 'leave' AND work_date >= '2026-08-01' AND work_date < '2026-09-01'
```

`scripts/eval.py`: với mỗi câu → `POST /agents/{id}/runs` (không stream, session mới) → lấy kết quả của lần gọi
`execute_sql_*` cuối cùng trong `tools` của run → chạy `expected_sql` bằng user `dbhub_ro` → so hai tập kết quả (bỏ qua tên
cột và thứ tự dòng, làm tròn số) → in bảng đúng/sai, token, thời gian. So **kết quả**, không so chuỗi SQL.

## 8. POC-3: agent OpenAI Agents SDK

Phác thảo, chi tiết lý do ở [ADR-001](04-adr-openai-agents-sdk.md):

```python
from agents import Agent as OAAgent
from agents import Runner, function_tool, set_trace_processors
from agents.mcp import MCPServerStreamableHttp, create_static_tool_filter
from agno.agents.base import BaseExternalAgent

# PgTraceProcessor tự viết: ghi trace OpenAI SDK vào agno_traces/agno_spans, không gửi lên OpenAI
set_trace_processors([PgTraceProcessor(db)])

skill_files = resolve_skill_files(pack)  # cùng thứ tự: ① Data plugin → ② domain


@function_tool
def load_skill(name: str) -> str:
    """Đọc nội dung đầy đủ của một skill trong danh mục."""
    return skill_files[name].read_text(encoding="utf-8")


dbhub = MCPServerStreamableHttp(
    params={"url": os.environ["DBHUB_URL"]},
    tool_filter=create_static_tool_filter(allowed_tool_names=[f"execute_sql_{src}", f"search_objects_{src}"]),
)
oa_agent = OAAgent(
    name="finance-openai",
    instructions=INSTRUCTIONS.format(...) + skill_index(skill_files),  # tên + mô tả, đúng thứ tự
    tools=[load_skill],
    mcp_servers=[dbhub],
)
# OpenAIAgentsAdapter(BaseExternalAgent): _arun_adapter gọi Runner.run(oa_agent, lịch sử + input);
# dbhub.connect() / cleanup() trong lifespan truyền vào AgentOS(lifespan=...).
```

## 9. Cấu hình

| Biến | Ví dụ | Dùng ở |
|---|---|---|
| `OPENAI_API_KEY` | — | model |
| `DATABASE_URL` | `postgresql+psycopg://dagent:dagent@localhost:5432/agentos` | `PostgresDb` |
| `DBHUB_URL` | `http://localhost:8080/mcp` | `MCPTools` |
| `TIMESHEET_DSN`, `FINANCE_DSN` | `postgres://dbhub_ro:...@localhost:5432/timesheet?sslmode=disable` | `dbhub.toml` |

## 10. Giới hạn đã biết của POC

- Không có phân quyền theo người dùng: ai vào được AgentOS là hỏi được mọi pack. Chỉ chạy trong máy dev/mạng nội bộ.
- Không chặn cột nhạy cảm ở tầng tool; dữ liệu mẫu không chứa PII thật.
- Agent có thể gửi nhiều câu SELECT nối bằng `;` (DBHub cho phép); readonly vẫn chặn mọi lệnh ghi.
- Trace có thể chứa nội dung câu hỏi và kết quả truy vấn — chấp nhận được với dữ liệu giả lập.
