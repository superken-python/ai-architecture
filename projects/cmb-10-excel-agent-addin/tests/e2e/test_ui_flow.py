"""Kiểm thử giao diện bằng Chromium thật.

Luồng: chat → file Excel → xem dữ liệu → /search → ghi vào cột → thêm dòng → hoàn tác.

Chạy: `make setup-e2e && make e2e`. Server chạy ở chế độ offline (không cần API key).
Đặt E2E_SCREENSHOTS=<thư mục> để lưu ảnh chụp từng bước.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.e2e
playwright = pytest.importorskip("playwright.sync_api")
PROJECT = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    port = _free_port()
    env = {
        **os.environ,
        "AGENT_MODE": "offline",
        "OPENAI_API_KEY": "",
        "PORT": str(port),
        "STORAGE_DIR": str(tmp_path_factory.mktemp("var")),
    }
    cmd = [sys.executable, "-m", "uvicorn", "excel_agent.main:create_app", "--factory", "--port", str(port)]
    proc = subprocess.Popen(cmd, cwd=PROJECT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            try:
                if httpx.get(f"{base}/health", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.5)
        else:
            raise RuntimeError("server không khởi động được")
        yield base
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def _shot(page, name: str) -> None:
    folder = os.environ.get("E2E_SCREENSHOTS")
    if folder:
        Path(folder).mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(Path(folder) / f"{name}.png"), full_page=True)


def test_export_preview_search_apply_undo(server: str) -> None:
    sync = playwright.sync_playwright
    exe = os.environ.get("CHROMIUM_PATH")
    with sync() as p:
        browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(server)
        expect = playwright.expect
        expect(page.locator("#mode-badge")).to_contain_text("Offline")

        # 1 · chat → agent gọi API → file Excel
        page.fill("#input", "Tạo file Excel danh sách khách hàng ở Hà Nội")
        page.press("#input", "Enter")
        card = page.locator(".file-card").first
        expect(card).to_be_visible(timeout=20_000)
        expect(card).to_contain_text("9 dòng")
        expect(page.locator(".tool-chip", has_text="Đã chuyển cho Excel Report Agent")).to_be_visible()
        _shot(page, "1-file-card")

        # 2 · bấm thẻ file → hiện dữ liệu
        card.click()
        expect(page.locator("#sheet-view")).to_be_visible()
        expect(page.locator("#grid tbody tr")).to_have_count(9)
        expect(page.locator("#wb-meta")).to_contain_text("phiên bản 1")

        # 3 · chọn cột Thành phố và 3 dòng đầu
        page.click('#grid th[data-col="Thành phố"]')
        page.click('#grid td.rownum[data-row="0"]')
        page.click('#grid td.rownum[data-row="2"]', modifiers=["Shift"])
        expect(page.locator("#selection-text")).to_contain_text("3")
        _shot(page, "2-preview-selected")

        # 4 · /search theo cột đang chọn → chọn 1 kết quả → ghi vào cột
        page.fill("#input", "/search Đà Nẵng")
        page.press("#input", "Enter")
        results = page.locator(".results-card").first
        expect(results).to_be_visible(timeout=20_000)
        expect(results).to_contain_text("cột Thành phố")
        results.locator('tbody input[type="checkbox"]').first.check()
        results.locator('[data-act="set"]').click()
        expect(results.locator("select[data-target]")).to_have_value("Thành phố")
        _shot(page, "3-search-apply-form")
        results.locator("[data-confirm]").click()
        expect(results.locator(".apply-result")).to_contain_text("Ghi 'Đà Nẵng'")
        expect(page.locator("#wb-meta")).to_contain_text("phiên bản 2")
        col = page.locator("#grid thead tr.headers th").all_inner_texts().index("Thành phố")
        cities = [
            page.locator(f"#grid tbody tr:nth-child({i}) td:nth-child({col + 1})").inner_text() for i in (1, 2, 3)
        ]
        assert cities == ["Đà Nẵng", "Đà Nẵng", "Đà Nẵng"]
        _shot(page, "4-after-set-column")

        # 5 · thêm 2 kết quả khác thành dòng mới
        boxes = results.locator('tbody input[type="checkbox"]')
        boxes.nth(0).uncheck()
        boxes.nth(1).check()
        boxes.nth(2).check()
        results.locator('[data-act="append"]').click()
        results.locator("[data-confirm]").click()
        expect(results.locator(".apply-result")).to_contain_text("Thêm 2 dòng mới")
        expect(page.locator("#grid tbody tr")).to_have_count(11)
        _shot(page, "5-after-append")

        # 6 · hoàn tác → quay về phiên bản 2 (9 dòng)
        page.click("#btn-undo")
        expect(page.locator("#wb-meta")).to_contain_text("phiên bản 2")
        expect(page.locator("#grid tbody tr")).to_have_count(9)

        # 7 · tải file về được
        href = page.locator("#btn-download").get_attribute("href")
        resp = httpx.get(server + href)
        assert resp.status_code == 200 and resp.content[:2] == b"PK"
        browser.close()
