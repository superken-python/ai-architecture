# Harness của agent: Agno chạy thế nào, dựng lại bằng LangChain, cải tiến theo Claude Code

| Thuộc tính | Chi tiết |
|---|---|
| Thuộc nhóm | [Nhóm 7 · AI Agent và tự động hóa quy trình](../02-skill-map/generated/nhom/g7-agent-tu-dong-hoa.md) · kỹ năng [LLM-05](../02-skill-map/generated/mang/llm.md#llm-05) |
| Mục tiêu | Hiểu harness của Agno tới mức **tự viết lại được** bằng LangChain, rồi làm harness tốt hơn theo cách Claude Code làm |
| Phiên bản đã đọc mã và chạy | `agno` 3.1.3 · `langchain` 1.4.6 · `langgraph` 1.2.16 · `langchain-core` 1.6.12 · `langgraph-checkpoint-sqlite` 3.1.2 · `langchain-openai` 1.7.2 |
| Code chạy được | [`labs/llm-05-trung-cap-harness-langchain/`](../../labs/llm-05-trung-cap-harness-langchain/README.md) — mọi khối code dưới đây là **nguyên văn** file trong lab (test `test_doc_sync.py` bảo đảm điều này) |
| Đã kiểm chứng | 24 test với model kịch bản: tái hiện từng thí nghiệm đã làm trên Agno, và từng lớp cải tiến |
| Chưa kiểm chứng | Chạy với model thật (môi trường làm tài liệu không có API key) · server AG-UI cho LangChain · Postgres |
| Ngày | 2026-10-17 |

Tài liệu đi theo thứ tự: **agent và harness là gì → Agno chạy một run ra sao (đã đo) → ánh xạ sang LangChain →
code từng mảnh → cải tiến**. Ví dụ xuyên suốt là trợ lý dữ liệu khách hàng trong Excel, rút gọn từ
[CMB-10](../../projects/cmb-10-excel-agent-addin/README.md).

## Mục lục

1. [Agent và harness](#1-agent-và-harness)
2. [Harness của Agno chạy thế nào](#2-harness-của-agno-chạy-thế-nào)
3. [Ánh xạ Agno sang LangChain](#3-ánh-xạ-agno-sang-langchain)
4. [Dựng lại bằng LangChain, từng mảnh](#4-dựng-lại-bằng-langchain-từng-mảnh)
5. [Cải tiến harness theo Claude Code](#5-cải-tiến-harness-theo-claude-code)
6. [Giới hạn và việc tiếp theo](#6-giới-hạn-và-việc-tiếp-theo)

## 1. Agent và harness

**Agent** = model + instructions + tools + trạng thái (lịch sử, memory). **Harness** = toàn bộ code bao quanh model:
dựng ngữ cảnh cho mỗi lần gọi model, chạy vòng lặp gọi tool, dừng đúng lúc, tạm dừng chờ người hoặc client, lưu
lại, và cho ta chen vào giữa các bước. Model quyết định *làm gì*; harness quyết định *model thấy gì, được làm gì,
và khi nào dừng*.

```
                ┌──────────────────────── một run ────────────────────────┐
tin nhắn user → │ dựng ngữ cảnh → gọi model → có tool call? ─không→ trả lời │ → lưu run
                │   (instructions,     ↑            │có                    │
                │    lịch sử, memory)  └── kết quả ← chạy tool             │
                │                       (hoặc DỪNG chờ client / người duyệt)│
                └──────────────────────────────────────────────────────────┘
```

Mọi framework agent đều có vòng lặp này. Khác nhau ở năm chỗ, và đó là năm chỗ phải viết lại khi đổi framework:

| Chỗ | Câu hỏi |
|---|---|
| Dựng ngữ cảnh | Model thấy những gì, theo thứ tự nào, lấy từ đâu? |
| Vòng lặp | Dừng khi nào? Có trần số bước không? |
| Tạm dừng | Run dừng giữa chừng để client chạy tool / người duyệt, rồi chạy tiếp ra sao? |
| Lưu trữ | Lịch sử, memory, run đang dừng nằm ở đâu? |
| Điểm chen | Code của ta chạy được ở trước/sau bước nào? |

## 2. Harness của Agno chạy thế nào

Mọi điều trong mục này đọc từ mã `agno` 3.1.3 (đường dẫn tính từ `site-packages/agno/`) và đo bằng thí nghiệm với
model kịch bản. Chỗ nào chỉ đọc mã mà chưa đo thì ghi rõ.

### 2.1 Tạo agent trong Agno

Agent của CMB-10 ([`excel_agent.py`](../../projects/cmb-10-excel-agent-addin/src/excel_agent/agents/excel_agent.py)):

```python
Agent(
    id="excel-agent",
    model=OpenAIResponses(id="gpt-5-mini", store=False),
    instructions=instructions,  # hàm async nhận run_context → chuỗi, chạy mỗi run
    tools=[SystemDataTools(deps_factory)],  # tool server; tool Excel do add-in gửi qua AG-UI
    db=SqliteDb(db_file="var/agentos.db"),  # session, run, memory đều nằm ở đây
    add_history_to_context=True,
    num_history_runs=settings.num_history_runs,
    tool_call_limit=settings.tool_call_limit,
)
# Bật memory dài hạn (CMB-10 chưa bật):
#   update_memory_on_run=True, memory_manager=MemoryManager(model=..., db=...)
```

Gọi: `await agent.arun(text, user_id=..., session_id=...)`. Qua AgentOS + AG-UI thì `session_id` = `threadId`.

### 2.2 Một run đi qua những bước nào

```
A. Nhận input: messages + tools của client (AG-UI) + context
   └─ client tools → Function(external_execution=True)                     (os/interfaces/agui, parse_client_tools)
B. [nền] update_memory_on_run → bắt đầu trích xuất memory từ TIN NHẮN USER  (agent/_run.py:526, _managers.py:180)
C. Dựng messages (agent/_messages.py:1879 get_run_messages, thứ tự ở :2360–2375):
     system  = instructions + memory của user_id (nếu add_memories_to_context) (_messages.py:1095)
     history = tin nhắn của N run gần nhất trong session                     (_messages.py:1965 → session/agent.py:141)
     user    = tin nhắn hiện tại
D. Vòng lặp model (models/base.py:705, while True):
     gọi model với TOÀN BỘ tools
     ├─ không có tool call                → break (base.py:874) → trả lời
     ├─ có tool call → run_function_calls (base.py:2416)
     │    ├─ vượt tool_call_limit         → tool đó trả lỗi, vòng lặp VẪN chạy (base.py:2437–2446)
     │    ├─ requires_confirmation        → đánh dấu chờ duyệt
     │    ├─ external_execution (client)  → đánh dấu chờ client (base.py:2550)
     │    └─ còn lại                      → chạy, thêm ToolMessage, lặp lại
     └─ có tool đang chờ                  → break: run TẠM DỪNG (base.py:852–866), lưu vào DB
E. Kết thúc: chờ tác vụ memory ở bước B xong (agent/_run.py:758), lưu run vào session
F. Chạy tiếp run tạm dừng: client gửi kết quả → continue_run / acontinue_run (agent/_run.py:3650, :4668)
   nạp run từ DB, chèn kết quả tool, quay lại D
```

Ghi memory ở bước B dùng một lượt gọi model riêng (`memory/manager.py:1044` `create_or_update_memories`): system
prompt liệt kê memory hiện có (`manager.py:962`), model được các tool `add_memory`, `update_memory`, `delete_memory`.

**Chưa đọc kỹ** (nên đọc trước khi viết lại phần tương ứng): luồng streaming, compaction và offload kết quả tool,
learning, session summary, Team/Workflow, hook/guardrail, tầng HTTP của AgentOS.

### 2.3 Những hành vi đã đo

| Hành vi | Kết quả đo trên Agno 3.1.3 | Nguồn trong mã | Khi viết lại |
|---|---|---|---|
| `tool_call_limit=2`, model gọi tool 40 lần | 2 tool chạy, model được gọi **41** lần; vòng lặp chỉ dừng khi model ngừng | `models/base.py:2437–2446` | Cần trần dừng hẳn (LangChain: `exit_behavior="end"`) |
| Ghi memory có được chờ? | Có: run trả về sau khi trích xuất xong; memory có ngay trong DB | `agent/_run.py:758` | Ghi xong trước khi trả lời là đơn giản và đúng |
| Trình trích xuất thấy gì? | Chỉ system prompt + **tin nhắn user**; không có câu trả lời, không có kết quả tool | `agent/_managers.py:30–50` | Giữ nguyên, hoặc cho xem thêm câu trả lời |
| `num_history_runs` không đặt | Mặc định **3** | `agent/agent.py:590–591` | Đặt tường minh |
| Không có `user_id` | Dùng `"default"` → mọi người ẩn danh **chung một memory** | `memory/manager.py` (`user_id = "default"`) | Không đọc/ghi memory khi thiếu `user_id` |
| Model trích xuất memory dùng `http_client` riêng? | Không: `Model.__deepcopy__` đặt `http_client=None` → mất proxy/transport tuỳ chỉnh | `models/base.py:3226` | Tạo model trích xuất riêng, đừng sao chép |

### 2.4 Năm run trên cùng một session

Kịch bản: tool `lookup`, memory bật, `num_history_runs` mặc định 3. "Model thấy" là input của lượt gọi model đầu tiên
trong run.

| Run | User nói | Model thấy (ngoài câu hiện tại) | Memory sau run |
|---|---|---|---|
| 1 | "Tôi là Lan, hay lọc theo Hà Nội" | Không lịch sử; system chỉ nói "có khả năng nhớ" | `Người dùng tên Lan, hay lọc theo Hà Nội` |
| 2 | "Tra KH-0012" | system **có** `<memories_from_previous_interactions>` · run 1 | không đổi |
| 3 | "Còn hạn mức không?" | memory · run 1, run 2 (**gồm cả tool call và kết quả tool**) | không đổi |
| 4 | "Gợi ý cách lọc như mọi khi" | memory · run 1–3 | không đổi |
| 5 | "Khách hàng khu vực tôi" | memory · **run 2–4** (run 1 đã ra khỏi cửa sổ) | không đổi |

Rút ra: câu "còn hạn mức không?" hiểu được nhờ **lịch sử** (kết quả tool của run 2), không nhờ memory. Memory chỉ
giữ điều về người dùng, và sống lâu hơn cửa sổ lịch sử (run 5). Bản LangChain ở mục 4 tái hiện đúng bảng này
(`test_five_runs_match_agno_experiment`).

## 3. Ánh xạ Agno sang LangChain

LangChain 1.x có `create_agent`: dựng sẵn một đồ thị LangGraph gồm nút `model` và nút `tools`, cộng các điểm chen
**middleware**. Một run đi qua các hook theo thứ tự:

```
before_agent → [ before_model → wrap_model_call(gọi model) → after_model → wrap_tool_call(chạy tool) ]* → after_agent
                └─────────────── lặp tới khi model không gọi tool, hoặc middleware cho dừng ───────────────┘
```

| Agno | LangChain / LangGraph | File trong lab | Khác biệt cần nhớ |
|---|---|---|---|
| `Agent(...)` | `create_agent(model, tools, middleware=[...])` | `harness/agent.py` | Tính năng nằm trong middleware, không nằm trong tham số |
| `instructions=fn(run_context)` | `@dynamic_prompt` | `harness/instructions.py` | Chạy trước **mỗi** lần gọi model (Agno: mỗi run) |
| `dependencies` / AG-UI `context` | `context_schema` + `invoke(..., context=...)` | `harness/context.py` | Không lưu vào state |
| `db` (bảng session, runs) | `checkpointer` (InMemorySaver, SqliteSaver, PostgresSaver) | `harness/agent.py` | Lưu **cả thread** thành state, không có khái niệm "run" |
| `session_id` | `config={"configurable": {"thread_id": ...}}` | `harness/run.py` | |
| `add_history_to_context`, `num_history_runs` | tự viết `HistoryWindowMiddleware` | `harness/history.py` | Chỉ cắt phần model thấy; state vẫn giữ đủ |
| `update_memory_on_run`, MemoryManager | `store` + tự viết `UserMemoryMiddleware` | `harness/memory.py` | Không có sẵn; ghi ở `after_agent` |
| `tool_call_limit` | `ToolCallLimitMiddleware(run_limit, exit_behavior)` + `ModelCallLimitMiddleware` | `harness/agent.py` | Có `exit_behavior="end"` — dừng hẳn |
| `external_execution=True` (tool client) | tool gọi `interrupt()`; client trả `Command(resume=...)` | `harness/tools.py` | Resume chạy lại thân tool từ đầu tới `interrupt()` |
| `requires_confirmation=True` | `HumanInTheLoopMiddleware(interrupt_on=...)` | `harness/agent.py` | Quyết định: approve / edit / reject / respond |
| `continue_run` | `invoke(Command(resume=...), cùng thread_id)` | `harness/run.py` | |
| AgentOS + AG-UI | không có sẵn trong lab | — | Phải tự viết server (mục 6) |

## 4. Dựng lại bằng LangChain, từng mảnh

### 4.0 Cài đặt và chạy

Cấu trúc lab:

```
labs/llm-05-trung-cap-harness-langchain/
├── harness/
│   ├── model.py         # model thật + model kịch bản cho test
│   ├── context.py       # ngữ cảnh mỗi run (user_id, sheet, vùng chọn)
│   ├── data.py          # dữ liệu khách hàng giả
│   ├── tools.py         # tool server + tool client (interrupt)
│   ├── instructions.py  # system prompt động
│   ├── history.py       # cửa sổ N run
│   ├── memory.py        # memory dài hạn theo user
│   ├── agent.py         # ráp harness tương đương Agno
│   ├── run.py           # ask / resume / pending
│   └── improved.py      # các lớp cải tiến kiểu Claude Code
├── rules/agent-rules.md # file luật dự án (vai trò như CLAUDE.md)
├── demo.py              # 5 run, in ra model thấy gì
├── eval_golden.py       # bộ đo vàng
├── sync_doc.py          # cập nhật code trong tài liệu này theo file của lab
└── tests/               # test_parity.py, test_improved.py, test_doc_sync.py
```

Chạy toàn bộ test (không đụng tới lockfile của repo):

```bash
uv run --no-project --python 3.13 \
  --with "langchain==1.4.6" --with "langgraph==1.2.16" \
  --with "langgraph-checkpoint-sqlite==3.1.2" --with "langchain-openai==1.7.2" --with pytest \
  python -m pytest labs/llm-05-trung-cap-harness-langchain
```

Chạy demo: cùng các `--with` như trên, thay lệnh cuối bằng `python demo.py` (chạy trong thư mục lab).
Sửa code trong lab xong thì chạy `python labs/llm-05-trung-cap-harness-langchain/sync_doc.py` để tài liệu này
cập nhật theo; `test_doc_sync.py` đỏ nếu quên.

### 4.1 Model

Model thật dùng `ChatOpenAI`; trỏ `base_url` sang vLLM, llama.cpp hoặc Ollama thì chạy được model local (endpoint
local thường chỉ có Chat Completions nên không bật Responses API). Model kịch bản đóng vai `ScriptBrain` của CMB-10:
trả lần lượt các bước định sẵn và **ghi lại mọi thứ nó nhận** — đây là cách ta kiểm harness mà không cần API.

```python
# file: harness/model.py
"""Model cho harness: model thật (OpenAI hoặc endpoint tương thích OpenAI) và model kịch bản để test.

Model kịch bản đóng vai `ScriptBrain` của CMB-10: mỗi lần được gọi trả về bước kế tiếp đã định sẵn và ghi lại
toàn bộ messages + tên tool nó nhận được, để test kiểm tra harness đã đưa gì cho model.
"""

from __future__ import annotations

import uuid
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


def build_model(model: str = "gpt-5-mini", *, base_url: str | None = None, api_key: str | None = None) -> BaseChatModel:
    """Model thật. `base_url` trỏ tới vLLM / llama.cpp / Ollama (đều có API tương thích OpenAI) nếu chạy local.

    Cần `pip install langchain-openai`. Chưa chạy thử với API thật trong lab này (môi trường không có key).
    """
    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {"model": model}
    if base_url:
        kwargs["base_url"] = base_url  # endpoint local thường chỉ có Chat Completions
    else:
        kwargs["use_responses_api"] = True  # OpenAI: Responses API
    if api_key:
        kwargs["api_key"] = api_key
    return ChatOpenAI(**kwargs)


def say(text: str) -> AIMessage:
    """Bước kịch bản: model trả lời bằng chữ, không gọi tool → vòng lặp dừng."""
    return AIMessage(content=text)


def call(name: str, **args: Any) -> AIMessage:
    """Bước kịch bản: model gọi một tool."""
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:12]}"}])


class ScriptedChatModel(BaseChatModel):
    """Model giả: trả lần lượt `steps`, ghi lại input của từng lần gọi."""

    steps: list[AIMessage]
    calls: list[list[BaseMessage]] = Field(default_factory=list)
    bound_tools: list[list[str]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Any, **kwargs: Any) -> ScriptedChatModel:
        self.bound_tools.append([getattr(t, "name", None) or t.get("name", "?") for t in tools])
        return self

    def _generate(self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any):
        self.calls.append(list(messages))
        if len(self.calls) > len(self.steps):
            raise AssertionError(f"Model được gọi lần {len(self.calls)} nhưng kịch bản chỉ có {len(self.steps)} bước")
        step = self.steps[len(self.calls) - 1]
        return ChatResult(generations=[ChatGeneration(message=step.model_copy(deep=True))])
```

### 4.2 Ngữ cảnh của run

Thứ client gửi kèm mỗi lần (người dùng, sheet đang mở, vùng chọn). Truyền bằng `context=`, đọc bằng
`runtime.context`. Nó không vào state nên không bị lưu, không phình lịch sử.

```python
# file: harness/context.py
"""Ngữ cảnh của mỗi run — tương đương `dependencies` / AG-UI `context` của Agno.

Truyền vào `agent.invoke(..., context=AgentContext(...))`. Middleware và tool đọc qua `runtime.context`.
Không nằm trong state nên không bị lưu vào checkpointer.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentContext:
    user_id: str | None = None  # None = chưa đăng nhập → không đọc/ghi memory (Agno dùng "default" chung)
    role: str = "editor"  # "viewer" chỉ được đọc — dùng cho ToolPolicyMiddleware ở phần cải tiến
    sheet: str | None = None
    headers: list[str] = field(default_factory=list)
    selection: str | None = None  # ví dụ "A2:A5"

    def describe(self) -> str:
        if not self.sheet:
            return "(không có workbook đang mở)"
        cols = ", ".join(self.headers) or "(chưa đọc tiêu đề)"
        return f"Sheet: {self.sheet}\nCột: {cols}\nVùng chọn: {self.selection or '(không)'}"
```

### 4.3 Dữ liệu và tool

Tool server là hàm Python có docstring: LangChain đọc type hint + docstring thành JSON schema gửi cho model —
**docstring chính là hướng dẫn sử dụng mà model đọc**, nên viết "khi nào dùng / khi nào không" và trả lỗi kèm gợi ý
bước tiếp.

```python
# file: harness/data.py
"""Dữ liệu khách hàng nhỏ trong bộ nhớ — thay cho API hệ thống của CMB-10."""

from __future__ import annotations

import copy

FIELDS = ("name", "city", "credit_limit", "debt", "status")

SEED = {
    "KH-0012": {
        "name": "Công ty An Phát",
        "city": "Hà Nội",
        "credit_limit": 300_000_000,
        "debt": 120_000_000,
        "status": "Đang giao",
    },
    "KH-0031": {
        "name": "Minh Long",
        "city": "Đà Nẵng",
        "credit_limit": 150_000_000,
        "debt": 20_000_000,
        "status": "Hoàn tất",
    },
    "KH-0047": {
        "name": "Hải Đăng",
        "city": "Hà Nội",
        "credit_limit": 80_000_000,
        "debt": 79_000_000,
        "status": "Đang giao",
    },
}


class CustomerDB:
    def __init__(self, rows: dict[str, dict] | None = None) -> None:
        self.rows = copy.deepcopy(rows if rows is not None else SEED)
        self.writes: list[tuple[str, str, str]] = []

    def search(self, query: str) -> list[dict]:
        q = query.strip().lower()
        return [
            {"id": cid, **row}
            for cid, row in self.rows.items()
            if q in cid.lower() or q in row["name"].lower() or q in row["city"].lower()
        ]

    def get(self, customer_id: str) -> dict | None:
        row = self.rows.get(customer_id)
        return {"id": customer_id, **row} if row else None

    def update(self, customer_id: str, field: str, value: str) -> None:
        if customer_id not in self.rows:
            raise KeyError(f"không có khách hàng {customer_id}")
        if field not in FIELDS:
            raise KeyError(f"không có trường '{field}'")
        current = self.rows[customer_id][field]
        self.rows[customer_id][field] = int(value) if isinstance(current, int) else value
        self.writes.append((customer_id, field, value))
```

Tool client (frontend tool) dùng `interrupt()`. Đây là chỗ khác Agno nhiều nhất về cơ chế:

| | Agno `external_execution` | LangGraph `interrupt()` |
|---|---|---|
| Dừng ở đâu | Harness thấy cờ trên tool, không gọi hàm | Hàm tool **được gọi**, dừng ở dòng `interrupt()` |
| Trạng thái lưu ở | DB của Agno (bảng runs) | Checkpointer, theo `thread_id` |
| Chạy tiếp | `continue_run` với kết quả | `invoke(Command(resume=kết_quả))` cùng `thread_id` |
| Khi chạy tiếp | Chèn kết quả, gọi model | Chạy lại thân tool từ đầu, `interrupt()` trả về kết quả |
| Tool khác chạy song song cùng lượt | — | **Không** chạy lại (đã đo) |

Hệ quả: không đặt side effect (ghi log, gọi API) **trước** `interrupt()` trong tool client.

```python
# file: harness/tools.py
"""Tool của agent.

- Tool server: chạy trong tiến trình agent (tương đương tool trong `tools=[...]` của Agno).
- Tool client (frontend tool): agent chỉ khai báo; thân tool gọi `interrupt()` để dừng run, client (add-in Excel)
  chạy thật rồi gửi kết quả về bằng `Command(resume=...)`. Tương đương `external_execution=True` của Agno.

Lưu ý khi resume: LangGraph chạy lại thân tool client từ đầu tới `interrupt()` (tool server chạy song song thì
không chạy lại). Vì vậy không đặt side effect trước `interrupt()`.
"""

from __future__ import annotations

import json
from typing import Any

from langchain.tools import BaseTool, ToolRuntime, tool
from langgraph.types import interrupt

from harness.data import FIELDS, CustomerDB


def make_server_tools(db: CustomerDB) -> list[BaseTool]:
    @tool
    def search_customers(query: str) -> str:
        """Tìm khách hàng theo mã (KH-0012), tên hoặc thành phố.

        Dùng khi người dùng hỏi về một khách hàng hoặc một nhóm khách hàng cụ thể.
        Không dùng khi câu hỏi đã có đủ dữ liệu trong lịch sử hội thoại.
        """
        rows = db.search(query)
        if not rows:
            return f"Không thấy khách hàng khớp '{query}'. Thử mã dạng KH-0012, một phần tên, hoặc tên thành phố."
        return json.dumps(rows, ensure_ascii=False)

    @tool
    def update_customer(customer_id: str, field: str, value: str) -> str:
        """Cập nhật MỘT trường của MỘT khách hàng trong hệ thống.

        Chỉ dùng sau khi đã tìm thấy đúng khách hàng bằng search_customers.
        field là một trong: name, city, credit_limit, debt, status.
        """
        try:
            db.update(customer_id, field, value)
        except KeyError as exc:
            fields = ", ".join(FIELDS)
            return f"Không cập nhật được: {exc}. Trường hợp lệ: {fields}. Kiểm tra lại mã bằng search_customers."
        return f"Đã cập nhật {customer_id}.{field} = {value}"

    return [search_customers, update_customer]


def _client_call(runtime: ToolRuntime, name: str, args: dict[str, Any]) -> str:
    """Dừng run, chờ client chạy tool. Giá trị resume được trả về cho model như kết quả tool."""
    result = interrupt({"type": "client_tool", "name": name, "args": args, "tool_call_id": runtime.tool_call_id})
    return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)


@tool
def excel_read_rows(rows: list[int], runtime: ToolRuntime) -> str:
    """Đọc các dòng (số dòng Excel, bắt đầu từ 2) trên sheet đang mở. Chạy trong add-in."""
    return _client_call(runtime, "excel_read_rows", {"rows": rows})


@tool
def excel_set_values(cells: dict[str, str], runtime: ToolRuntime) -> str:
    """Ghi giá trị vào ô trên sheet đang mở, ví dụ {"E2": "Hoàn tất"}. Chạy trong add-in, người dùng xác nhận trước."""
    return _client_call(runtime, "excel_set_values", {"cells": cells})


CLIENT_TOOLS: list[BaseTool] = [excel_read_rows, excel_set_values]
```

### 4.4 Instructions động

`@dynamic_prompt` biến một hàm thành middleware đặt system prompt trước mỗi lần gọi model. Ở đây nó đưa ngữ cảnh
sheet vào prompt, giống hàm `instructions(run_context)` của CMB-10.

```python
# file: harness/instructions.py
"""Instructions động — tương đương `instructions=async fn(run_context)` của Agno.

`@dynamic_prompt` chạy trước MỖI lần gọi model và đặt system prompt. Đọc dữ liệu mới (ngữ cảnh UI) mỗi lần.
"""

from __future__ import annotations

from langchain.agents.middleware import ModelRequest, dynamic_prompt

from harness.context import AgentContext

INSTRUCTIONS = """Bạn là trợ lý dữ liệu khách hàng chạy trong Excel.

Luật:
- Tra cứu bằng search_customers trước khi trả lời về một khách hàng. Không bịa mã hay số liệu.
- Trước khi ghi (update_customer, excel_set_values), đọc lại dữ liệu hiện tại.
- Thiếu thông tin để ghi thì hỏi lại một câu ngắn, không đoán.
- Trả lời ngắn, nêu rõ đã thay đổi gì.

Ngữ cảnh giao diện:
{ui}"""


@dynamic_prompt
def instructions(request: ModelRequest) -> str:
    ctx = request.runtime.context
    ui = ctx.describe() if isinstance(ctx, AgentContext) else "(không có)"
    return INSTRUCTIONS.format(ui=ui)
```

### 4.5 Lịch sử N run

LangGraph lưu cả thread trong state và mặc định đưa **toàn bộ** cho model. Để giống Agno, middleware này cắt phần
model thấy còn N run trước + run hiện tại, ranh giới run là `HumanMessage`. State không bị cắt — thread dài vẫn
phình; xử lý bằng `SummarizationMiddleware` (mục 5).

```python
# file: harness/history.py
"""Cửa sổ lịch sử theo số run — tương đương `add_history_to_context` + `num_history_runs` của Agno.

Khác biệt cần nhớ:
- Agno lưu từng run thành một dòng DB rồi lấy N run gần nhất. LangGraph lưu CẢ thread trong state (checkpointer),
  nên ở đây ta chỉ cắt phần MODEL NHÌN THẤY; state vẫn giữ đủ. Muốn state không phình, thêm SummarizationMiddleware.
- "Một run" = từ một HumanMessage tới trước HumanMessage kế tiếp (gồm tool call, kết quả tool, câu trả lời).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import AnyMessage, HumanMessage


def window(messages: list[AnyMessage], num_history_runs: int) -> list[AnyMessage]:
    """Giữ N run trước + run hiện tại (run hiện tại bắt đầu ở HumanMessage cuối)."""
    starts = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
    if len(starts) <= num_history_runs + 1:
        return messages
    return messages[starts[-(num_history_runs + 1)] :]


class HistoryWindowMiddleware(AgentMiddleware):
    def __init__(self, num_history_runs: int = 3) -> None:  # Agno mặc định 3
        super().__init__()
        self.num_history_runs = num_history_runs

    def _prepare(self, request: ModelRequest) -> ModelRequest:
        return request.override(messages=window(request.messages, self.num_history_runs))

    def wrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:
        return handler(self._prepare(request))

    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Awaitable[ModelResponse]]
    ) -> ModelResponse:
        return await handler(self._prepare(request))
```

### 4.6 Memory dài hạn

LangChain không có trình trích xuất memory sẵn như Agno, nên tự viết, và cố ý sửa hai chỗ yếu đã đo ở mục 2.3:
thiếu `user_id` thì bỏ qua, và model trích xuất là model riêng truyền vào (không sao chép model chính).

- **Đọc:** `wrap_model_call` lấy memory của `user_id` trong `store`, nối vào cuối system prompt.
- **Ghi:** `after_agent` (chạy một lần khi run kết thúc) gọi một agent nhỏ có ba tool add/update/delete.

Khác Agno về thời điểm: Agno trích xuất song song với lượt model chính; ở đây trích xuất sau cùng, tuần tự, nên run
dài thêm đúng thời gian trích xuất. Run đang tạm dừng (chờ client) thì chưa ghi; ghi khi run chạy tiếp và kết thúc.

```python
# file: harness/memory.py
"""Memory dài hạn theo user — tương đương `update_memory_on_run` + `add_memories_to_context` của Agno.

Hai nửa:
1. Đọc (mỗi lần gọi model): lấy memory của `user_id` từ store, nối vào cuối system prompt — giống Agno.
2. Ghi (một lần, khi run kết thúc — hook `after_agent`): chạy một agent nhỏ có tool add/update/delete_memory,
   đọc tin nhắn user của run vừa xong và quyết định ghi gì — giống MemoryManager của Agno.

Khác Agno, có chủ ý:
- `user_id` là None → không đọc, không ghi (Agno gom mọi người ẩn danh vào user "default").
- Ghi ở cuối run, tuần tự (Agno chạy song song với lượt model chính rồi chờ). Run bị interrupt thì chưa ghi;
  ghi khi run được resume và kết thúc.
- `include_assistant=True` cho trình trích xuất thấy cả câu trả lời cuối (Agno chỉ thấy tin nhắn user).
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse, ToolCallLimitMiddleware
from langchain.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore

MEMORY_PROMPT = """Bạn quản lý trí nhớ dài hạn về NGƯỜI DÙNG (không phải dữ liệu nghiệp vụ).
Đọc đoạn hội thoại và quyết định:
- add_memory: thêm thông tin ổn định, có ích về người dùng (tên, vai trò, khu vực phụ trách, cách làm việc quen).
- update_memory: sửa một memory đã có khi thông tin mới thay đổi nó.
- delete_memory: xóa memory sai, hoặc khi người dùng yêu cầu quên.
KHÔNG lưu: số liệu khách hàng, mã giao dịch, kết quả tra cứu, yêu cầu tạm thời.
Không có gì đáng nhớ thì trả lời "không có" và không gọi tool.

<existing_memories>
{existing}
</existing_memories>"""

CONTEXT_BLOCK = """Thông tin về người dùng từ các lần trước.
Nếu mâu thuẫn, ưu tiên thông tin trong cuộc trò chuyện hiện tại.
<memories_from_previous_interactions>
{items}
</memories_from_previous_interactions>"""

MAX_MEMORIES = 100  # store.search mặc định chỉ trả 10


def _user_id(runtime: Any) -> str | None:
    return getattr(runtime.context, "user_id", None)


def _text(message: AnyMessage | None) -> str:
    return message.text if message is not None else ""


class UserMemoryMiddleware(AgentMiddleware):
    def __init__(
        self,
        extractor_model: BaseChatModel,
        *,
        inject: bool = True,
        extract: bool = True,
        include_assistant: bool = False,
        namespace: str = "memories",
    ) -> None:
        super().__init__()
        self.extractor_model = extractor_model
        self.inject, self.extract, self.include_assistant = inject, extract, include_assistant
        self.namespace = namespace

    def ns(self, user_id: str) -> tuple[str, str]:
        return (self.namespace, user_id)

    def list(self, store: BaseStore, user_id: str) -> list[Any]:
        return store.search(self.ns(user_id), limit=MAX_MEMORIES)

    # ---------- 1. Đọc: nối memory vào system prompt trước mỗi lần gọi model ----------
    def _prepare(self, request: ModelRequest) -> ModelRequest:
        user_id, store = _user_id(request.runtime), request.runtime.store
        if not (self.inject and user_id and store):
            return request
        items = self.list(store, user_id)
        if not items:
            return request
        block = CONTEXT_BLOCK.format(items="\n".join(f"- {it.value['memory']}" for it in items))
        base = _text(request.system_message)
        return request.override(system_message=SystemMessage(content=f"{base}\n\n{block}" if base else block))

    def wrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:
        return handler(self._prepare(request))

    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Awaitable[ModelResponse]]
    ) -> ModelResponse:
        return await handler(self._prepare(request))

    # ---------- 2. Ghi: khi run kết thúc ----------
    def extraction_input(self, messages: list[AnyMessage]) -> HumanMessage | None:
        starts = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
        if not starts:
            return None
        run = messages[starts[-1] :]
        lines = [f"Người dùng: {_text(run[0])}"]
        if self.include_assistant:
            final = next((m for m in reversed(run) if isinstance(m, AIMessage) and not m.tool_calls), None)
            if final is not None:
                lines.append(f"Trợ lý: {_text(final)}")
        return HumanMessage(content="\n".join(lines))

    def extractor(self, store: BaseStore, user_id: str):
        ns = self.ns(user_id)

        @tool
        def add_memory(memory: str, topics: list[str] | None = None) -> str:
            """Thêm một memory mới về người dùng."""
            key = uuid.uuid4().hex[:8]
            store.put(ns, key, {"memory": memory, "topics": topics or []})
            return f"Đã thêm memory {key}"

        @tool
        def update_memory(memory_id: str, memory: str) -> str:
            """Sửa nội dung một memory đã có (theo ID trong existing_memories)."""
            old = store.get(ns, memory_id)
            if old is None:
                return f"Không có memory {memory_id}. Dùng add_memory nếu là thông tin mới."
            store.put(ns, memory_id, {**old.value, "memory": memory})
            return f"Đã sửa memory {memory_id}"

        @tool
        def delete_memory(memory_id: str) -> str:
            """Xóa một memory (theo ID trong existing_memories)."""
            store.delete(ns, memory_id)
            return f"Đã xóa memory {memory_id}"

        existing = "\n".join(f"ID: {it.key} | {it.value['memory']}" for it in self.list(store, user_id)) or "(chưa có)"
        return create_agent(
            self.extractor_model,
            tools=[add_memory, update_memory, delete_memory],
            system_prompt=MEMORY_PROMPT.format(existing=existing),
            middleware=[ToolCallLimitMiddleware(run_limit=5, exit_behavior="end")],
            checkpointer=False,  # không lưu hội thoại của trình trích xuất vào checkpointer của agent chính
            name="memory-extractor",
        )

    def _job(self, state: dict[str, Any], runtime: Runtime) -> tuple[Any, HumanMessage] | None:
        user_id, store = _user_id(runtime), runtime.store
        if not (self.extract and user_id and store):
            return None
        message = self.extraction_input(state["messages"])
        return (self.extractor(store, user_id), message) if message is not None else None

    def after_agent(self, state: dict[str, Any], runtime: Runtime) -> dict[str, Any] | None:
        job = self._job(state, runtime)
        if job:
            job[0].invoke({"messages": [job[1]]})
        return None

    async def aafter_agent(self, state: dict[str, Any], runtime: Runtime) -> dict[str, Any] | None:
        job = self._job(state, runtime)
        if job:
            await job[0].ainvoke({"messages": [job[1]]})
        return None
```

### 4.7 Giới hạn, người duyệt, ráp lại

**Thứ tự middleware có ý nghĩa.** Với `wrap_model_call`, middleware đứng trước là lớp ngoài: nó nhận request trước
và chuyển request đã sửa vào trong. `instructions` (đặt system prompt) phải đứng **trước** memory và mọi thứ nối
thêm vào system prompt — đứng sau thì nó ghi đè mất phần đã nối.

```python
# file: harness/agent.py
"""Ráp harness: model + tools + instructions + lịch sử + memory + giới hạn + người duyệt.

Thứ tự middleware quan trọng: với wrap_model_call, middleware ĐỨNG TRƯỚC là lớp NGOÀI và chạy trước.
`instructions` (đặt system prompt) phải đứng trước mọi middleware nối thêm vào system prompt (memory, rules, ...).
"""

from __future__ import annotations

from collections.abc import Sequence

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    HumanInTheLoopMiddleware,
    ModelCallLimitMiddleware,
    ToolCallLimitMiddleware,
)
from langchain.tools import BaseTool
from langchain_core.language_models import BaseChatModel
from langgraph.store.base import BaseStore
from langgraph.types import Checkpointer

from harness.context import AgentContext
from harness.data import CustomerDB
from harness.history import HistoryWindowMiddleware
from harness.instructions import instructions
from harness.memory import UserMemoryMiddleware
from harness.tools import CLIENT_TOOLS, make_server_tools


def build_agent(
    model: BaseChatModel,
    *,
    db: CustomerDB,
    checkpointer: Checkpointer,
    store: BaseStore | None = None,
    memory_model: BaseChatModel | None = None,
    num_history_runs: int = 3,
    tool_call_limit: int = 8,
    model_call_limit: int = 15,
    limit_exit: str = "end",
    approve_writes: bool = True,
    client_tools: bool = True,
    extra_tools: Sequence[BaseTool] = (),
    extra_middleware: Sequence[AgentMiddleware] = (),
):
    tools = [*make_server_tools(db), *(CLIENT_TOOLS if client_tools else []), *extra_tools]
    middleware: list[AgentMiddleware] = [
        # Agno: tool_call_limit chỉ chặn từng lượt gọi, vòng lặp vẫn chạy. Ở đây dừng hẳn ("end") và có thêm trần
        # số lượt gọi model — guard mà Agno không có.
        ModelCallLimitMiddleware(run_limit=model_call_limit, exit_behavior="end"),
        ToolCallLimitMiddleware(run_limit=tool_call_limit, exit_behavior=limit_exit),
        instructions,
        HistoryWindowMiddleware(num_history_runs),
    ]
    if memory_model is not None:
        middleware.append(UserMemoryMiddleware(memory_model))
    if approve_writes:
        # Agno: requires_confirmation=True trên tool
        middleware.append(
            HumanInTheLoopMiddleware(interrupt_on={"update_customer": {"allowed_decisions": ["approve", "reject"]}})
        )
    middleware.extend(extra_middleware)
    return create_agent(
        model,
        tools=tools,
        middleware=middleware,
        context_schema=AgentContext,
        checkpointer=checkpointer,
        store=store,
        name="excel-agent",
    )
```

### 4.8 Gọi agent: một request đi từ client vào

```python
# file: harness/run.py
"""Gọi agent như một server sẽ gọi: một tin nhắn mới, hoặc chạy tiếp run đang tạm dừng."""

from __future__ import annotations

from typing import Any

from langgraph.types import Command

from harness.context import AgentContext


def ask(agent: Any, text: str, *, thread: str = "t1", ctx: AgentContext | None = None) -> dict[str, Any]:
    """Một run mới trên thread. `thread` = threadId của AG-UI = session_id của Agno."""
    return agent.invoke(
        {"messages": [{"role": "user", "content": text}]},
        {"configurable": {"thread_id": thread}},
        context=ctx or AgentContext(user_id="u1"),
    )


def resume(agent: Any, value: Any, *, thread: str = "t1", ctx: AgentContext | None = None) -> dict[str, Any]:
    """Chạy tiếp run đang dừng ở interrupt(): kết quả tool client, hoặc quyết định duyệt {"decisions": [...]}."""
    return agent.invoke(
        Command(resume=value), {"configurable": {"thread_id": thread}}, context=ctx or AgentContext(user_id="u1")
    )


def pending(out: dict[str, Any]) -> list[Any]:
    """Các interrupt đang chờ (rỗng = run đã kết thúc)."""
    return [i.value for i in out.get("__interrupt__", [])]
```

Vòng đời một request từ add-in, với tool client và người duyệt:

```python
out = ask(agent, "Đổi trạng thái KH-0012 thành Hoàn tất", thread=thread_id, ctx=ctx)
while waiting := pending(out):
    request = waiting[0]
    if request.get("type") == "client_tool":  # tool client: add-in chạy Office.js
        value = run_in_excel(request["name"], request["args"])
    else:  # HumanInTheLoopMiddleware: hỏi người dùng
        value = {"decisions": [ask_user_to_approve(request["action_requests"])]}
    out = resume(agent, value, thread=thread_id, ctx=ctx)
answer = out["messages"][-1].text
```

`run_in_excel` và `ask_user_to_approve` là phía client, không có trong lab. Khi có **nhiều** interrupt cùng lúc
(model gọi song song hai tool client), LangGraph cần resume theo id của từng interrupt
(`Command(resume={interrupt.id: value, ...})`) — lab chưa có test cho trường hợp này.

### 4.9 Kiểm chứng: tái hiện thí nghiệm trên Agno

| Test | Chứng minh |
|---|---|
| `test_tool_limit_continue_behaves_like_agno` | `exit_behavior="continue"`: 2 tool chạy, model 9 lượt — giống hệt Agno |
| `test_tool_limit_end_stops_the_loop` | `exit_behavior="end"`: dừng ở lượt thứ 3 |
| `test_model_call_limit_caps_runaway_loop` | Trần số lượt model — Agno không có |
| `test_history_window_default_three_runs`, `..._two_runs` | Cửa sổ 3 / 2 run, đúng như Agno |
| `test_memory_written_at_end_of_run_and_injected_next_run` | Memory ghi xong khi run trả về; trích xuất chỉ thấy tin user; run sau thấy memory |
| `test_memory_skipped_without_user_id` | Thiếu `user_id` thì không ghi (Agno ghi vào "default") |
| `test_five_runs_match_agno_experiment` | Bảng 5 run ở mục 2.4 |
| `test_client_tool_pauses_and_resumes` | Tool client dừng, client trả kết quả, chạy tiếp |
| `test_write_needs_approval_then_approve_or_reject` | Duyệt thì ghi, từ chối thì không ghi và model nhận lý do |
| `test_async_invoke_runs_same_middlewares` | `ainvoke` (server AG-UI chạy async) đi qua đúng các middleware |
| `test_sqlite_checkpointer_survives_restart` | Tắt tiến trình, mở lại vẫn còn lịch sử |

```python
# file: tests/test_parity.py
"""Harness LangChain tái hiện đúng hành vi đã đo trên Agno 3.1.3 (và chỗ cố ý khác)."""

from __future__ import annotations

import asyncio

from harness.agent import build_agent
from harness.context import AgentContext
from harness.data import CustomerDB
from harness.model import ScriptedChatModel, call, say
from harness.run import ask, pending, resume
from langchain.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore


def counting_echo():
    counter = {"n": 0}

    @tool
    def echo(x: str) -> str:
        """Trả lại x."""
        counter["n"] += 1
        return f"echo:{x}"

    return echo, counter


def agent_with(model, **kwargs):
    kwargs.setdefault("db", CustomerDB())
    kwargs.setdefault("checkpointer", InMemorySaver())
    return build_agent(model, **kwargs)


# ---------------------------------------------------------------- Thí nghiệm 1: giới hạn tool
def test_tool_limit_continue_behaves_like_agno():
    """exit_behavior="continue": vượt giới hạn chỉ trả lỗi cho từng lượt, vòng lặp chạy tới khi model ngừng."""
    echo, counter = counting_echo()
    model = ScriptedChatModel(steps=[call("echo", x=str(i)) for i in range(8)] + [say("xong")])
    agent = agent_with(model, extra_tools=[echo], tool_call_limit=2, limit_exit="continue", model_call_limit=50)
    out = ask(agent, "thử")
    assert counter["n"] == 2
    assert len(model.calls) == 9  # đúng như Agno: 8 lượt gọi tool + 1 lượt trả lời
    assert out["messages"][-1].content == "xong"


def test_tool_limit_end_stops_the_loop():
    """exit_behavior="end": dừng ngay ở lượt vượt giới hạn — guard mà Agno không có."""
    echo, counter = counting_echo()
    model = ScriptedChatModel(steps=[call("echo", x=str(i)) for i in range(8)] + [say("xong")])
    agent = agent_with(model, extra_tools=[echo], tool_call_limit=2, limit_exit="end")
    out = ask(agent, "thử")
    assert counter["n"] == 2
    assert len(model.calls) == 3
    assert isinstance(out["messages"][-1], AIMessage) and not out["messages"][-1].tool_calls


def test_model_call_limit_caps_runaway_loop():
    echo, _ = counting_echo()
    model = ScriptedChatModel(steps=[call("echo", x=str(i)) for i in range(20)])
    agent = agent_with(model, extra_tools=[echo], tool_call_limit=100, model_call_limit=4)
    ask(agent, "thử")
    assert len(model.calls) == 4


# ---------------------------------------------------------------- Thí nghiệm 3: cửa sổ lịch sử
def humans_seen(call_messages) -> list[str]:
    return [m.text for m in call_messages if isinstance(m, HumanMessage)]


def test_history_window_default_three_runs(thread):
    model = ScriptedChatModel(steps=[say(f"trả lời {i}") for i in range(5)])
    agent = agent_with(model)  # num_history_runs mặc định 3, giống Agno
    for i in range(5):
        ask(agent, f"câu hỏi {i}", thread=thread)
    assert humans_seen(model.calls[-1]) == ["câu hỏi 1", "câu hỏi 2", "câu hỏi 3", "câu hỏi 4"]


def test_history_window_two_runs(thread):
    model = ScriptedChatModel(steps=[say(f"trả lời {i}") for i in range(5)])
    agent = agent_with(model, num_history_runs=2)
    for i in range(5):
        ask(agent, f"câu hỏi {i}", thread=thread)
    assert humans_seen(model.calls[-1]) == ["câu hỏi 2", "câu hỏi 3", "câu hỏi 4"]


# ---------------------------------------------------------------- Thí nghiệm 2 + 5 run: memory
def memory_agent(main_steps, memory_steps, **kwargs):
    main, memory, store = ScriptedChatModel(steps=main_steps), ScriptedChatModel(steps=memory_steps), InMemoryStore()
    agent = agent_with(main, store=store, memory_model=memory, **kwargs)
    return agent, main, memory, store


def memories(store, user_id="u1"):
    return [it.value["memory"] for it in store.search(("memories", user_id))]


def test_memory_written_at_end_of_run_and_injected_next_run(thread):
    agent, main, memory, store = memory_agent(
        [say("Đã ghi nhận."), say("Chào Lan.")],
        [call("add_memory", memory="Tên Lan, hay lọc theo Hà Nội"), say("ok"), say("không có")],
    )
    ask(agent, "Tôi là Lan, hay lọc theo Hà Nội", thread=thread)
    assert memories(store) == ["Tên Lan, hay lọc theo Hà Nội"]  # đã có ngay khi invoke trả về
    # Trình trích xuất chỉ thấy system + tin nhắn user, giống Agno
    extractor_input = memory.calls[0]
    assert [type(m) for m in extractor_input] == [SystemMessage, HumanMessage]
    assert extractor_input[1].text == "Người dùng: Tôi là Lan, hay lọc theo Hà Nội"

    ask(agent, "Chào", thread=thread)
    assert "memories_from_previous_interactions" not in main.calls[0][0].text  # run 1: chưa có memory
    assert "Tên Lan, hay lọc theo Hà Nội" in main.calls[1][0].text  # run 2: memory ở cuối system prompt


def test_memory_skipped_without_user_id(thread):
    agent, _, memory, store = memory_agent([say("Chào.")], [])
    ask(agent, "Tôi là Lan", thread=thread, ctx=AgentContext(user_id=None))
    assert memory.calls == [] and store.search(("memories",)) == []  # Agno sẽ ghi vào user "default"


def test_five_runs_match_agno_experiment(thread):
    agent, main, _, store = memory_agent(
        [
            say("Đã ghi nhận, Lan."),
            call("search_customers", query="KH-0012"),
            say("KH-0012 còn 180 triệu."),
            say("Còn 180 triệu."),
            say("Lọc theo Hà Nội."),
            say("KH-0012, KH-0047."),
        ],
        [call("add_memory", memory="Tên Lan, hay lọc theo Hà Nội"), say("ok")] + [say("không có")] * 4,
    )
    questions = [
        "Tôi là Lan, hay lọc theo Hà Nội",
        "Tra KH-0012",
        "Còn hạn mức không?",
        "Lọc như mọi khi",
        "Khách hàng khu vực tôi",
    ]
    seen = []
    for q in questions:
        before = len(main.calls)
        ask(agent, q, thread=thread)
        seen.append(main.calls[before])  # lượt model đầu tiên của mỗi run
    has_memory = ["memories_from_previous" in s[0].text for s in seen]
    assert has_memory == [False, True, True, True, True]
    assert humans_seen(seen[2]) == questions[:3]  # run 3 thấy run 1–2
    assert any(isinstance(m, ToolMessage) and "KH-0012" in m.text for m in seen[2])  # kết quả tool run 2 vẫn còn
    assert humans_seen(seen[4]) == questions[1:5]  # run 5: run 1 đã ra khỏi cửa sổ...
    assert memories(store) == ["Tên Lan, hay lọc theo Hà Nội"]  # ...nhưng memory vẫn giữ điều Lan nói ở run 1


# ---------------------------------------------------------------- Tạm dừng / chạy tiếp
def test_client_tool_pauses_and_resumes(thread):
    model = ScriptedChatModel(steps=[call("excel_read_rows", rows=[2, 3]), say("Dòng 2 là KH-0012.")])
    agent = agent_with(model)
    out = ask(agent, "Đọc dòng 2-3", thread=thread)
    (waiting,) = pending(out)
    assert waiting["type"] == "client_tool"
    assert waiting["name"] == "excel_read_rows" and waiting["args"] == {"rows": [2, 3]}
    # Client (add-in) chạy Office.js rồi gửi kết quả về
    out = resume(agent, {"2": ["KH-0012", "An Phát"]}, thread=thread)
    tool_msg = next(m for m in out["messages"] if isinstance(m, ToolMessage))
    assert tool_msg.text == '{"2": ["KH-0012", "An Phát"]}'
    assert out["messages"][-1].content == "Dòng 2 là KH-0012."


def test_write_needs_approval_then_approve_or_reject(thread):
    db = CustomerDB()
    model = ScriptedChatModel(
        steps=[
            call("update_customer", customer_id="KH-0012", field="status", value="Hoàn tất"),
            say("Đã cập nhật."),
            call("update_customer", customer_id="KH-0031", field="status", value="Tạm dừng"),
            say("Đã huỷ."),
        ]
    )
    agent = agent_with(model, db=db)
    out = ask(agent, "Đổi KH-0012 thành Hoàn tất", thread=thread)
    (request,) = pending(out)
    assert request["action_requests"][0]["name"] == "update_customer"
    assert db.writes == []  # chưa duyệt thì chưa ghi
    resume(agent, {"decisions": [{"type": "approve"}]}, thread=thread)
    assert db.writes == [("KH-0012", "status", "Hoàn tất")]

    ask(agent, "Đổi KH-0031 thành Tạm dừng", thread=thread)
    out = resume(agent, {"decisions": [{"type": "reject", "message": "Không đổi"}]}, thread=thread)
    assert db.writes == [("KH-0012", "status", "Hoàn tất")]
    assert any(isinstance(m, ToolMessage) and "Không đổi" in m.text for m in out["messages"])


# ---------------------------------------------------------------- Async + lưu bền
def test_async_invoke_runs_same_middlewares(thread):
    agent, main, _, store = memory_agent(
        [say("Đã ghi nhận."), say("Chào Lan.")], [call("add_memory", memory="Tên Lan"), say("ok"), say("không có")]
    )

    async def scenario():
        for text in ["Tôi là Lan", "Chào"]:
            await agent.ainvoke(
                {"messages": [{"role": "user", "content": text}]},
                {"configurable": {"thread_id": thread}},
                context=AgentContext(user_id="u1"),
            )

    asyncio.run(scenario())
    assert memories(store) == ["Tên Lan"]
    assert "Tên Lan" in main.calls[1][0].text


def test_sqlite_checkpointer_survives_restart(tmp_path, thread):
    path = str(tmp_path / "threads.db")
    with SqliteSaver.from_conn_string(path) as saver:
        agent_with(ScriptedChatModel(steps=[say("Đã ghi nhận.")]), checkpointer=saver).invoke(
            {"messages": [{"role": "user", "content": "Tôi là Lan"}]},
            {"configurable": {"thread_id": thread}},
            context=AgentContext(user_id="u1"),
        )
    model = ScriptedChatModel(steps=[say("Bạn là Lan.")])
    with SqliteSaver.from_conn_string(path) as saver:  # "khởi động lại" tiến trình
        agent_with(model, checkpointer=saver).invoke(
            {"messages": [{"role": "user", "content": "Tôi là ai?"}]},
            {"configurable": {"thread_id": thread}},
            context=AgentContext(user_id="u1"),
        )
    assert humans_seen(model.calls[0]) == ["Tôi là Lan", "Tôi là ai?"]
```

### 4.10 Lưu bền khi chạy thật

Lab dùng `InMemorySaver` / `InMemoryStore` (mất khi tắt) và có test `SqliteSaver`. Production dùng Postgres cho cả
hai — **đoạn dưới chưa chạy thử trong lab**:

```python
# pip install langgraph-checkpoint-postgres
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore

with PostgresSaver.from_conn_string(DB_URI) as saver, PostgresStore.from_conn_string(DB_URI) as store:
    saver.setup()  # tạo bảng lần đầu
    store.setup()
    agent = build_agent(model, db=db, checkpointer=saver, store=store, memory_model=memory_model)
```

## 5. Cải tiến harness theo Claude Code

Claude Code không thông minh hơn nhờ một cơ chế bí mật, mà nhờ harness: đưa **đúng** ngữ cảnh vào **đúng** lúc,
buộc **kiểm chứng**, chặn **thao tác mù**, và giữ ngữ cảnh **gọn**. Mỗi ý dưới đây thành một middleware độc lập,
bật/tắt riêng, có test.

### 5.1 Tám lớp

| # | Claude Code làm gì | Vì sao giúp | Middleware | Test |
|---|---|---|---|---|
| 1 | `CLAUDE.md` nạp mỗi session | Luật dự án do người viết, đáng tin hơn memory do model tự trích | `RulesFileMiddleware` | `test_rules_file_is_appended_and_reloaded` |
| 2 | `Edit` chỉ chạy khi file đã `Read` và chưa đổi từ lúc đọc | Chặn ghi theo trí nhớ sai, chặn ghi đè thay đổi của người khác | `ReadBeforeWriteMiddleware` | `test_write_without_read_is_blocked`, `test_write_blocked_when_data_changed_after_read` |
| 3 | Chạy test sau khi sửa | Model thấy ngay khi kết quả sai, sửa trong cùng run | `VerifyAfterWriteMiddleware` | `test_write_after_read_is_allowed_and_verified`, `test_verify_after_write_catches_silent_failure` |
| 4 | `<system-reminder>` chèn vào lượt user | Nhắc trạng thái mà không đổi phần đầu ngữ cảnh (prompt cache vẫn trúng) | `ReminderMiddleware` | `test_reminder_is_sent_to_model_but_not_stored` |
| 5 | Permission rules, chế độ quyền | Chặn bằng code, không trông vào model "tự giác" | `ToolPolicyMiddleware` + `HumanInTheLoopMiddleware` | `test_viewer_cannot_write` |
| 6 | Subagent: ngữ cảnh riêng, chỉ trả kết quả | Việc tra cứu nhiều bước không làm bẩn ngữ cảnh chính | `make_subagent_tool` | `test_subagent_returns_only_its_final_answer` |
| 7 | Danh sách việc | Giữ mục tiêu qua nhiều bước | `TodoListMiddleware` (có sẵn) | `test_todo_middleware_adds_write_todos_tool` |
| 8 | Tóm tắt khi dài, xoá kết quả tool cũ | Kết quả tool chiếm nhiều token nhất; ngữ cảnh dài làm model kém đi | `SummarizationMiddleware`, `ContextEditingMiddleware` (có sẵn) | `test_summarization_replaces_old_turns`, `test_context_editing_clears_old_tool_results` |

Thêm một lớp không phải middleware nhưng quan trọng nhất: **bộ đo vàng** (mục 5.4). Không có nó thì không biết thay
đổi nào làm agent tốt lên.

### 5.2 Chi tiết từng lớp

**1. File luật.** Nối `rules/agent-rules.md` vào cuối system prompt trong thẻ `<project_rules>`; đọc lại khi file
đổi (theo mtime), nên người nghiệp vụ sửa luật là agent theo ngay, không cần deploy. Khác memory: luật do người viết
và review, memory do model tự trích từ hội thoại.

**2. Đọc trước khi ghi.** Middleware giữ trong state một bảng `read_versions` (khóa bản ghi → dấu vân tay dữ liệu lúc
đọc). Tool đọc chạy xong thì ghi dấu vân tay; tool ghi chỉ được chạy khi khóa đã có và dấu vân tay **vẫn khớp** dữ
liệu hiện tại. Bị chặn thì model nhận `ToolMessage` lỗi kèm hướng dẫn ("Đọc lại rồi mới ghi") và tự sửa ở lượt sau.
State có reducer gộp dict, nên các tool đọc chạy song song không ghi đè nhau. Vì nằm trong state, bảng này được
checkpointer lưu cùng thread.

Lưu ý thứ tự: `HumanInTheLoopMiddleware` hỏi người duyệt ở `after_model`, **trước** khi tool chạy; lớp chặn này chạy
lúc tool chạy. Bật cả hai thì có thể người dùng duyệt xong mới bị chặn — chấp nhận được với POC; muốn tốt hơn thì
dùng `when=` trong `InterruptOnConfig` để chỉ hỏi duyệt khi đã đọc.

**3. Kiểm chứng sau khi ghi.** Sau khi tool ghi báo thành công, đọc lại nguồn và nối "Kiểm tra lại: OK" hoặc
"Kiểm tra lại: SAI — …" vào kết quả tool. Test dùng một DB "báo thành công nhưng không ghi" để chứng minh model
thấy được lỗi im lặng. Với tool client (Excel), việc đọc lại nằm ở add-in: sau `setValues`, đọc lại vùng vừa ghi và
trả về kèm kết quả.

**4. Nhắc trạng thái.** Thêm một `HumanMessage` `<system-reminder>…</system-reminder>` vào **cuối** messages của
lần gọi model (không lưu vào state). Đặt ở cuối thay vì sửa system prompt để phần đầu ngữ cảnh giữ nguyên giữa các
lượt — điều kiện để prompt cache của nhà cung cấp trúng (kỹ năng EFF về cache).

**5. Chính sách quyền.** Chặn tool theo `runtime.context.role` ngay trước khi tool chạy. Đây là ràng buộc cứng: model
có "quên" luật thì code vẫn chặn. Kết hợp với `HumanInTheLoopMiddleware` cho bước ghi.

**6. Subagent.** Một tool bọc một agent khác có ngữ cảnh riêng; agent chính chỉ nhận câu trả lời cuối. Test kiểm
rằng kết quả thô agent con tra được không lọt vào ngữ cảnh agent chính.

**7. Danh sách việc.** `TodoListMiddleware` có sẵn, thêm tool `write_todos` và hướng dẫn dùng. Chỉ đáng bật khi yêu
cầu thường có từ 3 bước trở lên.

**8. Quản lý ngữ cảnh.** `ContextEditingMiddleware(ClearToolUsesEdit(trigger, keep))` thay kết quả tool cũ bằng
`[cleared]` khi ngữ cảnh vượt ngưỡng token (chỉ phần model thấy). `SummarizationMiddleware` tóm tắt phần cũ và
**ghi đè state** (giữ `keep` tin nhắn cuối). Lưu ý: bản tóm tắt được chèn dưới dạng `HumanMessage`, nên
`HistoryWindowMiddleware` sẽ đếm nó như một run.

### 5.3 Code

```python
# file: harness/improved.py
"""Cải tiến harness theo cách Claude Code làm — mỗi lớp là một middleware độc lập, bật/tắt được.

| Claude Code                               | Middleware ở đây                                   |
|-------------------------------------------|----------------------------------------------------|
| CLAUDE.md nạp mỗi session                 | RulesFileMiddleware                                |
| Edit chỉ chạy khi file đã Read, chưa đổi  | ReadBeforeWriteMiddleware                          |
| Chạy test sau khi sửa                     | VerifyAfterWriteMiddleware                         |
| <system-reminder> chèn vào lượt user      | ReminderMiddleware                                 |
| Permission rules / chế độ quyền           | ToolPolicyMiddleware (+ HumanInTheLoopMiddleware)  |
| Tóm tắt khi hội thoại dài, xoá kết quả cũ | SummarizationMiddleware, ContextEditingMiddleware  |
| Danh sách việc (todo)                     | TodoListMiddleware                                 |
| Subagent ngữ cảnh riêng, chỉ trả kết quả  | make_subagent_tool                                 |
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import Annotated, Any, NotRequired

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ClearToolUsesEdit,
    ContextEditingMiddleware,
    ModelRequest,
    ModelResponse,
    SummarizationMiddleware,
    TodoListMiddleware,
    ToolCallRequest,
)
from langchain.tools import BaseTool, tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.store.base import BaseStore
from langgraph.types import Checkpointer, Command

from harness.agent import build_agent
from harness.data import CustomerDB

ToolHandler = Callable[[ToolCallRequest], ToolMessage | Command]
AsyncToolHandler = Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]]


def _blocked(request: ToolCallRequest, text: str) -> ToolMessage:
    return ToolMessage(
        content=text, tool_call_id=request.tool_call["id"], name=request.tool_call["name"], status="error"
    )


def _append_system(request: ModelRequest, block: str) -> ModelRequest:
    base = request.system_message.text if request.system_message else ""
    return request.override(system_message=SystemMessage(content=f"{base}\n\n{block}" if base else block))


class _ModelMiddleware(AgentMiddleware):
    """Khung chung: lớp con chỉ viết `_prepare`, có sẵn cả bản sync và async."""

    def _prepare(self, request: ModelRequest) -> ModelRequest:
        return request

    def wrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:
        return handler(self._prepare(request))

    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Awaitable[ModelResponse]]
    ) -> ModelResponse:
        return await handler(self._prepare(request))


# ---------------------------------------------------------------- 1. File luật dự án (CLAUDE.md)
class RulesFileMiddleware(_ModelMiddleware):
    """Nối nội dung file luật vào system prompt. Đọc lại khi file đổi — người sửa file, agent theo ngay."""

    def __init__(self, path: str | Path) -> None:
        super().__init__()
        self.path = Path(path)
        self._cache: tuple[float, str] | None = None

    def rules(self) -> str:
        mtime = self.path.stat().st_mtime
        if self._cache is None or self._cache[0] != mtime:
            self._cache = (mtime, self.path.read_text(encoding="utf-8").strip())
        return self._cache[1]

    def _prepare(self, request: ModelRequest) -> ModelRequest:
        return _append_system(request, f"<project_rules>\n{self.rules()}\n</project_rules>")


# ---------------------------------------------------------------- 2. Đọc trước khi ghi
def _merge(old: dict[str, str] | None, new: dict[str, str] | None) -> dict[str, str]:
    return {**(old or {}), **(new or {})}


class ReadTrackingState(AgentState):
    read_versions: NotRequired[Annotated[dict[str, str], _merge]]


class ReadBeforeWriteMiddleware(AgentMiddleware):
    """Chặn ghi vào bản ghi chưa đọc, hoặc đã bị đổi sau lần đọc (giống Edit của Claude Code).

    reads:  tool đọc → hàm (args, kết quả) trả các khóa đã đọc
    writes: tool ghi → hàm (args) trả khóa sẽ ghi
    fingerprint: khóa → dấu vân tay dữ liệu hiện tại (None nếu không có)
    """

    state_schema = ReadTrackingState

    def __init__(
        self,
        *,
        reads: dict[str, Callable[[dict, str], list[str]]],
        writes: dict[str, Callable[[dict], str]],
        fingerprint: Callable[[str], str | None],
    ) -> None:
        super().__init__()
        self.reads, self.writes, self.fingerprint = reads, writes, fingerprint

    def _check_write(self, request: ToolCallRequest) -> ToolMessage | None:
        key = self.writes[request.tool_call["name"]](request.tool_call["args"])
        seen = (request.state.get("read_versions") or {}).get(key)
        if seen is None:
            return _blocked(
                request, f"Chặn: chưa đọc {key} trong cuộc trò chuyện này. Đọc dữ liệu hiện tại trước khi ghi."
            )
        if seen != self.fingerprint(key):
            return _blocked(request, f"Chặn: {key} đã thay đổi sau lần đọc trước. Đọc lại rồi mới ghi.")
        return None

    def _after(self, request: ToolCallRequest, result: ToolMessage | Command) -> ToolMessage | Command:
        name = request.tool_call["name"]
        if not isinstance(result, ToolMessage) or result.status == "error":
            return result
        if name in self.reads:
            keys = self.reads[name](request.tool_call["args"], result.text)
        elif name in self.writes:
            keys = [self.writes[name](request.tool_call["args"])]  # ghi xong thì bản mới coi như đã đọc
        else:
            return result
        versions = {k: v for k in keys if (v := self.fingerprint(k)) is not None}
        return Command(update={"messages": [result], "read_versions": versions}) if versions else result

    def wrap_tool_call(self, request: ToolCallRequest, handler: ToolHandler) -> ToolMessage | Command:
        if request.tool_call["name"] in self.writes and (blocked := self._check_write(request)):
            return blocked
        return self._after(request, handler(request))

    async def awrap_tool_call(self, request: ToolCallRequest, handler: AsyncToolHandler) -> ToolMessage | Command:
        if request.tool_call["name"] in self.writes and (blocked := self._check_write(request)):
            return blocked
        return self._after(request, await handler(request))


# ---------------------------------------------------------------- 3. Kiểm chứng sau khi ghi
class VerifyAfterWriteMiddleware(AgentMiddleware):
    """Sau khi tool ghi chạy xong, đọc lại nguồn và nối kết quả kiểm tra vào ToolMessage — model thấy ngay nếu sai."""

    def __init__(self, verifiers: dict[str, Callable[[dict], str | None]]) -> None:
        super().__init__()
        self.verifiers = verifiers  # trả None nếu đúng, chuỗi mô tả lỗi nếu sai

    def _verify(self, request: ToolCallRequest, result: ToolMessage | Command) -> ToolMessage | Command:
        verify = self.verifiers.get(request.tool_call["name"])
        if verify is None or not isinstance(result, ToolMessage) or result.status == "error":
            return result
        problem = verify(request.tool_call["args"])
        note = "Kiểm tra lại: OK, dữ liệu nguồn khớp." if problem is None else f"Kiểm tra lại: SAI — {problem}"
        return result.model_copy(update={"content": f"{result.text}\n{note}"})

    def wrap_tool_call(self, request: ToolCallRequest, handler: ToolHandler) -> ToolMessage | Command:
        return self._verify(request, handler(request))

    async def awrap_tool_call(self, request: ToolCallRequest, handler: AsyncToolHandler) -> ToolMessage | Command:
        return self._verify(request, await handler(request))


# ---------------------------------------------------------------- 4. Nhắc trạng thái (system-reminder)
def default_reminder(request: ModelRequest) -> str | None:
    starts = [i for i, m in enumerate(request.messages) if isinstance(m, HumanMessage)]
    run = request.messages[starts[-1] :] if starts else request.messages
    used = sum(1 for m in run if isinstance(m, ToolMessage))
    return f"Hôm nay {dt.date.today().isoformat()}. Yêu cầu hiện tại đã dùng {used} lượt tool."


class ReminderMiddleware(_ModelMiddleware):
    """Chèn một tin nhắn <system-reminder> vào CUỐI messages của lần gọi model (không lưu vào state).

    Đặt ở cuối thay vì sửa system prompt để giữ nguyên phần đầu ngữ cảnh → prompt cache vẫn trúng.
    """

    def __init__(self, make: Callable[[ModelRequest], str | None] = default_reminder) -> None:
        super().__init__()
        self.make = make

    def _prepare(self, request: ModelRequest) -> ModelRequest:
        text = self.make(request)
        if not text:
            return request
        return request.override(
            messages=[*request.messages, HumanMessage(content=f"<system-reminder>{text}</system-reminder>")]
        )


# ---------------------------------------------------------------- 5. Chính sách quyền
class ToolPolicyMiddleware(AgentMiddleware):
    """Chặn tool theo quyền của người dùng (runtime.context.role) — chạy trước khi tool chạy."""

    def __init__(self, deny_by_role: dict[str, set[str]]) -> None:
        super().__init__()
        self.deny_by_role = deny_by_role

    def _check(self, request: ToolCallRequest) -> ToolMessage | None:
        role = getattr(request.runtime.context, "role", None)
        if request.tool_call["name"] in self.deny_by_role.get(role, set()):
            return _blocked(
                request,
                f"Không được phép: vai trò '{role}' không dùng được {request.tool_call['name']}. Báo người dùng.",
            )
        return None

    def wrap_tool_call(self, request: ToolCallRequest, handler: ToolHandler) -> ToolMessage | Command:
        return self._check(request) or handler(request)

    async def awrap_tool_call(self, request: ToolCallRequest, handler: AsyncToolHandler) -> ToolMessage | Command:
        return self._check(request) or await handler(request)


# ---------------------------------------------------------------- 6. Subagent
def make_subagent_tool(
    name: str, description: str, model: BaseChatModel, tools: Sequence[BaseTool], system_prompt: str
) -> BaseTool:
    """Một agent con chạy với ngữ cảnh riêng; agent chính chỉ nhận câu trả lời cuối (không nhận các bước giữa)."""
    sub = create_agent(model, tools=list(tools), system_prompt=system_prompt, checkpointer=False, name=name)

    @tool(name, description=description)
    def run_subagent(task: str) -> str:
        out = sub.invoke({"messages": [HumanMessage(content=task)]})
        final = next((m for m in reversed(out["messages"]) if isinstance(m, AIMessage) and not m.tool_calls), None)
        return final.text if final else "(agent con không trả lời)"

    return run_subagent


# ---------------------------------------------------------------- Ráp lại cho bài toán khách hàng
def customer_guards(db: CustomerDB) -> list[AgentMiddleware]:
    def fingerprint(key: str) -> str | None:
        row = db.get(key)
        return (
            hashlib.sha1(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12] if row else None
        )

    def read_ids(args: dict, result: str) -> list[str]:
        try:
            return [row["id"] for row in json.loads(result)]
        except (json.JSONDecodeError, TypeError, KeyError):
            return []  # kết quả lỗi / không tìm thấy → không có gì được coi là đã đọc

    def verify_update(args: dict) -> str | None:
        row = db.get(args["customer_id"])
        if row is None:
            return f"không còn khách hàng {args['customer_id']}"
        if str(row.get(args["field"])) != str(args["value"]):
            return f"{args['field']} hiện là {row.get(args['field'])!r}, không phải {args['value']!r}"
        return None

    return [
        ToolPolicyMiddleware({"viewer": {"update_customer", "excel_set_values"}}),
        ReadBeforeWriteMiddleware(
            reads={"search_customers": read_ids},
            writes={"update_customer": lambda args: args["customer_id"]},
            fingerprint=fingerprint,
        ),
        VerifyAfterWriteMiddleware({"update_customer": verify_update}),
    ]


def build_improved_agent(
    model: BaseChatModel,
    *,
    db: CustomerDB,
    checkpointer: Checkpointer,
    store: BaseStore | None = None,
    memory_model: BaseChatModel | None = None,
    summary_model: BaseChatModel | None = None,
    rules_path: str | Path | None = None,
    subagents: Sequence[BaseTool] = (),
    todo: bool = False,
    reminders: bool = True,
    **kwargs: Any,
):
    extra: list[AgentMiddleware] = []
    if rules_path is not None:
        extra.append(RulesFileMiddleware(rules_path))
    if summary_model is not None:
        # Hội thoại dài: tóm tắt phần cũ (ghi đè state), giữ 20 tin nhắn cuối.
        extra.append(SummarizationMiddleware(summary_model, trigger=("tokens", 8000), keep=("messages", 20)))
    # Kết quả tool cũ chiếm nhiều token nhất: thay bằng "[cleared]" khi ngữ cảnh vượt ngưỡng, giữ 3 kết quả gần nhất.
    extra.append(ContextEditingMiddleware(edits=[ClearToolUsesEdit(trigger=6000, keep=3)]))
    if todo:
        extra.append(TodoListMiddleware())
    extra.extend(customer_guards(db))
    if reminders:
        extra.append(ReminderMiddleware())
    return build_agent(
        model,
        db=db,
        checkpointer=checkpointer,
        store=store,
        memory_model=memory_model,
        extra_tools=subagents,
        extra_middleware=extra,
        **kwargs,
    )
```

File luật mẫu:

````markdown
<!-- file: rules/agent-rules.md -->
# Luật dữ liệu khách hàng

- Mã khách hàng có dạng `KH-` + 4 chữ số. Không tự tạo mã mới.
- `credit_limit` và `debt` là số nguyên VND, không dấu phân cách (300000000, không phải 300.000.000).
- `status` chỉ nhận: Đang giao, Hoàn tất, Tạm dừng.
- Giảm `credit_limit` quá 50% trong một lần: hỏi người dùng xác nhận trước khi gọi tool ghi.
- Khi trả lời về tiền, ghi rõ đơn vị (triệu VND).
````

### 5.4 Bộ đo vàng

Mỗi ca: câu hỏi + tool đầu tiên mong đợi + đối số phải có. Chạy trước và sau mỗi thay đổi prompt, tool, model hoặc
middleware; in token vào/ra, tính chi phí khi đặt giá. Test của lab chỉ kiểm phần chấm điểm bằng model kịch bản;
**chạy với model thật cần `OPENAI_API_KEY`** (hoặc `--base-url` tới model local) và chưa chạy trong tài liệu này.

```python
# file: eval_golden.py
"""Bộ đo vàng: mỗi ca = câu hỏi + tool đầu tiên mong đợi + đối số phải có. Đo "agent chọn đúng tool" trước
mọi thay đổi prompt / tool / model.

Chạy với model thật (cần langchain-openai và OPENAI_API_KEY):
    python eval_golden.py                       # gpt-5-mini
    python eval_golden.py --model gpt-5 --base-url http://localhost:8000/v1   # endpoint tương thích OpenAI

In ra token vào/ra; chi phí chỉ tính khi đặt PRICE_IN_PER_MTOK / PRICE_OUT_PER_MTOK (USD cho 1 triệu token).
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from harness.agent import build_agent
from harness.context import AgentContext
from harness.data import CustomerDB
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver


@dataclass
class Case:
    question: str
    tool: str | None  # None = không được gọi tool
    args: dict[str, Any] = field(
        default_factory=dict
    )  # các cặp khóa/giá trị phải có (so chuỗi, không phân biệt hoa thường)


CASES = [
    Case("Tra KH-0012 giúp tôi", "search_customers", {"query": "KH-0012"}),
    Case("Khách hàng ở Đà Nẵng có những ai?", "search_customers", {"query": "Đà Nẵng"}),
    Case("Đổi trạng thái KH-0047 thành Hoàn tất", "search_customers"),  # luật: tra cứu trước khi ghi
    Case("Chào bạn", None),
]


@dataclass
class Result:
    case: Case
    got: tuple[str, dict] | None
    passed: bool
    tokens_in: int = 0
    tokens_out: int = 0


def first_tool_call(messages: list[Any]) -> tuple[str, dict] | None:
    for m in messages:
        if isinstance(m, AIMessage) and m.tool_calls:
            return m.tool_calls[0]["name"], m.tool_calls[0]["args"]
    return None


def matches(case: Case, got: tuple[str, dict] | None) -> bool:
    if case.tool is None:
        return got is None
    if got is None or got[0] != case.tool:
        return False
    return all(str(got[1].get(k, "")).lower() == str(v).lower() for k, v in case.args.items())


def run(make_agent: Callable[[], Any], cases: list[Case] = CASES) -> list[Result]:
    results = []
    for case in cases:
        agent = make_agent()
        out = agent.invoke(
            {"messages": [{"role": "user", "content": case.question}]},
            {"configurable": {"thread_id": uuid.uuid4().hex}},
            context=AgentContext(user_id=None),
        )
        usage = [m.usage_metadata for m in out["messages"] if isinstance(m, AIMessage) and m.usage_metadata]
        got = first_tool_call(out["messages"])
        results.append(
            Result(
                case,
                got,
                matches(case, got),
                sum(u["input_tokens"] for u in usage),
                sum(u["output_tokens"] for u in usage),
            )
        )
    return results


def report(results: list[Result]) -> str:
    passed = sum(r.passed for r in results)
    lines = [f"Đạt {passed}/{len(results)}"]
    lines += [
        f"  SAI: {r.case.question!r} → mong {r.case.tool} {r.case.args}, nhận {r.got}" for r in results if not r.passed
    ]
    tin, tout = sum(r.tokens_in for r in results), sum(r.tokens_out for r in results)
    lines.append(f"Token vào {tin}, ra {tout}")
    pin, pout = os.environ.get("PRICE_IN_PER_MTOK"), os.environ.get("PRICE_OUT_PER_MTOK")
    if pin and pout:
        lines.append(f"Chi phí ≈ {(tin * float(pin) + tout * float(pout)) / 1e6:.4f} USD")
    else:
        lines.append("Chi phí: đặt PRICE_IN_PER_MTOK và PRICE_OUT_PER_MTOK để tính")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--base-url")
    args = parser.parse_args()
    if not args.base_url and not os.environ.get("OPENAI_API_KEY"):
        print("Cần OPENAI_API_KEY (hoặc --base-url tới endpoint local).", file=sys.stderr)
        return 1
    from harness.model import build_model

    def make_agent():
        model = build_model(args.model, base_url=args.base_url, api_key="local" if args.base_url else None)
        return build_agent(model, db=CustomerDB(), checkpointer=InMemorySaver(), approve_writes=True)

    print(report(run(make_agent)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### 5.5 Test cho phần cải tiến

```python
# file: tests/test_improved.py
"""Các lớp cải tiến theo Claude Code: mỗi test kiểm một hành vi."""

from __future__ import annotations

import os
import time

from eval_golden import CASES, report, run
from harness.agent import build_agent
from harness.context import AgentContext
from harness.data import CustomerDB
from harness.improved import (
    ReminderMiddleware,
    RulesFileMiddleware,
    build_improved_agent,
    make_subagent_tool,
)
from harness.model import ScriptedChatModel, call, say
from harness.run import ask
from langchain.agents.middleware import ClearToolUsesEdit, ContextEditingMiddleware, SummarizationMiddleware
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver


def improved(model, db=None, **kwargs):
    kwargs.setdefault("approve_writes", False)  # tắt người duyệt để test tập trung vào lớp đang kiểm
    return build_improved_agent(model, db=db or CustomerDB(), checkpointer=InMemorySaver(), **kwargs)


def tool_texts(out) -> list[str]:
    return [m.text for m in out["messages"] if isinstance(m, ToolMessage)]


UPDATE = {"customer_id": "KH-0012", "field": "status", "value": "Hoàn tất"}


# ---------------------------------------------------------------- 1. File luật
def test_rules_file_is_appended_and_reloaded(tmp_path, thread):
    rules = tmp_path / "rules.md"
    rules.write_text("- Mã KH có dạng KH-0000", encoding="utf-8")
    model = ScriptedChatModel(steps=[say("ok"), say("ok")])
    agent = build_agent(
        model, db=CustomerDB(), checkpointer=InMemorySaver(), extra_middleware=[RulesFileMiddleware(rules)]
    )
    ask(agent, "a", thread=thread)
    assert "<project_rules>\n- Mã KH có dạng KH-0000\n</project_rules>" in model.calls[0][0].text
    time.sleep(0.01)
    rules.write_text("- Luật mới", encoding="utf-8")
    os.utime(rules, (time.time() + 5, time.time() + 5))  # bảo đảm mtime đổi trên mọi hệ file
    ask(agent, "b", thread=thread)
    assert "- Luật mới" in model.calls[1][0].text


# ---------------------------------------------------------------- 2. Đọc trước khi ghi
def test_write_without_read_is_blocked(thread):
    db = CustomerDB()
    model = ScriptedChatModel(steps=[call("update_customer", **UPDATE), say("Tôi sẽ đọc trước.")])
    out = ask(improved(model, db), "Đổi KH-0012 thành Hoàn tất", thread=thread)
    assert db.writes == []
    assert tool_texts(out) == ["Chặn: chưa đọc KH-0012 trong cuộc trò chuyện này. Đọc dữ liệu hiện tại trước khi ghi."]


def test_write_after_read_is_allowed_and_verified(thread):
    db = CustomerDB()
    model = ScriptedChatModel(
        steps=[call("search_customers", query="KH-0012"), call("update_customer", **UPDATE), say("Xong.")]
    )
    out = ask(improved(model, db), "Đổi KH-0012 thành Hoàn tất", thread=thread)
    assert db.writes == [("KH-0012", "status", "Hoàn tất")]
    assert tool_texts(out)[-1] == "Đã cập nhật KH-0012.status = Hoàn tất\nKiểm tra lại: OK, dữ liệu nguồn khớp."


def test_write_blocked_when_data_changed_after_read(thread):
    db = CustomerDB()
    model = ScriptedChatModel(
        steps=[
            call("search_customers", query="KH-0012"),
            say("Đã xem."),
            call("update_customer", **UPDATE),
            say("Tôi sẽ đọc lại."),
        ]
    )
    agent = improved(model, db)
    ask(agent, "Xem KH-0012", thread=thread)
    db.update("KH-0012", "debt", "0")  # người khác sửa dữ liệu giữa hai lượt
    out = ask(agent, "Đổi thành Hoàn tất", thread=thread)
    assert db.get("KH-0012")["status"] == "Đang giao"
    assert tool_texts(out)[-1] == "Chặn: KH-0012 đã thay đổi sau lần đọc trước. Đọc lại rồi mới ghi."


# ---------------------------------------------------------------- 3. Kiểm chứng sau khi ghi
class SilentlyBrokenDB(CustomerDB):
    def update(self, customer_id: str, field: str, value: str) -> None:
        self.writes.append((customer_id, field, value))  # báo thành công nhưng không ghi gì


def test_verify_after_write_catches_silent_failure(thread):
    model = ScriptedChatModel(
        steps=[call("search_customers", query="KH-0012"), call("update_customer", **UPDATE), say("…")]
    )
    out = ask(improved(model, SilentlyBrokenDB()), "Đổi KH-0012", thread=thread)
    assert tool_texts(out)[-1].endswith("Kiểm tra lại: SAI — status hiện là 'Đang giao', không phải 'Hoàn tất'")


# ---------------------------------------------------------------- 4. Nhắc trạng thái
def test_reminder_is_sent_to_model_but_not_stored(thread):
    model = ScriptedChatModel(steps=[call("search_customers", query="Hà Nội"), say("ok")])
    agent = build_agent(
        model,
        db=CustomerDB(),
        checkpointer=InMemorySaver(),
        extra_middleware=[ReminderMiddleware(lambda req: "Còn 7 lượt tool.")],
    )
    out = ask(agent, "Khách Hà Nội", thread=thread)
    last = model.calls[1][-1]
    assert isinstance(last, HumanMessage) and last.text == "<system-reminder>Còn 7 lượt tool.</system-reminder>"
    assert not any("system-reminder" in m.text for m in out["messages"])  # state sạch


# ---------------------------------------------------------------- 5. Chính sách quyền
def test_viewer_cannot_write(thread):
    db = CustomerDB()
    model = ScriptedChatModel(
        steps=[call("search_customers", query="KH-0012"), call("update_customer", **UPDATE), say("…")]
    )
    out = ask(improved(model, db), "Đổi", thread=thread, ctx=AgentContext(user_id="u1", role="viewer"))
    assert db.writes == []
    assert tool_texts(out)[-1].startswith("Không được phép: vai trò 'viewer'")


# ---------------------------------------------------------------- 6. Subagent
def test_subagent_returns_only_its_final_answer(thread):
    db = CustomerDB()
    from harness.tools import make_server_tools

    sub_model = ScriptedChatModel(
        steps=[call("search_customers", query="Hà Nội"), say("Hà Nội có 2 khách: KH-0012, KH-0047.")]
    )
    research = make_subagent_tool(
        "research_customers",
        "Tra cứu nhiều bước về khách hàng, trả lại bản tóm tắt.",
        sub_model,
        make_server_tools(db)[:1],
        "Bạn tra cứu khách hàng, trả lời ngắn.",
    )
    main = ScriptedChatModel(steps=[call("research_customers", task="Khách hàng ở Hà Nội"), say("Có 2 khách.")])
    ask(improved(main, db, subagents=[research]), "Ai ở Hà Nội?", thread=thread)
    seen_by_main = [m for m in main.calls[1] if isinstance(m, ToolMessage)]
    assert [m.text for m in seen_by_main] == ["Hà Nội có 2 khách: KH-0012, KH-0047."]
    assert not any("Công ty An Phát" in m.text for m in seen_by_main)  # kết quả thô của agent con không lọt ra


# ---------------------------------------------------------------- 7. Lập kế hoạch
def test_todo_middleware_adds_write_todos_tool(thread):
    model = ScriptedChatModel(steps=[say("ok")])
    ask(improved(model, todo=True), "a", thread=thread)
    assert "write_todos" in model.bound_tools[-1]


# ---------------------------------------------------------------- 8. Quản lý ngữ cảnh
def test_context_editing_clears_old_tool_results(thread):
    steps = [call("search_customers", query=q) for q in ["KH-0012", "KH-0031", "KH-0047", "Hà Nội"]] + [say("ok")]
    model = ScriptedChatModel(steps=steps)
    editing = ContextEditingMiddleware(edits=[ClearToolUsesEdit(trigger=200, keep=1)])
    ask(
        build_agent(model, db=CustomerDB(), checkpointer=InMemorySaver(), extra_middleware=[editing]),
        "a",
        thread=thread,
    )
    last_seen = [m.text for m in model.calls[-1] if isinstance(m, ToolMessage)]
    assert last_seen[:-1] == ["[cleared]"] * (len(last_seen) - 1)  # chỉ giữ kết quả mới nhất
    assert "KH-0012" in last_seen[-1]


def test_summarization_replaces_old_turns(thread):
    model = ScriptedChatModel(steps=[say(f"trả lời {i}") for i in range(4)])
    summarizer = ScriptedChatModel(steps=[say("TÓM TẮT: Lan hỏi về KH-0012.")] * 3)
    summary = SummarizationMiddleware(summarizer, trigger=("messages", 5), keep=("messages", 2))
    agent = build_agent(model, db=CustomerDB(), checkpointer=InMemorySaver(), extra_middleware=[summary])
    for i in range(4):
        ask(agent, f"câu {i}", thread=thread)
    assert summarizer.calls, "đã phải tóm tắt"
    assert any("TÓM TẮT: Lan hỏi về KH-0012." in m.text for m in model.calls[-1])
    assert not any(m.text == "câu 0" for m in model.calls[-1])  # lượt cũ đã được thay bằng bản tóm tắt


# ---------------------------------------------------------------- 9. Bộ đo vàng
def test_golden_eval_runner_scores_scripted_answers():
    answers = iter(
        [
            [call("search_customers", query="KH-0012"), say("ok")],
            [call("search_customers", query="Đà Nẵng"), say("ok")],
            [call("update_customer", **UPDATE)],  # sai luật: ghi trước khi tra cứu
            [say("Chào bạn!")],
        ]
    )

    def make_agent():
        return build_agent(ScriptedChatModel(steps=next(answers)), db=CustomerDB(), checkpointer=InMemorySaver())

    results = run(make_agent, CASES)
    assert [r.passed for r in results] == [True, True, False, True]
    assert report(results).startswith("Đạt 3/4")
```

## 6. Giới hạn và việc tiếp theo

- **Chưa chạy với model thật.** Mọi test dùng model kịch bản: chúng chứng minh harness đưa đúng thứ cho model và
  chặn đúng chỗ, **không** chứng minh model thật chọn tool đúng. Việc đó là của `eval_golden.py`.
- **Chưa có server AG-UI.** Muốn thay AgentOS cho CMB-10 phải viết một endpoint nhận `RunAgentInput`, gọi
  `ask`/`resume` như mục 4.8 và phát sự kiện AG-UI (`RUN_STARTED`, `TEXT_MESSAGE_*`, `TOOL_CALL_START/ARGS/END`,
  `RUN_FINISHED`) từ `agent.stream(...)`. Một interrupt `client_tool` ứng với `TOOL_CALL_*` không có kết quả, đúng như
  AgentOS đang làm. Chưa kiểm gói adapter AG-UI có sẵn nào cho LangGraph.
- **Cảnh báo đã biết:** khi run dừng ở `interrupt()` với `context=AgentContext(...)`, pydantic in một
  `UserWarning` về serializer của trường `context`. Không ảnh hưởng kết quả (test vẫn xanh).
- **Chưa làm:** chọn tool theo câu hỏi khi có nhiều tool (`LLMToolSelectorMiddleware`, `ProviderToolSearchMiddleware`
  có sẵn), trace gửi Langfuse/OTel, prompt cache có đo.

## Nguồn

- Mã `agno` 3.1.3: `agent/_run.py`, `agent/_messages.py`, `agent/_managers.py`, `agent/agent.py`, `agent/_init.py`,
  `session/agent.py`, `models/base.py`, `memory/manager.py`.
- Mã `langchain` 1.4.6: `agents/factory.py`, `agents/middleware/types.py`, `tool_call_limit.py`,
  `model_call_limit.py`, `human_in_the_loop.py`, `summarization.py`, `context_editing.py`, `todo.py`;
  `langgraph` 1.2.16: `types.py` (`interrupt`, `Command`), `store/base`.
- So sánh cơ chế bốn framework: [01-co-che-agent.md](01-co-che-agent.md). Radar framework: [README.md](README.md).
