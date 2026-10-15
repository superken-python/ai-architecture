# Lab 01 — Tự code Report Agent với Agno

Trước khi bắt đầu: hoàn thành [Lab 00](agent_framework_learning_from_scratch.md) đến checkpoint MCP. Đây là bài riêng cho engine Agno; dùng chung `service.py`, `rules.py`, `reporting.py`, `mcp_client.py` và dữ liệu, không kéo thả bản sao sang project khác.

## 1. Mục tiêu và ranh giới

Sau bài này, bạn cần giải thích được model, tool, session history và revision báo cáo khác nhau như thế nào. Baseline chạy CLI: lấy evidence bắt buộc qua MCP, cho Agno viết narrative có schema, render KPI bằng code và lưu v1/v2.

Agno session database lưu lịch sử run; nó không tự tạo hệ quản lý phiên bản artifact hoặc bảo đảm resume giữa một tool đang chạy dở. Bài này lưu revision riêng bằng JSON để bạn nhìn rõ hai trách nhiệm đó. Không suy ra bảo đảm crash recovery từ việc chat history còn sau restart.

API tham khảo dùng `agno.db.sqlite.SqliteDb`, `db=`, `add_history_to_context` và `output_schema`; thay cho nhóm API `agno.storage.sqlite.SqliteStorage` trong bản cũ. Xem [Agno SQLite](https://docs.agno.com/database/providers/sqlite/usage/sqlite-for-agent) và [structured output](https://docs.agno.com/input-output/structured-output/agent). Chạy theo version đã lock; dùng `⌘B` kiểm tra signature nếu môi trường khác.

## 2. Chuẩn bị — 15 phút

Trong project thực hành đã tạo ở Lab 00:

```bash
uv add agno openai 'sqlalchemy[asyncio]'
uv run python setup_assets.py
uv run python mcp_client.py
```

Cài xong giữ `uv.lock`. `.env` dùng `OPENAI_API_KEY`, `MODEL_ID` là tên model không có prefix provider. Chưa chạy model ở bước này; chỉ kiểm tra MCP nhận đủ 3+3 dòng.

Extra `sqlalchemy[asyncio]` kéo thêm `greenlet`: một số bản Agno import cả SQLite async khi bạn chỉ dùng `SqliteDb`, nên cài `sqlalchemy` trơn có thể vẫn lỗi lúc import trên macOS.

**PyCharm:** `⌥F12` mở Terminal, `⌘1` mở Project, `⌘⇧A` → New để tạo `agno_cli.py`. Tạo Run Configuration kiểu Python, script là `agno_cli.py`, parameters `report-01 "Lập báo cáo Q2/2026"`, working directory là root project.

## 3. Tự thiết kế trước khi xem code — 20 phút

Viết ra hợp đồng của ba hàm:

- `inspect_rules()` trả quy ước chính xác từ Excel; đây là Python tool trong process.
- `build_agent(thread_id)` trả Agent với persistent session database.
- `main(thread_id, instruction)` lấy evidence qua MCP, truyền draft cũ, chạy model, kiểm tra output và lưu artifact.

Bắt buộc lấy dữ liệu không nên chỉ phụ thuộc lời nhắc “luôn gọi tool”; baseline điều phối bước đó bằng code. Tool tự chọn là chỗ thử nghiệm thêm khả năng của model. Ghi riêng vào trace việc nào do ứng dụng gọi, việc nào do LLM chọn.

## 4. Code tham khảo — `agno_cli.py`

Tự gõ theo ba nhóm: imports + tool, build agent, CLI. Sau mỗi nhóm `⌘⌥L` để format và `⌃⌥O` dọn imports.

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

Chương trình đọc hai quý cố định Q2/Q1 2026 để so sánh công bằng giữa ba framework. Yêu cầu “chuyển sang Q3” chưa được hỗ trợ chỉ bằng prompt: cần thêm input quý có validation và truyền đến MCP. Tương tự, thay đổi cách hiển thị bảng phải sửa renderer; narrative không được quyền sửa số gốc.

Baseline luôn refresh database nhưng vẫn truyền draft trước để sửa nhận xét. Cache evidence qua nhiều lượt là bài mở rộng, cần policy rõ khi nào dữ liệu hết hạn.

## 5. Chạy v1, sửa v2 và tách session

```bash
uv run python agno_cli.py report-01 'Lập báo cáo Q2, chỉ rõ hai rủi ro Cloud và FinTech.'
uv run python agno_cli.py report-01 'Rút tóm tắt còn 3 ý, thêm hành động có người phụ trách dạng vai trò.'
uv run python agno_cli.py report-02 'Lập báo cáo Q2 cho phiên độc lập.'
```

Kết quả cần quan sát:

| Nơi lưu | Cần có |
| --- | --- |
| `storage/agno_sessions.db` | Lịch sử run theo session |
| `storage/agno-report-01.json` | Revision 2 và report mới nhất |
| `storage/agno-report-01/v1.md`, `v2.md` | Hai artifact để so sánh |
| `storage/agno-report-02/v1.md` | Session mới bắt đầu ở v1 |

Mỗi lệnh CLI đã là một process mới, vì vậy chuỗi v1/v2 kiểm tra tính lưu trữ qua restart bình thường. Nó chưa kiểm tra crash giữa model call và lúc ghi state.

Đối chiếu bảng KPI với Lab 00. Có đủ 4 phần; research ghi fixture; không có URL giả hoặc chuẩn ngành bịa ra. Narrative có thể vẫn viết sai dù schema hợp lệ: đọc kỹ ý nghĩa, không chỉ nhìn code chạy thành công.

## 6. Debug bằng PyCharm — 25 phút

| Điểm dừng | Phím/action | Cần quan sát |
| --- | --- | --- |
| `current, prior = ...` | `⌘F8`, Debug configuration | Hai list đủ phòng ban |
| `make_evidence(...)` | `F7` vào hàm | Tại sao Cloud bị vàng? |
| `response = await ...` | `F8` | Kiểu của `response.content` |
| `revision = ...` | `⌥F8` | `previous.get("revision", 0)` ở v1/v2 |
| `inspect_rules` | Breakpoint | Model có thực sự gọi tool không? |

Nếu model không gọi `inspect_rules`, đây không tự động là lỗi: evidence đã có dữ liệu cần thiết. Thử thêm yêu cầu “xác minh quy ước Excel bằng tool” rồi xem trace. Không dùng việc model tự thuật “tôi đã gọi tool” thay cho trace thực.

Bài refactor: chọn phần load/save state → `⌘⌥M` Extract Method. Đổi `thread_id` thành `report_session_id` bằng `⇧F6`, rồi dùng `⌥F7` xem mọi chỗ đã đổi đúng.

## 7. Bài tập mở rộng theo thứ tự

### A. Tool do LLM chọn và MCP

Tạo async tool `fetch_quarter_metrics(quarter: str)` mở `ClientSession`, gọi `get_metrics`. Tách helper client để nhận quarter thay vì thu cố định hai quý. Đăng ký wrapper đó trong `tools`. Đây là bước học tool selection; giữ validation đầu vào và yêu cầu kiểm tra evidence trước render.

So sánh trace giữa hai cách: orchestration luôn gọi MCP trước model, và model tự quyết định gọi MCP. Trường hợp thứ hai phải xử lý thiếu tool result, gọi sai quý và tool thất bại. Không thay bằng import hàm server trực tiếp.

### B. Cache, session history và revision repository

Thay JSON state bằng SQLite repository:

```text
reports(thread_id, revision, request_id UNIQUE, markdown, evidence_hash, created_at)
PRIMARY KEY(thread_id, revision)
```

Dùng transaction và expected revision để tránh hai lượt cùng ghi v2. `request_id` trùng trả lại artifact đã commit. Lịch sử chat chỉ giữ 5 run không phải toàn bộ revision archive. Khi lưu report và session DB ở hai nơi, không tự coi hai write là một transaction nguyên tử.

Nghiệm thu: hai tiến trình cùng sửa report-01 không âm thầm ghi đè nhau; crash sau model trước commit có hành vi retry được mô tả rõ.

### C. Research thật và UI

Thay fixture theo hợp đồng research ở Lab 00, kiểm tra counter cache hit. Sau đó triển khai A2A bằng SDK. Cuối cùng viết API + AG-UI adapter; dùng `arun` hoặc async streaming API đúng version. Khi output schema được stream, đừng render một object chưa đủ field như kết quả cuối đã validate.

## 8. Lỗi thường gặp và câu hỏi tự kiểm tra

| Lỗi | Hướng xử lý |
| --- | --- |
| `No module named agno.storage` | Đang dùng API cũ; baseline dùng `agno.db.sqlite` |
| Output không validate thành Narrative | Xem model có hỗ trợ structured output và version API không |
| Key sai khi dùng tên `openai:...` | `MODEL_ID` của Agno không chứa prefix provider |
| Session có history nhưng report thiếu revision | Hai tầng lưu riêng; kiểm tra JSON artifact state |
| File report bị ghi đè khi chạy đồng thời | Baseline chưa có concurrency control; làm bài repository |

Trước khi kết thúc, tự trả lời:

1. Tools ở `tools=[...]` khác thế nào với helper `collect_metrics()` được gọi trước model?
2. Xóa `agno_sessions.db` nhưng giữ JSON state thì còn và mất những gì?
3. Giữ session DB nhưng xóa JSON state sẽ có rủi ro gì cho số revision?
4. Muốn lọc riêng FIN_TECH, bạn sửa contract, evidence hay chỉ prompt? Tại sao?
5. Đâu là bằng chứng số liệu đúng, đâu là bằng chứng narrative đúng?

**Hoàn thành baseline** khi chạy được v1/v2, session độc lập, KPI đúng và giải thích được các câu hỏi trên. Đi tiếp: [Lab 02 — Pydantic AI + Temporal](guide_02_pydantic_ai_temporal.md).
