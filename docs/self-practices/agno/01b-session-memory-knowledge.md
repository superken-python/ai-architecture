# Lab 01b — Session, memory và knowledge (Phần 4–6)

Thuộc [Lab 01 — Agno và AgentOS](../guide_01_agno.md). Cần xong [Lab 01a](01a-agent-tool-output-streaming.md) (Phần 1–3): các phần dưới dùng lại `KpiTools` và `inspect_rules`.

Ba phần này trả lời ba câu hỏi khác nhau, rất hay bị trộn lẫn:

| Câu hỏi | Cơ chế của Agno | Phạm vi | Ai ghi |
| --- | --- | --- | --- |
| "Trong cuộc trò chuyện này ta đã nói gì?" | **Session**: lịch sử run, `session_state`, tóm tắt | Một `session_id` | Agno, tự động sau mỗi run |
| "Người này là ai, thích gì?" | **Memory**: các câu ngắn về người dùng | Một `user_id`, qua mọi session | Một lượt gọi model trích xuất (tự động hoặc agent tự quyết) |
| "Tài liệu nói gì về việc này?" | **Knowledge** (RAG): tìm trong vector DB | Mọi người dùng | Bạn nạp (index) trước |

---

## Phần 4 — Session: lịch sử, state và tóm tắt

**Học xong phần này bạn:** giữ được ngữ cảnh qua nhiều lượt và qua cả khi process khởi động lại, lưu dữ liệu có cấu trúc theo session, và biết cái giá của tóm tắt tự động.

### 4.1 Agno lưu gì vào database

Mở file SQLite sau một run (ví dụ bằng DB Browser hay `sqlite3`), bạn thấy các bảng này (đã đo với Agno 3.1.3):

| Bảng | Một dòng là | Cột đáng xem |
| --- | --- | --- |
| `agno_sessions` | Một session | `session_id`, `agent_id`, `user_id`, `session_data` (chứa `session_state` và `session_metrics`), `summary` |
| `agno_runs` | Một run | `run_id`, `session_id`, `status`, `run_index`, `run_data` (messages, tools, metrics, content) |
| `agno_memories` | Một memory (Phần 5) | `memory`, `input` (câu của người dùng sinh ra memory), `user_id`, `agent_id` |
| `agno_schema_versions` | Phiên bản schema | — |

AgentOS còn tạo thêm các bảng eval, trace, span, metrics khi bạn dùng tới (Phần 12, 16).

### 4.2 Lịch sử hội thoại hoạt động ra sao (đã đo)

`add_history_to_context=True` + `session_id`:

- Trước mỗi lượt gọi model, Agno đọc các run trước của **cùng `session_id`** từ `agno_runs` và chèn lại **toàn bộ** message của chúng, kể cả lời gọi tool và kết quả tool. Request của run thứ hai có thứ tự role `developer → user → assistant → tool → assistant → user`.
- `num_history_runs=3` (mặc định cũng là 3): chỉ lấy 3 run gần nhất. Ở run thứ 5, model chỉ thấy câu hỏi của run 2, 3, 4 và câu hiện tại; câu của run 1 đã rơi khỏi ngữ cảnh.
- Session khác thì không thấy gì của nhau.

Về `developer`: `OpenAIChat` đổi role `system` thành `developer` khi gửi lên API (chuẩn mới của OpenAI). Trong `run.messages` bạn vẫn thấy `system`; trên đường truyền là `developer`.

### 4.3 `session_state`: dữ liệu có cấu trúc của session

`session_state` là một dict lưu trong `agno_sessions.session_data`. Ba cách dùng, Phần 4 dùng cả ba:

1. **Giá trị khởi tạo**: `Agent(session_state={"revision": 0, ...})` áp dụng cho session **mới**. Session đã có state trong DB thì Agno nạp state đã lưu.
2. **Tool đọc/ghi state**: tool có tham số `run_context: RunContext` được Agno truyền tự động (tham số này không xuất hiện trong schema gửi cho model). Sửa `run_context.session_state` trong tool, Agno lưu lại sau khi run xong.
3. **State trong prompt**: `{revision}` trong instructions được thay bằng giá trị trong state (session mới: `Phiên bản hiện tại: v0, quý None.`; test chứng minh run thứ hai nhận `v1, quý 2026-Q2`). `add_session_state_to_context=True` thêm cuối system prompt một khối `<session_state>{...}</session_state>`; đã đo, khối này có cả ba khoá Agno tự thêm: `current_user_id`, `current_session_id`, `current_run_id`.

Thêm `enable_agentic_state=True` thì agent có tool `update_session_state` để model tự sửa state. Tiện, nhưng mọi thay đổi do model quyết định. Giá trị cần chính xác (số phiên bản) nên để tool của bạn tính, như `record_revision`.

### 4.4 Tóm tắt session và cái giá của nó

`enable_session_summaries=True`: **cuối mỗi run có thêm một lượt gọi model** để tóm tắt. Đã đo: lượt này có system prompt bắt đầu bằng `Analyze the following conversation between a user and an assistant...`, user message là `Provide the summary of the conversation.`, model trả JSON `{"summary": ..., "topics": [...]}` lưu vào cột `summary`. Một run 1 lượt trả lời thành 2 lượt gọi model.

`add_session_summary_to_context=True` đưa bản tóm tắt vào system prompt của run sau. Kết hợp với `num_history_runs` nhỏ thì ngữ cảnh gọn, nhưng tóm tắt do model viết có thể bỏ sót chi tiết. Đọc lại bằng `agent.get_session_summary(session_id=...)`.

### 4.5 Session không phải hệ quản lý phiên bản báo cáo

Lab 01 bản cũ đã nói đúng: lịch sử run không thay được kho phiên bản artifact. `session_state["revision"]` ở đây là bộ đếm tiện dụng, chưa phải bảo đảm:

- Hai request đồng thời cùng session có thể cùng đọc `revision=1` và cùng ghi `2`.
- `notes` chỉ là ghi chú; nội dung báo cáo `v1.md`, `v2.md` vẫn do `save_local_report` lưu (Phần 7, 11).

Bài tập B ở cuối [guide_01_agno.md](../guide_01_agno.md#7-bài-tập-mở-rộng) làm repository SQLite có khoá phiên bản cho việc này.

### 4.6 Code

**File: `agno_lab/p04_session.py`**

```python
"""Phần 4 — Session: lịch sử hội thoại, session_state và tóm tắt session, đều lưu trong database.

uv run python -m agno_lab.p04_session report-01 lan "Lập báo cáo Q2"
uv run python -m agno_lab.p04_session report-01 lan "Rút tóm tắt còn 3 ý"   # cùng session: nhớ v1
"""

from __future__ import annotations

import sys

from agno.agent import Agent, RunOutput
from agno.run import RunContext

from agno_lab.p01_agent import KpiTools
from agno_lab.settings import db, model


def record_revision(run_context: RunContext, quarter: str, note: str) -> str:
    """Ghi nhận đã viết xong một phiên bản báo cáo cho quý `quarter`, kèm ghi chú ngắn về thay đổi.

    Chỉ gọi SAU khi đã viết xong nội dung của phiên bản đó.
    """
    state = run_context.session_state  # dict của session hiện tại; Agno lưu lại sau khi run xong
    state["revision"] += 1
    state["quarter"] = quarter
    state["notes"].append(f"v{state['revision']}: {note}")
    return f"Đã ghi nhận phiên bản v{state['revision']}"


def build_agent(agentic_state: bool = False) -> Agent:
    return Agent(
        id="report-assistant",
        name="Report Assistant",
        model=model(),
        db=db(),  # không có db thì không có lịch sử, state, tóm tắt
        session_state={"revision": 0, "quarter": None, "notes": []},  # giá trị khởi tạo cho session MỚI
        add_session_state_to_context=True,  # đưa state vào system prompt
        enable_agentic_state=agentic_state,  # True: thêm tool update_session_state, model tự ghi state
        add_history_to_context=True,
        num_history_runs=3,  # 3 run gần nhất của session (mặc định cũng là 3)
        enable_session_summaries=True,  # cuối mỗi run: thêm MỘT lượt gọi model để tóm tắt session
        add_session_summary_to_context=True,
        tools=[KpiTools(), record_revision],
        instructions=[
            "Bạn soạn báo cáo KPI theo nhiều phiên bản trong cùng một phiên làm việc, bằng tiếng Việt.",
            "Phiên bản hiện tại: v{revision}, quý {quarter}.",  # {…} được thay bằng giá trị trong session_state
            "Sau khi viết xong một phiên bản, gọi record_revision.",
        ],
    )


def chat(session_id: str, user_id: str, message: str) -> RunOutput:
    return build_agent().run(message, session_id=session_id, user_id=user_id)


def show(session_id: str) -> str:
    agent = build_agent()
    summary = agent.get_session_summary(session_id=session_id)
    history = agent.get_chat_history(session_id=session_id)
    return "\n".join(
        [
            f"state: {agent.get_session_state(session_id=session_id)}",
            f"summary: {summary.summary if summary else None}",
            f"history: {len(history)} message",
        ]
    )


if __name__ == "__main__":
    session_id, user_id, message = sys.argv[1:4]
    print(chat(session_id, user_id, message).content)
    print(show(session_id))
```

Đọc code:

- `record_revision(run_context, quarter, note)`: model chỉ thấy `quarter` và `note`; `run_context` do Agno truyền. Docstring dặn "chỉ gọi SAU khi đã viết xong" — điều kiện gọi tool nằm trong docstring.
- `chat()` tạo `Agent` mới mỗi lần, giống một process mới: state và lịch sử vẫn còn vì nằm trong DB, không nằm trong object.
- `show()` dùng ba API đọc lại session: `get_session_state`, `get_session_summary`, `get_chat_history`.

### 4.7 Chạy thử

```bash
uv run python -m agno_lab.p04_session report-01 lan "Lập báo cáo Q2"
uv run python -m agno_lab.p04_session report-01 lan "Rút tóm tắt còn 3 ý"   # cùng session: thấy v1
uv run python -m agno_lab.p04_session report-02 lan "Lập báo cáo Q2"        # session mới: state từ đầu
```

Sau lệnh thứ hai, dòng `state:` phải có `revision: 2` (nếu model gọi `record_revision` cả hai lần) và `summary:` có nội dung. Mở `storage/agno_lab.db`, xem bảng `agno_runs` để thấy hai run của `report-01`.

### 4.8 Checkpoint

```bash
uv run pytest tests/test_p04_session.py -v      # 4 passed
```

<details>
<summary>Test của Phần 4 — <code>tests/test_p04_session.py</code></summary>

**File: `tests/test_p04_session.py`**

```python
from agno_lab.p04_session import build_agent, chat, show
from mock_llm import answer_json, call, say

SUMMARY = "Analyze the following conversation between a user and an assistant"  # system prompt lượt tóm tắt


def system_prompt(request: dict) -> str:
    return next(m["content"] for m in request["messages"] if m["role"] in ("system", "developer"))


def users(request: dict) -> list[str]:
    return [m["content"] for m in request["messages"] if m["role"] == "user"]


def script_summaries(llm, *texts):
    llm.script(*[answer_json({"summary": t, "topics": ["báo cáo"]}) for t in texts], match=SUMMARY)


def test_state_persists_across_runs_and_instances(llm):
    llm.script(call("record_revision", quarter="2026-Q2", note="bản đầu"), say("Đã viết v1."))
    llm.script(call("record_revision", quarter="2026-Q2", note="rút gọn"), say("Đã viết v2."))
    script_summaries(llm, "Lập báo cáo Q2.", "Rút gọn báo cáo Q2.")

    chat("report-01", "lan", "Lập báo cáo Q2")
    run = chat("report-01", "lan", "Rút tóm tắt còn 3 ý")  # mỗi lần chat là một Agent mới, như một process mới
    assert run.session_state["revision"] == 2
    assert run.session_state["notes"] == ["v1: bản đầu", "v2: rút gọn"]
    main = [r for r in llm.requests if SUMMARY not in system_prompt(r)]
    assert "Phiên bản hiện tại: v1, quý 2026-Q2." in system_prompt(main[2])  # instructions đọc từ state


def test_history_is_per_session(llm):
    llm.script(say("A1"), say("A2"), say("B1"))
    script_summaries(llm, "s1", "s1b", "s2")
    chat("report-01", "lan", "câu 1")
    chat("report-01", "lan", "câu 2")
    chat("report-02", "lan", "câu khác")
    main = [r for r in llm.requests if SUMMARY not in system_prompt(r)]
    assert users(main[1]) == ["câu 1", "câu 2"]  # run 2 thấy run 1
    assert users(main[2]) == ["câu khác"]  # session khác không thấy gì


def test_summary_is_an_extra_model_call_and_goes_into_context(llm):
    llm.script(say("A1"), say("A2"))
    script_summaries(llm, "Lan lập báo cáo Q2.", "Lan sửa báo cáo Q2.")
    chat("report-01", "lan", "câu 1")
    assert len(llm.requests) == 2  # 1 lượt trả lời + 1 lượt tóm tắt
    chat("report-01", "lan", "câu 2")
    main = [r for r in llm.requests if SUMMARY not in system_prompt(r)]
    assert "Lan lập báo cáo Q2." in system_prompt(main[1])
    assert "summary: Lan sửa báo cáo Q2." in show("report-01")


def test_agentic_state_adds_update_tool(llm):
    llm.script(say("ok"))
    script_summaries(llm, "x")
    build_agent(agentic_state=True).run("chào", session_id="s", user_id="u")
    assert "update_session_state" in [t["function"]["name"] for t in llm.requests[0]["tools"]]
```

</details>

Chú ý cách test tách hai loại request: request tóm tắt nhận ra bằng câu `Analyze the following conversation...` trong system prompt (kênh `SUMMARY` của `mock_llm`), còn lại là request trả lời.

### 4.9 Bài tập

1. Chạy 5 lượt trong cùng session với `num_history_runs=2`. Ở lượt 5, model còn nhớ yêu cầu của lượt 1 không? Bật `add_session_summary_to_context` thì sao?
2. Tắt `enable_session_summaries` và đếm lại số lượt gọi model trong test `test_summary_is_an_extra_model_call_and_goes_into_context`.
3. Viết tool `undo_revision(run_context)` giảm `revision` đi 1 và xoá ghi chú cuối, kèm test.

---

## Phần 5 — Memory dài hạn theo người dùng

**Học xong phần này bạn:** cho agent nhớ người dùng qua mọi session, kiểm soát nó nhớ gì, và biết vì sao thiếu `user_id` là lỗi bảo mật.

### 5.1 Vòng đời của một memory (đã đo)

Với `update_memory_on_run=True`, mỗi run diễn ra như sau:

```text
Run N (user_id="lan"):
  ├─ Lượt gọi model trích xuất (MemoryManager), CHẠY SONG SONG với lượt trả lời:
  │    system: "You are a Memory Manager that is responsible for managing information and
  │             preferences about the user..." + memory_capture_instructions của bạn
  │             + <existing_memories> (ID và nội dung memory đã có của lan)
  │    user:   CHỈ tin nhắn của người dùng trong run này (không có câu trả lời của assistant)
  │    tools:  add_memory, update_memory, delete_memory
  │    → model gọi add_memory("Lan phụ trách khối Cloud, thích báo cáo ngắn") → lưu vào agno_memories
  └─ Lượt trả lời bình thường
Run N+1 (session MỚI, vẫn user_id="lan"):
  system prompt có thêm:
    <memories_from_previous_interactions>
    - Lan phụ trách khối Cloud, thích báo cáo ngắn
    </memories_from_previous_interactions>
```

Hệ quả:

- **Mỗi run tốn thêm ít nhất một lượt gọi model** cho việc trích xuất, kể cả khi không có gì để nhớ. Token của lượt này được ghi riêng trong `session_metrics` (mục `memory_model`). `MemoryManager(model=...)` cho phép dùng model rẻ hơn.
- Vì chạy song song, memory vừa trích ở run N **chưa** có trong ngữ cảnh của chính run N; run sau mới thấy.
- Trình trích xuất thấy ID của memory cũ nên có thể sửa hoặc xoá thay vì thêm trùng.

### 5.2 Hai chế độ

| Chế độ | Cấu hình | Khi nào ghi | Hợp với |
| --- | --- | --- | --- |
| Tự động | `update_memory_on_run=True` | Sau mỗi run | Trợ lý cá nhân, cần nhớ đều đặn |
| Agent tự quyết | `enable_agentic_memory=True` | Khi model gọi tool `update_user_memory(task=...)` | Chỉ ghi khi người dùng yêu cầu rõ ("nhớ giúp tôi...") |

`memory_capture_instructions` là chỗ bạn quyết định **nhớ gì**. Ở đây: chỉ thông tin ổn định về người dùng, **không** nhớ số liệu KPI (số liệu thay đổi mỗi quý; nhớ sai số thì lần sau agent trả lời theo memory cũ thay vì gọi tool).

### 5.3 `user_id` là ranh giới bảo mật

Đã đo: run không có `user_id` được Agno ghi memory vào user `"default"`. Mọi người dùng ẩn danh **dùng chung** bucket này: memory của người này hiện ra trong câu trả lời cho người khác. Vì vậy `ask()` từ chối khi thiếu `user_id`. Trong AgentOS (Phần 12) có xác thực, `user_id` nên lấy từ danh tính đã xác thực, không lấy từ tham số client gửi lên.

### 5.4 Memory khác RAG ở đâu

| | Memory | Knowledge (Phần 6) |
| --- | --- | --- |
| Nội dung | Câu ngắn về **người dùng** | Tài liệu **chung** |
| Ai tạo | Model trích từ hội thoại | Bạn nạp từ nguồn |
| Đưa vào ngữ cảnh | Toàn bộ memory của user, mỗi run | Chỉ đoạn tìm được, khi model gọi tool tìm |
| Rủi ro chính | Nhớ sai, nhớ thứ không nên nhớ, lẫn người dùng | Tìm sai đoạn, tài liệu cũ |

### 5.5 Code

**File: `agno_lab/p05_memory.py`**

```python
"""Phần 5 — Memory dài hạn theo người dùng: tự động sau mỗi run, hoặc để agent tự quyết khi nào ghi.

uv run python -m agno_lab.p05_memory lan "Tôi là Lan, phụ trách khối Cloud, thích báo cáo ngắn"
uv run python -m agno_lab.p05_memory lan "Tóm tắt KPI cho tôi"     # session mới vẫn nhớ Lan
"""

from __future__ import annotations

import sys
import uuid

from agno.agent import Agent, RunOutput
from agno.memory import MemoryManager

from agno_lab.p01_agent import KpiTools
from agno_lab.settings import db, model

CAPTURE = (
    "Chỉ nhớ thông tin ổn định về NGƯỜI DÙNG: tên, vai trò, phòng ban phụ trách, cách trình bày báo cáo ưa thích. "
    "KHÔNG nhớ số liệu KPI, kết quả tra cứu, hay yêu cầu tạm thời của một lần."
)


def build_agent(agentic: bool = False) -> Agent:
    return Agent(
        id="memory-assistant",
        name="Memory Assistant",
        model=model(),
        db=db(),
        # Trình trích xuất memory dùng model RIÊNG truyền vào (có thể rẻ hơn model chính).
        memory_manager=MemoryManager(model=model(), db=db(), memory_capture_instructions=CAPTURE),
        update_memory_on_run=not agentic,  # tự động: mỗi run thêm MỘT lượt gọi model trích memory từ tin nhắn user
        enable_agentic_memory=agentic,  # agent có tool update_user_memory, tự quyết khi nào ghi
        tools=[KpiTools()],
        instructions=["Trả lời bằng tiếng Việt. Cá nhân hoá theo memory về người dùng nếu có."],
    )


def ask(user_id: str | None, message: str, session_id: str | None = None, agentic: bool = False) -> RunOutput:
    if not user_id:
        # Agno gom mọi run thiếu user_id vào user "default" → memory của nhiều người trộn vào nhau.
        raise ValueError("Cần user_id để đọc/ghi memory")
    return build_agent(agentic).run(message, user_id=user_id, session_id=session_id or uuid.uuid4().hex)


def memories(user_id: str) -> list[str]:
    return [m.memory for m in build_agent().get_user_memories(user_id=user_id)]


if __name__ == "__main__":
    user, message = sys.argv[1], sys.argv[2]
    print(ask(user, message).content)
    print("memory:", memories(user))
```

Đọc code:

- `MemoryManager(model=model(), db=db(), memory_capture_instructions=CAPTURE)`: trình trích xuất là một agent nhỏ có model riêng.
- `update_memory_on_run=not agentic` / `enable_agentic_memory=agentic`: chọn một trong hai chế độ.
- `memories(user_id)` đọc lại bằng `get_user_memories` để kiểm tra, sửa hoặc xoá thủ công (AgentOS có API `/memories` cho việc này, Phần 12).

### 5.6 Chạy thử

```bash
uv run python -m agno_lab.p05_memory lan "Tôi là Lan, phụ trách khối Cloud, thích báo cáo ngắn"
uv run python -m agno_lab.p05_memory lan "Tóm tắt KPI 2026-Q2 cho tôi"   # session mới vẫn biết Lan
uv run python -m agno_lab.p05_memory minh "Tóm tắt KPI 2026-Q2 cho tôi"  # người khác: không có memory của Lan
```

### 5.7 Checkpoint

```bash
uv run pytest tests/test_p05_memory.py -v      # 4 passed
```

<details>
<summary>Test của Phần 5 — <code>tests/test_p05_memory.py</code></summary>

**File: `tests/test_p05_memory.py`**

```python
import pytest

from agno_lab.p05_memory import ask, build_agent, memories
from mock_llm import call, say

MEMORY = "You are a Memory Manager"  # system prompt của trình trích xuất memory trong Agno 3.1.3


def roles(request: dict) -> list[str]:
    return [m["role"] for m in request["messages"]]


def test_automatic_memory_crosses_sessions(llm):
    llm.script(say("Chào Lan."), say("Báo cáo ngắn cho khối Cloud."))
    llm.script(
        call("add_memory", memory="Tên Lan, phụ trách khối Cloud, thích báo cáo ngắn"),
        say("ok"),
        say("không có"),
        match=MEMORY,
    )
    ask("lan", "Tôi là Lan, phụ trách khối Cloud, thích báo cáo ngắn", session_id="s1")
    assert memories("lan") == ["Tên Lan, phụ trách khối Cloud, thích báo cáo ngắn"]

    ask("lan", "Tóm tắt KPI cho tôi", session_id="s2")  # session MỚI, không có lịch sử
    main = [r for r in llm.requests if MEMORY not in r["messages"][0]["content"]]
    assert "phụ trách khối Cloud" in main[1]["messages"][0]["content"]  # memory nằm trong system prompt
    extractor = llm.requests_for(MEMORY)[0]
    assert "KHÔNG nhớ số liệu KPI" in extractor["messages"][0]["content"]  # luật CAPTURE của ta
    assert "assistant" not in roles(extractor)  # trình trích xuất chỉ thấy tin nhắn user


def test_memory_is_per_user(llm):
    llm.script(say("ok"))
    llm.script(call("add_memory", memory="Tên Lan"), say("ok"), match=MEMORY)
    ask("lan", "Tôi là Lan")
    assert memories("lan") == ["Tên Lan"] and memories("minh") == []


def test_missing_user_id_is_refused_and_agno_default_shows_why(llm):
    with pytest.raises(ValueError, match="user_id"):
        ask(None, "Tôi là Lan")
    llm.script(say("ok"))
    llm.script(call("add_memory", memory="Tên Lan"), say("ok"), match=MEMORY)
    build_agent().run("Tôi là Lan", session_id="s")  # gọi Agno trực tiếp, không user_id
    assert memories("default") == ["Tên Lan"]  # mọi người ẩn danh dùng chung bucket này


def test_agentic_memory_lets_the_agent_decide(llm):
    llm.script(call("update_user_memory", task="Lưu: Lan phụ trách khối Cloud"), say("Đã ghi nhớ."))
    llm.script(call("add_memory", memory="Lan phụ trách khối Cloud"), say("ok"), match=MEMORY)
    run = ask("lan", "Nhớ giúp: tôi phụ trách khối Cloud", agentic=True)
    assert [t.tool_name for t in run.tools] == ["update_user_memory"]
    assert memories("lan") == ["Lan phụ trách khối Cloud"]
```

</details>

### 5.8 Bài tập

1. Nói "Tôi chuyển sang phụ trách FinTech" ở một session mới. Mở bảng `agno_memories`: memory cũ được sửa (`update_memory`) hay có thêm dòng mới?
2. Thêm vào `CAPTURE` luật "không nhớ email, số điện thoại". Viết test: người dùng nói email, `memories()` không được chứa `@`.
3. Đo chi phí: chạy 10 câu hỏi với memory tự động và 10 câu với agentic memory, so `session_metrics`.

---

## Phần 6 — Knowledge (RAG): tìm đúng đoạn tài liệu

**Học xong phần này bạn:** nạp tài liệu vào vector DB sao cho cập nhật được mà không nhúng lại tất cả, lọc theo metadata, và biết chỗ nào **không** được dùng RAG.

### 6.1 Ranh giới: exact trước, semantic sau

Lab 00 §8 đã chốt: số liệu và rule KPI **bắt buộc** lấy chính xác (`get_quarter_kpis`, `inspect_rules`). Tìm gần đúng có thể trả về rule của phòng ban khác hoặc bỏ sót rule. Knowledge chỉ dùng cho hướng dẫn bổ sung: style guide, giải thích rule bằng lời. Instructions của agent ở phần này nói rõ ranh giới đó.

### 6.2 Các mảnh ghép

```text
documents()  → (name ổn định, text, metadata)
   │  index(): so hash, xoá name đã biến mất, insert(upsert=True)
   ▼
Knowledge(vector_db=LanceDb(embedder=OpenAIEmbedder))
   │  search(query, filters={"source": "style"})   ← bạn gọi trực tiếp
   │  search_knowledge=True → tool search_knowledge_base(query)   ← model gọi
   ▼
Agent
```

Hành vi đã đo:

- `insert(name=..., upsert=True)`: chèn lại cùng `name` thì **thay** bản cũ — đổi ngưỡng KPI_02 rồi index lại, tìm kiếm chỉ còn bản mới.
- Document đã bị xoá khỏi nguồn **không tự biến mất**: phải gọi `remove_vectors_by_name(name)`. `index()` nhớ danh sách name ở `index_state.json` để biết name nào đã mất.
- Nguồn không đổi (hash giống) thì `index()` trả 0 và **không gọi API embedding lần nào**: không tốn tiền.
- `search(..., filters={"source": "rules"})` chỉ trả document có metadata khớp: tìm "CLOUD_OPS ngưỡng" với bộ lọc `rules` ra đúng 3 rule, không lẫn dòng style guide.
- `search_knowledge=True` thêm tool `search_knowledge_base` vào danh sách tool của model.

Embedding dùng endpoint OpenAI-compatible giống model (`OPENAI_BASE_URL`). `mock_llm` có `/v1/embeddings` dùng mẹo băm từ: câu chung từ khoá thì gần nhau, đủ để học luồng, không phải semantic thật. Đổi `EMBEDDING_DIMS` thì phải xoá thư mục LanceDB và index lại, vì bảng cũ có số chiều khác.

### 6.3 Code

**File: `agno_lab/p06_knowledge.py`**

```python
"""Phần 6 — Knowledge (RAG): nạp quy ước và style guide vào vector DB, agent tự tìm khi cần.

Theo Lab 00 §8: số liệu và rule BẮT BUỘC lấy chính xác bằng tool; semantic search chỉ cho hướng dẫn bổ sung.

    uv run python -m agno_lab.p06_knowledge index
    uv run python -m agno_lab.p06_knowledge ask "Phần II của báo cáo cần trình bày thế nào?"
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

from agno.agent import Agent
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.lancedb import LanceDb, SearchType

from agno_lab.p01_agent import KpiTools, inspect_rules
from agno_lab.settings import ROOT, model, vector_dir
from rules import load_rules

Doc = tuple[str, str, dict]  # (name ổn định, nội dung, metadata)


def knowledge() -> Knowledge:
    embedder = OpenAIEmbedder(
        id=os.getenv("EMBEDDING_ID", "text-embedding-3-small"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        dimensions=int(os.getenv("EMBEDDING_DIMS", "1536")),  # đổi số chiều thì phải xoá và dựng lại bảng
    )
    vector_db = LanceDb(
        uri=str(vector_dir()), table_name="report_guides", embedder=embedder, search_type=SearchType.vector
    )
    return Knowledge(
        name="report-guides", description="Quy ước KPI và hướng dẫn trình bày báo cáo", vector_db=vector_db
    )


def documents() -> list[Doc]:
    """Mỗi rule Excel và mỗi dòng style guide là một document có name ổn định và metadata để lọc."""
    docs: list[Doc] = []
    for code, rule in load_rules().items():
        text = (
            f"{rule['rule_id']} áp dụng cho {rule['dept_name']} ({code}): loại {rule['kind']}, "
            f"ngưỡng {rule['threshold']}, nhãn {rule['label']}."
        )
        docs.append((rule["rule_id"], text, {"source": "rules", "rule_id": rule["rule_id"], "dept_code": code}))
    for line in (ROOT / "data/report_style_guide.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            section = line.split(":")[0]  # "Phần I", "Phần II", ...
            docs.append((f"style-{section}", line, {"source": "style", "section": section}))
    return docs


def index(kb: Knowledge, docs: list[Doc]) -> int:
    """Nạp lại khi nguồn đổi. Trả về số document đã nhúng (0 = không có gì đổi, không tốn tiền embedding)."""
    state_file = vector_dir() / "index_state.json"
    digest = hashlib.sha256(json.dumps(docs, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    if state_file.exists() and json.loads(state_file.read_text())["hash"] == digest:
        return 0
    old = json.loads(state_file.read_text())["names"] if state_file.exists() else []
    names = [name for name, _, _ in docs]
    for name in set(old) - set(names):  # rule đã bị xoá khỏi Excel: xoá vector của nó
        kb.remove_vectors_by_name(name)
    for name, text, meta in docs:
        kb.insert(name=name, text_content=text, metadata=meta, upsert=True)  # cùng name → bản cũ bị thay
    state_file.write_text(json.dumps({"hash": digest, "names": names}))
    return len(docs)


def build_agent(kb: Knowledge) -> Agent:
    return Agent(
        id="guide-assistant",
        name="Guide Assistant",
        model=model(),
        knowledge=kb,
        search_knowledge=True,  # thêm tool search_knowledge_base; model tự quyết khi nào tìm
        tools=[KpiTools(), inspect_rules],
        instructions=[
            "Số liệu và quy ước KPI: luôn dùng get_quarter_kpis và inspect_rules (chính xác, không tìm gần đúng).",
            "Cách trình bày báo cáo: tìm bằng search_knowledge_base rồi trích đúng hướng dẫn tìm được.",
        ],
    )


if __name__ == "__main__":
    kb = knowledge()
    if sys.argv[1:2] == ["index"]:
        print(f"Đã nhúng {index(kb, documents())} document")
    else:
        print(build_agent(kb).run(sys.argv[2] if len(sys.argv) > 2 else "Phần II trình bày thế nào?").content)
```

Đọc code:

- Mỗi rule là **một document** có name là `rule_id`; mỗi dòng style guide là một document `style-Phần I`... Chia nhỏ theo đơn vị ý nghĩa giúp kết quả tìm kiếm gọn và trích dẫn được.
- `hashlib.sha256(json.dumps(docs, sort_keys=True))`: một hash cho cả bộ tài liệu. Bản production nên hash từng document để chỉ nhúng lại phần đổi.
- `SearchType.vector`: chỉ dùng vector. LanceDB còn có `hybrid` (vector + từ khoá) — xem bài tập 3.

### 6.4 Chạy thử

```bash
uv run python -m agno_lab.p06_knowledge index           # lần đầu: "Đã nhúng 7 document"
uv run python -m agno_lab.p06_knowledge index           # lần hai: "Đã nhúng 0 document"
uv run python -m agno_lab.p06_knowledge ask "Phần II của báo cáo cần trình bày thế nào?"
```

### 6.5 Checkpoint

```bash
uv run pytest tests/test_p06_knowledge.py -v      # 4 passed
```

<details>
<summary>Test của Phần 6 — <code>tests/test_p06_knowledge.py</code></summary>

**File: `tests/test_p06_knowledge.py`**

```python
from agno_lab.p06_knowledge import build_agent, documents, index, knowledge
from mock_llm import call, say


def contents(results) -> list[str]:
    return [d.content for d in results]


def test_documents_have_stable_names_and_metadata():
    docs = {name: meta for name, _, meta in documents()}
    assert {"KPI_01", "KPI_02", "KPI_03", "style-Phần II"} <= set(docs)
    assert docs["KPI_02"] == {"source": "rules", "rule_id": "KPI_02", "dept_code": "CLOUD_OPS"}


def test_search_and_metadata_filter(llm):
    kb = knowledge()
    assert index(kb, documents()) == 7
    style = kb.search("Phần II bảng KPI USD Rule_ID", max_results=1, filters={"source": "style"})
    assert contents(style) == ["Phần II: Bảng KPI, USD, 2 chữ số thập phân, Rule_ID."]
    rules = kb.search("CLOUD_OPS ngưỡng", max_results=10, filters={"source": "rules"})
    assert all(d.meta_data["source"] == "rules" for d in rules) and len(rules) == 3


def test_reindex_skips_unchanged_and_replaces_changed(llm):
    kb = knowledge()
    docs = documents()
    index(kb, docs)
    calls_before = len(llm.embedding_requests)
    assert index(kb, docs) == 0 and len(llm.embedding_requests) == calls_before  # không đổi → không nhúng lại

    changed = [
        (n, t.replace("ngưỡng 10.0", "ngưỡng 15.0"), m) for n, t, m in docs if n != "KPI_03"
    ]  # đổi ngưỡng KPI_02, xoá KPI_03
    index(kb, changed)
    rules = contents(kb.search("ngưỡng", max_results=10, filters={"source": "rules"}))
    assert any("ngưỡng 15.0" in r for r in rules) and not any("ngưỡng 10.0" in r for r in rules)
    assert not any(r.startswith("KPI_03") for r in rules)  # rule đã xoá không còn được tìm thấy


def test_agent_searches_knowledge_with_a_tool(llm):
    kb = knowledge()
    index(kb, documents())
    llm.script(call("search_knowledge_base", query="Phần II trình bày"), say("Phần II là bảng KPI bằng USD."))
    run = build_agent(kb).run("Phần II của báo cáo trình bày thế nào?")
    tool_names = [t["function"]["name"] for t in llm.requests[0]["tools"]]
    assert "search_knowledge_base" in tool_names and "get_quarter_kpis" in tool_names
    (search,) = run.tools
    assert "Phần II: Bảng KPI" in search.result
```

</details>

### 6.6 Bài tập

1. Sửa ngưỡng KPI_02 trong `data/internal_rules.xlsx` (bằng Excel), chạy `index` lại, hỏi agent ngưỡng mới. Đếm số request embedding.
2. Đổi `index()` để hash **từng** document và chỉ nhúng lại document đổi. Viết test đếm `llm.embedding_requests`.
3. Thử `SearchType.hybrid` (cần full-text index của LanceDB) và so kết quả với `vector` cho câu "Rule_ID".
4. Hỏi agent "Ngưỡng KPI_02 là bao nhiêu?" với model thật. Nó dùng `inspect_rules` hay `search_knowledge_base`? Sửa instructions nếu nó chọn sai.

---

**Câu hỏi tự kiểm tra Phần 4–6**

1. Xoá `storage/agno_lab.db` thì mất những gì: lịch sử, state, tóm tắt, memory, vector?
2. Vì sao memory vừa trích ở run N chưa có trong câu trả lời của run N?
3. Chạy không có `user_id` thì memory đi đâu? Hậu quả với hệ thống nhiều người dùng?
4. Vì sao rule KPI không được tìm bằng semantic search dù đã nạp vào knowledge?
5. Rule bị xoá khỏi Excel nhưng không gọi `remove_vectors_by_name` thì chuyện gì xảy ra?

Tiếp theo: [Lab 01c — Tool nâng cao, HITL và guardrail (Phần 7–8)](01c-tool-hitl-guardrail.md).
