"""Demo 5 run trên cùng một thread, model kịch bản — in ra đúng những gì model nhận ở mỗi run.

    python demo.py              # harness tương đương Agno
    python demo.py --improved   # thêm các lớp cải tiến kiểu Claude Code

Cùng kịch bản với thí nghiệm đã làm trên Agno 3.1.3 (xem docs/agent-radar/02-harness-agno-sang-langchain.md, mục 2.4).
"""

from __future__ import annotations

import argparse

from harness.agent import build_agent
from harness.context import AgentContext
from harness.data import CustomerDB
from harness.improved import build_improved_agent
from harness.model import ScriptedChatModel, call, say
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

QUESTIONS = [
    "Tôi là Lan, hay lọc khách hàng theo Hà Nội",
    "Tra KH-0012 giúp tôi",
    "Còn hạn mức không?",
    "Gợi ý cho tôi cách lọc như mọi khi",
    "Liệt kê khách hàng khu vực tôi phụ trách",
]


def short(m: BaseMessage) -> str:
    if isinstance(m, SystemMessage):
        return f"system   {'(có memory)' if 'memories_from_previous' in m.text else '(không memory)'}"
    if isinstance(m, AIMessage) and m.tool_calls:
        return f"ai→tool  {m.tool_calls[0]['name']}({m.tool_calls[0]['args']})"
    if isinstance(m, ToolMessage):
        return f"tool     {m.text[:60]}"
    role = "human" if isinstance(m, HumanMessage) else "ai"
    return f"{role:<8} {m.text[:60]}"


def scripted_models() -> tuple[ScriptedChatModel, ScriptedChatModel]:
    main = ScriptedChatModel(
        steps=[
            say("Đã ghi nhận, Lan."),
            call("search_customers", query="KH-0012"),
            say("KH-0012 còn hạn mức 180 triệu."),
            say("KH-0012 còn 180 triệu."),
            say("Lọc theo Hà Nội như bạn hay làm."),
            call("search_customers", query="Hà Nội"),
            say("Khách hàng Hà Nội: KH-0012, KH-0047."),
        ]
    )
    memory = ScriptedChatModel(
        steps=[
            call("add_memory", memory="Người dùng tên Lan, hay lọc khách hàng theo Hà Nội"),
            say("ok"),
            say("không có"),
            say("không có"),
            say("không có"),
            say("không có"),
        ]
    )
    return main, memory


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--improved", action="store_true")
    args = parser.parse_args()
    model, memory_model = scripted_models()
    store, db = InMemoryStore(), CustomerDB()
    build = build_improved_agent if args.improved else build_agent
    agent = build(model, db=db, checkpointer=InMemorySaver(), store=store, memory_model=memory_model)
    cfg = {"configurable": {"thread_id": "demo"}}
    ctx = AgentContext(user_id="lan", sheet="KhachHang", headers=["Mã KH", "Tên", "Thành phố"])
    for i, question in enumerate(QUESTIONS, start=1):
        before = len(model.calls)
        agent.invoke({"messages": [{"role": "user", "content": question}]}, cfg, context=ctx)
        print(f"\n===== RUN {i}: {question}")
        for k, seen in enumerate(model.calls[before:], start=1):
            print(f"  lượt model {k}: {len(seen)} message")
            for m in seen:
                print("    ", short(m))
        print("  memory:", [it.value["memory"] for it in store.search(("memories", "lan"))])


if __name__ == "__main__":
    main()
