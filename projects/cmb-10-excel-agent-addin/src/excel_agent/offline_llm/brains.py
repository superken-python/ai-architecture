""" "Bộ não" của model giả lập: đọc request Responses API (lịch sử + tool) và quyết định bước tiếp theo."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from excel_agent.agents.summaries import HELP_TEXT, summarize, summarize_excel
from excel_agent.core.text import normalize
from excel_agent.offline_llm import rules
from excel_agent.offline_llm.app import Call, Output, Text

OFFLINE_NOTE = "\n\n*(chế độ offline — chưa có `OPENAI_API_KEY`, câu được hiểu bằng luật cố định)*"
NO_EXCEL = "Chưa kết nối được Excel (giao diện không khai báo công cụ excel_*). Hãy mở một file Excel trước."


@dataclass
class Step:
    name: str
    args: dict[str, Any]
    output: str | None = None


@dataclass
class Turn:
    """Lượt hiện tại: câu hỏi cuối của người dùng, trạng thái Excel và các tool đã gọi kể từ câu hỏi đó."""

    user_text: str
    ui: dict[str, Any]
    steps: list[Step]
    tools: set[str]

    def last(self, name: str) -> Step | None:
        return next((s for s in reversed(self.steps) if s.name == name), None)

    def output_json(self, name: str) -> dict[str, Any]:
        step = self.last(name)
        try:
            data = json.loads(step.output or "") if step else {}
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(str(p.get("text", "")) for p in content if isinstance(p, dict))
    return ""


def _ui_from(context: str) -> dict[str, Any]:
    body = context.split("</additional context>", 1)[0].strip()
    try:
        deps = json.loads(body)
    except json.JSONDecodeError:
        return {}
    ui = deps.get("excel_ui") if isinstance(deps, dict) else None
    if isinstance(ui, str):
        try:
            ui = json.loads(ui)
        except json.JSONDecodeError:
            return {}
    return ui if isinstance(ui, dict) else {}


def read_turn(body: dict[str, Any]) -> Turn:
    items = body.get("input") or []
    if isinstance(items, str):
        items = [{"role": "user", "content": items}]
    users = [i for i, it in enumerate(items) if isinstance(it, dict) and it.get("role") == "user"]
    start = users[-1] if users else -1
    raw = _text(items[start]["content"]) if users else ""
    question, _, context = raw.partition("<additional context>")
    steps: list[Step] = []
    by_id: dict[str, Step] = {}
    for it in items[start + 1 :]:
        if not isinstance(it, dict):
            continue
        if it.get("type") == "function_call":
            try:
                args = json.loads(it.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            step = Step(str(it.get("name")), args)
            by_id[str(it.get("call_id"))] = step
            steps.append(step)
        elif it.get("type") == "function_call_output" and str(it.get("call_id")) in by_id:
            by_id[str(it.get("call_id"))].output = _text(it.get("output"))
    tools = {str(t.get("name")) for t in body.get("tools") or [] if isinstance(t, dict)}
    return Turn(question.strip(), _ui_from(context), steps, tools)


class RuleBrain:
    """Model offline: hiểu vài mẫu câu tiếng Việt bằng luật, gọi đúng tool như gpt-5-mini sẽ gọi."""

    def respond(self, request: dict[str, Any]) -> list[Output]:
        turn = read_turn(request)
        intent = rules.detect_intent(turn.user_text)
        handler = getattr(self, f"_{intent}")
        out = handler(turn)
        return [Text(out.text + OFFLINE_NOTE)] if isinstance(out, Text) else [out]

    def _help(self, turn: Turn) -> Output:
        return Text(HELP_TEXT)

    def _report(self, turn: Turn) -> Output:
        step = turn.last("export_excel")
        if step is None:
            return Call("export_excel", rules.report_args(turn.user_text))
        return Text(summarize(step.output or ""))

    def _search(self, turn: Turn) -> Output:
        step = turn.last("search_data")
        if step is None:
            return Call("search_data", rules.search_args(turn.user_text))
        return Text(summarize(step.output or ""))

    def _find_sheet(self, turn: Turn) -> Output:
        if "excel_find_rows" not in turn.tools:
            return Text(NO_EXCEL)
        step = turn.last("excel_find_rows")
        if step is None:
            return Call("excel_find_rows", rules.sheet_find_args(turn.user_text, turn.ui.get("headers") or []))
        return Text(summarize_excel("excel_find_rows", step.output or ""))

    def _update(self, turn: Turn) -> Output:
        if "excel_set_values" not in turn.tools:
            return Text(NO_EXCEL)
        step = turn.last("excel_set_values")
        if step is not None:
            return Text(summarize_excel("excel_set_values", step.output or ""))
        rows = (turn.ui.get("selection") or {}).get("rows") or []
        if not rows:
            return Text("Chọn các dòng cần ghi trên bảng Excel trước (bấm số dòng bên trái), rồi gửi lại yêu cầu.")
        args = rules.update_args(turn.user_text, turn.ui.get("headers") or [], rows)
        if args is None:
            return Text('Ghi rõ giá trị trong ngoặc kép và tên cột, ví dụ: ghi "VIP" vào cột Phân khúc.')
        return Call("excel_set_values", args)

    def _append(self, turn: Turn) -> Output:
        if "excel_append_rows" not in turn.tools:
            return Text(NO_EXCEL)
        done = turn.last("excel_append_rows")
        if done is not None:
            return Text(summarize_excel("excel_append_rows", done.output or ""))
        if turn.last("search_data") is None:
            return Call("search_data", rules.record_query(turn.user_text))
        found = turn.output_json("search_data")
        records = found.get("records") or []
        if not records:
            return Text(f"Không tìm thấy “{found.get('query', '')}” trong hệ thống nên chưa thêm gì vào bảng.")
        headers = turn.ui.get("headers") or turn.output_json("excel_get_context").get("headers") or []
        if not headers:
            if turn.last("excel_get_context") is None and "excel_get_context" in turn.tools:
                return Call("excel_get_context", {})
            return Text(NO_EXCEL)
        query = normalize(str(found.get("query", "")))
        exact = [r for r in records if any(normalize(str(v)) == query for v in r.values())]
        row = rules.map_record((exact or records)[0], headers)
        if not row:
            return Text("Bản ghi tìm được không có trường nào trùng tên cột của sheet đang mở.")
        return Call("excel_append_rows", {"rows": [row]})


@dataclass
class ScriptBrain:
    """Model "kịch bản" cho test: mỗi lần gọi trả bước kế tiếp; lưu request để kiểm tra model đã nhận gì."""

    steps: list[list[Output]]
    requests: list[dict[str, Any]] = field(default_factory=list)

    def respond(self, request: dict[str, Any]) -> list[Output]:
        self.requests.append(request)
        if len(self.requests) > len(self.steps):
            raise AssertionError(
                f"Model được gọi lần {len(self.requests)} nhưng kịch bản chỉ có {len(self.steps)} bước"
            )
        return self.steps[len(self.requests) - 1]

    def assert_complete(self) -> None:
        assert len(self.requests) == len(self.steps), f"Mới chạy {len(self.requests)}/{len(self.steps)} bước"
