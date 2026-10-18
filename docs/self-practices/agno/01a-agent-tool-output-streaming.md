# Lab 01a — Agent, tool, output có cấu trúc và streaming (Phần 1–3)

Thuộc [Lab 01 — Agno và AgentOS](../guide_01_agno.md). Làm xong [Phần 0 — chuẩn bị](../guide_01_agno.md#3-phần-0--chuẩn-bị-project) trước: project có `agno_lab/settings.py`, `mock_llm.py`, `conftest.py`.

Ba phần này dựng "lõi" mà mọi phần sau dùng lại: một agent gọi tool, một agent trả dữ liệu đúng schema, và cách nhận kết quả theo thời gian thực.

| Phần | Module | Học được |
| --- | --- | --- |
| 1 | `agno_lab/p01_agent.py` | Agent = model + instructions + tools; vòng lặp tool; đọc `RunOutput` |
| 2 | `agno_lab/p02_structured.py` | `input_schema`, `output_schema`; LLM viết chữ, code giữ số |
| 3 | `agno_lab/p03_streaming.py` | `stream=True`, `stream_events=True`; thứ tự sự kiện; bản async |

---

## Phần 1 — Agent đầu tiên

**Học xong phần này bạn:** tự viết được tool cho agent, biết model "thấy" tool như thế nào, và đọc được một run đã xảy ra những gì.

### 1.1 Một run của agent chạy ra sao

`agent.run("Phòng ban nào bị cảnh báo ở 2026-Q2?")` không phải một lần gọi model. Đó là một **vòng lặp**:

```text
1. Agno dựng danh sách message:
     system  = description + instructions (+ <additional_information>, ví dụ markdown=True)
     user    = câu hỏi
   và danh sách tool dạng JSON Schema (tên, mô tả, tham số).
2. Gọi model.
3. Model trả về một trong hai:
     a) tool_calls  → Agno chạy từng tool, thêm message role=tool chứa kết quả, quay lại bước 2
     b) chữ thường  → vòng lặp dừng, đó là câu trả lời
4. Trả RunOutput: content, tools đã chạy, messages, metrics (token), status.
```

Đã đo trên Agno 3.1.3 với câu hỏi có một lần gọi tool, `run.messages` có đúng 5 message theo thứ tự `system → user → assistant(tool_calls=[get_quarter_kpis]) → tool → assistant`. Lượt gọi model thứ hai nhận kết quả tool trong message `tool`; đó là cách model "đọc" được dữ liệu.

System prompt thật mà model nhận (in từ `run.messages[0].content`):

```text
Trợ lý phân tích KPI phòng ban từ database nội bộ.
- Trả lời bằng tiếng Việt, ngắn gọn.
- Luôn lấy số liệu bằng get_quarter_kpis; không tự tính hay đoán số.
- Giải thích cảnh báo bằng rule_id và ngưỡng trong inspect_rules khi được hỏi lý do.

<additional_information>
- Use markdown to format your answers.
</additional_information>
```

`description` đứng đầu, mỗi phần tử của `instructions` thành một gạch đầu dòng, `markdown=True` thêm khối `<additional_information>`. Agent không có `description` lẫn `instructions` thì **không có system message nào**.

### 1.2 Model thấy tool như thế nào

Agno đọc **tên hàm, type hint và docstring** để tạo JSON Schema. Đây là schema thật gửi cho model (lấy từ request mà `mock_llm` nhận):

```json
{
  "type": "function",
  "function": {
    "name": "get_quarter_kpis",
    "description": "Tính KPI và cảnh báo của mọi phòng ban trong một quý (dạng YYYY-Q1..Q4), so với quý liền trước.\nDùng khi người dùng hỏi số liệu, margin, tăng trưởng hoặc cảnh báo của một quý.",
    "parameters": {"type": "object", "properties": {"quarter": {"type": "string"}}, "required": ["quarter"]}
  }
}
```

Hệ quả cần nhớ:

- **Docstring là hướng dẫn sử dụng mà model đọc.** Viết rõ tool làm gì, *khi nào* dùng, định dạng tham số. Mô tả mơ hồ thì model chọn sai tool.
- **Type hint thành kiểu tham số.** Agno còn bọc hàm bằng `pydantic.validate_call`: model truyền sai kiểu thì lỗi validate được trả về cho model, hàm của bạn không chạy với dữ liệu sai kiểu.
- **Giá trị trả về nên là chuỗi** (thường là JSON với `ensure_ascii=False` để giữ tiếng Việt). Đó là thứ model đọc ở lượt sau.

Hai cách viết tool:

| Cách | Khi dùng | Ví dụ trong Phần 1 |
| --- | --- | --- |
| Hàm Python | Tool đơn lẻ, không cần cấu hình chung | `inspect_rules()` |
| `Toolkit` | Nhóm hàm liên quan, cần chung cấu hình: `cache_results`, `include_tools`/`exclude_tools`, `requires_confirmation_tools`... | `KpiTools.get_quarter_kpis` |

### 1.3 Khi tool gặp lỗi

Đã đo hai cách xử lý:

| Tool làm gì | Agno làm gì | Model nhận gì |
| --- | --- | --- |
| `raise ValueError("quý không tồn tại")` | Bắt exception, log WARNING + traceback, đánh dấu `tool_call_error=True`, **run vẫn chạy tiếp và kết thúc COMPLETED** | Đúng chuỗi `quý không tồn tại` |
| `return "Lỗi: ... Quý phải có dạng 2026-Q2"` | Coi là kết quả bình thường | Thông báo có hướng dẫn sửa |

Cả hai đều không làm hỏng run. Cách thứ hai tốt hơn vì bạn quyết định model đọc gì: nêu lỗi kèm cách sửa, model tự gọi lại với tham số đúng ở lượt sau (test `test_bad_quarter_returns_guidance_and_model_retries` chứng minh điều này).

Một tham số nữa nên biết: `Agent(tool_call_limit=N)`. Đã đo với `N=1`: lần gọi tool thứ hai **không chạy**, model nhận message `Tool call limit reached. Tool call inspect_rules not executed. Don't try to execute it again...` và vẫn được gọi tiếp để trả lời. Giới hạn này chặn tool chạy quá số lần, nhưng **không** cắt ngang vòng lặp.

### 1.4 Code

**File: `agno_lab/p01_agent.py`**

```python
"""Phần 1 — Agent đầu tiên: model, instructions, tool (hàm và Toolkit), chạy và đọc RunOutput.

uv run python -m agno_lab.p01_agent "Phòng ban nào bị cảnh báo ở 2026-Q2?"
"""

from __future__ import annotations

import json
import sys

from agno.agent import Agent, RunOutput
from agno.tools import Toolkit

from agno_lab.settings import model
from reporting import make_evidence
from rules import load_rules
from service import read_metrics


def previous_quarter(quarter: str) -> str:
    year, number = int(quarter[:4]), int(quarter[-1])
    return f"{year - 1}-Q4" if number == 1 else f"{year}-Q{number - 1}"


# Tool dạng hàm: Agno đọc tên hàm, type hint và docstring để tạo JSON schema gửi cho model.
# Docstring là "hướng dẫn sử dụng" model đọc — viết rõ khi nào dùng.
def inspect_rules() -> str:
    """Đọc toàn bộ quy ước KPI từ Excel: rule_id, phòng ban, loại rule, ngưỡng và nhãn cảnh báo.

    Dùng khi cần biết vì sao một phòng ban bị cảnh báo hoặc ngưỡng của rule là bao nhiêu.
    """
    return json.dumps(load_rules(), ensure_ascii=False)


# Tool dạng Toolkit: gom nhiều hàm liên quan, chia sẻ cấu hình (cache, include/exclude, instructions...).
class KpiTools(Toolkit):
    def __init__(self, **options) -> None:  # options của Toolkit: cache_results, include_tools, timeout...
        super().__init__(name="kpi_tools", tools=[self.get_quarter_kpis], **options)

    def get_quarter_kpis(self, quarter: str) -> str:
        """Tính KPI và cảnh báo của mọi phòng ban trong một quý (dạng YYYY-Q1..Q4), so với quý liền trước.

        Dùng khi người dùng hỏi số liệu, margin, tăng trưởng hoặc cảnh báo của một quý.
        """
        try:
            evidence = make_evidence(read_metrics(quarter), read_metrics(previous_quarter(quarter)))
        except ValueError as exc:  # lỗi có hướng dẫn → model tự sửa ở lượt sau, không làm hỏng run
            return f"Lỗi: {exc}. Quý phải có dạng 2026-Q2 và đã có dữ liệu."
        return json.dumps(evidence["kpis"], ensure_ascii=False)


def build_agent() -> Agent:
    return Agent(
        id="kpi-analyst",
        name="KPI Analyst",
        model=model(),
        description="Trợ lý phân tích KPI phòng ban từ database nội bộ.",
        instructions=[
            "Trả lời bằng tiếng Việt, ngắn gọn.",
            "Luôn lấy số liệu bằng get_quarter_kpis; không tự tính hay đoán số.",
            "Giải thích cảnh báo bằng rule_id và ngưỡng trong inspect_rules khi được hỏi lý do.",
        ],
        tools=[inspect_rules, KpiTools()],
        markdown=True,
    )


def describe(run: RunOutput) -> str:
    """Những gì nên nhìn sau mỗi run: nội dung, tool đã chạy, token."""
    lines = [f"status={run.status.value} run_id={run.run_id}", f"content: {run.content}"]
    for t in run.tools or []:
        lines.append(f"tool {t.tool_name}({t.tool_args}) -> {str(t.result)[:80]}")
    m = run.metrics
    lines.append(f"tokens: input={m.input_tokens} output={m.output_tokens} total={m.total_tokens}")
    return "\n".join(lines)


if __name__ == "__main__":
    question = sys.argv[1] if len(sys.argv) > 1 else "Phòng ban nào bị cảnh báo ở 2026-Q2?"
    print(describe(build_agent().run(question)))
```

Đọc code:

- `id="kpi-analyst"`: địa chỉ để AgentOS (Phần 12), Team (Phần 10) và A2A (Phần 14) gọi đúng agent. Không đặt `id` thì lúc chạy Agno sinh id từ `name` (`"KPI Analyst"` → `kpi-analyst`), không có cả `name` thì sinh tên ngẫu nhiên kiểu `clear-hubble-05a166b2`. Đặt `id` cố định để đổi tên hiển thị không làm đổi địa chỉ.
- `model=model()`: lấy từ `settings.py`. Đổi OpenAI ↔ Ollama ↔ mock chỉ cần sửa `.env`.
- `KpiTools.__init__(**options)`: chuyển tiếp cấu hình cho `Toolkit` → Phần 7 dùng `KpiTools(cache_results=True)` mà không sửa class.
- `get_quarter_kpis` dùng lại `make_evidence` của Lab 00: **số liệu do code tính**, model chỉ đọc kết quả.
- `describe(run)`: thói quen nên có — sau mỗi run, nhìn `status`, `content`, tool đã chạy với tham số gì, tốn bao nhiêu token.

### 1.5 Chạy thử

```bash
uv run python -m agno_lab.p01_agent "Phòng ban nào bị cảnh báo ở 2026-Q2?"
```

Với model thật: dòng `tool get_quarter_kpis({'quarter': '2026-Q2'}) -> ...` phải xuất hiện, và câu trả lời phải nêu CLOUD_OPS (KPI_02) và FIN_TECH (KPI_03). Không có dòng `tool` nghĩa là model trả lời mà không lấy số liệu — đọc lại instructions và docstring.

Với `mock_llm` ở chế độ tự động: model giả không bao giờ tự gọi tool, bạn chỉ thấy `content: (mock) Đã nhận: ...`. Muốn thấy cả vòng lặp mà không cần API key, chạy checkpoint dưới đây — model giả được nạp sẵn kịch bản "gọi tool → trả lời".

Thử thêm trong PyCharm: đặt breakpoint trong `get_quarter_kpis`, Debug, xem call stack để thấy Agno gọi hàm của bạn từ đâu (`agno/tools/function.py`).

### 1.6 Checkpoint

```bash
uv run pytest tests/test_p01_agent.py -v      # 4 passed
```

<details>
<summary>Test của Phần 1 — <code>tests/test_p01_agent.py</code></summary>

**File: `tests/test_p01_agent.py`**

```python
import asyncio
import json

from agno_lab.p01_agent import build_agent, describe
from mock_llm import call, say


def tool_messages(request: dict) -> list[str]:
    return [m["content"] for m in request["messages"] if m["role"] == "tool"]


def test_tool_call_and_answer(llm):
    llm.script(call("get_quarter_kpis", quarter="2026-Q2"), say("CLOUD_OPS (KPI_02) và FIN_TECH (KPI_03) bị cảnh báo."))
    run = build_agent().run("Phòng ban nào bị cảnh báo ở 2026-Q2?")

    assert run.content == "CLOUD_OPS (KPI_02) và FIN_TECH (KPI_03) bị cảnh báo."
    (tool,) = run.tools
    assert tool.tool_name == "get_quarter_kpis" and tool.tool_args == {"quarter": "2026-Q2"}
    kpis = {row["dept_code"]: row["alert"] for row in json.loads(tool.result)}
    assert kpis == {"AI_LAB": "ĐẠT", "CLOUD_OPS": "CẢNH BÁO VÀNG", "FIN_TECH": "YÊU CẦU GIẢI TRÌNH"}
    # lượt gọi model thứ 2 nhận kết quả tool — đó là vòng lặp agent
    assert "CẢNH BÁO VÀNG" in tool_messages(llm.requests[1])[0]
    assert run.metrics.total_tokens > 0
    assert "tool get_quarter_kpis" in describe(run)


def test_tools_are_sent_as_json_schema(llm):
    llm.script(say("ok"))
    build_agent().run("chào")
    tools = {t["function"]["name"]: t["function"] for t in llm.requests[0]["tools"]}
    assert set(tools) == {"inspect_rules", "get_quarter_kpis"}
    assert tools["get_quarter_kpis"]["parameters"]["properties"]["quarter"]["type"] == "string"
    assert "Dùng khi người dùng hỏi số liệu" in tools["get_quarter_kpis"]["description"]  # docstring → mô tả


def test_bad_quarter_returns_guidance_and_model_retries(llm):
    llm.script(
        call("get_quarter_kpis", quarter="Q2-2026"),
        call("get_quarter_kpis", quarter="2026-Q2"),
        say("Đã sửa quý và lấy được số liệu."),
    )
    run = build_agent().run("KPI quý 2 năm 2026")
    first, second = run.tools
    assert first.result.startswith("Lỗi: quarter phải có dạng YYYY-Q1..Q4")
    assert json.loads(second.result)[0]["dept_code"] == "AI_LAB"


def test_async_run(llm):
    llm.script(say("xin chào"))
    run = asyncio.run(build_agent().arun("chào"))
    assert run.content == "xin chào"
```

</details>

Bốn test chứng minh: (1) tool được gọi đúng tham số và kết quả quay lại model ở lượt 2; (2) tool được gửi dưới dạng JSON Schema lấy từ docstring; (3) lỗi có hướng dẫn giúp model tự sửa; (4) `arun` (async) cho kết quả như `run`.

### 1.7 Bài tập

1. Thêm tool `list_quarters() -> str` trả các quý có dữ liệu (đọc từ `service.py`). Hỏi "Có dữ liệu những quý nào?" và kiểm tra model gọi đúng tool.
2. Xóa dòng `Dùng khi...` trong docstring của `get_quarter_kpis`, chạy lại với model thật 5 lần. Model có còn gọi tool đều đặn không?
3. Đặt `tool_call_limit=1` rồi hỏi một câu cần cả `get_quarter_kpis` và `inspect_rules`. Đọc `run.messages` để thấy thông báo "Tool call limit reached".
4. Viết test cho bài 1 bằng `llm.script(call("list_quarters"), say(...))`.

---

## Phần 2 — Input và output có cấu trúc

**Học xong phần này bạn:** cho agent nhận input có kiểu và trả object Pydantic, biết chính xác Agno làm gì khi model trả sai schema, và tách việc của LLM (viết chữ) khỏi việc của code (tính và trình bày số).

### 2.1 Cơ chế (đã đo)

| Cấu hình | Agno làm gì | Model nhận gì |
| --- | --- | --- |
| `input_schema=ReportRequest` | Validate input **trước** khi gọi model; sai thì `ValueError`, không tốn token | Input thành message user dạng JSON: `{"quarter": "2026-Q2", "instruction": "..."}` |
| `output_schema=Narrative` | Gửi `response_format={"type": "json_schema", "json_schema": {"name": "Narrative", ...}}`, parse câu trả lời thành `Narrative` | Yêu cầu trả JSON đúng schema |
| `use_json_mode=True` | Gửi `response_format={"type": "json_object"}` và thêm cuối system prompt đoạn `Provide your output as a JSON containing the following fields: <json_fields>...` kèm thuộc tính từng trường | Dùng cho model/endpoint không hỗ trợ `json_schema` (nhiều model local) |

**Bẫy quan trọng nhất của phần này:** khi model trả JSON không đúng schema, Agno 3.1.3 chỉ log WARNING, để `run.content` là **chuỗi thô**, và `run.status` **vẫn là COMPLETED**. Code nào tin `run.content` là `Narrative` sẽ hỏng ở chỗ khác, xa nơi lỗi xảy ra. Vì vậy `write_narrative` kiểm tra `isinstance(run.content, Narrative)` và ném `NarrativeInvalid` ngay tại chỗ.

### 2.2 Chia việc: LLM viết chữ, code giữ số

Lab 00 đã đặt hợp đồng: `Narrative` chỉ gồm `executive_summary` và `actions`. Bảng KPI do `render_report` dựng từ evidence, nên **không con số nào trong bảng đi qua LLM**. `build_report` thể hiện đúng hợp đồng đó: model viết nhận xét, code đọc lại số liệu từ database và render bảng. Model có viết sai một con số trong câu tóm tắt thì bảng vẫn đúng, và cổng kiểm tra ở Phần 11 bắt được lỗi trong câu.

### 2.3 Code

**File: `agno_lab/p02_structured.py`**

```python
"""Phần 2 — Input/Output có cấu trúc: input_schema, output_schema, và việc của LLM tách khỏi việc của code.

uv run python -m agno_lab.p02_structured 2026-Q2 "Lập báo cáo, nêu hai rủi ro chính"
"""

from __future__ import annotations

import sys

from agno.agent import Agent
from pydantic import BaseModel, Field

from agno_lab.p01_agent import KpiTools, inspect_rules, previous_quarter
from agno_lab.settings import model
from reporting import Narrative, make_evidence, render_report
from service import read_metrics


class ReportRequest(BaseModel):
    """Input có kiểu: sai định dạng thì lỗi TRƯỚC khi tốn một lượt gọi model."""

    quarter: str = Field(pattern=r"^\d{4}-Q[1-4]$", description="Quý cần báo cáo, ví dụ 2026-Q2")
    instruction: str = Field(min_length=3, max_length=500, description="Yêu cầu của người dùng")


class NarrativeInvalid(RuntimeError):
    """Model trả output không đúng schema. Agno chỉ log WARNING và để content là chuỗi — ta phải tự chặn."""


def build_writer(json_mode: bool = False) -> Agent:
    return Agent(
        id="report-writer",
        name="Report Writer",
        model=model(),
        input_schema=ReportRequest,
        output_schema=Narrative,  # model trả JSON theo schema; run.content là Narrative
        use_json_mode=json_mode,  # True cho model không hỗ trợ json_schema (một số model local)
        tools=[KpiTools(), inspect_rules],
        instructions=[
            "Viết narrative cho báo cáo KPI bằng tiếng Việt.",
            "Gọi get_quarter_kpis cho đúng quý trong input trước khi viết.",
            "Chỉ dùng số từ kết quả tool. Không viết bảng số liệu — ứng dụng tự render bảng.",
        ],
    )


def write_narrative(request: ReportRequest, agent: Agent | None = None) -> Narrative:
    run = (agent or build_writer()).run(input=request)
    if not isinstance(run.content, Narrative):
        raise NarrativeInvalid(f"Output không đúng schema Narrative: {str(run.content)[:200]}")
    return run.content


def build_report(request: ReportRequest, revision: int = 1) -> str:
    """LLM viết nhận xét; code tính số và render bảng. Số liệu không bao giờ đi qua LLM."""
    narrative = write_narrative(request)
    evidence = make_evidence(read_metrics(request.quarter), read_metrics(previous_quarter(request.quarter)))
    return render_report(evidence, narrative, revision)


if __name__ == "__main__":
    quarter, instruction = (sys.argv[1], sys.argv[2]) if len(sys.argv) == 3 else ("2026-Q2", "Lập báo cáo KPI")
    print(build_report(ReportRequest(quarter=quarter, instruction=instruction)))
```

Đọc code:

- `Field(pattern=r"^\d{4}-Q[1-4]$")`: luật định dạng nằm ở schema, không nằm trong prompt. Gửi `"Q2"` thì lỗi trước khi gọi model.
- `run(input=request)`: truyền object Pydantic (hoặc dict) qua tham số `input`. Chỉ truyền dict khi agent **có** `input_schema`: đã đo, agent không có `input_schema` coi dict là một message (cần khoá `role`) và báo `No messages to be sent to the model`.
- Agent vẫn có tool khi có `output_schema`: model gọi `get_quarter_kpis` trước, rồi mới trả JSON ở lượt cuối.
- `json_mode`: bật khi endpoint báo lỗi kiểu `response_format json_schema not supported`.

### 2.4 Chạy thử

```bash
uv run python -m agno_lab.p02_structured 2026-Q2 "Lập báo cáo, nêu hai rủi ro chính"
```

Kết quả là báo cáo Markdown 4 phần giống Lab 00. Với `mock_llm` ở chế độ tự động, model giả sinh JSON hợp lệ từ schema (nội dung kiểu `(mock) nội dung mẫu`), nên bạn vẫn thấy đủ bảng KPI thật — bằng chứng rằng số liệu không đi qua model.

### 2.5 Checkpoint

```bash
uv run pytest tests/test_p02_structured.py -v      # 5 passed
```

<details>
<summary>Test của Phần 2 — <code>tests/test_p02_structured.py</code></summary>

**File: `tests/test_p02_structured.py`**

```python
import json

import pytest

from agno_lab.p02_structured import NarrativeInvalid, ReportRequest, build_report, build_writer, write_narrative
from mock_llm import answer_json, call
from reporting import Narrative

GOOD = {
    "executive_summary": ["Cloud tăng chi phí 18%.", "FinTech giảm doanh thu 12,5%."],
    "actions": ["Rà soát chi phí."],
}


def test_input_is_validated_before_any_model_call(llm):
    with pytest.raises(ValueError, match="quarter"):
        build_writer().run(input={"quarter": "Q2", "instruction": "lập báo cáo"})
    assert llm.requests == []  # không tốn lượt gọi model nào


def test_input_schema_becomes_json_user_message_and_output_is_typed(llm):
    llm.script(call("get_quarter_kpis", quarter="2026-Q2"), answer_json(GOOD))
    narrative = write_narrative(ReportRequest(quarter="2026-Q2", instruction="Nêu hai rủi ro"))
    assert isinstance(narrative, Narrative) and narrative.actions == ["Rà soát chi phí."]
    user = next(m["content"] for m in llm.requests[0]["messages"] if m["role"] == "user")
    assert json.loads(user) == {"quarter": "2026-Q2", "instruction": "Nêu hai rủi ro"}
    fmt = llm.requests[0]["response_format"]
    assert fmt["type"] == "json_schema" and fmt["json_schema"]["name"] == "Narrative"


def test_invalid_output_is_not_silently_accepted(llm):
    llm.script(answer_json({"executive_summary": ["thiếu actions"]}))
    run = build_writer().run(input=ReportRequest(quarter="2026-Q2", instruction="lập báo cáo"))
    assert run.status.value == "COMPLETED" and isinstance(run.content, str)  # Agno coi là thành công!
    llm.script(answer_json({"executive_summary": ["thiếu actions"]}))
    with pytest.raises(NarrativeInvalid):
        write_narrative(ReportRequest(quarter="2026-Q2", instruction="lập báo cáo"))


def test_json_mode_for_models_without_json_schema(llm):
    llm.script(answer_json(GOOD))
    narrative = write_narrative(
        ReportRequest(quarter="2026-Q2", instruction="lập báo cáo"), agent=build_writer(json_mode=True)
    )
    assert narrative.executive_summary == GOOD["executive_summary"]
    assert llm.requests[0]["response_format"] == {"type": "json_object"}


def test_numbers_come_from_code_not_llm(llm):
    llm.script(call("get_quarter_kpis", quarter="2026-Q2"), answer_json(GOOD))
    report = build_report(ReportRequest(quarter="2026-Q2", instruction="lập báo cáo"))
    assert "6.59%" in report and "| KPI_02 | CẢNH BÁO VÀNG |" in report
    assert "- Cloud tăng chi phí 18%." in report
```

</details>

### 2.6 Bài tập

1. Thêm trường `risks: list[str] = Field(max_length=3)` vào một model mới `NarrativeWithRisks`, dùng làm `output_schema`, render thành mục riêng trong báo cáo.
2. Thêm `departments: list[str] | None` vào `ReportRequest` để lọc phòng ban. Trả lời câu hỏi cuối Lab 01 cũ: lọc FIN_TECH thì sửa contract, evidence hay prompt?
3. Viết test: model trả `{"executive_summary": [], "actions": ["x"]}` (rỗng, vi phạm `min_length=1`) thì `write_narrative` phải ném `NarrativeInvalid`.

---

## Phần 3 — Streaming

**Học xong phần này bạn:** hiển thị câu trả lời theo từng mảnh, biết khi nào tool bắt đầu/kết thúc, và biết bản nào dùng cho CLI, bản nào cho server.

### 3.1 Ba mức streaming

| Gọi | Nhận được |
| --- | --- |
| `run(q)` | Một `RunOutput` khi xong |
| `run(q, stream=True)` | Iterator các sự kiện **nội dung** (`RunContent`): mảnh chữ |
| `run(q, stream=True, stream_events=True)` | Mọi sự kiện: run, model request, tool, nội dung, hoàn tất |
| thêm `yield_run_output=True` | Phần tử cuối là `RunOutput` đầy đủ (status, metrics) |

Thứ tự sự kiện đã đo với một lần gọi tool:

```text
RunStarted
ModelRequestStarted → RunContent... → ModelRequestCompleted      (lượt 1: model quyết định gọi tool)
ToolCallStarted → ToolCallCompleted
ModelRequestStarted → RunContent (nhiều mảnh) → ModelRequestCompleted   (lượt 2: model viết câu trả lời)
RunContentCompleted
RunCompleted        (kèm metrics)
RunOutput           (chỉ khi yield_run_output=True)
```

Không bật `stream_events` thì chỉ có sự kiện nội dung: không biết tool đang chạy. Giao diện muốn hiện "đang tra cứu số liệu..." thì cần `stream_events=True` (AG-UI ở Phần 13 làm việc này cho bạn).

### 3.2 Code

**File: `agno_lab/p03_streaming.py`**

```python
"""Phần 3 — Streaming: nhận token và sự kiện (tool, model, hoàn tất) ngay khi chúng xảy ra.

uv run python -m agno_lab.p03_streaming "KPI quý 2026-Q2 thế nào?"
"""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator, Iterator

from agno.run.agent import RunEvent, RunOutput

from agno_lab.p01_agent import build_agent


def timeline(question: str) -> Iterator[str]:
    """stream=True: nhận dữ liệu theo từng mảnh. stream_events=True: nhận cả sự kiện tool/model, không chỉ chữ."""
    for event in build_agent().run(question, stream=True, stream_events=True, yield_run_output=True):
        if isinstance(event, RunOutput):  # yield_run_output=True: phần tử cuối là RunOutput đầy đủ
            yield f"\n[xong] {event.status.value}, {event.metrics.total_tokens} token"
        elif event.event == RunEvent.run_content.value and event.content:
            yield event.content  # một mảnh token
        elif event.event == RunEvent.tool_call_started.value:
            yield f"\n[tool] {event.tool.tool_name}({event.tool.tool_args})"
        elif event.event == RunEvent.tool_call_completed.value:
            yield f"\n[tool xong] {str(event.tool.result)[:60]}...\n"


async def atimeline(question: str) -> AsyncIterator[str]:
    """Bản async — dùng trong server (FastAPI) để không chặn event loop. Không bật stream_events: chỉ nhận chữ."""
    async for event in build_agent().arun(question, stream=True):
        if event.event == RunEvent.run_content.value and event.content:
            yield event.content


if __name__ == "__main__":
    for piece in timeline(sys.argv[1] if len(sys.argv) > 1 else "KPI quý 2026-Q2 thế nào?"):
        print(piece, end="", flush=True)
    print()
```

Đọc code:

- So sánh `event.event == RunEvent.run_content.value`: mỗi sự kiện có trường `event` là tên chuỗi; dùng enum `RunEvent` để không gõ sai.
- `atimeline` dùng `arun(..., stream=True)` với `async for`. Trong FastAPI hay bất kỳ server async nào, **luôn dùng bản `a...`**: `run()` đồng bộ trong async handler sẽ chặn event loop, mọi request khác phải chờ (lỗi đã chỉ ra ở Lab 00 §1).
- Với `output_schema`, các mảnh stream là JSON chưa hoàn chỉnh. Đừng render chúng như kết quả cuối: chỉ dùng object đã validate trong `RunOutput`.

### 3.3 Chạy thử

```bash
uv run python -m agno_lab.p03_streaming "KPI quý 2026-Q2 thế nào?"
```

Với model thật, bạn thấy dòng `[tool] get_quarter_kpis(...)` trước, rồi chữ chạy dần, cuối cùng `[xong] COMPLETED, ... token`.

### 3.4 Checkpoint

```bash
uv run pytest tests/test_p03_streaming.py -v      # 4 passed
```

<details>
<summary>Test của Phần 3 — <code>tests/test_p03_streaming.py</code></summary>

**File: `tests/test_p03_streaming.py`**

```python
import asyncio

from agno.run.agent import RunEvent

from agno_lab.p01_agent import build_agent
from agno_lab.p03_streaming import atimeline, timeline
from mock_llm import call, say

ANSWER = "Cloud và FinTech bị cảnh báo, AI Lab đạt."


def test_event_order_with_tool(llm):
    llm.script(call("get_quarter_kpis", quarter="2026-Q2"), say(ANSWER))
    names = [e.event for e in build_agent().run("KPI 2026-Q2?", stream=True, stream_events=True)]
    order = [RunEvent.run_started, RunEvent.tool_call_started, RunEvent.tool_call_completed, RunEvent.run_completed]
    positions = [names.index(e.value) for e in order]
    assert positions == sorted(positions)  # bắt đầu → tool → tool xong → hoàn tất
    assert names.count(RunEvent.run_content.value) >= 2  # chữ đến theo nhiều mảnh
    assert llm.requests[0]["stream"] is True


def test_timeline_text_and_final_output(llm):
    llm.script(call("get_quarter_kpis", quarter="2026-Q2"), say(ANSWER))
    text = "".join(timeline("KPI 2026-Q2?"))
    assert "[tool] get_quarter_kpis({'quarter': '2026-Q2'})" in text
    assert ANSWER in text and "[xong] COMPLETED" in text


def test_without_stream_events_only_content(llm):
    llm.script(say(ANSWER))
    names = {e.event for e in build_agent().run("chào", stream=True)}
    assert RunEvent.run_content.value in names
    assert RunEvent.tool_call_started.value not in names and RunEvent.model_request_started.value not in names


def test_async_stream(llm):
    llm.script(say(ANSWER))

    async def collect():
        return "".join([piece async for piece in atimeline("chào")])

    assert asyncio.run(collect()) == ANSWER
```

</details>

### 3.5 Bài tập

1. Đếm thời gian từ `RunStarted` đến mảnh chữ đầu tiên (time-to-first-token) và in ra cuối `timeline`.
2. In thêm `ModelRequestCompleted` kèm số token của từng lượt gọi model. Câu hỏi nào tốn nhiều lượt nhất?
3. Viết `atimeline` bản có `stream_events=True` và trả về `dict` cho mỗi sự kiện — đây là nền của một API SSE tự viết (so sánh với AG-UI ở Phần 13).

---

**Câu hỏi tự kiểm tra Phần 1–3**

1. Một run có 2 lần gọi tool tuần tự thì có ít nhất bao nhiêu lượt gọi model? Vì sao?
2. Model nhận mô tả tool từ đâu? Bạn sửa chỗ nào để model dùng tool đúng lúc hơn?
3. `run.status == COMPLETED` có bảo đảm `run.content` là `Narrative` không? Bạn chặn bằng cách nào?
4. Vì sao bảng KPI trong báo cáo không thể sai dù model viết nhầm số trong phần tóm tắt?
5. Khi nào dùng `run(stream=True)`, khi nào `arun(stream=True)`?

Tiếp theo: [Lab 01b — Session, memory và knowledge (Phần 4–6)](01b-session-memory-knowledge.md).
