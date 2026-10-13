"""Kiểm thử web POC bằng Chromium thật (server offline, không cần API key).

Luồng: chat → file Excel → xem dữ liệu → agent thêm dòng (tool Excel tạm dừng → xác nhận) → chặn trùng mã → hủy →
tìm trong sheet → ghi cột cho dòng đang chọn → /search → ghi vào cột → hoàn tác → tải file.

Chạy: `make setup-e2e && make e2e`. Đặt E2E_SCREENSHOTS=<thư mục> để lưu ảnh chụp từng bước.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.e2e.conftest import shot

pytestmark = pytest.mark.e2e
playwright = pytest.importorskip("playwright.sync_api")
expect = playwright.expect
PENDING = ".confirm-card:not(.accepted):not(.rejected)"  # thẻ xác nhận đang chờ người dùng bấm


def ask(page: Any, text: str) -> None:
    page.fill("#input", text)
    page.press("#input", "Enter")
    expect(page.locator("#send")).to_be_enabled(timeout=20_000)  # nút Gửi bật lại = lượt chat đã xong


def last_answer(page: Any) -> Any:
    return page.locator(".msg.assistant").last


def cell(page: Any, row: int, column: str) -> str:
    col = page.locator("#grid thead tr.headers th").all_inner_texts().index(column)
    return page.locator(f'#grid tbody tr[data-row="{row - 2}"] td').nth(col).inner_text()


def test_web_poc_full_flow(server: str, browser: Any) -> None:
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(server)
    expect(page.locator("#mode-badge")).to_contain_text("Offline")

    # 1 · chat → agent gọi API → file Excel → bấm xem dữ liệu
    page.fill("#input", "Tạo file Excel danh sách khách hàng ở Hà Nội")
    page.press("#input", "Enter")
    card = page.locator(".file-card").first
    expect(card).to_contain_text("9 dòng", timeout=20_000)
    expect(page.locator(".tool-chip.done", has_text="Gọi API xuất Excel")).to_be_visible()
    card.locator("button", has_text="Xem dữ liệu").click()
    expect(page.locator("#grid tbody tr")).to_have_count(9)
    expect(page.locator("#wb-meta")).to_contain_text("phiên bản 1")
    shot(page, "web-1-file")

    # 2 · agent: tìm trong hệ thống (server) → thêm dòng (tool Excel, run tạm dừng) → xem trước → xác nhận
    page.fill("#input", "Thêm khách hàng KH-0012 vào bảng")
    page.press("#input", "Enter")
    confirm = page.locator(PENDING)
    expect(confirm).to_contain_text("KH-0012", timeout=20_000)
    expect(confirm).to_contain_text("từ dòng 11")
    expect(page.locator(".tool-chip.client", has_text="Thêm dòng vào sheet")).to_be_visible()
    shot(page, "web-2-confirm-append")
    confirm.locator("[data-ok]").click()
    expect(page.locator("#send")).to_be_enabled(timeout=20_000)
    expect(last_answer(page)).to_contain_text("Đã thêm 1 dòng vào sheet Khách hàng (dòng 11)")
    expect(page.locator("#grid tbody tr")).to_have_count(10)
    assert cell(page, 11, "Mã KH") == "KH-0012" and cell(page, 11, "Điện thoại").startswith("0")
    expect(page.locator("#wb-meta")).to_contain_text("phiên bản 2")

    # 3 · thêm lại cùng mã → bị chặn trước khi tới bước xác nhận; mã khác → người dùng bấm Hủy
    ask(page, "Thêm khách hàng KH-0012 vào bảng")
    expect(last_answer(page)).to_contain_text("đã có ở dòng 11")
    page.fill("#input", "Thêm khách hàng KH-0020 vào bảng")
    page.press("#input", "Enter")
    page.locator(PENDING).locator("[data-no]").click()
    expect(page.locator("#send")).to_be_enabled(timeout=20_000)
    expect(last_answer(page)).to_contain_text("Bạn đã hủy")
    expect(page.locator("#grid tbody tr")).to_have_count(10)

    # 4 · tìm trong sheet đang mở → chọn dòng tìm được
    ask(page, "Tìm dòng có Thành phố là Nha Trang trong bảng")
    expect(last_answer(page)).to_contain_text("dòng 11")
    expect(page.locator('#grid tbody tr[data-row="9"]')).to_have_class("row-sel")

    # 5 · chọn 2 dòng → agent ghi một giá trị vào cột (xem trước giá trị cũ → mới)
    page.click("#btn-clear-selection")
    page.click('#grid td.rownum[data-row="0"]')
    page.click('#grid td.rownum[data-row="1"]', modifiers=["Shift"])
    page.fill("#input", 'Ghi "VIP" vào cột Phân khúc cho các dòng đang chọn')
    page.press("#input", "Enter")
    confirm = page.locator(PENDING)
    expect(confirm.locator("td.new").first).to_have_text("VIP", timeout=20_000)
    confirm.locator("[data-ok]").click()
    expect(page.locator("#send")).to_be_enabled(timeout=20_000)
    assert cell(page, 2, "Phân khúc") == "VIP" and cell(page, 3, "Phân khúc") == "VIP"
    expect(page.locator("#wb-meta")).to_contain_text("phiên bản 3")
    shot(page, "web-3-set-values")

    # 6 · /search theo cột đang chọn (không gọi model) → chọn 1 kết quả → ghi vào cột cho 3 dòng
    page.click("#btn-clear-selection")
    page.click('#grid th[data-col="Thành phố"]')
    page.click('#grid td.rownum[data-row="0"]')
    page.click('#grid td.rownum[data-row="2"]', modifiers=["Shift"])
    ask(page, "/search Đà Nẵng")
    results = page.locator(".results-card").last
    expect(results).to_contain_text("cột Thành phố")
    results.locator('tbody input[type="checkbox"]').first.check()
    results.locator('[data-act="set"]').click()
    expect(results.locator("select[data-target]")).to_have_value("Thành phố")
    results.locator("[data-confirm]").click()
    expect(results.locator(".apply-result")).to_contain_text("Ghi 'Đà Nẵng'")
    assert [cell(page, r, "Thành phố") for r in (2, 3, 4)] == ["Đà Nẵng"] * 3
    expect(page.locator("#wb-meta")).to_contain_text("phiên bản 4")
    shot(page, "web-4-search-apply")

    # 7 · hoàn tác → phiên bản 3; tải file về được
    page.click("#btn-undo")
    expect(page.locator("#wb-meta")).to_contain_text("phiên bản 3")
    href = page.locator("#btn-download").get_attribute("href")
    resp = httpx.get(server + href)
    assert resp.status_code == 200 and resp.content[:2] == b"PK"
    page.close()
