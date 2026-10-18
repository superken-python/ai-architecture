# Harness của agent: Agno chạy thế nào, dựng lại bằng LangChain, cải tiến theo Claude Code

| Thuộc tính | Chi tiết |
|---|---|
| Thuộc nhóm | [Nhóm 7 · AI Agent và tự động hóa quy trình](../02-skill-map/generated/nhom/g7-agent-tu-dong-hoa.md) · kỹ năng [LLM-05](../02-skill-map/generated/mang/llm.md#llm-05) |
| Mục tiêu | Hiểu harness của Agno tới mức **tự viết lại được** bằng LangChain, rồi làm harness tốt hơn theo cách Claude Code làm |
| Phiên bản đã đọc mã và chạy | `agno` 3.1.3 · `langchain` 1.4.6 · `langgraph` 1.2.16 · `langchain-core` 1.6.12 · `langgraph-checkpoint-sqlite` 3.1.2 · `langchain-openai` 1.7.2 · `langchain-mcp-adapters` 0.3.2 + `mcp` 1.30.0 (mục 6.5) |
| Code chạy được | [`labs/llm-05-trung-cap-harness-langchain/`](../../labs/llm-05-trung-cap-harness-langchain/README.md) — mọi khối code dưới đây là **nguyên văn** file trong lab (test `test_doc_sync.py` bảo đảm điều này) |
| Đã kiểm chứng | 72 test với model kịch bản: 47 test hành vi (tái hiện từng thí nghiệm đã làm trên Agno, từng lớp cải tiến, và các tính năng còn lại của Lab 01 ở mục 6) + 25 test tài liệu khớp code |
| Chưa kiểm chứng | Chạy với model thật (môi trường làm tài liệu không có API key) · Postgres · server AG-UI (để sau, xem [ưu tiên](#ưu-tiên-và-thứ-tự-học)) |
| Ngày | 2026-10-17 · bổ sung mục 6 ngày 2026-10-18 |

Tài liệu đi theo thứ tự: **agent và harness là gì → Agno chạy một run ra sao (đã đo) → ánh xạ sang LangChain →
code từng mảnh → cải tiến**. Ví dụ xuyên suốt là trợ lý dữ liệu khách hàng trong Excel, rút gọn từ
[CMB-10](../../projects/cmb-10-excel-agent-addin/README.md).

## Tóm tắt

- **Harness** là phần code quanh model: dựng ngữ cảnh, chạy vòng lặp gọi tool, dừng, tạm dừng chờ người/client, lưu
  trữ, và các điểm cho ta chen vào. Model quyết định làm gì; harness quyết định model thấy gì và được làm gì.
- **Một run của Agno:** system (instructions + memory của user) + N run lịch sử (mặc định 3) + câu hiện tại → vòng
  lặp model ↔ tool tới khi model không gọi tool nữa (hoặc có tool chờ client/người duyệt → run tạm dừng, lưu DB) →
  lưu run. Memory được trích nền từ **tin nhắn user**, và run chờ trích xong mới trả lời.
- **Ba điểm yếu đã đo ở Agno:** `tool_call_limit` không dừng vòng lặp; thiếu `user_id` thì mọi người dùng chung
  memory `"default"`; model trích xuất memory mất `http_client` tuỳ chỉnh.
- **LangChain:** `create_agent` + middleware — mỗi tính năng của Agno thành một middleware. Có sẵn: trần dừng hẳn
  (`exit_behavior="end"`), người duyệt, tóm tắt, todo. Phải tự viết: cửa sổ N run và memory theo user. Tool client =
  `interrupt()` + `Command(resume=...)`.
- **Lịch sử, không phải memory, giữ mạch hội thoại** ("còn hạn mức không?" hiểu được nhờ kết quả tool ở run trước).
  Memory chỉ giữ điều về người dùng và sống lâu hơn cửa sổ lịch sử.
- **Cải tiến kiểu Claude Code:** luật do người viết, đọc trước khi ghi, kiểm chứng sau khi ghi, nhắc trạng thái ở cuối
  ngữ cảnh, quyền chặn bằng code, subagent, todo, giữ ngữ cảnh gọn — và đo mọi thay đổi bằng bộ đo vàng.
- **Phần còn lại của Agno** (mục 6): output có schema, `session_state`, guardrail, RAG, MCP client, team, workflow
  `StateGraph`, nhiều tool client cùng lượt — mỗi thứ một module, có test và cột "khác biệt đã đo".
- **Mức kiểm chứng:** 72 test với model kịch bản chứng minh harness đưa đúng thứ cho model và chặn đúng chỗ; chưa
  chứng minh model thật chọn tool đúng (cần chạy `eval_golden.py` với API key).

### Ưu tiên và thứ tự học

Quyết định ngày 2026-10-17: **tập trung agent harness và workflow agent trước; AG-UI và API để sau** — khớp lộ trình
tự học ([mục 10 "AG-UI và API: học sau CLI"](../self-practices/agent_framework_learning_from_scratch.md#10-ag-ui-và-api-học-sau-cli)).

| Bước | Học gì | Ở đâu |
|---|---|---|
| 1. Agent harness | Vòng lặp model ↔ tool, lịch sử, memory, tạm dừng/chạy tiếp, giới hạn, các lớp kiểm soát | Tài liệu này + [lab LLM-05](../../labs/llm-05-trung-cap-harness-langchain/README.md) |
| 2. Workflow agent | Các bước cố định trong `StateGraph` (rẽ nhánh, gate, người duyệt); bước nào cần tự chọn tool thì đặt một harness nhỏ vào đó; dùng lại checkpointer, `interrupt()`, giới hạn, memory | [Mục 6.7](#67-workflow) + [Lab 03 LangGraph](../self-practices/guide_03_langgraph.md) |
| 3. AG-UI / API | Đưa harness hoặc workflow lên giao diện | Để sau ([mục 7](#7-giới-hạn-và-việc-tiếp-theo)) |

Chọn workflow hay agent cho một bước: **biết trước các bước thì dùng workflow** (rẻ hơn, dễ kiểm chứng hơn); chỉ để
model tự chọn tool ở bước thật sự mở. Hai thứ dùng chung một bộ "viên gạch" — học harness trước là học các viên
gạch đó.

## Mục lục

1. [Agent và harness](#1-agent-và-harness)
2. [Harness của Agno chạy thế nào](#2-harness-của-agno-chạy-thế-nào)
3. [Ánh xạ Agno sang LangChain](#3-ánh-xạ-agno-sang-langchain)
4. [Dựng lại bằng LangChain, từng mảnh](#4-dựng-lại-bằng-langchain-từng-mảnh)
5. [Cải tiến harness theo Claude Code](#5-cải-tiến-harness-theo-claude-code)
6. [Phần còn lại của Agno trong LangChain](#6-phần-còn-lại-của-agno-trong-langchain)
7. [Giới hạn và việc tiếp theo](#7-giới-hạn-và-việc-tiếp-theo)

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
| `output_schema`, `session_state`, guardrail, knowledge, MCP, team, workflow | xem bảng ở mục 6 | `harness/structured.py` … `workflow.py` | Mục 6 |
| AgentOS + AG-UI | không có sẵn trong lab | — | Phải tự viết server (mục 7) |

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
│   ├── run.py           # ask / resume / pending / resume_all
│   ├── improved.py      # các lớp cải tiến kiểu Claude Code
│   ├── structured.py    # mục 6.1: output có schema
│   ├── state.py         # mục 6.2: state của session
│   ├── guards.py        # mục 6.3: guardrail, hook, model dự phòng
│   ├── knowledge.py     # mục 6.4: RAG
│   ├── mcp_tools.py     # mục 6.5: MCP client
│   ├── team.py          # mục 6.6: team
│   └── workflow.py      # mục 6.7: workflow StateGraph
├── rules/agent-rules.md # file luật dự án (vai trò như CLAUDE.md)
├── mcp_customer_server.py # MCP server nhỏ (mcp 1.x) cho mục 6.5
├── demo.py              # 5 run, in ra model thấy gì
├── eval_golden.py       # bộ đo vàng
├── sync_doc.py          # cập nhật code trong tài liệu này theo file của lab
└── tests/               # test_parity.py, test_improved.py, test_agno_mapping.py, test_workflow.py, test_doc_sync.py
```

Chạy toàn bộ test (không đụng tới lockfile của repo):

```bash
uv run --no-project --python 3.13 \
  --with "langchain==1.4.6" --with "langgraph==1.2.16" \
  --with "langgraph-checkpoint-sqlite==3.1.2" --with "langchain-openai==1.7.2" \
  --with "langchain-mcp-adapters==0.3.2" --with "mcp==1.30.0" --with "numpy==2.3.4" --with pytest \
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


def _tool_name(tool: Any) -> str:
    """Tên tool dù là BaseTool, dict schema, hay class Pydantic (with_structured_output truyền class)."""
    if isinstance(tool, dict):
        return tool.get("name") or tool.get("function", {}).get("name", "?")
    return getattr(tool, "name", None) or getattr(tool, "__name__", "?")


class ScriptedChatModel(BaseChatModel):
    """Model giả: trả lần lượt `steps`, ghi lại input của từng lần gọi."""

    steps: list[AIMessage]
    calls: list[list[BaseMessage]] = Field(default_factory=list)
    bound_tools: list[list[str]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Any, **kwargs: Any) -> ScriptedChatModel:
        self.bound_tools.append([_tool_name(t) for t in tools])
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


def resume_all(agent: Any, out: dict[str, Any], results: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Model gọi nhiều tool client trong CÙNG một lượt → nhiều interrupt. Client trả kết quả theo tool_call_id;
    LangGraph nhận `Command(resume={interrupt_id: giá trị})`. Thiếu kết quả nào thì run vẫn dừng ở interrupt đó."""
    by_interrupt = {
        i.id: results[i.value["tool_call_id"]] for i in out["__interrupt__"] if i.value["tool_call_id"] in results
    }
    return resume(agent, by_interrupt, **kwargs)
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
    name: str,
    description: str,
    model: BaseChatModel,
    tools: Sequence[BaseTool],
    system_prompt: str,
    *,
    return_direct: bool = False,
) -> BaseTool:
    """Một agent con chạy với ngữ cảnh riêng; agent chính chỉ nhận câu trả lời cuối (không nhận các bước giữa).

    `return_direct=True`: run của agent chính dừng ngay, trả nguyên văn câu của agent con (như Team mode="route").
    """
    sub = create_agent(model, tools=list(tools), system_prompt=system_prompt, checkpointer=False, name=name)

    @tool(name, description=description, return_direct=return_direct)
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

## 6. Phần còn lại của Agno trong LangChain

Mục 1–5 dựng **harness**: lịch sử, memory, giới hạn, tool client, người duyệt. [Lab 01 Agno](../self-practices/guide_01_agno.md)
có 16 phần; mục này ánh xạ các phần còn lại sang LangChain/LangGraph. Mỗi dòng có module và test đã chạy (model kịch
bản); cột cuối là chỗ hai framework **khác nhau** khi đo cùng một tình huống.

| Lab 01 Agno | LangChain / LangGraph | File | Khác biệt đã đo |
|---|---|---|---|
| Phần 2 · `output_schema` | `create_agent(response_format=ToolStrategy(Schema))` | `harness/structured.py` | Agno: sai schema thì WARNING, `content` là chuỗi, status COMPLETED. LangChain: gửi lỗi validate cho model và **cho thử lại** |
| Phần 4 · `session_state` | trường riêng trong `state_schema` + tool trả `Command(update=...)` + `@dynamic_prompt` | `harness/state.py` | Prompt đọc lại state trước **mỗi** lượt gọi model (Agno: mỗi run) |
| Phần 8 · pre/post hook, guardrail, fallback | `@before_agent`, `@after_agent`, `PIIMiddleware`, `ModelFallbackMiddleware` | `harness/guards.py` | Agno: post-hook chặn mà `content` vẫn giữ câu vi phạm. LangChain: thay hẳn message (cùng `id`) |
| Phần 6 · `Knowledge` | vector store + tool tìm kiếm có `filter` | `harness/knowledge.py` | Gần như 1–1: upsert theo id, xoá theo id, lọc metadata |
| Phần 9 · `MCPTools` | `langchain-mcp-adapters` (`MultiServerMCPClient`) | `harness/mcp_tools.py` | Adapter 0.3.2 cần **mcp<2**, Agno 3.1.3 cần **mcp>=2.1** → không chung một môi trường |
| Phần 10 · `Team` | agent trưởng nhóm + agent con làm tool (`make_subagent_tool`) | `harness/team.py` | `route` = tool `return_direct=True`; thành viên chỉ nhận `task` ở cả hai |
| Phần 11 · `Workflow` | `StateGraph` | `harness/workflow.py` | Node có `interrupt()` chạy lại từ đầu khi resume |
| Phần 7/13 · nhiều tool client cùng lượt | nhiều `interrupt()` + `Command(resume={interrupt_id: ...})` | `harness/run.py` (`resume_all`) | Trả thiếu kết quả thì run vẫn dừng ở interrupt còn lại |

Chưa ánh xạ trong lab: AgentOS (REST, trace), AG-UI, A2A, MCP server và eval của Lab 01 (Phần 12–16). Phía LangChain,
các vai này thường do LangGraph Platform/`langgraph dev`, LangSmith và adapter AG-UI của bên thứ ba đảm nhận; lab
**chưa** kiểm chứng gói nào trong số đó.

Cài thêm cho mục này: `langchain-mcp-adapters` 0.3.2, `mcp` 1.30.0, `numpy` 2.3.4 (lệnh đầy đủ ở [mục 4.0](#40-cài-đặt-và-chạy)).

### 6.1 Output có schema

`ToolStrategy(Schema)` biến schema thành một tool; model "trả kết quả" bằng cách gọi tool đó, LangChain validate
bằng Pydantic rồi đặt object vào `structured_response`. Đã đo:

- Một lần gọi model nếu output hợp lệ; ToolMessage `Returning structured response: ...` được thêm vào lịch sử.
- Sai schema: ToolMessage `Error: Failed to parse structured output for tool 'CustomerBrief': ...` quay về model, model
  sửa ở lượt sau. `handle_errors=False` thì ném `StructuredOutputValidationError`.
- Model trả lời bằng chữ thay vì gọi tool kết quả: LangChain gọi model thêm lượt nữa; tool được bind với
  `tool_choice="any"` để ép gọi tool.
- `ProviderStrategy(Schema)` dùng structured output gốc của provider (giống `output_schema` của Agno gửi
  `response_format` json_schema).

```python
# file: harness/structured.py
"""Output có schema — Agno `output_schema` ↔ LangChain `create_agent(response_format=...)`.

`ToolStrategy(Schema)`: model trả kết quả bằng cách GỌI một tool mang tên schema; LangChain validate bằng Pydantic.
Khác Agno 3.1.3 (đã đo cả hai):
- Sai schema: Agno chỉ log WARNING, `content` là chuỗi, status vẫn COMPLETED. LangChain (handle_errors=True, mặc định)
  gửi lỗi validate về cho model trong một ToolMessage và cho thử lại; handle_errors=False thì ném
  StructuredOutputValidationError.
- Model trả lời bằng chữ thay vì gọi tool kết quả: LangChain gọi model thêm lượt nữa (và bind tool với
  tool_choice="any" để ép gọi tool).
`ProviderStrategy(Schema)`: dùng structured output gốc của provider (response_format json_schema), không qua tool.
"""

from __future__ import annotations

from typing import Any, Literal

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from harness.data import CustomerDB
from harness.tools import make_server_tools


class CustomerBrief(BaseModel):
    """Tóm tắt một khách hàng cho người phụ trách."""  # docstring thành mô tả của tool kết quả

    customer_id: str = Field(pattern=r"^KH-\d{4}$", description="Mã khách hàng, ví dụ KH-0012")
    summary: str = Field(min_length=10, description="Tình hình công nợ và giao hàng, một hai câu")
    risk: Literal["thấp", "trung bình", "cao"]


def build_brief_agent(model: BaseChatModel, db: CustomerDB, *, retry_on_error: bool = True) -> Any:
    search = make_server_tools(db)[0]  # chỉ cho đọc
    return create_agent(
        model,
        tools=[search],
        system_prompt="Tra cứu khách hàng bằng search_customers rồi trả tóm tắt đúng schema.",
        response_format=ToolStrategy(CustomerBrief, handle_errors=retry_on_error),
        name="brief-agent",
    )


def brief(agent: Any, question: str) -> CustomerBrief:
    """Kết quả đã validate nằm ở `structured_response`, tách khỏi message cuối."""
    return agent.invoke({"messages": [{"role": "user", "content": question}]})["structured_response"]
```

### 6.2 State của session

```python
# file: harness/state.py
"""State của session — Agno `session_state` ↔ trường riêng trong state của LangGraph.

- `session_state={"revision": 0, ...}` ↔ `class DraftState(AgentState): revision: NotRequired[int]` + `state_schema=`.
- Tool nhận `run_context` rồi sửa `run_context.session_state` ↔ tool nhận `runtime: ToolRuntime`, trả
  `Command(update={...})`.
- `"{revision}"` trong instructions ↔ `@dynamic_prompt` đọc `request.state`, chạy trước MỖI lượt gọi model.
- Lưu theo `session_id` trong db ↔ lưu theo `thread_id` trong checkpointer.

Tham số `runtime` bị ẩn khỏi schema gửi cho model, giống `run_context` của Agno.
"""

from __future__ import annotations

from typing import Any, NotRequired

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt
from langchain.tools import ToolRuntime, tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ToolMessage
from langgraph.types import Checkpointer, Command


class DraftState(AgentState):
    revision: NotRequired[int]
    notes: NotRequired[list[str]]


@tool
def record_revision(note: str, runtime: ToolRuntime) -> Command:
    """Ghi nhận đã viết xong một phiên bản thư, kèm ghi chú ngắn về thay đổi. Chỉ gọi SAU khi đã viết xong."""
    revision = runtime.state.get("revision", 0) + 1
    notes = [*runtime.state.get("notes", []), f"v{revision}: {note}"]
    reply = ToolMessage(f"Đã ghi nhận phiên bản v{revision}", tool_call_id=runtime.tool_call_id)
    return Command(update={"revision": revision, "notes": notes, "messages": [reply]})


@dynamic_prompt
def revision_prompt(request: ModelRequest) -> str:
    return (
        "Bạn soạn thư cho khách hàng theo nhiều phiên bản trong cùng một phiên làm việc.\n"
        f"Phiên bản hiện tại: v{request.state.get('revision', 0)}. Viết xong một bản thì gọi record_revision."
    )


def build_state_agent(model: BaseChatModel, checkpointer: Checkpointer) -> Any:
    return create_agent(
        model,
        tools=[record_revision],
        state_schema=DraftState,
        middleware=[revision_prompt],
        checkpointer=checkpointer,
        name="draft-agent",
    )
```

Test đo được: system prompt của ba lượt gọi model lần lượt là `v0` (trước khi gọi tool), `v1` (ngay sau tool, cùng
run) và `v1` (run sau): `@dynamic_prompt` chạy trước mỗi lượt gọi model, trong khi `{revision}` của Agno chỉ được
thay một lần đầu run. Tham số `runtime` không có trong schema gửi cho model.

### 6.3 Guardrail, hook và model dự phòng

```python
# file: harness/guards.py
"""Guardrail, pre/post hook và model dự phòng — Agno Phần 8 ↔ middleware của LangChain.

- `pre_hooks` + `InputCheckError` ↔ `@before_agent(can_jump_to=["end"])` trả `{"jump_to": "end"}`.
  Cả hai không gọi model.
- `PIIDetectionGuardrail(mask_pii=True)` ↔ `PIIMiddleware("email", strategy="redact" | "mask")`.
  Agno che thành `***********`; LangChain thành `[REDACTED_EMAIL]` (redact) hoặc `lan@****.vn` (mask).
- `post_hooks` + `OutputCheckError` ↔ `@after_agent` trả message CÙNG `id` để ghi đè.
  Agno: status ERROR nhưng `content` vẫn là output vi phạm. LangChain: message vi phạm bị thay hẳn.
- `FallbackConfig(on_error=[model])` ↔ `ModelFallbackMiddleware(model)`.
  Cả hai không ghi lại model nào đã trả lời; cần thì tự ghi.
"""

from __future__ import annotations

import re
from typing import Any

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import ModelFallbackMiddleware, PIIMiddleware, after_agent, before_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from harness.data import CustomerDB
from harness.tools import make_server_tools

BLOCKED_URL = "[bị chặn] Câu trả lời chứa URL — không được dẫn nguồn web."


@before_agent(can_jump_to=["end"])
def require_customer_id(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Chặn TRƯỚC khi gọi model: yêu cầu phải nêu mã khách hàng."""
    if not re.search(r"KH-\d{4}", state["messages"][-1].text):
        return {"messages": [AIMessage("Yêu cầu phải nêu mã khách hàng dạng KH-0012.")], "jump_to": "end"}
    return None


@after_agent
def no_external_urls(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Kiểm tra SAU khi có câu trả lời: message mới cùng id thay message cũ (reducer add_messages)."""
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and re.search(r"https?://", last.text):
        return {"messages": [AIMessage(id=last.id, content=BLOCKED_URL)]}
    return None


def build_guarded_agent(model: BaseChatModel, db: CustomerDB, *, fallback: BaseChatModel | None = None) -> Any:
    middleware: list[Any] = [
        require_customer_id,
        PIIMiddleware("email", strategy="redact", apply_to_input=True),  # model thấy [REDACTED_EMAIL]
        no_external_urls,
    ]
    if fallback is not None:
        middleware.append(ModelFallbackMiddleware(fallback))  # model chính lỗi → thử model này
    return create_agent(model, tools=make_server_tools(db)[:1], middleware=middleware, name="guarded-agent")
```

`@before_agent(can_jump_to=["end"])` trả `{"jump_to": "end"}` để kết thúc run trước lượt gọi model đầu tiên.
`@after_agent` chạy một lần khi run xong; trả `AIMessage` cùng `id` với message cuối thì reducer `add_messages`
**thay** message đó, nên câu vi phạm không còn trong state. `PIIMiddleware(apply_to_input=True)` che email trước
khi model thấy, và state cũng chỉ giữ bản đã che.

### 6.4 Knowledge (RAG)

```python
# file: harness/knowledge.py
"""Knowledge (RAG) — Agno `Knowledge` + `search_knowledge=True` ↔ vector store + một tool tìm kiếm.

| Agno | LangChain |
|---|---|
| `kb.insert(name=..., upsert=True)` | `store.add_documents(docs, ids=[...])` — cùng id thì ghi đè |
| `kb.remove_vectors_by_name(name)` | `store.delete(ids=[...])` |
| `kb.search(q, filters={"source": ...})` | `store.similarity_search(q, k, filter=lambda d: ...)` |
| `search_knowledge=True` → tool `search_knowledge_base` | tự viết tool gọi `similarity_search` |

`InMemoryVectorStore` cần numpy. `KeywordEmbeddings` băm từ khoá (giống `/v1/embeddings` của mock_llm ở lab Agno):
câu chung từ khoá thì gần nhau — đủ để học luồng offline, không phải semantic thật. Production: OpenAIEmbeddings,
Ollama... và vector DB có lưu bền (pgvector, LanceDB, Qdrant).
"""

from __future__ import annotations

import hashlib
import math
import re

from langchain.tools import BaseTool, tool
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore

POLICIES: dict[str, tuple[str, dict]] = {  # id ổn định → (nội dung, metadata)
    "no-90": ("Nợ trên 90% hạn mức tín dụng: tạm dừng giao hàng mới, báo trưởng phòng tín dụng.", {"source": "policy"}),
    "no-qua-han": ("Nợ quá hạn 30 ngày: gửi thư nhắc nợ lần một, sau 60 ngày gọi điện.", {"source": "policy"}),
    "thu-nhac-no": ("Thư nhắc nợ phải nêu tên khách hàng, số tiền nợ và hạn thanh toán.", {"source": "style"}),
}


class KeywordEmbeddings(Embeddings):
    def __init__(self, dims: int = 256) -> None:
        self.dims = dims

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dims
        for word in re.findall(r"\w+", text.lower()):
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dims] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def index(store: InMemoryVectorStore, docs: dict[str, tuple[str, dict]]) -> dict[str, int]:
    """Đồng bộ store với nguồn: ghi đè theo id, xoá id đã biến mất khỏi nguồn."""
    removed = [doc_id for doc_id in store.store if doc_id not in docs]
    if removed:
        store.delete(ids=removed)
    store.add_documents([Document(page_content=text, metadata=meta) for text, meta in docs.values()], ids=list(docs))
    return {"upserted": len(docs), "removed": len(removed)}


def make_policy_tool(store: InMemoryVectorStore) -> BaseTool:
    @tool
    def search_policies(query: str) -> str:
        """Tìm chính sách công nợ của công ty (chỉ chính sách, không có số liệu khách hàng)."""
        hits = store.similarity_search(query, k=2, filter=lambda doc: doc.metadata["source"] == "policy")
        return "\n".join(f"[{doc.id}] {doc.page_content}" for doc in hits) or "Không tìm thấy chính sách phù hợp."

    return search_policies
```

### 6.5 MCP client

Server MCP nhỏ của lab (FastMCP của mcp 1.x, cùng dữ liệu khách hàng):

```python
# file: mcp_customer_server.py
"""MCP server nhỏ cho lab: công bố tra cứu khách hàng (dữ liệu của harness/data.py) qua stdio.

Dùng SDK mcp 1.x (FastMCP) vì langchain-mcp-adapters 0.3.2 cần mcp<2. Lab Agno (Agno 3.1.3) thì cần mcp>=2.1:
hai lab chạy ở hai môi trường riêng.

    python mcp_customer_server.py      # thường không chạy tay: client khởi động nó như một subprocess
"""

from __future__ import annotations

from harness.data import CustomerDB
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

mcp = FastMCP("customers")
DB = CustomerDB()


@mcp.tool()
def find_customers(query: str) -> list[dict]:
    """Tìm khách hàng theo mã (KH-0012), một phần tên hoặc thành phố."""
    rows = DB.search(query)
    if not rows:
        raise ToolError(f"Không thấy khách hàng khớp '{query}'. Thử mã dạng KH-0012 hoặc tên thành phố.")
    return rows


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

```python
# file: harness/mcp_tools.py
"""MCP client — Agno `MCPTools` ↔ `langchain-mcp-adapters` (`MultiServerMCPClient`).

Đã đo với langchain-mcp-adapters 0.3.2 (cần mcp<2; lab Agno cần mcp>=2.1 → hai lab, hai môi trường):
- `get_tools()` đọc danh sách tool + schema từ server, trả `StructuredTool` CHỈ có bản async → agent phải chạy
  `ainvoke`; `invoke` đồng bộ ném `NotImplementedError: StructuredTool does not support sync invocation`.
- Mặc định mỗi lần gọi tool mở một session MỚI (với stdio là khởi động lại subprocess server). Muốn giữ một
  session cho cả run: `async with client.session(name) as s: tools = await load_mcp_tools(s)`.
- `ToolError` của server tới được model: ToolMessage `status="error"`, nội dung "Error executing tool ...: <lỗi>".
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

LAB = Path(__file__).resolve().parents[1]
SERVERS = {
    "customers": {"command": sys.executable, "args": [str(LAB / "mcp_customer_server.py")], "transport": "stdio"},
}


async def ask_with_mcp(model: BaseChatModel, question: str, *, one_session: bool = True) -> dict[str, Any]:
    client = MultiServerMCPClient(SERVERS)
    system = "Tra cứu khách hàng bằng tool MCP find_customers; không tự đoán số liệu."
    if not one_session:
        agent = create_agent(model, tools=await client.get_tools(), system_prompt=system)
        return await agent.ainvoke({"messages": [{"role": "user", "content": question}]})
    async with client.session("customers") as session:  # một subprocess cho cả run
        agent = create_agent(model, tools=await load_mcp_tools(session), system_prompt=system)
        return await agent.ainvoke({"messages": [{"role": "user", "content": question}]})
```

So với `MCPTools` của Agno: cả hai đọc tool + schema từ server, đều cần chạy async. Khác ở mặc định kết nối: Agno mở
kết nối một lần trong `async with tools:`; adapter mở session mới cho **mỗi lần gọi tool** (với stdio là khởi động
lại subprocess) trừ khi bạn dùng `client.session(...)` như `ask_with_mcp(one_session=True)`.

### 6.6 Team

`make_subagent_tool` (mục 5.3, lớp 6) nay nhận `return_direct`. Team là một agent trưởng nhóm có các agent con làm tool:

```python
# file: harness/team.py
"""Team — Agno `Team(mode=...)` ↔ agent trưởng nhóm có các agent con làm tool (`make_subagent_tool`).

| Agno | LangChain |
|---|---|
| `members=[agent, ...]`, `role` của thành viên | mỗi thành viên là một tool; `description` của tool đóng vai `role` |
| `delegate_task_to_member(member_id, task)` | gọi tool của thành viên với `task` |
| `mode="coordinate"`: trưởng nhóm tổng hợp | tool thường: kết quả quay về trưởng nhóm, nó viết câu trả lời cuối |
| `mode="route"`: trả nguyên văn câu trả lời của thành viên | tool `return_direct=True`: run dừng ngay sau tool |
| `run.member_responses` | các ToolMessage trong `messages` |

Giống Agno: thành viên CHỈ nhận `task` trưởng nhóm viết, không nhận câu hỏi gốc của người dùng.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel

from harness.data import CustomerDB
from harness.improved import make_subagent_tool
from harness.tools import make_server_tools

LEAD = "Bạn là trưởng nhóm chăm sóc khách hàng. Giao tra cứu cho ask_analyst, giao viết thư cho ask_writer."
ANALYST = "Bạn là chuyên viên tra cứu khách hàng. Chỉ trả số liệu lấy từ tool."
WRITER = "Bạn là người viết thư cho khách hàng. Không thêm số liệu ngoài phần được giao."


def build_team(lead: BaseChatModel, member: Callable[[str], BaseChatModel], db: CustomerDB, mode: str = "coordinate"):
    """`member(name)` trả model cho từng thành viên (test truyền model kịch bản riêng cho mỗi người)."""
    direct = mode == "route"
    analyst = make_subagent_tool(
        "ask_analyst",
        "Tra cứu dữ liệu khách hàng: hạn mức, công nợ, trạng thái giao hàng.",
        member("analyst"),
        make_server_tools(db)[:1],
        ANALYST,
        return_direct=direct,
    )
    writer = make_subagent_tool(
        "ask_writer",
        "Viết thư cho khách hàng từ dữ liệu được giao.",
        member("writer"),
        [],
        WRITER,
        return_direct=direct,
    )
    return create_agent(lead, tools=[analyst, writer], system_prompt=LEAD, name=f"team-{mode}")


def member_answers(out: dict[str, Any]) -> list[tuple[str, str]]:
    """(tên thành viên, câu trả lời) — tương đương `run.member_responses` của Agno."""
    return [(m.name, m.content) for m in out["messages"] if m.type == "tool"]
```

### 6.7 Workflow

Cùng cấu trúc với workflow báo cáo ở [Phần 11 của Lab 01](../self-practices/agno/01d-mcp-team-workflow.md#phần-11--workflow-luồng-do-code-quyết-định),
áp vào bài toán thư nhắc nợ. Docstring có bảng đối chiếu từng khối `Parallel`, `Loop`, `Router`, `Condition`,
`HumanReview` với `StateGraph`.

```python
# file: harness/workflow.py
"""Workflow — Agno `Workflow` (Phần 11 của Lab 01) ↔ `StateGraph` của LangGraph.

Bài toán: viết thư nhắc nợ cho một khách hàng. Luồng giống workflow báo cáo của Agno, từng khối một:

    START ─┬─ fetch_customer ─┐                     (Agno: Parallel)
           └─ fetch_policy  ──┴─ prepare ─► mode?   (Agno: Router)
                 ├─ "chỉ số liệu" → numbers_only (không gọi LLM) ─────────────────┐
                 └─ write (LLM) → gate ─► ok? → alert? ─► escalate ─► review ─► publish   (Condition, HumanReview)
                       ▲            │ sai, còn lượt                ▲   └─ không ─┘
                       └────────────┘ (Agno: Loop, max 3) ── hết lượt → failed → END (Agno: StepOutput(stop=True))

| Agno | LangGraph |
|---|---|
| `Step(executor=fn)` | node là hàm nhận state, trả dict cập nhật |
| `Step(agent=...)` | node gọi model (`with_structured_output`) hoặc một agent |
| `Parallel(a, b)` | hai cạnh từ START; node có hai cạnh vào chạy sau khi cả hai xong |
| `Loop(end_condition, max_iterations)` | cạnh có điều kiện quay về `write` + bộ đếm `attempt` trong state |
| `Router(selector)` / `Condition(evaluator)` | `add_conditional_edges(node, hàm chọn)` |
| `HumanReview` | `interrupt()` trong node `review`; chạy tiếp bằng `Command(resume=...)` |
| `session_state` theo `session_id` | state theo `thread_id` trong checkpointer |
| `continue_run(run_id=..., session_id=...)` | graph mới, cùng checkpointer, `invoke(Command(resume=...), thread_id)` |

Khác Agno: node chứa `interrupt()` chạy lại TỪ ĐẦU khi resume → không đặt side effect trước `interrupt()`.
"""

from __future__ import annotations

import json
from typing import Any, NotRequired, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Checkpointer, interrupt
from pydantic import BaseModel, Field, ValidationError

from harness.data import CustomerDB
from harness.knowledge import POLICIES

WRITER = "Bạn viết thư nhắc nợ cho khách hàng bằng tiếng Việt, lịch sự, ngắn gọn."
MAX_DRAFTS = 3


class Letter(BaseModel):
    subject: str = Field(min_length=5)
    body: str = Field(min_length=20)


class LetterFlow(TypedDict):
    customer_id: str
    instruction: str
    customer: NotRequired[dict]
    policy: NotRequired[str]
    attempt: NotRequired[int]
    feedback: NotRequired[str]
    letter: NotRequired[dict | None]
    escalation: NotRequired[str | None]
    status: NotRequired[str]  # drafting | failed | rejected | sent
    revision: NotRequired[int]  # tăng mỗi lần gửi trong cùng thread, như session_state["revision"] của Agno
    last_sent: NotRequired[str]


def money(value: int) -> str:
    return f"{value:,}".replace(",", ".")  # 79000000 → 79.000.000


def build_workflow(model: BaseChatModel, db: CustomerDB, outbox: list[dict], checkpointer: Checkpointer):
    # ------------------------------------------------------------ bước hàm thuần (không LLM)
    def fetch_customer(state: LetterFlow) -> dict:
        return {"customer": db.get(state["customer_id"])}

    def fetch_policy(state: LetterFlow) -> dict:
        return {"policy": "\n".join(text for text, meta in POLICIES.values() if meta["source"] == "policy")}

    def prepare(state: LetterFlow) -> dict:
        return {"attempt": 0, "feedback": "", "letter": None, "escalation": None, "status": "drafting"}

    def numbers_only(state: LetterFlow) -> dict:
        customer = state["customer"]
        body = f"Kính gửi {customer['name']}, công nợ hiện tại của quý khách là {money(customer['debt'])} đồng."
        return {"letter": Letter(subject="Thông báo công nợ", body=body).model_dump()}

    # ------------------------------------------------------------ bước LLM
    def write(state: LetterFlow) -> dict:
        request = {
            "instruction": state["instruction"],
            "customer": state["customer"],
            "policy": state["policy"],
            "previous_letter": state.get("last_sent", ""),
            "feedback_from_last_attempt": state.get("feedback", ""),
        }
        messages = [SystemMessage(WRITER), HumanMessage(json.dumps(request, ensure_ascii=False))]
        try:
            letter = model.with_structured_output(Letter).invoke(messages)
        except ValidationError:
            return {"letter": None}
        return {"letter": letter.model_dump()}

    # ------------------------------------------------------------ cổng kiểm tra bằng code
    def gate(state: LetterFlow) -> dict:
        customer, letter = state["customer"], state.get("letter")
        problems: list[str] = []
        if letter is None:
            problems.append("Thư không đúng schema Letter")
        else:
            if customer["name"] not in letter["body"]:
                problems.append(f"Thư chưa nêu tên khách hàng {customer['name']}")
            if money(customer["debt"]) not in letter["body"]:
                problems.append(f"Thư chưa nêu đúng số tiền nợ {money(customer['debt'])} đồng")
        return {"attempt": state.get("attempt", 0) + 1, "feedback": "; ".join(problems)}

    def after_gate(state: LetterFlow) -> str:
        if not state["feedback"]:
            return "passed"
        return "write" if state["attempt"] < MAX_DRAFTS else "failed"

    def failed(state: LetterFlow) -> dict:
        return {"status": "failed"}

    def alert(state: LetterFlow) -> str:
        customer = state["customer"]
        return "escalate" if customer["debt"] > 0.9 * customer["credit_limit"] else "review"

    def escalate(state: LetterFlow) -> dict:
        return {"escalation": "Báo trưởng phòng tín dụng: nợ vượt 90% hạn mức, tạm dừng giao hàng mới."}

    # ------------------------------------------------------------ người duyệt và gửi
    def review(state: LetterFlow) -> dict:
        decision = interrupt({"type": "review", "letter": state["letter"], "escalation": state.get("escalation")})
        return {"status": "approved" if decision.get("approve") else "rejected"}

    def publish(state: LetterFlow) -> dict:
        revision = state.get("revision", 0) + 1
        outbox.append({"customer_id": state["customer_id"], "revision": revision, **state["letter"]})
        return {"status": "sent", "revision": revision, "last_sent": state["letter"]["subject"]}

    # ------------------------------------------------------------ ráp đồ thị
    graph = StateGraph(LetterFlow)
    for name, node in [
        ("fetch_customer", fetch_customer),
        ("fetch_policy", fetch_policy),
        ("prepare", prepare),
        ("numbers_only", numbers_only),
        ("write", write),
        ("gate", gate),
        ("failed", failed),
        ("escalate", escalate),
        ("review", review),
        ("publish", publish),
    ]:
        graph.add_node(name, node)
    graph.add_edge(START, "fetch_customer")
    graph.add_edge(START, "fetch_policy")
    graph.add_edge(["fetch_customer", "fetch_policy"], "prepare")  # chờ CẢ HAI nhánh song song
    graph.add_conditional_edges(
        "prepare", lambda s: "numbers_only" if "chỉ số liệu" in s["instruction"].lower() else "write"
    )
    graph.add_edge("write", "gate")
    graph.add_conditional_edges("gate", after_gate, {"passed": "alert", "write": "write", "failed": "failed"})
    graph.add_node("alert", lambda s: {})  # điểm rẽ của Condition
    graph.add_conditional_edges("alert", alert)
    graph.add_edge("numbers_only", "alert")
    graph.add_edge("escalate", "review")
    graph.add_conditional_edges("review", lambda s: "publish" if s["status"] == "approved" else END)
    graph.add_edge("publish", END)
    graph.add_edge("failed", END)
    return graph.compile(checkpointer=checkpointer)


def start(flow: Any, thread: str, customer_id: str, instruction: str) -> dict[str, Any]:
    return flow.invoke(
        {"customer_id": customer_id, "instruction": instruction}, {"configurable": {"thread_id": thread}}
    )
```

Đọc code:

- Song song: hai cạnh từ `START`, `add_edge(["fetch_customer", "fetch_policy"], "prepare")` chờ cả hai.
- Vòng sửa có giới hạn: `gate` là code; `after_gate` trả `"write"` khi còn lượt, `"failed"` khi hết, `"passed"` khi đạt.
- Người duyệt: `review` gọi `interrupt(...)`; khi resume, node này chạy lại **từ đầu** tới `interrupt()` rồi nhận giá
  trị resume, nên trước `interrupt()` không có side effect. Việc gửi thư nằm ở node `publish` sau đó.
- `prepare` đặt lại các khoá của một lần chạy; `revision` và `last_sent` giữ qua các lần chạy trên cùng `thread_id`,
  như `session_state` của workflow Agno.

### 6.8 Nhiều tool client trong cùng một lượt

Câu hỏi mở của lab cũ ("hai tool client được gọi song song: resume thế nào?") đã có lời giải đo được: mỗi tool client
là một `interrupt()` riêng, có `id` riêng. Client trả kết quả theo `tool_call_id`; `resume_all` (cuối
[mục 4.8](#48-gọi-agent-một-request-đi-từ-client-vào)) đổi thành `Command(resume={interrupt_id: giá trị})`. Trả một phần thì
run vẫn dừng ở tool còn thiếu, model chưa được gọi lại.

### 6.9 Test của mục này

```python
# file: tests/test_agno_mapping.py
"""Phần còn lại của Agno (Lab 01) dựng bằng LangChain: hành vi đã đo của từng bên, chỗ giống và chỗ khác."""

from __future__ import annotations

import asyncio

import pytest
from harness.data import CustomerDB
from harness.guards import BLOCKED_URL, build_guarded_agent
from harness.knowledge import POLICIES, KeywordEmbeddings, index, make_policy_tool
from harness.mcp_tools import SERVERS, ask_with_mcp
from harness.model import ScriptedChatModel, call, say
from harness.run import pending, resume_all
from harness.state import build_state_agent
from harness.structured import CustomerBrief, brief, build_brief_agent
from harness.team import build_team, member_answers
from harness.tools import CLIENT_TOOLS
from langchain.agents import create_agent
from langchain.agents.structured_output import StructuredOutputValidationError
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver

GOOD = {"customer_id": "KH-0047", "summary": "Nợ 79 triệu, sát hạn mức 80 triệu.", "risk": "cao"}


def ask(agent, text: str, thread: str | None = None) -> dict:
    config = {"configurable": {"thread_id": thread}} if thread else None
    return agent.invoke({"messages": [{"role": "user", "content": text}]}, config)


# ---------------------------------------------------------------- Phần 2: output có schema
def test_structured_output_is_a_tool_call_validated_by_pydantic():
    model = ScriptedChatModel(steps=[call("search_customers", query="KH-0047"), call("CustomerBrief", **GOOD)])
    result = brief(build_brief_agent(model, CustomerDB()), "Tóm tắt KH-0047")
    assert isinstance(result, CustomerBrief) and result.risk == "cao"
    assert model.bound_tools[0] == ["search_customers", "CustomerBrief"]  # schema thành một tool


def test_invalid_output_is_sent_back_and_retried_unlike_agno():
    bad = {**GOOD, "customer_id": "0047"}
    model = ScriptedChatModel(steps=[call("CustomerBrief", **bad), call("CustomerBrief", **GOOD)])
    result = brief(build_brief_agent(model, CustomerDB()), "Tóm tắt KH-0047")
    assert result.customer_id == "KH-0047" and len(model.calls) == 2
    error = next(m for m in model.calls[1] if isinstance(m, ToolMessage))
    assert "Failed to parse structured output" in error.content  # model đọc lỗi validate rồi sửa


def test_retry_can_be_turned_off():
    model = ScriptedChatModel(steps=[call("CustomerBrief", **{**GOOD, "risk": "rất cao"})])
    with pytest.raises(StructuredOutputValidationError):
        brief(build_brief_agent(model, CustomerDB(), retry_on_error=False), "Tóm tắt KH-0047")


# ---------------------------------------------------------------- Phần 4: state của session
def test_state_is_updated_by_tool_and_read_by_prompt_across_runs():
    model = ScriptedChatModel(steps=[call("record_revision", note="bản đầu"), say("Đã viết v1."), say("Đang ở v1.")])
    agent = build_state_agent(model, InMemorySaver())
    ask(agent, "Viết thư nhắc nợ KH-0047", thread="s1")
    out = ask(agent, "Đang ở phiên bản nào?", thread="s1")
    assert out["revision"] == 1 and out["notes"] == ["v1: bản đầu"]
    prompts = [call_messages[0].content for call_messages in model.calls]  # system prompt của từng lượt gọi model
    assert "v0" in prompts[0] and "v1" in prompts[1] and "v1" in prompts[2]  # đọc lại state trước MỖI lượt


def test_runtime_parameter_is_hidden_from_the_model():
    from harness.state import record_revision

    assert list(record_revision.tool_call_schema.model_json_schema()["properties"]) == ["note"]


# ---------------------------------------------------------------- Phần 8: guardrail, hook, model dự phòng
def test_pre_hook_blocks_without_calling_the_model():
    model = ScriptedChatModel(steps=[])
    out = ask(build_guarded_agent(model, CustomerDB()), "chào bạn")
    assert out["messages"][-1].content.startswith("Yêu cầu phải nêu mã khách hàng") and model.calls == []


def test_pii_is_redacted_before_the_model_and_in_state():
    model = ScriptedChatModel(steps=[say("Đã ghi nhận.")])
    out = ask(build_guarded_agent(model, CustomerDB()), "KH-0012, gửi về lan@corp.vn")
    assert model.calls[0][-1].content == "KH-0012, gửi về [REDACTED_EMAIL]"
    assert "lan@corp.vn" not in out["messages"][0].content  # khác Agno: state cũng không giữ email


def test_post_hook_replaces_the_bad_answer_unlike_agno():
    model = ScriptedChatModel(steps=[say("Theo https://example.com, ngành tăng 32,5%.")])
    out = ask(build_guarded_agent(model, CustomerDB()), "So sánh KH-0012 với ngành")
    assert out["messages"][-1].content == BLOCKED_URL
    assert not any("example.com" in m.content for m in out["messages"])  # Agno: content vẫn giữ câu vi phạm


class DeadModel(ScriptedChatModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls.append(list(messages))
        raise ConnectionError("provider không phản hồi")


def test_fallback_model_answers_when_primary_fails():
    primary, backup = DeadModel(steps=[]), ScriptedChatModel(steps=[say("Trả lời từ model dự phòng.")])
    out = ask(build_guarded_agent(primary, CustomerDB(), fallback=backup), "KH-0012 còn nợ bao nhiêu?")
    assert out["messages"][-1].content == "Trả lời từ model dự phòng."
    assert len(primary.calls) == 1 and len(backup.calls) == 1


# ---------------------------------------------------------------- Phần 6: knowledge (RAG)
def test_index_upserts_by_id_and_removes_deleted_documents():
    store = InMemoryVectorStore(KeywordEmbeddings())
    assert index(store, POLICIES) == {"upserted": 3, "removed": 0}
    changed = {k: (v[0].replace("90%", "80%"), v[1]) for k, v in POLICIES.items() if k != "no-qua-han"}
    assert index(store, changed) == {"upserted": 2, "removed": 1}
    assert sorted(store.store) == ["no-90", "thu-nhac-no"] and "80%" in store.store["no-90"]["text"]


def test_agent_searches_policies_with_a_metadata_filter():
    store = InMemoryVectorStore(KeywordEmbeddings())
    index(store, POLICIES)
    model = ScriptedChatModel(steps=[call("search_policies", query="nợ vượt hạn mức tín dụng"), say("Tạm dừng giao.")])
    out = ask(create_agent(model, tools=[make_policy_tool(store)]), "Nợ gần hạn mức thì làm gì?")
    (found,) = [m.content for m in out["messages"] if isinstance(m, ToolMessage)]
    assert found.startswith("[no-90]") and "[thu-nhac-no]" not in found  # style guide bị lọc ra


# ---------------------------------------------------------------- Phần 9: MCP client
def test_mcp_tools_come_from_the_server_and_errors_reach_the_model():
    model = ScriptedChatModel(
        steps=[call("find_customers", query="Hà Nội"), call("find_customers", query="zzz"), say("ok")]
    )
    out = asyncio.run(ask_with_mcp(model, "Khách ở Hà Nội?"))
    assert model.bound_tools[0] == ["find_customers"]  # tên + schema lấy từ server
    found, missing = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    assert "KH-0012" in str(found.content) and "KH-0047" in str(found.content)
    assert missing.status == "error" and "Không thấy khách hàng khớp 'zzz'" in str(missing.content)


def test_mcp_tools_need_async_invocation():
    tools = asyncio.run(MultiServerMCPClient(SERVERS).get_tools())
    model = ScriptedChatModel(steps=[call("find_customers", query="KH-0012"), say("ok")])
    with pytest.raises(NotImplementedError, match="sync invocation"):
        ask(create_agent(model, tools=tools), "KH-0012?")  # invoke đồng bộ


# ---------------------------------------------------------------- Phần 10: team
def test_coordinate_leader_delegates_then_synthesizes():
    lead = ScriptedChatModel(
        steps=[
            call("ask_analyst", task="Công nợ và hạn mức của KH-0047?"),
            call("ask_writer", task="Viết 2 câu nhắc nợ 79.000.000 đồng cho Hải Đăng"),
            say("Đã có số liệu và thư nháp cho KH-0047."),
        ]
    )
    members = {
        "analyst": ScriptedChatModel(steps=[call("search_customers", query="KH-0047"), say("Nợ 79 triệu / 80 triệu.")]),
        "writer": ScriptedChatModel(steps=[say("Kính gửi Hải Đăng, quý khách còn nợ 79.000.000 đồng.")]),
    }
    out = ask(build_team(lead, members.__getitem__, CustomerDB()), "Chuẩn bị nhắc nợ KH-0047")
    assert member_answers(out) == [
        ("ask_analyst", "Nợ 79 triệu / 80 triệu."),
        ("ask_writer", "Kính gửi Hải Đăng, quý khách còn nợ 79.000.000 đồng."),
    ]
    assert out["messages"][-1].content == "Đã có số liệu và thư nháp cho KH-0047." and len(lead.calls) == 3
    member_input = [m.content for m in members["writer"].calls[0] if m.type == "human"]
    assert member_input == ["Viết 2 câu nhắc nợ 79.000.000 đồng cho Hải Đăng"]  # chỉ nhận task, như Agno


def test_route_returns_the_member_answer_verbatim():
    lead = ScriptedChatModel(steps=[call("ask_analyst", task="Hạn mức KH-0012?")])
    members = {
        "analyst": ScriptedChatModel(steps=[say("Hạn mức 300.000.000 đồng.")]),
        "writer": ScriptedChatModel(steps=[]),
    }
    out = ask(build_team(lead, members.__getitem__, CustomerDB(), mode="route"), "Hạn mức của KH-0012?")
    assert out["messages"][-1].content == "Hạn mức 300.000.000 đồng." and len(lead.calls) == 1


# ---------------------------------------------------------------- Phần 7/13: nhiều tool client cùng lượt
def test_two_client_tools_in_one_turn_resume_together():
    both = AIMessage(
        content="",
        tool_calls=[
            {"name": "excel_read_rows", "args": {"rows": [2]}, "id": "c1"},
            {"name": "excel_set_values", "args": {"cells": {"E2": "Hoàn tất"}}, "id": "c2"},
        ],
    )
    model = ScriptedChatModel(steps=[both, say("Đã đọc dòng 2 và ghi E2.")])
    agent = create_agent(model, tools=CLIENT_TOOLS, checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "multi"}}
    out = agent.invoke({"messages": [{"role": "user", "content": "Đọc dòng 2 rồi đánh dấu hoàn tất"}]}, config)
    assert sorted(p["tool_call_id"] for p in pending(out)) == ["c1", "c2"]  # hai interrupt cùng lúc

    half = resume_all(agent, out, {"c1": "Dòng 2: Công ty An Phát"}, thread="multi")
    assert [p["tool_call_id"] for p in pending(half)] == ["c2"] and len(model.calls) == 1  # còn chờ c2

    done = resume_all(agent, half, {"c2": "Đã ghi E2"}, thread="multi")
    assert pending(done) == [] and done["messages"][-1].content == "Đã đọc dòng 2 và ghi E2."
    results = {m.tool_call_id: m.content for m in done["messages"] if isinstance(m, ToolMessage)}
    assert results == {"c1": "Dòng 2: Công ty An Phát", "c2": "Đã ghi E2"}
```

```python
# file: tests/test_workflow.py
"""Workflow thư nhắc nợ bằng StateGraph: cùng sáu tình huống với test workflow của Agno (Lab 01, Phần 11)."""

from __future__ import annotations

import sqlite3

from harness.data import CustomerDB
from harness.model import ScriptedChatModel, call
from harness.run import pending
from harness.workflow import MAX_DRAFTS, build_workflow, start
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

GOOD = {"subject": "Nhắc thanh toán công nợ", "body": "Kính gửi Hải Đăng, quý khách còn nợ 79.000.000 đồng."}
NO_AMOUNT = {"subject": "Nhắc thanh toán công nợ", "body": "Kính gửi Hải Đăng, mong quý khách sớm thanh toán."}


def letter(**fields) -> object:
    return call("Letter", **fields)


def flow(model, outbox, checkpointer=None):
    return build_workflow(model, CustomerDB(), outbox, checkpointer or InMemorySaver())


def approve(graph, thread: str, ok: bool = True) -> dict:
    return graph.invoke(Command(resume={"approve": ok}), {"configurable": {"thread_id": thread}})


def test_rewrites_with_feedback_then_waits_for_review():
    model, outbox = ScriptedChatModel(steps=[letter(**NO_AMOUNT), letter(**GOOD)]), []
    graph = flow(model, outbox)
    out = start(graph, "w1", "KH-0047", "Viết thư nhắc nợ")
    (review,) = pending(out)
    assert review["type"] == "review" and review["letter"] == GOOD and outbox == []  # chưa duyệt thì chưa gửi
    second_prompt = model.calls[1][-1].content
    assert "Thư chưa nêu đúng số tiền nợ 79.000.000 đồng" in second_prompt  # lần 2 nhận nhận xét của cổng
    assert review["escalation"].startswith("Báo trưởng phòng tín dụng")  # nợ 79/80 triệu > 90% hạn mức

    final = approve(graph, "w1")
    assert final["status"] == "sent" and final["revision"] == 1 and outbox[0]["subject"] == GOOD["subject"]


def test_draft_with_invalid_schema_counts_as_a_failed_attempt():
    model, outbox = ScriptedChatModel(steps=[letter(subject="x", body="ngắn"), letter(**GOOD)]), []
    out = start(flow(model, outbox), "w7", "KH-0047", "Viết thư nhắc nợ")
    assert pending(out)[0]["letter"] == GOOD and len(model.calls) == 2
    assert "Thư không đúng schema Letter" in model.calls[1][-1].content


def test_exhausted_drafts_stop_the_flow():
    model, outbox = ScriptedChatModel(steps=[letter(**NO_AMOUNT)] * MAX_DRAFTS), []
    out = start(flow(model, outbox), "w2", "KH-0047", "Viết thư nhắc nợ")
    assert out["status"] == "failed" and pending(out) == [] and len(model.calls) == MAX_DRAFTS and outbox == []


def test_numbers_only_route_skips_the_llm():
    model, outbox = ScriptedChatModel(steps=[]), []
    graph = flow(model, outbox)
    out = start(graph, "w3", "KH-0012", "Chỉ số liệu thôi")
    assert pending(out)[0]["letter"]["body"].endswith("120.000.000 đồng.") and model.calls == []
    assert pending(out)[0]["escalation"] is None  # 120/300 triệu: không vượt 90% hạn mức
    assert approve(graph, "w3")["status"] == "sent"


def test_rejected_review_sends_nothing():
    model, outbox = ScriptedChatModel(steps=[letter(**GOOD)]), []
    graph = flow(model, outbox)
    start(graph, "w4", "KH-0047", "Viết thư nhắc nợ")
    final = approve(graph, "w4", ok=False)
    assert final["status"] == "rejected" and outbox == [] and final.get("revision", 0) == 0


def test_second_run_on_the_same_thread_builds_on_the_first():
    model, outbox = ScriptedChatModel(steps=[letter(**GOOD), letter(**{**GOOD, "subject": "Nhắc nợ lần hai"})]), []
    graph = flow(model, outbox)
    start(graph, "w5", "KH-0047", "Viết thư nhắc nợ")
    approve(graph, "w5")
    start(graph, "w5", "KH-0047", "Viết lại, giọng cứng rắn hơn")
    final = approve(graph, "w5")
    assert final["revision"] == 2 and [m["revision"] for m in outbox] == [1, 2]
    assert GOOD["subject"] in model.calls[1][-1].content  # lần 2 viết dựa trên thư đã gửi lần 1


def test_resume_from_a_new_graph_instance(tmp_path):
    db_file = tmp_path / "flow.db"
    model, outbox = ScriptedChatModel(steps=[letter(**GOOD)]), []
    first = flow(model, outbox, SqliteSaver(sqlite3.connect(db_file, check_same_thread=False)))
    assert pending(start(first, "w6", "KH-0047", "Viết thư nhắc nợ"))  # dừng chờ duyệt, rồi "process" kết thúc

    restarted = flow(
        ScriptedChatModel(steps=[]), outbox, SqliteSaver(sqlite3.connect(db_file, check_same_thread=False))
    )
    final = approve(restarted, "w6")  # như continue_run(run_id=..., session_id=...) của Agno
    assert final["status"] == "sent" and outbox[0]["customer_id"] == "KH-0047"
```

## 7. Giới hạn và việc tiếp theo

- **Chưa chạy với model thật.** Mọi test dùng model kịch bản: chúng chứng minh harness đưa đúng thứ cho model và
  chặn đúng chỗ, **không** chứng minh model thật chọn tool đúng. Việc đó là của `eval_golden.py`.
- **Workflow agent** (ưu tiên hiện tại): [mục 6.7](#67-workflow) đã có một `StateGraph` đầy đủ (song song, vòng sửa có
  giới hạn, rẽ nhánh, người duyệt, lưu bền). Bước tiếp: đặt một harness của mục 4 vào một node (bước cần tự chọn
  tool), theo [Lab 03 LangGraph](../self-practices/guide_03_langgraph.md).
- **AG-UI để sau (chủ ý, chưa cần lúc này).** Khi làm: thay AgentOS cho CMB-10 phải viết một endpoint nhận `RunAgentInput`, gọi
  `ask`/`resume` như mục 4.8 và phát sự kiện AG-UI (`RUN_STARTED`, `TEXT_MESSAGE_*`, `TOOL_CALL_START/ARGS/END`,
  `RUN_FINISHED`) từ `agent.stream(...)`. Một interrupt `client_tool` ứng với `TOOL_CALL_*` không có kết quả, đúng như
  AgentOS đang làm. Chưa kiểm gói adapter AG-UI có sẵn nào cho LangGraph.
- **Cảnh báo đã biết:** khi run dừng ở `interrupt()` với `context=AgentContext(...)`, pydantic in một
  `UserWarning` về serializer của trường `context`. Không ảnh hưởng kết quả (test vẫn xanh).
- **Chưa làm:** chọn tool theo câu hỏi khi có nhiều tool (`LLMToolSelectorMiddleware`, `ProviderToolSearchMiddleware`
  có sẵn), trace gửi Langfuse/OTel, prompt cache có đo; phần AgentOS/A2A/MCP server/eval của Lab 01 (mục 6).
- **Hai SDK MCP:** lab này dùng mcp 1.x (vì `langchain-mcp-adapters` 0.3.2 cần `mcp<2`), lab Agno dùng mcp 2.x. Khi
  adapter hỗ trợ mcp 2.x, `mcp_customer_server.py` phải đổi `FastMCP` → `MCPServer` như Bước 0 của Lab 01.

## Nguồn

- Mã `agno` 3.1.3: `agent/_run.py`, `agent/_messages.py`, `agent/_managers.py`, `agent/agent.py`, `agent/_init.py`,
  `session/agent.py`, `models/base.py`, `memory/manager.py`.
- Mã `langchain` 1.4.6: `agents/factory.py`, `agents/middleware/types.py`, `tool_call_limit.py`,
  `model_call_limit.py`, `human_in_the_loop.py`, `summarization.py`, `context_editing.py`, `todo.py`;
  `langgraph` 1.2.16: `types.py` (`interrupt`, `Command`), `store/base`.
- So sánh cơ chế bốn framework: [01-co-che-agent.md](01-co-che-agent.md). Radar framework: [README.md](README.md).
