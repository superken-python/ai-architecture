# Lab 01 — Agno và AgentOS: tự code từng phần

Trước khi bắt đầu: hoàn thành [Lab 00](agent_framework_learning_from_scratch.md) đến checkpoint MCP. Đây là bài riêng cho engine Agno; dùng chung `service.py`, `rules.py`, `reporting.py`, `mcp_client.py` và dữ liệu, không kéo thả bản sao sang project khác.

Bài gồm **baseline** `agno_cli.py` (mục 4) và **16 phần**, mỗi phần một module `agno_lab/pNN_*.py` kèm test. Mỗi phần có: cơ chế bên trong (đo trên Agno 3.1.3, không đoán), code hoàn chỉnh, giải thích, lệnh chạy, checkpoint và bài tập. Đi hết 16 phần là bạn đã tự viết đủ các tính năng chính của Agno: agent, tool, structured output, streaming, session, memory, knowledge, HITL, guardrail, MCP client, team, workflow, AgentOS, AG-UI, A2A, MCP server và eval.

**Project tham chiếu đã kiểm chứng:** [`labs/llm-05-trung-cap-agno-agentos/`](../../labs/llm-05-trung-cap-agno-agentos/README.md) chứa đúng code của tài liệu này (test `test_doc_sync.py` bảo đảm hai bên khớp) và 74 test chạy với model giả lập, không cần API key. Ngày kiểm chứng: **17/10/2026**, Python 3.12, `agno==3.1.3`, `mcp==2.3.0`.

**Cách học:** như Lab 00, tự gõ từng module, chạy checkpoint rồi mới sang phần sau. Code ghi `File:` là module hoàn chỉnh; đọc lời giải sau khi tự thử 20–30 phút.

## 1. Mục tiêu và ranh giới

Sau bài này, bạn cần giải thích được model, tool, session history, memory, knowledge và revision báo cáo khác nhau như thế nào; chỗ nào model quyết định, chỗ nào code quyết định; và làm sao đưa agent thành dịch vụ có kiểm soát. Baseline chạy CLI: lấy evidence bắt buộc qua MCP, cho Agno viết narrative có schema, render KPI bằng code và lưu v1/v2.

Agno session database lưu lịch sử run; nó không tự tạo hệ quản lý phiên bản artifact hoặc bảo đảm resume giữa một tool đang chạy dở. Bài này lưu revision riêng bằng JSON để bạn nhìn rõ hai trách nhiệm đó. Không suy ra bảo đảm crash recovery từ việc chat history còn sau restart.

API tham khảo dùng `agno.db.sqlite.SqliteDb`, `db=`, `add_history_to_context` và `output_schema`; thay cho nhóm API `agno.storage.sqlite.SqliteStorage` trong bản cũ. Xem [Agno SQLite](https://docs.agno.com/database/providers/sqlite/usage/sqlite-for-agent) và [structured output](https://docs.agno.com/input-output/structured-output/agent). Chạy theo version đã lock; dùng `⌘B` kiểm tra signature nếu môi trường khác.

## 2. Lộ trình 16 phần

| Phần | Module | Tính năng Agno | Câu hỏi thực tế được trả lời | Tài liệu |
| --- | --- | --- | --- | --- |
| 0 | `settings.py`, `mock_llm.py` | Cấu hình model/DB, model giả lập | Học không cần API key thế nào? | [mục 3](#3-phần-0--chuẩn-bị-project) |
| 1 | `p01_agent.py` | Agent, tool hàm, `Toolkit`, `RunOutput` | Agent gọi tool thế nào, model thấy tool ra sao? | [01a](agno/01a-agent-tool-output-streaming.md) |
| 2 | `p02_structured.py` | `input_schema`, `output_schema`, JSON mode | Sao cho output luôn đúng schema, số không qua LLM? | [01a](agno/01a-agent-tool-output-streaming.md) |
| 3 | `p03_streaming.py` | `stream`, `stream_events`, `arun` | Hiện chữ và tiến trình tool theo thời gian thực? | [01a](agno/01a-agent-tool-output-streaming.md) |
| 4 | `p04_session.py` | Session, history, `session_state`, tóm tắt | Nhớ cuộc trò chuyện qua nhiều lượt, qua restart? | [01b](agno/01b-session-memory-knowledge.md) |
| 5 | `p05_memory.py` | `MemoryManager`, memory tự động/agentic | Nhớ người dùng qua mọi session, nhớ gì? | [01b](agno/01b-session-memory-knowledge.md) |
| 6 | `p06_knowledge.py` | `Knowledge`, LanceDB, embedder, filter | RAG cập nhật được, không nhúng lại tất cả? | [01b](agno/01b-session-memory-knowledge.md) |
| 7 | `p07_tools_hitl.py` | Xác nhận, hỏi thêm, tool ở client, hook, cache | Người duyệt trước khi agent ghi dữ liệu? | [01c](agno/01c-tool-hitl-guardrail.md) |
| 8 | `p08_guardrails.py` | Pre/post hook, guardrail, model dự phòng | Chặn input/output xấu, sống sót khi provider lỗi? | [01c](agno/01c-tool-hitl-guardrail.md) |
| 9 | `p09_mcp.py` | `MCPTools` (stdio, HTTP), tự bọc client | Agent tự gọi tool ở process khác? | [01d](agno/01d-mcp-team-workflow.md) |
| 10 | `p10_team.py` | Team: coordinate, route, broadcast | Nhiều agent chuyên trách phối hợp? | [01d](agno/01d-mcp-team-workflow.md) |
| 11 | `p11_workflow.py` | Workflow: Parallel, Loop, Router, Condition, HumanReview | Quy trình cố định có vòng sửa và người duyệt? | [01d](agno/01d-mcp-team-workflow.md) |
| 12 | `p12_os.py`, `p12_client.py` | AgentOS: REST, security key, tracing | Đưa agent thành dịch vụ, đọc trace? | [01e](agno/01e-agentos-agui-a2a-mcp-eval.md) |
| 13 | `p13_agui.py` | AG-UI: sự kiện, state, frontend tool | Nối agent với giao diện web/add-in? | [01e](agno/01e-agentos-agui-a2a-mcp-eval.md) |
| 14 | `p14_a2a.py` | A2A: Agent Card, `A2AClient`, `RemoteAgent` | Gọi agent ở dịch vụ khác, đưa vào team? | [01e](agno/01e-agentos-agui-a2a-mcp-eval.md) |
| 15 | `p15_mcp_server.py` | AgentOS làm MCP server, `MCPConfig` | Cho Claude Code/Cursor dùng agent của bạn? | [01e](agno/01e-agentos-agui-a2a-mcp-eval.md) |
| 16 | `p16_evals.py` | Reliability, Accuracy, Judge, Performance, suite | Biết agent đủ tốt trước khi đổi prompt/model? | [01e](agno/01e-agentos-agui-a2a-mcp-eval.md) |

**Thứ tự gợi ý** (theo ưu tiên harness/workflow trước, giao diện sau): 0 → 1–8 → 11 → 9–10 → 12 → 16 → 13–15. Phần 13–15 cần khi nối với giao diện hay hệ thống khác.

## 3. Phần 0 — Chuẩn bị project

### 3.1 Cài thư viện

Trong project thực hành đã tạo ở Lab 00, chép file pin version dưới đây vào gốc project rồi cài:

**File: `requirements.txt`**

```text
# Lab 01 — Agno 3.1.3 + AgentOS. Đã kiểm chứng ngày 17/10/2026 với Python 3.12: 74 test qua (model giả lập).
# Extra của agno: os = AgentOS (FastAPI, tracing), mcp = MCPTools + MCP server, agui/a2a = hai giao thức,
# sqlite/lancedb = lưu trữ và vector DB, openai = model OpenAI và mọi endpoint tương thích (Ollama, vLLM, mock).
agno[os,mcp,sqlite,lancedb,openai,agui,a2a]==3.1.3
mcp==2.3.0  # agno[mcp] cần mcp>=2.1,<3 — Lab 00 dùng mcp 1.x, xem Bước 0 trong guide_01_agno.md
fastmcp==4.1.0
ag-ui-protocol==1.0.0
a2a-sdk==0.3.26
openai==3.33.0
fastapi==0.143.3
uvicorn==0.54.0
lancedb==0.40.0
openpyxl==3.1.5  # Lab 00: đọc/ghi Excel quy ước KPI
python-dotenv==1.2.4
httpx==0.28.1
pytest==9.1.1
```

```bash
uv add -r requirements.txt      # cập nhật pyproject.toml + uv.lock; mcp 1.x của Lab 00 được nâng lên 2.3.0
uv run python setup_assets.py
```

Cài xong giữ `uv.lock`. Extra `sqlite` của Agno kéo theo `sqlalchemy[asyncio]` (có `greenlet`), thay cho lệnh `uv add 'sqlalchemy[asyncio]'` của bản cũ. `lancedb` (Phần 6) kéo theo `pyarrow`, khoảng 340 MB; bỏ extra `lancedb` nếu chưa học Phần 6.

**PyCharm:** `⌥F12` mở Terminal, `⌘1` mở Project, `⌘⇧A` → New để tạo file. Đánh dấu thư mục `tests` là Test Sources Root (chuột phải → Mark Directory as) để chạy test bằng nút ▶ cạnh tên hàm.

### 3.2 Bước 0 — nâng MCP lên 2.x

Lab 00 cố ý dùng SDK `mcp` 1.x và dặn "không nâng lên v2 rồi giữ nguyên imports". Lab 01 **phải** nâng: `agno[mcp]` của Agno 3.1.3 cần `mcp>=2.1,<3` và `fastmcp>=4,<5`. Đã đo: với mcp 1.30, `from agno.tools.mcp import MCPTools` lỗi ngay `ImportError: cannot import name 'MCPError'`. Lệnh `uv add -r requirements.txt` ở trên đã nâng `mcp`; giờ sửa hai file của Lab 00 cho đúng API 2.x.

**`mcp_client.py`: sửa đúng một dòng.** mcp 2.x đổi `isError` thành `is_error`:

```diff
-                if response.isError:
+                if response.is_error:  # mcp 2.x: isError (v1) đổi thành is_error
```

**`mcp_db_server.py`: ba thay đổi.** `FastMCP` đổi tên thành `MCPServer` (gói `mcp.server.mcpserver`); lỗi đã lường trước phải là `ToolError`, vì mcp 2.x giấu chi tiết mọi exception lạ thành `Error executing tool get_metrics`; thêm tuỳ chọn `--http` để Phần 9 chạy server qua streamable-http.

**File: `mcp_db_server.py`**

```python
import argparse

from mcp.server.mcpserver import MCPServer  # mcp 2.x: FastMCP (v1) đổi tên thành MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from service import read_metrics

mcp = MCPServer("enterprise-report-lab")


@mcp.resource("schema://enterprise/metrics")
def schema() -> str:
    return (
        "department_metrics(dept_code TEXT, quarter TEXT, revenue_usd INTEGER, "
        "cost_usd INTEGER, active_projects INTEGER); key=(dept_code, quarter). "
        "Money is USD, quarter format YYYY-Q1..Q4."
    )


@mcp.tool()
def get_metrics(quarter: str) -> list[dict]:
    """Đọc metrics của một quý có dạng YYYY-Q1..Q4, không nhận SQL tự do."""
    try:
        return read_metrics(quarter)
    except ValueError as exc:
        # mcp 2.x giấu chi tiết mọi exception lạ ("Error executing tool ..."); lỗi đã lường trước phải là
        # ToolError thì model mới đọc được hướng dẫn sửa.
        raise ToolError(str(exc)) from exc


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", type=int, help="chạy streamable-http ở cổng này thay vì stdio")
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="streamable-http", host="127.0.0.1", port=args.http)
    else:
        mcp.run(transport="stdio")
```

**Nghiệm thu Bước 0** (như Lab 00): `uv run python mcp_client.py` vẫn in 3 dòng Q2 và 3 dòng Q1. Thêm một điểm của mcp 2.x: tool trả `list[dict]` thì client nhận **mỗi dòng một `TextContent`**; vòng lặp gom block trong `mcp_client.py` của Lab 00 đã xử lý đúng trường hợp này.

### 3.3 Cấu trúc project

```text
enterprise-report-lab/                  ← project thực hành của bạn (tạo ở Lab 00)
├── .env                                ← không commit (mẫu: .env.example ở mục 3.4)
├── requirements.txt                    ← mục 3.1
├── setup_assets.py  service.py  rules.py  reporting.py     ← Lab 00, giữ nguyên
├── mcp_db_server.py  mcp_client.py     ← Lab 00, sửa theo Bước 0
├── agno_cli.py                         ← baseline Lab 01 (mục 4)
├── mock_llm.py                         ← model giả lập (mục 3.5)
├── conftest.py                         ← hạ tầng test (mục 3.6)
├── agno_lab/
│   ├── __init__.py                     ← file rỗng (có thể chỉ một dòng docstring)
│   ├── settings.py                     ← model(), db(), vector_dir()
│   └── p01_agent.py … p16_evals.py     ← 16 phần
├── tests/
│   ├── settings_paths.py  servers.py   ← tiện ích test
│   └── test_p01_agent.py … test_p16_evals.py
├── data/                               ← Lab 00 tạo: enterprise.db, internal_rules.xlsx, report_style_guide.txt
└── storage/                            ← báo cáo v1.md/v2.md, agno_lab.db, lancedb/
```

Chạy mọi lệnh ở **gốc project**: `uv run python -m agno_lab.p01_agent ...` (chạy dạng module để `import agno_lab...`, `import service` đều tìm thấy).

### 3.4 File `.env` và `agno_lab/settings.py`

**File: `.env.example`**

```text
# Sao chép thành .env rồi chọn MỘT trong ba cấu hình model. Không commit file .env.

# 1) OpenAI
# OPENAI_API_KEY=sk-...
# MODEL_ID=gpt-5-mini

# 2) Model local có API tương thích OpenAI (Ollama, vLLM, LM Studio...)
# OPENAI_BASE_URL=http://localhost:11434/v1
# OPENAI_API_KEY=local
# MODEL_ID=qwen3:8b

# 3) Model giả lập, không cần API key: chạy `uv run python mock_llm.py` ở một terminal khác
OPENAI_BASE_URL=http://127.0.0.1:8900/v1
OPENAI_API_KEY=mock
MODEL_ID=mock

# Phần 6 (knowledge): model embedding và số chiều. Đổi số chiều thì xoá storage/lancedb rồi index lại.
# EMBEDDING_ID=text-embedding-3-small
# EMBEDDING_DIMS=1536

# Không gửi telemetry của Agno
AGNO_TELEMETRY=false

# Phần 12: bật khoá cho AgentOS (mọi request cần header Authorization: Bearer <khoá>)
# OS_SECURITY_KEY=doi-khoa-nay
```

Ba cấu hình dùng chung một code nhờ `OpenAIChat(base_url=...)`: Agno gửi request chuẩn OpenAI Chat Completions tới `OPENAI_BASE_URL`, nên OpenAI, Ollama, vLLM hay `mock_llm` đều chạy được. `MODEL_ID` là tên model **không có prefix provider** (`gpt-5-mini`, không phải `openai:gpt-5-mini`).

**File: `agno_lab/settings.py`**

```python
"""Cấu hình chung cho các phần của Lab 01: đọc .env, tạo model và database.

Mọi phần đều gọi `model()` và `db()` ở đây, nên đổi model (OpenAI, Ollama, vLLM, mock_llm) chỉ cần sửa .env.
"""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path

from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIChat
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def model(**kwargs) -> OpenAIChat:
    """Model dùng chung.

    MODEL_ID: tên model, không có prefix provider (gpt-5-mini, qwen3:8b, ...).
    OPENAI_BASE_URL (tuỳ chọn): endpoint tương thích OpenAI — mock_llm, Ollama, vLLM, LM Studio.
    """
    return OpenAIChat(id=os.environ["MODEL_ID"], base_url=os.getenv("OPENAI_BASE_URL") or None, **kwargs)


def db() -> SqliteDb:
    """Một file SQLite cho mọi phần (session, memory, eval, trace...). AGNO_DB đổi đường dẫn — test dùng thư mục tạm.

    Trả CÙNG một object cho cùng một file: AgentOS gom db của mọi agent/team/workflow theo id, hai object khác
    nhau trỏ cùng file sẽ bị cảnh báo "multiple distinct databases share id".
    """
    return _db(os.getenv("AGNO_DB", str(ROOT / "storage" / "agno_lab.db")))


@cache
def _db(path: str) -> SqliteDb:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return SqliteDb(db_file=path)


def vector_dir() -> Path:
    """Thư mục LanceDB cho Phần 6 (knowledge). AGNO_VECTORS đổi đường dẫn."""
    path = Path(os.getenv("AGNO_VECTORS", str(ROOT / "storage" / "lancedb")))
    path.mkdir(parents=True, exist_ok=True)
    return path
```

Đọc code:

- Mọi phần gọi `model()` và `db()` ở đây, nên đổi model chỉ cần sửa `.env`.
- `db()` trả **cùng một object** cho cùng một file (`@cache`). Đã đo: mỗi agent một `SqliteDb` trỏ cùng file thì AgentOS (Phần 12) cảnh báo `multiple distinct databases share id`.
- `AGNO_DB`, `AGNO_VECTORS` cho phép test dùng thư mục tạm: không test nào thấy session của test khác.

### 3.5 Model giả lập `mock_llm.py`

Một server nhỏ giả API OpenAI (`/v1/chat/completions` thường và stream, `/v1/embeddings`, `/v1/models`). Dùng để:

- **Học offline**: `uv run python mock_llm.py`, đặt `.env` theo cấu hình 3. Ở chế độ tự động, request đòi JSON theo schema nhận JSON hợp lệ sinh từ schema, request thường nhận câu `(mock) Đã nhận: ...`; model giả **không bao giờ tự gọi tool**.
- **Test tất định**: test nạp kịch bản bằng `llm.script(call("get_quarter_kpis", quarter="2026-Q2"), say("..."), match="câu trong system prompt")`. Mỗi request lấy bước kế tiếp của **kênh** có `match` xuất hiện trong system prompt; nhờ vậy test của team, memory, tóm tắt session biết request nào của agent nào. Kênh hết bước thì trả HTTP 500 thay vì lấy nhầm bước của kênh khác.

Mock chứng minh code nối đúng: tool được gọi, kết quả quay lại model, schema được validate, sự kiện đúng thứ tự. Nó **không** chứng minh model thật chọn tool đúng; việc đó cần model thật và eval (Phần 16).

<details>
<summary>Code đầy đủ — <code>mock_llm.py</code> (chép nguyên file, không cần tự gõ)</summary>

**File: `mock_llm.py`**

```python
"""Server giả lập API OpenAI: Chat Completions (thường + stream) và Embeddings — học Agno không cần API key.

    uv run python mock_llm.py                 # http://127.0.0.1:8900/v1, chế độ tự động
    # .env: OPENAI_BASE_URL=http://127.0.0.1:8900/v1  OPENAI_API_KEY=mock  MODEL_ID=mock

Hai chế độ trả lời:
- Kịch bản (test): nạp trước các bước bằng `MockLLM.script(...)`; mỗi request lấy bước kế tiếp của kênh khớp.
- Tự động (học offline): không có kịch bản thì request đòi JSON theo schema nhận JSON hợp lệ sinh từ schema,
  request thường nhận một câu mẫu. Không bao giờ tự gọi tool.

Mock không thông minh: nó chứng minh code nối đúng (tool được gọi, kết quả quay lại model, schema được validate),
KHÔNG chứng minh model thật chọn tool đúng — việc đó cần model thật và bộ eval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import socket
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse


# ---------------------------------------------------------------- bước kịch bản
@dataclass
class Step:
    text: str | None = None
    tool_calls: list[dict] | None = None  # [{"name": ..., "arguments": {...}}]


def say(text: str) -> Step:
    """Model trả lời bằng chữ (hoặc JSON dạng chuỗi) và không gọi tool → vòng lặp agent dừng."""
    return Step(text=text)


def answer_json(value: Any) -> Step:
    """Model trả JSON — dùng khi agent có output_schema."""
    return Step(text=json.dumps(value, ensure_ascii=False))


def call(name: str, **arguments: Any) -> Step:
    """Model gọi một tool."""
    return Step(tool_calls=[{"name": name, "arguments": arguments}])


def calls(*pairs: tuple[str, dict]) -> Step:
    """Model gọi nhiều tool trong cùng một lượt (song song)."""
    return Step(tool_calls=[{"name": n, "arguments": a} for n, a in pairs])


@dataclass
class Channel:
    match: str  # chuỗi phải có trong system prompt; "" = kênh mặc định
    steps: list[Step] = field(default_factory=list)
    used: int = 0


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(part.get("text", "") for part in content if isinstance(part, dict))
    return ""


def system_text(body: dict) -> str:
    return "\n".join(
        _text(m.get("content")) for m in body.get("messages", []) if m.get("role") in ("system", "developer")
    )


# ---------------------------------------------------------------- JSON mẫu từ schema (chế độ tự động)
def example_from_schema(schema: dict, defs: dict | None = None) -> Any:
    defs = defs if defs is not None else schema.get("$defs", {})
    if "$ref" in schema:
        return example_from_schema(defs[schema["$ref"].split("/")[-1]], defs)
    if "anyOf" in schema:
        options = [s for s in schema["anyOf"] if s.get("type") != "null"] or schema["anyOf"]
        return example_from_schema(options[0], defs)
    if "enum" in schema:
        return schema["enum"][0]
    kind = schema.get("type")
    if kind == "object":
        props = schema.get("properties", {})
        return {key: example_from_schema(sub, defs) for key, sub in props.items()}
    if kind == "array":
        count = max(1, schema.get("minItems", 1))
        return [example_from_schema(schema.get("items", {"type": "string"}), defs) for _ in range(count)]
    if kind == "integer":
        return 1
    if kind == "number":
        return 1.0
    if kind == "boolean":
        return True
    return "(mock) nội dung mẫu"


# ---------------------------------------------------------------- embeddings tất định
def embed(text: str, dims: int) -> list[float]:
    """Hashing trick: cùng từ → cùng chiều. Đủ để thấy câu chung từ khóa gần nhau; không phải semantic thật."""
    vector = [0.0] * dims
    for word in re.findall(r"\w+", text.lower()):
        digest = int(hashlib.md5(word.encode()).hexdigest(), 16)
        vector[digest % dims] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


# ---------------------------------------------------------------- server
class MockLLM:
    def __init__(self) -> None:
        self.channels: list[Channel] = []
        self.requests: list[dict] = []
        self.embedding_requests: list[dict] = []
        self._lock = threading.Lock()
        self.app = self._build_app()
        self.base_url: str | None = None

    # --- API cho test ---
    def script(self, *steps: Step, match: str = "") -> Channel:
        """Thêm bước cho kênh `match` (chuỗi có trong system prompt của agent cần trả lời)."""
        with self._lock:
            channel = next((c for c in self.channels if c.match == match), None)
            if channel is None:
                channel = Channel(match)
                # kênh có điều kiện được xét trước kênh mặc định
                self.channels.insert(0 if match else len(self.channels), channel)
            channel.steps.extend(steps)
            return channel

    def reset(self) -> None:
        with self._lock:
            self.channels.clear()
            self.requests.clear()
            self.embedding_requests.clear()

    def requests_for(self, match: str) -> list[dict]:
        return [r for r in self.requests if match in system_text(r)]

    def remaining(self) -> dict[str, int]:
        return {c.match or "<mặc định>": len(c.steps) - c.used for c in self.channels}

    # --- chọn câu trả lời ---
    def _next(self, body: dict) -> Step:
        with self._lock:
            self.requests.append(body)
            if not self.channels:
                return self._auto(body)
            sys_text = system_text(body)
            channel = next((c for c in self.channels if c.match and c.match in sys_text), None)
            channel = channel or next((c for c in self.channels if not c.match), None)
            if channel is None:
                raise RuntimeError(f"mock: không có kênh nào khớp system prompt: {sys_text[:200]!r}")
            if channel.used >= len(channel.steps):  # hết bước thì báo lỗi, không lấy bước của kênh khác
                raise RuntimeError(
                    f"mock: kịch bản kênh {channel.match or '<mặc định>'!r} đã hết ({channel.used} bước)"
                )
            channel.used += 1
            return channel.steps[channel.used - 1]

    @staticmethod
    def _auto(body: dict) -> Step:
        response_format = body.get("response_format") or {}
        if response_format.get("type") == "json_schema":
            return answer_json(example_from_schema(response_format["json_schema"]["schema"]))
        if response_format.get("type") == "json_object":
            return answer_json({"result": "(mock)"})
        last_user = next(
            (_text(m.get("content")) for m in reversed(body.get("messages", [])) if m.get("role") == "user"), ""
        )
        return say(f"(mock) Đã nhận: {last_user[:120]}")

    # --- định dạng OpenAI ---
    @staticmethod
    def _usage(body: dict, step: Step) -> dict:
        prompt = sum(len(_text(m.get("content")) or "") for m in body.get("messages", [])) // 4 + 1
        completion = len(step.text or json.dumps(step.tool_calls or [])) // 4 + 1
        return {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": prompt + completion}

    @staticmethod
    def _tool_calls(step: Step) -> list[dict]:
        return [
            {
                "id": f"call_{uuid.uuid4().hex[:16]}",
                "type": "function",
                "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"], ensure_ascii=False)},
            }
            for tc in step.tool_calls or []
        ]

    def _completion(self, body: dict, step: Step) -> dict:
        message: dict[str, Any] = {"role": "assistant", "content": step.text}
        tool_calls = self._tool_calls(step)
        if tool_calls:
            message["tool_calls"] = tool_calls
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": body.get("model", "mock"),
            "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls" if tool_calls else "stop"}],
            "usage": self._usage(body, step),
        }

    def _stream(self, body: dict, step: Step):
        base = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": body.get("model", "mock"),
        }

        def chunk(delta: dict, finish: str | None = None, **extra: Any) -> str:
            payload = {**base, "choices": [{"index": 0, "delta": delta, "finish_reason": finish}], **extra}
            return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        yield chunk({"role": "assistant", "content": ""})
        text = step.text or ""
        for i in range(0, len(text), 24):  # chia nhỏ để thấy token streaming
            yield chunk({"content": text[i : i + 24]})
        tool_calls = self._tool_calls(step)
        for index, tc in enumerate(tool_calls):
            yield chunk({"tool_calls": [{"index": index, **tc}]})
        yield chunk({}, "tool_calls" if tool_calls else "stop")
        if (body.get("stream_options") or {}).get("include_usage"):
            usage = {**base, "choices": [], "usage": self._usage(body, step)}
            yield f"data: {json.dumps(usage)}\n\n"
        yield "data: [DONE]\n\n"

    def _build_app(self) -> FastAPI:
        app = FastAPI(title="mock-openai", telemetry={"tracing": False})  # không trộn span của mock vào trace agent

        @app.post("/v1/chat/completions")
        async def chat(request: Request):
            body = await request.json()
            try:
                step = self._next(body)
            except RuntimeError as exc:
                return JSONResponse({"error": {"message": str(exc), "type": "mock_script"}}, status_code=500)
            if body.get("stream"):
                return StreamingResponse(self._stream(body, step), media_type="text/event-stream")
            return self._completion(body, step)

        @app.post("/v1/embeddings")
        async def embeddings(request: Request):
            body = await request.json()
            self.embedding_requests.append(body)
            inputs = body["input"] if isinstance(body["input"], list) else [body["input"]]
            dims = int(body.get("dimensions") or 1536)
            data = [{"object": "embedding", "index": i, "embedding": embed(str(t), dims)} for i, t in enumerate(inputs)]
            tokens = sum(len(str(t)) for t in inputs) // 4 + 1
            return {
                "object": "list",
                "data": data,
                "model": body.get("model", "mock"),
                "usage": {"prompt_tokens": tokens, "total_tokens": tokens},
            }

        @app.get("/v1/models")
        async def models():
            return {"object": "list", "data": [{"id": "mock", "object": "model", "owned_by": "mock"}]}

        return app

    # --- chạy server ---
    def serve_in_thread(self, port: int = 0) -> str:
        """Chạy server trong thread nền (cho test). Trả base_url dạng http://127.0.0.1:PORT/v1."""
        self.base_url = serve_in_thread(self.app, port) + "/v1"
        return self.base_url


def serve_in_thread(app: Any, port: int = 0) -> str:
    """Chạy một ứng dụng ASGI (mock này, hoặc AgentOS) bằng uvicorn trong thread nền. Trả http://127.0.0.1:PORT."""
    if port == 0:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    deadline = time.time() + 20
    while not server.started:
        if time.time() > deadline:
            raise RuntimeError("server không khởi động được")
        time.sleep(0.02)
    return f"http://127.0.0.1:{port}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8900)
    args = parser.parse_args()
    print(f"Mock OpenAI ở http://127.0.0.1:{args.port}/v1 (chế độ tự động). Ctrl+C để dừng.")
    uvicorn.run(MockLLM().app, host="127.0.0.1", port=args.port, log_level="warning")
```

</details>

### 3.6 Hạ tầng test

- `conftest.py` (gốc project): chạy `mock_llm` một lần cho cả phiên test, đặt biến môi trường, seed dữ liệu Lab 00; fixture `llm` xoá kịch bản cũ; mỗi test một DB riêng; mỗi test một client HTTP mới.
- `tests/settings_paths.py`: đường dẫn file kết quả trong `storage/`.
- `tests/servers.py`: chạy server thật bằng tiến trình riêng (MCP HTTP ở Phần 9, AgentOS ở Phần 12) trên cổng còn trống.

Vì sao có fixture `fresh_http_client`: Agno dùng **một `httpx.AsyncClient` cho cả tiến trình** (model, `A2AClient`, `AgentOSClient`), kết nối gắn với event loop đã mở nó. Mỗi `asyncio.run()` trong test là một loop mới, nên mỗi test cần client mới. Chương trình thật chỉ có một event loop nên không cần việc này.

**File: `conftest.py`**

```python
"""Hạ tầng test: model giả lập chạy một lần cho cả phiên, mỗi test có database riêng.

Thư mục này được pytest đưa vào sys.path, nên `import agno_lab`, `import service`... chạy được như khi bạn
chạy lệnh ở gốc project thực hành.
"""

from __future__ import annotations

import os

import httpx
import pytest
from agno.utils.http import set_default_async_client

import setup_assets
from mock_llm import MockLLM

_MOCK = MockLLM()


@pytest.fixture(scope="session", autouse=True)
def _environment():
    os.environ["OPENAI_BASE_URL"] = _MOCK.serve_in_thread()
    os.environ["OPENAI_API_KEY"] = "mock"
    os.environ["MODEL_ID"] = "mock"
    os.environ["AGNO_TELEMETRY"] = "false"
    setup_assets.main()  # seed idempotent: data/ của project tham chiếu
    yield


@pytest.fixture
def llm() -> MockLLM:
    """Model giả lập, đã xoá kịch bản và request của test trước."""
    _MOCK.reset()
    return _MOCK


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Mỗi test một file SQLite riêng — không test nào thấy session của test khác."""
    monkeypatch.setenv("AGNO_DB", str(tmp_path / "agno.db"))
    monkeypatch.setenv("AGNO_VECTORS", str(tmp_path / "lancedb"))
    return tmp_path / "agno.db"


@pytest.fixture(autouse=True)
def fresh_http_client():
    """Agno dùng MỘT httpx.AsyncClient cho cả tiến trình (model, A2AClient, AgentOSClient...), và kết nối của client
    gắn với event loop đã mở nó. Mỗi asyncio.run()/TestClient trong test là một loop mới → mỗi test một client mới.
    Chương trình thật không cần việc này: chỉ có một event loop (một asyncio.run hoặc server uvicorn)."""
    set_default_async_client(httpx.AsyncClient(timeout=60, follow_redirects=True))
```

**File: `tests/settings_paths.py`**

```python
"""Đường dẫn file kết quả trong project tham chiếu, dùng chung cho test."""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def storage_file(*parts: str) -> Path:
    return ROOT.joinpath("storage", *parts)


def clean_storage(report_id: str) -> None:
    shutil.rmtree(ROOT / "storage" / report_id, ignore_errors=True)
```

**File: `tests/servers.py`**

```python
"""Chạy server thật cho test: một tiến trình riêng như production, trên cổng còn trống."""

import contextlib
import os
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator

from settings_paths import ROOT


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def process_server(args: list[str], port: int, **env: str) -> Iterator[str]:
    """Chạy `python <args>` ở gốc project (thêm biến môi trường `env`), đợi cổng mở, trả http://127.0.0.1:PORT."""
    with tempfile.TemporaryFile() as log:
        proc = subprocess.Popen([sys.executable, *args], cwd=ROOT, env={**os.environ, **env}, stdout=log, stderr=log)
        try:
            deadline = time.time() + 60
            while True:
                try:
                    socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                    break
                except OSError:
                    if proc.poll() is not None or time.time() > deadline:
                        log.seek(0)
                        raise RuntimeError(f"server không khởi động: {args}\n{log.read().decode()[-3000:]}") from None
                    time.sleep(0.1)
            yield f"http://127.0.0.1:{port}"
        finally:
            proc.terminate()
            proc.wait(timeout=10)
```

Chạy toàn bộ test (khoảng 1,5 phút): `uv run pytest -q`. Chạy một phần: `uv run pytest tests/test_p04_session.py -v`.

## 4. Baseline `agno_cli.py`

Baseline giữ nguyên như bản đầu của Lab 01; đã chạy lại với Agno 3.1.3 + mcp 2.x (sau Bước 0) và không cần sửa dòng nào. Nó làm theo cách "code điều phối": luôn lấy evidence qua MCP **trước** khi gọi model. 16 phần sau lần lượt mở từng tính năng mà baseline chưa dùng.

### 4.1 Tự thiết kế trước khi xem code — 20 phút

Viết ra hợp đồng của ba hàm:

- `inspect_rules()` trả quy ước chính xác từ Excel; đây là Python tool trong process.
- `build_agent(thread_id)` trả Agent với persistent session database.
- `main(thread_id, instruction)` lấy evidence qua MCP, truyền draft cũ, chạy model, kiểm tra output và lưu artifact.

Bắt buộc lấy dữ liệu không nên chỉ phụ thuộc lời nhắc "luôn gọi tool"; baseline điều phối bước đó bằng code. Tool tự chọn là chỗ thử nghiệm thêm khả năng của model (Phần 9). Ghi riêng vào trace việc nào do ứng dụng gọi, việc nào do LLM chọn.

### 4.2 Code tham khảo

Tự gõ theo ba nhóm: imports + tool, build agent, CLI. Sau mỗi nhóm `⌘⌥L` để format và `⌃⌥O` dọn imports.

**File: `agno_cli.py`**

```python
import asyncio
import json
import os
import sys
from pathlib import Path

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIChat
from dotenv import load_dotenv

from mcp_client import collect_metrics
from reporting import Narrative, make_evidence, make_prompt, render_report, save_local_report
from rules import load_rules

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def inspect_rules() -> str:
    """Đọc toàn bộ quy ước KPI từ Excel, giữ nguyên rule_id và threshold."""
    return json.dumps(load_rules(), ensure_ascii=False)


def build_agent(thread_id: str) -> Agent:
    model_id = os.environ["MODEL_ID"]
    (ROOT / "storage").mkdir(exist_ok=True)
    return Agent(
        name="enterprise-report",
        model=OpenAIChat(id=model_id),
        db=SqliteDb(db_file=str(ROOT / "storage/agno_sessions.db")),
        session_id=thread_id,
        add_history_to_context=True,
        num_history_runs=5,
        tools=[inspect_rules],
        output_schema=Narrative,
        instructions=[
            "Viết narrative cho báo cáo bằng tiếng Việt.",
            "Dùng evidence được cấp; gọi inspect_rules nếu cần kiểm tra quy ước.",
            "Không viết lại bảng số liệu; ứng dụng sẽ render bảng.",
            "Không suy diễn benchmark từ research fixture.",
        ],
    )


async def main(thread_id: str, instruction: str):
    if not thread_id or not all(c.isalnum() or c in "-_" for c in thread_id):
        raise ValueError("ID chỉ gồm chữ, số, - hoặc _")
    state_path = ROOT / "storage" / f"agno-{thread_id}.json"
    previous = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    # Để dễ kiểm tra số liệu, baseline luôn lấy lại 2 quý qua MCP mỗi lượt.
    current, prior = await collect_metrics()
    evidence = make_evidence(current, prior)
    prompt = make_prompt(evidence, instruction, previous.get("report", ""))
    response = await build_agent(thread_id).arun(prompt)
    narrative = Narrative.model_validate(response.content)
    revision = previous.get("revision", 0) + 1
    report = render_report(evidence, narrative, revision)
    save_local_report(f"agno-{thread_id}", revision, report)
    state = {"revision": revision, "report": report}
    temporary = state_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    temporary.replace(state_path)
    print(report)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit('Dùng: agno_cli.py report-01 "Yêu cầu báo cáo"')
    asyncio.run(main(sys.argv[1], sys.argv[2]))
```

Chương trình đọc hai quý cố định Q2/Q1 2026 để so sánh công bằng giữa ba framework. Yêu cầu "chuyển sang Q3" chưa được hỗ trợ chỉ bằng prompt: cần thêm input quý có validation và truyền đến MCP (Phần 2 làm việc này bằng `ReportRequest`). Tương tự, thay đổi cách hiển thị bảng phải sửa renderer; narrative không được quyền sửa số gốc.

Baseline luôn refresh database nhưng vẫn truyền draft trước để sửa nhận xét. Cache evidence qua nhiều lượt là bài mở rộng, cần policy rõ khi nào dữ liệu hết hạn.

Hai điểm cần biết khi chạy với Agno 3.1.3 (giải thích ở Phần 2 và 4): `Narrative.model_validate(response.content)` là cổng kiểm tra đúng chỗ, vì model trả sai schema thì Agno chỉ log WARNING và `content` là chuỗi; `num_history_runs=5` nghĩa là chỉ 5 run gần nhất của session được đưa lại vào ngữ cảnh.

### 4.3 Chạy v1, sửa v2 và tách session

```bash
uv run python agno_cli.py report-01 'Lập báo cáo Q2, chỉ rõ hai rủi ro Cloud và FinTech.'
uv run python agno_cli.py report-01 'Rút tóm tắt còn 3 ý, thêm hành động có người phụ trách dạng vai trò.'
uv run python agno_cli.py report-02 'Lập báo cáo Q2 cho phiên độc lập.'
```

Kết quả cần quan sát:

| Nơi lưu | Cần có |
| --- | --- |
| `storage/agno_sessions.db` | Lịch sử run theo session (bảng `agno_sessions`, `agno_runs`) |
| `storage/agno-report-01.json` | Revision 2 và report mới nhất |
| `storage/agno-report-01/v1.md`, `v2.md` | Hai artifact để so sánh |
| `storage/agno-report-02/v1.md` | Session mới bắt đầu ở v1 |

Mỗi lệnh CLI đã là một process mới, vì vậy chuỗi v1/v2 kiểm tra tính lưu trữ qua restart bình thường. Nó chưa kiểm tra crash giữa model call và lúc ghi state.

Đối chiếu bảng KPI với Lab 00. Có đủ 4 phần; research ghi fixture; không có URL giả hoặc chuẩn ngành bịa ra. Narrative có thể vẫn viết sai dù schema hợp lệ: đọc kỹ ý nghĩa, không chỉ nhìn code chạy thành công.

Với `mock_llm` (cấu hình 3), baseline chạy đủ vòng v1/v2 và in báo cáo có bảng KPI thật; phần tóm tắt là chữ mẫu `(mock) nội dung mẫu`.

### 4.4 Debug bằng PyCharm — 25 phút

| Điểm dừng | Phím/action | Cần quan sát |
| --- | --- | --- |
| `current, prior = ...` | `⌘F8`, Debug configuration | Hai list đủ phòng ban |
| `make_evidence(...)` | `F7` vào hàm | Tại sao Cloud bị vàng? |
| `response = await ...` | `F8` | Kiểu của `response.content` |
| `revision = ...` | `⌥F8` | `previous.get("revision", 0)` ở v1/v2 |
| `inspect_rules` | Breakpoint | Model có thực sự gọi tool không? |

Nếu model không gọi `inspect_rules`, đây không tự động là lỗi: evidence đã có dữ liệu cần thiết. Thử thêm yêu cầu "xác minh quy ước Excel bằng tool" rồi xem trace. Không dùng việc model tự thuật "tôi đã gọi tool" thay cho trace thực (Phần 12 đọc trace qua API).

Bài refactor: chọn phần load/save state → `⌘⌥M` Extract Method. Đổi `thread_id` thành `report_session_id` bằng `⇧F6`, rồi dùng `⌥F7` xem mọi chỗ đã đổi đúng.

## 5. Học từng phần

| Tài liệu | Phần | Nội dung chính |
| --- | --- | --- |
| [Lab 01a — Agent, tool, output, streaming](agno/01a-agent-tool-output-streaming.md) | 1–3 | Vòng lặp tool, schema tool từ docstring, lỗi tool, `output_schema` không tự chặn output sai, thứ tự sự kiện stream |
| [Lab 01b — Session, memory, knowledge](agno/01b-session-memory-knowledge.md) | 4–6 | Bảng DB Agno tạo, history theo session, `session_state`, chi phí tóm tắt; vòng đời memory; RAG có upsert và xoá |
| [Lab 01c — Tool nâng cao, HITL, guardrail](agno/01c-tool-hitl-guardrail.md) | 7–8 | Xác nhận/hỏi thêm/tool ở client, chạy tiếp từ process khác, hook; pre/post hook, PII, injection, model dự phòng |
| [Lab 01d — MCP, Team, Workflow](agno/01d-mcp-team-workflow.md) | 9–11 | `MCPTools` stdio/HTTP; 4 chế độ team; workflow có Parallel, Loop, Router, Condition, HumanReview |
| [Lab 01e — AgentOS, AG-UI, A2A, MCP server, eval](agno/01e-agentos-agui-a2a-mcp-eval.md) | 12–16 | REST, khoá, trace; sự kiện AG-UI và frontend tool; Agent Card và RemoteAgent; MCPConfig; eval cho CI |

## 6. Bản đồ tính năng Agno

Tra nhanh sau khi học: tính năng nằm ở đâu, API chính, và điều đã đo cần nhớ.

| Tính năng | Phần | API chính | Điều đã đo cần nhớ |
| --- | --- | --- | --- |
| Tool hàm / Toolkit | 1 | `tools=[fn, Toolkit]` | Docstring thành mô tả tool; tool ném exception thì model nhận chuỗi lỗi, run vẫn COMPLETED |
| Giới hạn tool | 1 | `tool_call_limit` | Vượt giới hạn: tool không chạy, model nhận "Tool call limit reached", vòng lặp vẫn tiếp |
| Output có schema | 2 | `output_schema`, `use_json_mode` | Sai schema: WARNING, `content` là chuỗi, status vẫn COMPLETED → tự kiểm |
| Input có schema | 2 | `input_schema`, `run(input=...)` | Sai input: `ValueError` trước khi gọi model |
| Streaming | 3 | `stream`, `stream_events`, `yield_run_output` | Không có `stream_events` thì không thấy sự kiện tool |
| Lịch sử | 4 | `db`, `session_id`, `add_history_to_context`, `num_history_runs` | Chèn lại toàn bộ message (kể cả tool) của N run gần nhất; mặc định 3 |
| State | 4 | `session_state`, `RunContext`, `{key}` trong instructions | Tham số `run_context` bị ẩn khỏi schema tool; state lưu sau run |
| Tóm tắt session | 4 | `enable_session_summaries` | Thêm 1 lượt gọi model mỗi run |
| Memory | 5 | `MemoryManager`, `update_memory_on_run`, `enable_agentic_memory` | Trích xuất chạy song song, chỉ thấy tin user; thiếu `user_id` → user `default` dùng chung |
| Knowledge | 6 | `Knowledge`, `LanceDb`, `insert(upsert=True)`, `search_knowledge` | Name bị xoá khỏi nguồn phải `remove_vectors_by_name` |
| HITL | 7 | `requires_confirmation`, `requires_user_input`, `external_execution`, `continue_run` | `user_input_fields` bị ẩn khỏi model; chạy tiếp được từ process khác nhờ DB |
| Hook | 7–8 | `tool_hooks`, `pre_hooks`, `post_hooks` | Post-hook chặn: status ERROR nhưng `content` vẫn là output vi phạm |
| Guardrail | 8 | `PromptInjectionGuardrail`, `PIIDetectionGuardrail(mask_pii=True)` | Chặn trước model: không tốn token |
| Model dự phòng | 8 | `FallbackConfig(on_error=[...], callback=...)` | `run.model` vẫn ghi model chính |
| MCP client | 9 | `MCPTools(server_params / url, transport, include_tools)` | Cần mcp ≥ 2.1; lỗi phải là `ToolError` |
| Team | 10 | `Team(mode=..., members=[...])` | Thành viên chỉ nhận `task`, không nhận câu hỏi gốc |
| Workflow | 11 | `Step`, `Parallel`, `Loop`, `Router`, `Condition`, `HumanReview` | Bước agent nhận nội dung bước liền trước; `StepOutput(stop=True)` dừng cả workflow |
| AgentOS | 12 | `AgentOS(...)`, `get_app()`, `AgentOSClient` | Cần `base_app` tắt tracing native của FastAPI; tracing là toàn tiến trình |
| Bảo mật | 12 | `OS_SECURITY_KEY` | Khoá mọi route trừ `/health`; `/docs` vẫn mở nếu không tắt |
| AG-UI | 13 | `interfaces=[AGUI(agent=...)]`, `POST /agui` | State client ghi đè state server; lịch sử lấy từ DB |
| A2A | 14 | `a2a_interface=True`, `A2AClient`, `RemoteAgent` | `contextId` = session; Team có RemoteAgent chỉ chạy `arun` |
| MCP server | 15 | `mcp=True`, `MCPConfig(tools=[agent.as_tool(...)])` | `/mcp` cũng cần khoá; server card công khai |
| Eval | 16 | `ReliabilityEval`, `AccuracyEval`, `AgentAsJudgeEval`, `PerformanceEval`, `run_cases` | Giám khảo mặc định là model OpenAI → luôn truyền `model=` |

## 7. Bài tập mở rộng

### A. Tool do LLM chọn và MCP

Tạo async tool `fetch_quarter_metrics(quarter: str)` mở `ClientSession`, gọi `get_metrics`. Tách helper client để nhận quarter thay vì thu cố định hai quý. Đăng ký wrapper đó trong `tools`. Đây là bước học tool selection; giữ validation đầu vào và yêu cầu kiểm tra evidence trước render. **Lời giải: Phần 9, cách A** (rồi so với `MCPTools`, cách B).

So sánh trace giữa hai cách: orchestration luôn gọi MCP trước model, và model tự quyết định gọi MCP. Trường hợp thứ hai phải xử lý thiếu tool result, gọi sai quý và tool thất bại. Không thay bằng import hàm server trực tiếp.

### B. Cache, session history và revision repository

Thay JSON state bằng SQLite repository:

```text
reports(thread_id, revision, request_id UNIQUE, markdown, evidence_hash, created_at)
PRIMARY KEY(thread_id, revision)
```

Dùng transaction và expected revision để tránh hai lượt cùng ghi v2. `request_id` trùng trả lại artifact đã commit. Lịch sử chat chỉ giữ 5 run không phải toàn bộ revision archive. Khi lưu report và session DB ở hai nơi, không tự coi hai write là một transaction nguyên tử.

Nghiệm thu: hai tiến trình cùng sửa report-01 không âm thầm ghi đè nhau; crash sau model trước commit có hành vi retry được mô tả rõ. Liên quan: `session_state` ở Phần 4 (không phải kho phiên bản), `Toolkit(cache_results=True)` ở Phần 7, workflow v1 → v2 ở Phần 11.

### C. Research thật và UI

Thay fixture theo hợp đồng research ở Lab 00, kiểm tra counter cache hit. Sau đó triển khai A2A bằng SDK (**Phần 14** đã dựng research service và gọi qua `A2AClient`, `RemoteAgent`). Cuối cùng viết API + AG-UI adapter (**Phần 12–13**); dùng `arun` hoặc async streaming API đúng version. Khi output schema được stream, đừng render một object chưa đủ field như kết quả cuối đã validate.

## 8. Tổng kết và đi tiếp

### 8.1 Lỗi thường gặp

| Lỗi | Hướng xử lý |
| --- | --- |
| `No module named agno.storage` | Đang dùng API cũ; dùng `agno.db.sqlite` |
| `ImportError: cannot import name 'MCPError'` khi import `agno.tools.mcp` | Còn mcp 1.x; làm Bước 0 |
| `No module named 'mcp.server.fastmcp'` sau khi nâng mcp | mcp 2.x đổi tên: `mcp.server.mcpserver.MCPServer` |
| Model nhận `Error executing tool get_metrics`, không biết sai gì | mcp 2.x giấu exception lạ; raise `ToolError` |
| Output không validate thành Narrative | Model trả sai schema: kiểm `isinstance`, thử `use_json_mode=True` với model local |
| Key sai khi dùng tên `openai:...` | `MODEL_ID` của Agno không chứa prefix provider |
| `Async function ... can't be used with synchronous agent.run()` | Agent có tool async: dùng `arun` |
| `'RemoteAgent' object has no attribute 'run'` | Team có thành viên ở xa: dùng `await team.arun(...)` |
| `RuntimeError: Event loop is closed` | Gọi `asyncio.run()` nhiều lần với client async dùng chung; gom vào một `asyncio.run(main())` |
| `/traces` lọc theo session ra rỗng | Thiếu `base_app=FastAPI(telemetry={"tracing": False})` |
| Cảnh báo `multiple distinct databases share id` | Dùng chung một object `SqliteDb` cho cùng file (`settings.db()`) |
| Session có history nhưng report thiếu revision | Hai tầng lưu riêng; kiểm tra JSON artifact state |
| File report bị ghi đè khi chạy đồng thời | Baseline chưa có concurrency control; làm bài tập B |
| `mock: kịch bản kênh ... đã hết` (HTTP 500) trong test | Test gọi model nhiều lần hơn kịch bản; đếm lại lượt gọi (ví dụ lượt tóm tắt, lượt trích memory) |

### 8.2 Câu hỏi tự kiểm tra

1. Tools ở `tools=[...]` khác thế nào với helper `collect_metrics()` được gọi trước model?
2. Xóa `agno_sessions.db` nhưng giữ JSON state thì còn và mất những gì?
3. Giữ session DB nhưng xóa JSON state sẽ có rủi ro gì cho số revision?
4. Muốn lọc riêng FIN_TECH, bạn sửa contract, evidence hay chỉ prompt? Tại sao?
5. Đâu là bằng chứng số liệu đúng, đâu là bằng chứng narrative đúng?
6. Một yêu cầu "lập báo cáo, duyệt rồi lưu" nên là agent nhiều tool, team hay workflow? Vì sao?
7. Ba cơ chế "nhớ" của Agno (history, memory, knowledge) khác nhau ở phạm vi và ai ghi?
8. Bạn đưa agent ra cho giao diện web, cho một agent ở đội khác và cho Claude Code. Mỗi trường hợp dùng giao thức nào, cần bảo vệ gì?

### 8.3 Phạm vi đã kiểm chứng

- 74 test của project tham chiếu chạy với `mock_llm`, gồm cả server thật bằng tiến trình riêng (MCP HTTP, AgentOS có khoá và tracing), và một lần cài sạch từ `requirements.txt`.
- Hành vi ghi "đã đo" được đo trên Agno 3.1.3 bằng request thật mà mock nhận, không lấy từ tài liệu marketing. Chỗ ghi "đọc code" hoặc "chưa kiểm chứng" thì chưa có test.
- Mock không đánh giá chất lượng câu trả lời của model thật. Chạy lại các phần với model của bạn và dùng eval (Phần 16) để biết chất lượng.

### 8.4 Đi tiếp

- [Lab 02 — Pydantic AI + Temporal](guide_02_pydantic_ai_temporal.md): cùng bài toán với workflow chạy bền.
- [Lab 03 — LangGraph](guide_03_langgraph.md): workflow dạng đồ thị trạng thái, so với Phần 11.
- [Harness Agno → LangChain](../agent-radar/02-harness-agno-sang-langchain.md): một run của Agno chạy ra sao bên trong và dựng lại bằng LangChain.

**Hoàn thành Lab 01** khi chạy được baseline v1/v2, qua checkpoint của 16 phần và trả lời được các câu hỏi ở mục 8.2.
