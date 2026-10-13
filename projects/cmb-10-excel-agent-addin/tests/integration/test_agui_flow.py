"""Luồng đầy đủ qua AgentOS: POST /agui (AG-UI) → adapter → OpenAI Agents SDK → tool → API dữ liệu → workbook."""

from __future__ import annotations

import httpx

from tests.conftest import agui_run, text_of, tool_results


async def test_chat_creates_excel_file_via_handoff(client: httpx.AsyncClient) -> None:
    events = await agui_run(client, "Tạo file Excel danh sách khách hàng ở Hà Nội")
    types = [e["type"] for e in events]
    assert types[0] == "RUN_STARTED" and types[-1] == "RUN_FINISHED"
    calls = [e["toolCallName"] for e in events if e["type"] == "TOOL_CALL_START"]
    assert calls == ["transfer_to_excel_report_agent", "export_excel"]
    handoff, workbook = tool_results(events)
    assert handoff == {"type": "handoff", "to": "Excel Report Agent"}
    assert workbook["type"] == "workbook" and workbook["rows"] == 9
    assert workbook["filters"] == [{"column": "Thành phố", "op": "eq", "value": "Hà Nội"}]
    assert "Đã tạo file" in text_of(events)

    # bấm vào file → xem dữ liệu
    preview = (await client.get(workbook["preview_url"])).json()
    city = preview["columns"].index("Thành phố")
    assert preview["total_rows"] == 9 and {row[city] for row in preview["rows"]} == {"Hà Nội"}
    download = await client.get(workbook["download_url"])
    assert download.status_code == 200 and download.content[:2] == b"PK"


async def test_search_command_uses_selected_column_then_apply(client: httpx.AsyncClient) -> None:
    created = tool_results(await agui_run(client, "Tạo file Excel khách hàng ở Hà Nội", thread_id="t-2"))[-1]
    wid = created["workbook_id"]
    ui = {"active_workbook_id": wid, "selected_column": "Thành phố", "selected_rows": [0, 1]}
    events = await agui_run(client, "/search Đà Nẵng", thread_id="t-2", ui=ui)
    # lệnh "/" chạy bằng code: chỉ một tool, không có handoff
    assert [e["toolCallName"] for e in events if e["type"] == "TOOL_CALL_START"] == ["search_data"]
    result = tool_results(events)[0]
    assert result["type"] == "search_results" and result["column"] == "Thành phố"
    assert result["target"] == {"workbook_id": wid, "column": "Thành phố", "rows": [0, 1]}
    assert all(r["Thành phố"] == "Đà Nẵng" for r in result["records"])

    # người dùng chọn 1 kết quả → ghi vào cột cho 2 dòng đang chọn
    body = {
        "mode": "set_column",
        "records": result["records"][:1],
        "target_column": "Thành phố",
        "row_indexes": [0, 1],
        "expected_version": 1,
    }
    applied = await client.post(f"/api/v1/workbooks/{wid}/apply", json=body)
    assert applied.status_code == 200, applied.text
    assert applied.json()["workbook"]["version"] == 2
    again = await client.post(f"/api/v1/workbooks/{wid}/apply", json=body)  # phiên bản cũ → bị chặn
    assert again.status_code == 422 and "phiên bản" in again.json()["detail"]

    undone = await client.post(f"/api/v1/workbooks/{wid}/undo")
    assert undone.json()["version"] == 1


async def test_search_command_column_syntax_and_errors(client: httpx.AsyncClient) -> None:
    result = tool_results(await agui_run(client, "/search Phân khúc: Đại lý", thread_id="t-3"))[0]
    assert result["column"] == "Phân khúc" and result["total"] == 20
    # phần trước dấu ":" không phải tên cột → tìm toàn văn
    result = tool_results(await agui_run(client, "/search in:san_pham màn hình: 27 inch", thread_id="t-3"))[0]
    assert result["dataset"] == "san_pham" and result["column"] is None
    result = tool_results(await agui_run(client, "/search in:khong_co abc", thread_id="t-3"))[0]
    assert result["type"] == "error"
    events = await agui_run(client, "/help", thread_id="t-3")
    assert "/search" in text_of(events) and not tool_results(events)


async def test_rest_run_without_streaming(client: httpx.AsyncClient) -> None:
    """Endpoint REST chuẩn của AgentOS cũng chạy được agent OpenAI Agents SDK (qua _arun_adapter)."""
    resp = await client.post("/agents/excel-agent/runs", data={"message": "/datasets", "stream": "false"})
    assert resp.status_code == 200, resp.text
    assert "khach_hang" in resp.json()["content"]


async def test_ui_config_and_workbook_errors(client: httpx.AsyncClient) -> None:
    config = (await client.get("/api/v1/config")).json()
    assert config == {
        "mode": "offline",
        "model": "offline-rules",
        "triage": True,
        "default_dataset": "khach_hang",
        "agui_path": "/agui",
        "agent_id": "excel-agent",
    }
    assert (await client.get("/api/v1/workbooks/khongco123")).status_code == 404
    assert (await client.get("/")).status_code == 200
