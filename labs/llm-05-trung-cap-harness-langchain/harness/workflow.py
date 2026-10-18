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
