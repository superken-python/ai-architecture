"""Luồng đầy đủ qua AgentOS thật: POST /agui (AG-UI) → agent Agno → tool server / tool Excel ở client.

Model là bộ luật offline đi qua đúng đường code `OpenAIResponses` của Agno (API giả lập trong tiến trình).
"""

from __future__ import annotations

import httpx

from tests.conftest import EXCEL_TOOLS, SHEET_UI, agui_resume, agui_run, pending_calls, text_of, tool_results


async def test_chat_creates_excel_file_then_preview(client: httpx.AsyncClient) -> None:
    events = await agui_run(client, "Tạo file Excel danh sách khách hàng ở Hà Nội", tools=EXCEL_TOOLS)
    types = [e["type"] for e in events]
    assert types[0] == "RUN_STARTED" and types[-1] == "RUN_FINISHED"
    assert [e["toolCallName"] for e in events if e["type"] == "TOOL_CALL_START"] == ["export_excel"]
    workbook = tool_results(events)[0]
    assert workbook["type"] == "workbook" and workbook["rows"] == 9
    assert workbook["filters"] == [{"column": "Thành phố", "op": "eq", "value": "Hà Nội"}]
    assert "Đã tạo file" in text_of(events) and not pending_calls(events)

    # bấm vào file → xem dữ liệu
    preview = (await client.get(workbook["preview_url"])).json()
    city = preview["columns"].index("Thành phố")
    assert preview["total_rows"] == 9 and {row[city] for row in preview["rows"]} == {"Hà Nội"}
    download = await client.get(workbook["download_url"])
    assert download.status_code == 200 and download.content[:2] == b"PK"


async def test_append_record_pauses_for_excel_then_resumes(client: httpx.AsyncClient) -> None:
    """search_data chạy ở server → excel_append_rows tạm dừng chờ add-in → add-in gửi kết quả → agent trả lời."""
    text = "Thêm khách hàng KH-0012 vào bảng"
    events = await agui_run(client, text, thread_id="t-append", ui=SHEET_UI, tools=EXCEL_TOOLS)
    assert tool_results(events)[0]["records"][0]["Mã KH"] == "KH-0012"
    (call,) = pending_calls(events)
    assert call["name"] == "excel_append_rows" and events[-1]["type"] == "RUN_FINISHED"
    # chỉ các cột có trong sheet, giá trị lấy nguyên từ hệ thống (điện thoại giữ số 0 đầu)
    row = call["args"]["rows"][0]
    assert list(row) == ["Mã KH", "Tên khách hàng", "Thành phố", "Điện thoại"]
    assert row["Mã KH"] == "KH-0012" and row["Điện thoại"].startswith("0")

    applied = {"status": "applied", "sheet": "Khách hàng", "rows_added": 1, "first_row": 12, "last_row": 12}
    events = await agui_resume(client, "t-append", text, {call["id"]: applied}, [call], SHEET_UI, EXCEL_TOOLS)
    assert not pending_calls(events)
    assert "Đã thêm 1 dòng vào sheet Khách hàng (dòng 12)" in text_of(events)

    # lịch sử lưu ở server (SQLite của AgentOS): run đã chuyển từ tạm dừng sang hoàn thành
    runs = (await client.get("/sessions/t-append/runs", params={"type": "agent"})).json()
    assert runs[-1]["status"] in ("COMPLETED", "completed")


async def test_user_rejects_write(client: httpx.AsyncClient) -> None:
    text = "Thêm khách hàng KH-0003 vào bảng"
    (call,) = pending_calls(await agui_run(client, text, thread_id="t-reject", ui=SHEET_UI, tools=EXCEL_TOOLS))
    rejected = {"status": "rejected", "message": "Người dùng đã hủy"}
    events = await agui_resume(client, "t-reject", text, {call["id"]: rejected}, [call], SHEET_UI, EXCEL_TOOLS)
    assert "Bạn đã hủy" in text_of(events)


async def test_find_rows_and_set_values_on_selection(client: httpx.AsyncClient) -> None:
    text = "Tìm dòng có Thành phố là Đà Nẵng trong bảng"
    (call,) = pending_calls(await agui_run(client, text, thread_id="t-find", ui=SHEET_UI, tools=EXCEL_TOOLS))
    assert call["name"] == "excel_find_rows"
    assert call["args"]["column"] == "Thành phố" and call["args"]["query"] == "Đà Nẵng"
    found = {"status": "ok", "sheet": "Khách hàng", "column": "Thành phố", "query": "Đà Nẵng", "total": 2,
             "matches": [{"row": 4, "values": {}}, {"row": 9, "values": {}}]}  # fmt: skip
    events = await agui_resume(client, "t-find", text, {call["id"]: found}, [call], SHEET_UI, EXCEL_TOOLS)
    assert "dòng 4, 9" in text_of(events)

    text = 'Ghi "VIP" vào cột Phân khúc cho các dòng đang chọn'
    ui = {**SHEET_UI, "headers": [*SHEET_UI["headers"], "Phân khúc"]}
    (call,) = pending_calls(await agui_run(client, text, thread_id="t-set", ui=ui, tools=EXCEL_TOOLS))
    assert call["args"] == {"column": "Phân khúc", "rows": [3, 4], "values": ["VIP"], "create_column": False}


async def test_excel_tools_missing_means_no_excel(client: httpx.AsyncClient) -> None:
    events = await agui_run(client, "Thêm khách hàng KH-0012 vào bảng", thread_id="t-noexcel")
    assert not pending_calls(events) and "Chưa kết nối được Excel" in text_of(events)


async def test_search_command_uses_selected_column_then_apply(client: httpx.AsyncClient) -> None:
    created = tool_results(await agui_run(client, "Tạo file Excel khách hàng ở Hà Nội", thread_id="t-2"))[-1]
    wid = created["workbook_id"]
    ui = {"host": "web", "workbook_id": wid, "selection": {"column": "Thành phố", "rows": [2, 3]}}
    out = (await client.post("/api/v1/commands", json={"text": "/search Đà Nẵng", "ui": ui})).json()
    assert out["handled"] and out["result"]["type"] == "search_results"
    result = out["result"]
    assert result["column"] == "Thành phố" and all(r["Thành phố"] == "Đà Nẵng" for r in result["records"])
    assert "Tìm thấy" in out["text"]

    # người dùng chọn 1 kết quả → ghi vào cột cho 2 dòng đang chọn (dòng Excel 2, 3 = chỉ số 0, 1)
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


async def test_commands_column_syntax_dataset_guess_and_errors(client: httpx.AsyncClient) -> None:
    async def command(text: str, ui: dict | None = None) -> dict:
        return (await client.post("/api/v1/commands", json={"text": text, "ui": ui or {}})).json()

    result = (await command("/search Phân khúc: Đại lý"))["result"]
    assert result["column"] == "Phân khúc" and result["total"] == 20
    # phần trước dấu ":" không phải tên cột → tìm toàn văn
    result = (await command("/search in:san_pham màn hình: 27 inch"))["result"]
    assert result["dataset"] == "san_pham" and result["column"] is None
    assert (await command("/search in:khong_co abc"))["result"]["type"] == "error"
    # Excel thật: không có workbook_id → đoán dataset theo tiêu đề cột của sheet
    sheet = {"host": "office", "headers": ["Mã SP", "Tên sản phẩm", "Đơn giá (VND)"]}
    assert (await command("/search laptop", sheet))["result"]["dataset"] == "san_pham"
    assert "/search" in (await command("/help"))["text"]
    assert "Không có lệnh" in (await command("/xyz"))["text"]
    assert (await command("xin chào"))["handled"] is False


async def test_rest_run_without_streaming(client: httpx.AsyncClient) -> None:
    """Endpoint REST chuẩn của AgentOS cũng chạy được agent (Responses API không stream)."""
    resp = await client.post(
        "/agents/excel-agent/runs", data={"message": "tìm khách hàng ở Cần Thơ", "stream": "false"}
    )
    assert resp.status_code == 200, resp.text
    assert "Tìm thấy" in resp.json()["content"]


async def test_ui_config_and_pages(client: httpx.AsyncClient) -> None:
    config = (await client.get("/api/v1/config")).json()
    assert config == {
        "mode": "offline",
        "model": "offline-rules",
        "framework": "agno",
        "default_dataset": "khach_hang",
        "agui_path": "/agui",
        "agent_id": "excel-agent",
    }
    assert (await client.get("/api/v1/workbooks/khongco123")).status_code == 404
    assert (await client.get("/")).status_code == 200
    taskpane = await client.get("/static/taskpane.html")
    assert taskpane.status_code == 200 and "office.js" in taskpane.text
    assert (await client.get("/static/assets/icon-80.png")).content[:4] == b"\x89PNG"
