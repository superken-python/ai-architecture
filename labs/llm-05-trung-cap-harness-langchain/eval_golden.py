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
