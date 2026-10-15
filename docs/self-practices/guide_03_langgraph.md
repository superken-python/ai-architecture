# Lab 03 — Tự code Report Agent bằng LangGraph

Điều kiện: hoàn thành [Lab 00](agent_framework_learning_from_scratch.md). Bài này dùng cùng input, rule và renderer để bạn tập trung vào đồ thị trạng thái và checkpoint. Không cần Temporal server hoặc Agno để chạy.

## 1. Mục tiêu và graph topology

```text
START
  → prepare_turn          reset attempt/feedback của lượt hiện tại
  → gather_context        MCP + exact rules; có thể tái dùng evidence
  → draft                 model trả Narrative
  → gate                  kiểm tra schema + policy của lượt
       ├─ pass → finalize → END
       ├─ fail, còn lượt → draft
       └─ fail, hết lượt → raise; không xuất report đã duyệt
```

`revision` là số bản báo cáo đã được chấp nhận. `attempt` là số lần thử viết trong **lượt hiện tại**. Không dùng revision làm ngân sách retry. Checkpoint lưu state theo `thread_id`; nó không tự trở thành archive báo cáo nghiệp vụ hoặc cache chung cho mọi thread.

Nguồn: [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) và [checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers). Baseline dùng `SqliteSaver` cho CLI đồng bộ; API async nên dùng async graph/checkpointer tương ứng.

## 2. Chuẩn bị — 15 phút

```bash
uv add langgraph langgraph-checkpoint-sqlite langchain-core pydantic-ai
uv run python setup_assets.py
```

Baseline gọi helper model của [Lab 02](guide_02_pydantic_ai_temporal.md). Bạn chỉ cần tự tạo **`pydantic_cli.py`** từ phần chặng CLI của Lab 02; không cần các file Temporal hay cài Temporal. Pydantic AI ở đây là adapter model có typed output, LangGraph chịu trách nhiệm điều phối. Đây không phải yêu cầu bắt buộc của LangGraph; bài tập cuối sẽ thay bằng model adapter khác.

**PyCharm:** tạo `langgraph_cli.py` bằng New File, `⌘B` vào `StateGraph` và `TypedDict` để đọc type. Tạo Run Configuration với parameters `lg-01 "Phân tích Q2"`.

## 3. Thiết kế state trước khi gõ code — 20 phút

| Field | Ai cập nhật | Có giữ giữa các lượt? |
| --- | --- | --- |
| `messages` | Input + finalize | Có, reducer `add_messages` |
| `instruction` | CLI | Ghi đè mỗi lượt |
| `refresh` | CLI | Gán rõ mỗi lượt |
| `evidence` | gather_context | Có; refresh khi yêu cầu |
| `narrative` | draft | Ghi đè mỗi attempt |
| `attempt`, `feedback`, `passed` | prepare/draft/gate | Reset mỗi lượt |
| `summary_limit` | CLI | Gán rõ mỗi lượt |
| `revision`, `report` | finalize | Chỉ đổi sau gate pass |

Checkpoint có thể lưu cả state của lần thử chưa đạt. Đọc `report`/`revision` đã finalize để hiển thị bản accepted; không coi mọi checkpoint là một report revision. Baseline không nhận hai lượt đồng thời trên cùng thread.

## 4. Code tham khảo — `langgraph_cli.py`

Tự gõ theo nhóm: state → nodes → edges → runner. Chạy được từng nhóm rồi mới ghép. Dùng `⌘⌥M` để tách một node khi bạn thấy quá dài.

```python
import argparse
import asyncio
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from mcp_client import collect_metrics
from pydantic_cli import generate_narrative
from reporting import Narrative, make_evidence, render_report, save_local_report

ROOT = Path(__file__).resolve().parent
MAX_ATTEMPTS = 3


class ReportState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    instruction: str
    refresh: bool
    summary_limit: int
    evidence: dict
    narrative: dict
    attempt: int
    feedback: str
    passed: bool
    revision: int
    report: str


def prepare_turn(state: ReportState) -> dict:
    return {"attempt": 0, "feedback": "", "passed": False}


def gather_context(state: ReportState) -> dict:
    if state.get("evidence") and not state["refresh"]:
        return {}
    current, previous = asyncio.run(collect_metrics())
    return {"evidence": make_evidence(current, previous)}


def draft(state: ReportState) -> dict:
    instruction = (
        f"{state['instruction']}\n"
        f"Tóm tắt tối đa {state['summary_limit']} ý.\n"
        f"Phản hồi kiểm tra lần trước: {state.get('feedback', '')}"
    )
    narrative = asyncio.run(generate_narrative(
        state["evidence"], instruction, state.get("report", ""),
    ))
    return {"narrative": narrative.model_dump(), "attempt": state["attempt"] + 1}


def gate(state: ReportState) -> dict:
    narrative = Narrative.model_validate(state["narrative"])
    feedback = []
    if len(narrative.executive_summary) > state["summary_limit"]:
        feedback.append(f"Rút tóm tắt xuống tối đa {state['summary_limit']} ý.")
    if any(not text.strip() for text in narrative.executive_summary + narrative.actions):
        feedback.append("Không được có ý tóm tắt hoặc hành động rỗng.")
    return {"passed": not feedback, "feedback": " ".join(feedback)}


def route(state: ReportState) -> str:
    if state["passed"]:
        return "finalize"
    if state["attempt"] >= MAX_ATTEMPTS:
        raise RuntimeError(f"Gate không đạt sau {MAX_ATTEMPTS} lần: {state['feedback']}")
    return "draft"


def finalize(state: ReportState) -> dict:
    revision = state.get("revision", 0) + 1
    narrative = Narrative.model_validate(state["narrative"])
    report = render_report(state["evidence"], narrative, revision)
    return {"revision": revision, "report": report,
            "messages": [AIMessage(content=report)]}


def build_graph(checkpointer):
    builder = StateGraph(ReportState)
    for name, node in [
        ("prepare_turn", prepare_turn), ("gather_context", gather_context),
        ("draft", draft), ("gate", gate), ("finalize", finalize),
    ]:
        builder.add_node(name, node)
    builder.add_edge(START, "prepare_turn")
    builder.add_edge("prepare_turn", "gather_context")
    builder.add_edge("gather_context", "draft")
    builder.add_edge("draft", "gate")
    builder.add_conditional_edges("gate", route, {"draft": "draft", "finalize": "finalize"})
    builder.add_edge("finalize", END)
    return builder.compile(checkpointer=checkpointer)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("thread_id")
    parser.add_argument("instruction", nargs="?")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--summary-limit", type=int, choices=range(1, 6), default=3)
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    if not args.thread_id or not all(c.isalnum() or c in "-_" for c in args.thread_id):
        parser.error("thread_id chỉ gồm chữ, số, - hoặc _")
    (ROOT / "storage").mkdir(exist_ok=True)
    with SqliteSaver.from_conn_string(str(ROOT / "storage/langgraph.db")) as saver:
        graph = build_graph(saver)
        config = {"configurable": {"thread_id": args.thread_id}, "recursion_limit": 30}
        if args.history:
            for snapshot in graph.get_state_history(config):
                values = snapshot.values
                print(snapshot.config["configurable"].get("checkpoint_id"),
                      "revision=", values.get("revision", 0),
                      "attempt=", values.get("attempt", 0),
                      "next=", snapshot.next)
            return
        if args.show:
            values = graph.get_state(config).values
            print(values.get("report", "Chưa có report đã finalize."))
            return
        if not args.instruction:
            parser.error("Cần instruction hoặc --show/--history")
        state = graph.invoke({
            "messages": [HumanMessage(content=args.instruction)],
            "instruction": args.instruction,
            "refresh": args.refresh,
            "summary_limit": args.summary_limit,
        }, config)
        save_local_report(f"lg-{args.thread_id}", state["revision"], state["report"])
        print(state["report"])


if __name__ == "__main__":
    main()
```

Ở đây `asyncio.run` chỉ dùng bên trong node đồng bộ của **CLI đồng bộ**. Đừng bê nguyên cách này vào async HTTP endpoint vì event loop đã chạy. Khi chuyển async, đổi node sang `async def`, await model/MCP, dùng async saver và `ainvoke`/`astream`.

Gate baseline kiểm tra schema, số ý và chuỗi rỗng. Nó **không phải bộ chứng minh semantic/factual correctness**. Tính đúng của bảng dựa vào rules và renderer xác định; nhận xét vẫn phải đối chiếu evidence. Đừng thêm check tìm một chữ “KPI” rồi gọi là compliance đầy đủ.

## 5. Chạy hai lượt và kiểm tra lịch sử

```bash
uv run python langgraph_cli.py lg-01 'Phân tích Q2, nêu rủi ro và hành động.'
uv run python langgraph_cli.py lg-01 'Rút tóm tắt còn 2 ý và ưu tiên Cloud.' --summary-limit 2
uv run python langgraph_cli.py lg-01 --show
uv run python langgraph_cli.py lg-01 --history
```

Kết quả:

- v1/v2 xuất ở `storage/lg-lg-01/` vì tên artifact có prefix `lg-` và ID trong ví dụ là `lg-01`.
- State sống trong `storage/langgraph.db`; mỗi CLI là process mới, v2 vẫn lấy lại report cũ.
- Có nhiều checkpoint hơn số revision vì checkpoint ghi theo bước, không chỉ cuối báo cáo.
- Lượt hai giữ evidence cũ nếu không có `--refresh`. Đây là snapshot có chủ ý, không phải bằng chứng DB hiện tại vẫn giống snapshot.

Sửa threshold Excel rồi chạy:

```bash
uv run python langgraph_cli.py lg-01 'Cập nhật báo cáo từ dữ liệu và quy ước mới.' --refresh
```

Lúc này gather_context đọc lại DB và rules. Thử ID khác: revision bắt đầu từ 1. Ghi lại số lần gọi MCP để chứng minh lúc reuse không gọi lại, thay vì dựa vào nhận xét của model.

## 6. Thử gate và lỗi có chủ đích

Trước khi tốn API call cho vòng retry, kiểm tra các hàm thuần trong Python Console:

```python
from langgraph_cli import gate, route

sample = {
    "narrative": {"executive_summary": ["A", "B", "C"], "actions": ["Rà soát."]},
    "summary_limit": 2,
    "attempt": 1,
}
update = gate(sample)
assert update["passed"] is False
assert route({**sample, **update}) == "draft"
assert route({**sample, "passed": True}) == "finalize"
```

Đổi `attempt=3`, gọi route với `passed=False`: phải raise. Để thử toàn graph mà không tốn model, tạm thay implementation draft trả cùng narrative ba ý và tăng attempt. Giữ summary limit = 2; graph phải lỗi sau 3 lần, revision accepted không tăng. Khôi phục code draft trước khi tiếp tục.

**PyCharm debug:** breakpoint ở `prepare_turn`, `route`, `finalize`. `⌥F8` xem `state.get("revision")` và `state["attempt"]`. Chạy v4 để chứng minh attempt vẫn bắt đầu từ 0; revision 4 không làm bỏ qua gate. `⌘B` vào `add_messages` để hiểu reducer: message có ID được cập nhật theo reducer; không đơn giản là thay toàn bộ list.

Baseline truyền draft trước làm ngữ cảnh, chưa truyền toàn bộ `messages` vào model. Field messages phục vụ inspect/checkpoint. Nếu muốn hội thoại đầy đủ, thiết kế conversion sang message model và policy cắt gọn; không gửi vô hạn toàn bộ báo cáo cũ.

## 7. Bài tập history, time travel và interrupt

### A. History thật và fork

`--show` đọc snapshot mới nhất; `--history` liệt kê checkpoint. Viết thêm `--checkpoint-id` để inspect `graph.get_state()` với config gồm thread_id và checkpoint_id. Sau đó thử replay/fork trên thread thực hành riêng, đối chiếu report trước và sau. Đừng gọi endpoint “history” nếu nó chỉ trả latest report.

### B. Human-in-the-loop

Đọc [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts). Thêm node review **sau gate và trước finalize**:

```python
from langgraph.types import interrupt


def human_review(state):
    decision = interrupt({
        "proposed_narrative": state["narrative"],
        "proposed_revision": state.get("revision", 0) + 1,
    })
    if decision.get("approved") is not True:
        raise ValueError("Người review chưa chấp nhận bản nháp")
    return {}
```

Đây là **đoạn mở rộng**, chưa được nối trong graph baseline. Tự nối `gate → human_review → finalize`; đổi route pass về node review. Resume bằng `Command(resume={"approved": True})` trên cùng thread/checkpointer. Khi bị interrupt, state trả về có thể chưa có report mới; runner phải hiển thị “đang chờ review”, không export như thành công.

Lưu ý: node có interrupt được thực thi lại khi resume. Side effect đặt trước `interrupt()` có thể chạy lại; tách side effect hoặc làm idempotent. Thử dừng process lúc đang chờ rồi resume từ process mới.

### C. Durable checkpoint không đồng nghĩa exactly-once

Thêm một counter giả lập external side effect vào node, dừng giữa thực thi và checkpoint rồi resume để quan sát. Thiết kế key `(thread_id, request_id, operation)` ở hệ thống ghi thật. Serializing requests cùng thread và kiểm tra request_id là việc của ứng dụng; checkpointer không tự thay thế transaction nghiệp vụ.

## 8. Từ CLI sang UI và adapters

1. Thay helper model bằng adapter riêng, ví dụ `ChatOpenAI.with_structured_output(Narrative)`, rồi giữ nguyên nodes và state. Cài dependency của adapter, đọc API version tương ứng.
2. Thêm async MCP và async checkpointer, quản lý connection bằng lifespan.
3. Stream node updates cho debug; `stream_mode="updates"` không đồng nghĩa stream token. Token streaming cần stream mode/model hooks phù hợp phiên bản.
4. Chuyển graph updates sang AG-UI bằng SDK, dùng đúng input/event schema ở Lab 00.
5. Thêm research provider/A2A adapter, ghi `mode`, sources, TTL trong evidence; refresh phải cập nhật toàn bộ snapshot liên quan.

## 9. So sánh trên cùng bài toán

| Câu hỏi | Agno baseline | Pydantic AI + Temporal baseline | LangGraph baseline |
| --- | --- | --- | --- |
| Ai điều phối? | Hàm CLI + Agent | Workflow/update + Activity | Nodes/edges rõ ràng |
| Typed narrative | `output_schema` | `output_type` | Adapter model + Narrative |
| State chính ở đâu? | Session DB + JSON revision | Workflow event history | SQLite checkpoints |
| Mức resume của bài | Giữa các lượt đã lưu | Activity đã hoàn thành được replay | Checkpoint theo bước |
| Phần cần tự bổ sung | Atomic revision repository | Idempotency side effect, history policy | Concurrency theo thread, idempotency |
| Quy ước KPI | Shared exact rules | Shared exact rules | Shared exact rules |

Bảng mô tả **code trong lab**, không xếp hạng mọi khả năng của framework. Dùng cùng dataset, model, prompt và số lượt khi so sánh; ghi cả thời gian, token/cost thực đo, lỗi và khả năng inspect.

## 10. Checklist cuối bài

- [ ] Vẽ lại graph từ trí nhớ, giải thích ai cập nhật từng field.
- [ ] v1/v2 tồn tại qua process restart.
- [ ] `--history` trả nhiều checkpoint, khác với `--show`.
- [ ] Attempt reset mỗi lượt; hết retry không tạo accepted revision.
- [ ] Reuse và refresh evidence có hành vi đúng như mô tả.
- [ ] Hiểu giới hạn gate với nội dung narrative.
- [ ] Nếu làm interrupt: process mới resume được và không lặp side effect ngoài ý muốn.

Quay lại [Lab 00](agent_framework_learning_from_scratch.md#11-checklist-và-nhịp-thực-hành) để chọn milestone RAG, live research, A2A và AG-UI tiếp theo.
