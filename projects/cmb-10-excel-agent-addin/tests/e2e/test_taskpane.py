"""Kiểm thử task pane của Office add-in bằng Chromium + Office.js giả lập (tests/e2e/fake_office.js).

Không có Excel thật trong CI, nên test này kiểm phần code Office.js của add-in (web/js/hosts/office-host.js) trên một
bản mô phỏng các API đang dùng. Luồng: tìm trong bảng → thêm dòng vào Excel Table (giữ số 0 đầu) → ghi cột cho vùng
đang chọn → chặn ghi khi ô bị sửa sau lúc xem trước → /search → ghi vào cột → chèn file xuất từ hệ thống → sheet không
phải Table, dữ liệu bắt đầu ở B3.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.e2e.conftest import shot

pytestmark = pytest.mark.e2e
playwright = pytest.importorskip("playwright.sync_api")
expect = playwright.expect
PENDING = ".confirm-card:not(.accepted):not(.rejected)"  # thẻ xác nhận đang chờ người dùng bấm
FAKE_OFFICE = (Path(__file__).parent / "fake_office.js").read_text(encoding="utf-8")
OFFICE_JS = "https://appsforoffice.microsoft.com/lib/1/hosted/office.js"

INIT = {
    "workbook": "Bao-cao-khach-hang.xlsx",
    "sheets": [
        {
            "name": "Khách hàng",
            "table": "KhachHang",
            "rows": [
                ["Mã KH", "Tên khách hàng", "Thành phố", "Điện thoại"],
                ["KH-0001", "Đại lý An Phát 01", "TP. Hồ Chí Minh", "0957169990"],
                ["KH-0002", "Ngô Thị An", "Hà Nội", "0998139237"],
                ["KH-0010", "Khách Huế", "Huế", "0900000010"],
                ["KH-0006", "Khách Đà Nẵng", "Đà Nẵng", "0900000006"],
            ],
        },
        {
            "name": "Đơn hàng",
            "rows": [[], [], ["", "Mã ĐH", "Mã KH", "Trạng thái"], ["", "DH-1", "KH-0001", "Đã giao"],
                     ["", "DH-2", "KH-0002", "Đang giao"], ["", "DH-3", "KH-0006", "Đã giao"]],
        },
    ],
}  # fmt: skip


def ask(page: Any, text: str) -> None:
    page.fill("#input", text)
    page.press("#input", "Enter")
    expect(page.locator("#send")).to_be_enabled(timeout=20_000)


def start(page: Any, text: str) -> Any:
    """Gửi câu hỏi và chờ thẻ xác nhận ghi xuất hiện (run đang tạm dừng chờ người dùng)."""
    page.fill("#input", text)
    page.press("#input", "Enter")
    card = page.locator(PENDING)
    expect(card).to_be_visible(timeout=20_000)
    return card


def answer(page: Any) -> Any:
    return page.locator(".msg.assistant").last


def sheet(page: Any, name: str) -> list[list[Any]]:
    return page.evaluate("(n) => window.__fakeExcel.dump(n)", name)


def test_taskpane_with_office_js(server: str, browser: Any) -> None:
    page = browser.new_page(viewport={"width": 400, "height": 900})  # cỡ task pane thật
    page.add_init_script(f"window.__FAKE_EXCEL_INIT__ = {__import__('json').dumps(INIT, ensure_ascii=False)};")
    page.route(OFFICE_JS, lambda route: route.fulfill(status=200, content_type="text/javascript", body=FAKE_OFFICE))
    page.goto(f"{server}/static/taskpane.html")
    expect(page.locator("#excel-status")).to_contain_text("Bao-cao-khach-hang.xlsx · sheet Khách hàng")
    expect(page.locator("#mode-badge")).to_contain_text("Offline")

    # 1 · tìm trong bảng đang mở → chọn dòng tìm được trên sheet
    ask(page, "Tìm dòng có Thành phố là Huế trong bảng")
    expect(answer(page)).to_contain_text("dòng 4")
    assert ["select", "Khách hàng!C4:C4"] in page.evaluate("window.__fakeExcel.calls")

    # 2 · tra hệ thống rồi thêm vào Excel Table (rows.add), điện thoại giữ số 0 đầu
    card = start(page, "Thêm khách hàng KH-0012 vào bảng")
    expect(card).to_contain_text("từ dòng 6")
    shot(page, "taskpane-1-confirm")
    card.locator("[data-ok]").click()
    expect(page.locator("#send")).to_be_enabled(timeout=20_000)
    expect(answer(page)).to_contain_text("Đã thêm 1 dòng vào sheet Khách hàng (dòng 6)")
    assert sheet(page, "Khách hàng")[5] == ["KH-0012", "Công ty CP Phú Gia 12", "Nha Trang", "0959255609"]
    assert ["table.rows.add", 1] in page.evaluate("window.__fakeExcel.calls")

    # 3 · người dùng chọn C2:C3 → agent ghi cùng một giá trị cho vùng chọn
    page.evaluate("window.__fakeExcel.select('Khách hàng', 1, 2, 2, 1)")
    expect(page.locator("#excel-status")).to_contain_text("cột Thành phố")
    card = start(page, 'Ghi "Cần Thơ" vào cột Thành phố cho các dòng đang chọn')
    expect(card.locator("td.old").first).to_have_text("TP. Hồ Chí Minh")
    card.locator("[data-ok]").click()
    expect(page.locator("#send")).to_be_enabled(timeout=20_000)
    assert [r[2] for r in sheet(page, "Khách hàng")[1:3]] == ["Cần Thơ", "Cần Thơ"]

    # 4 · ô bị sửa trong lúc thẻ xác nhận đang mở → không ghi đè, agent báo lỗi
    card = start(page, 'Ghi "Huế" vào cột Thành phố cho các dòng đang chọn')
    page.evaluate("window.__fakeExcel.setCell('Khách hàng', 1, 2, 'Sửa tay')")
    card.locator("[data-ok]").click()
    expect(page.locator("#send")).to_be_enabled(timeout=20_000)
    expect(answer(page)).to_contain_text("đã đổi từ lúc xem trước")
    assert [r[2] for r in sheet(page, "Khách hàng")[1:3]] == ["Sửa tay", "Cần Thơ"]  # không ô nào bị ghi

    # 5 · /search theo cột đang chọn (không gọi model) → tích 1 kết quả → ghi vào cột cho 2 dòng
    ask(page, "/search Đà Nẵng")
    results = page.locator(".results-card").last
    expect(results).to_contain_text("cột Thành phố")
    results.locator('tbody input[type="checkbox"]').first.check()
    results.locator('[data-act="set"]').click()
    expect(results.locator("select[data-target]")).to_have_value("Thành phố")
    results.locator("[data-confirm]").click()
    expect(results.locator(".apply-result")).to_contain_text("Đã ghi 2 ô vào cột Thành phố")
    assert [r[2] for r in sheet(page, "Khách hàng")[1:3]] == ["Đà Nẵng", "Đà Nẵng"]
    shot(page, "taskpane-2-search")

    # 6 · file do agent xuất từ hệ thống → chèn thành sheet mới trong workbook đang mở
    ask(page, "Tạo file Excel khách hàng ở Hà Nội")
    page.locator(".file-card").last.locator("button", has_text="Chèn vào workbook").click()
    expect(page.locator("#toast")).to_contain_text("Đã chèn dữ liệu thành sheet mới")
    inserted = [c for c in page.evaluate("window.__fakeExcel.calls") if c[0] == "insertWorksheetsFromBase64"]
    assert inserted and inserted[0][1].startswith("UEsDB")  # nội dung .xlsx (zip "PK")

    # 7 · sheet không phải Excel Table, bảng bắt đầu ở B3: số dòng trả về đúng, thêm dòng ghi ngay dưới vùng dữ liệu
    page.evaluate("window.__fakeExcel.select('Đơn hàng', 0, 0)")
    expect(page.locator("#excel-status")).to_contain_text("sheet Đơn hàng")
    ask(page, "Tìm dòng có Trạng thái là Đang giao trong bảng")
    expect(answer(page)).to_contain_text("dòng 5")
    card = start(page, "Thêm khách hàng KH-0005 vào bảng")
    expect(card).to_contain_text("từ dòng 7")
    card.locator("[data-ok]").click()
    expect(page.locator("#send")).to_be_enabled(timeout=20_000)
    assert sheet(page, "Đơn hàng")[6][1:4] == ["", "KH-0005", ""]
    page.close()
