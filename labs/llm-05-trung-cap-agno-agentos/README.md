# LLM-05 · Trung cấp · Agno và AgentOS từng phần: agent, workflow, MCP, AG-UI, A2A, eval

**Kỹ năng:** [LLM-05 Tool calling và điều phối workflow/agent](../../docs/02-skill-map/generated/mang/llm.md#llm-05) · **Mức:** Trung cấp (AgentOS, A2A, MCP server chạm mức Nâng cao)
**Thời lượng:** ~12 giờ, chia 16 phần · **Nhóm phụ thuộc:** môi trường riêng từ `requirements.txt` (không thêm vào lockfile chung) · **Chi phí API ước tính:** 0 USD (model giả lập `mock_llm.py`); chạy lại 16 phần với model thật < 0,5 USD

Đây là **project tham chiếu** của bài tự học [Lab 01 — Agno và AgentOS](../../docs/self-practices/guide_01_agno.md): tài liệu chứa toàn bộ code của thư mục này, có giải thích từng phần. `tests/test_doc_sync.py` bảo đảm code trong tài liệu và code ở đây là một.

## Mục tiêu

Sau lab này bạn làm được: tự viết agent Agno có tool, output có schema, streaming, session, memory, knowledge, người duyệt và guardrail; ghép thành team và workflow; đưa chúng ra thành dịch vụ AgentOS có khoá, trace, AG-UI, A2A, MCP server; và đo bằng eval — mỗi tính năng có test chứng minh hành vi đã đo trên Agno 3.1.3.

## Dữ liệu

Dữ liệu giả của [Lab 00](../../docs/self-practices/agent_framework_learning_from_scratch.md): 3 phòng ban × 2 quý trong SQLite, quy ước KPI trong Excel, style guide dạng text. `setup_assets.py` tạo vào `data/` (idempotent); `conftest.py` tự gọi khi chạy test. Không có dữ liệu thật, không cần tải gì.

## Cài đặt

Phiên bản đã chạy (17/10/2026): Python 3.12, `agno` 3.1.3, `mcp` 2.3.0, `fastmcp` 4.1.0, `ag-ui-protocol` 1.0.0, `a2a-sdk` 0.3.26 — đủ danh sách trong `requirements.txt`.

Thư mục này nằm trong repo ai-architecture (cũng là một project uv), nên lệnh dưới đây chạy bằng môi trường riêng dựng từ
`requirements.txt` (`--no-project`), không đụng `pyproject.toml` của repo. Muốn dựng project của riêng bạn từ thư mục
trống, có `.venv` và mở bằng PyCharm, làm theo
[Cách B ở mục 3.1 của guide](../../docs/self-practices/guide_01_agno.md#cách-b--bắt-đầu-từ-thư-mục-trống).

Từ gốc repo, chép cả khối vào Terminal (bash hoặc zsh của macOS). Hàm `lab01` thay cho tiền tố dài; nó chỉ có trong
cửa sổ Terminal đang mở, mở cửa sổ mới thì dán lại dòng thứ hai.

```bash
cd labs/llm-05-trung-cap-agno-agentos
lab01() { uv run --no-project --python 3.12 --with-requirements requirements.txt "$@"; }
lab01 python -m pytest -q
```

| Lệnh | Làm gì |
| --- | --- |
| `lab01 python -m pytest -q` | Toàn bộ test, ~1,5 phút, không cần API key |
| `lab01 python mock_llm.py` | Model giả ở cổng 8900 để chạy các module bằng tay; để nó chạy ở một cửa sổ Terminal riêng |
| `cp .env.example .env` | Chọn OpenAI, model local hoặc mock |
| `lab01 python agno_cli.py report-01 "Lập báo cáo Q2"` | Baseline |
| `lab01 python -m agno_lab.p01_agent "Phòng ban nào bị cảnh báo ở 2026-Q2?"` | Phần 1 |
| `lab01 python -m agno_lab.p12_os` | AgentOS ở <http://localhost:7777/docs> |

Lệnh không có chú thích `#` phía sau vì zsh mặc định không hiểu `#` khi dán vào Terminal; biến kiểu
`AGNO='uv run ...'` rồi gọi `$AGNO python ...` cũng không chạy trên zsh (zsh không tách biến thành nhiều từ), nên ở đây
dùng hàm.

Sửa code xong: `python sync_doc.py` cập nhật các khối code trong tài liệu.

## Các bước

1. Đọc [guide_01_agno.md](../../docs/self-practices/guide_01_agno.md) mục 1–3: lộ trình, Bước 0 nâng MCP lên 2.x, `settings.py`, `mock_llm.py`, hạ tầng test.
2. Chạy baseline `agno_cli.py` hai lượt cùng session (v1 → v2) và một session khác.
3. Học Phần 1–8 ([01a](../../docs/self-practices/agno/01a-agent-tool-output-streaming.md), [01b](../../docs/self-practices/agno/01b-session-memory-knowledge.md), [01c](../../docs/self-practices/agno/01c-tool-hitl-guardrail.md)): mỗi phần đọc cơ chế, chạy module, chạy test `tests/test_pNN_*.py`.
4. Học Phần 11 (workflow) trước Phần 9–10 nếu ưu tiên harness/workflow ([01d](../../docs/self-practices/agno/01d-mcp-team-workflow.md)).
5. Học Phần 12 và 16 ([01e](../../docs/self-practices/agno/01e-agentos-agui-a2a-mcp-eval.md)): AgentOS, trace, eval. Phần 13–15 (AG-UI, A2A, MCP server) khi cần nối giao diện hoặc hệ thống khác.
6. Có API key hoặc model local: chạy lại từng module với model thật, so với hành vi ghi trong tài liệu; chạy `python -m agno_lab.p16_evals`.

## Kiểm tra kết quả

- [ ] 117 test xanh: 74 test hành vi của 16 phần + 43 test đồng bộ tài liệu–code (`tests/test_doc_sync.py`; sửa code xong chạy `python sync_doc.py`).
- [ ] Baseline tạo `storage/agno-report-01/v1.md`, `v2.md` và `storage/agno-report-02/v1.md`.
- [ ] Giải thích được vì sao `run.status == COMPLETED` không bảo đảm `run.content` đúng schema (Phần 2), và vì sao post-hook chặn mà `content` vẫn là output vi phạm (Phần 8).
- [ ] Mở `storage/agno_lab.db`, chỉ ra bảng chứa lịch sử run, state, memory, eval, trace.
- [ ] Đọc cây span của một run qua `GET /traces/{trace_id}` và chỉ ra lượt gọi model nào quyết định gọi tool.
- [ ] Với model thật: in token vào/ra của một run (`describe(run)` ở Phần 1) và kết quả `SUITE:` của Phần 16.

## Câu hỏi mở rộng

- Thay `session_state["revision"]` bằng repository SQLite có khoá phiên bản (bài tập B của Lab 01) và nối vào bước `publish` của workflow.
- Viết giao diện web tối giản đọc SSE từ `/agui`, áp `STATE_DELTA`, chạy frontend tool `highlight_departments` (Phần 13), rồi so với add-in Excel của [CMB-10](../../projects/cmb-10-excel-agent-addin/README.md).
- Dựng lại workflow Phần 11 bằng LangGraph ([Lab 03](../../docs/self-practices/guide_03_langgraph.md)) và bằng harness LangChain ([lab LangChain](../llm-05-trung-cap-harness-langchain/README.md)); so cách dừng/chạy tiếp và số dòng code.
- Đưa bộ case của Phần 16 vào CI với model thật, chặn merge khi `status != "PASS"`.

## Cảnh báo đã biết

- `agno[mcp]` 3.1.3 cần `mcp>=2.1`; Lab 00 dùng mcp 1.x. Bản trong lab đã sửa `mcp_db_server.py` (MCPServer, ToolError, `--http`) và một dòng `mcp_client.py` (`is_error`). Các file khác của Lab 00 giữ nguyên văn; `ruff.toml` của lab bỏ qua hai cảnh báo lint trên code đó thay vì sửa code của người học.
- Tracing của Agno là toàn tiến trình (AgentOS `tracing=True` đầu tiên quyết định DB nhận span); test tracing chạy AgentOS ở tiến trình riêng.
- Agno dùng một `httpx.AsyncClient` cho cả tiến trình; `conftest.py` cấp client mới cho mỗi test vì mỗi `asyncio.run()` là một event loop mới.
- Bước nối với Claude Code (`claude mcp add ...`, Phần 15) và JWT của AgentOS chưa được kiểm chứng trong lab.
