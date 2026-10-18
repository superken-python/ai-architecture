#!/usr/bin/env python3
"""Kiểm thử khói trang web bằng trình duyệt thật (Playwright + Chromium).

    make site-test
    # tương đương: uv run --with playwright python scripts/smoke_site.py [--shots thư-mục-ảnh]

Sinh trang vào thư mục tạm, phục vụ qua HTTP, rồi mở mọi trang ở cỡ desktop (sáng) và điện thoại (tối):
không lỗi JavaScript, không tràn ngang, có tiêu đề; thử đánh dấu tiến độ, quiz nhận diện, bộ lọc, đổi giao diện.
Khung xem tài liệu: mở từ bước lộ trình và trang Tài liệu, đóng/Esc quay về đúng trang, liên kết trong tài liệu mở
tài liệu khác hoặc trang kỹ năng; rồi mở MỌI tài liệu đã render: sơ đồ mermaid vẽ được, công thức KaTeX vẽ được,
code có tô màu, không tràn ngang trên điện thoại.
Lần đầu cần tải Chromium: `uv run --with playwright playwright install chromium`
(hoặc đặt PLAYWRIGHT_CHROMIUM=/đường/dẫn/chrome nếu máy đã có sẵn).
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aiarch import catalog as c  # noqa: E402
from aiarch import site  # noqa: E402

VIEWPORTS = [("desktop", {"width": 1280, "height": 900}, "light"), ("mobile", {"width": 390, "height": 844}, "dark")]


def routes() -> list[str]:
    cat = c.load()
    first_step = cat.roadmap["stages"][0]["steps"][0]["id"]
    return [
        "",
        "lo-trinh",
        f"lo-trinh/{first_step}",
        *[f"lo-trinh/{st['id']}" for st in cat.roadmap["stages"]],
        "nhom",
        *[f"nhom/{g['id']}" for g in cat.groups],
        "ky-nang",
        f"ky-nang/{cat.skills[0]['id']}",
        "ma-tran",
        "to-hop",
        f"to-hop/{cat.combinations[0]['id']}",
        "tai-lieu",
        "tai-lieu/agent",
        "tien-do",
        "khong-ton-tai",
    ]


def doc_hash(path: str, anchor: str = "") -> str:
    return f"#/doc/{quote(path)}" + (f"#{quote(anchor, safe='')}" if anchor else "")


def open_doc(page, path: str) -> None:
    """Mở tài liệu bằng cách đổi hash (như bấm link) rồi chờ khung xem vẽ xong sơ đồ và công thức."""
    page.evaluate("h => { location.hash = h; }", doc_hash(path))
    page.wait_for_function(
        "p => { const b = document.getElementById('viewer-body'); return b && b.dataset.ready === '1' && "
        "location.hash.includes(encodeURI(p).split('/').pop()); }",
        arg=path,
        timeout=20000,
    )


def check_viewer(page, base: str, name: str, problems: list[str]) -> None:
    """Luồng dùng thật của khung xem tài liệu: mở, chuyển tài liệu, sang trang kỹ năng, đóng, Esc."""
    cat = c.load()
    first = cat.roadmap["stages"][0]["steps"][0]["id"]
    visible = "document.getElementById('viewer').hidden === false"

    # Từ bước đầu tiên của lộ trình: "Học ngay" → bài học mở trong khung xem, không rời trang web
    page.goto(f"{base}/#/lo-trinh/{first}")
    page.wait_for_selector("#app h1")
    page.click(".learn-bar a.res-lesson")
    page.wait_for_selector("#viewer-body[data-ready='1']", timeout=20000)
    if not page.evaluate(visible):
        problems.append(f"[{name}] bấm 'Học ngay' ở bước {first} không mở khung xem")
    if page.locator("#viewer-body .highlight span").count() == 0:
        problems.append(f"[{name}] bài học {first}: code không được tô màu")
    lesson_title = page.inner_text("#viewer-title")

    # "Tiếp theo" → tài liệu kế tiếp, vẫn trong khung xem
    page.click("#viewer-after .pager-next")
    page.wait_for_function("t => document.getElementById('viewer-title').textContent !== t", arg=lesson_title)
    page.wait_for_selector("#viewer-body[data-ready='1']", timeout=20000)

    # Đóng → quay về đúng bước lộ trình, khung xem ẩn
    page.click("#viewer .viewer-close")
    page.wait_for_function(f"!({visible})")
    if page.evaluate("location.hash") != f"#/lo-trinh/{first}":
        problems.append(f"[{name}] đóng khung xem không quay về #/lo-trinh/{first}: {page.evaluate('location.hash')}")

    # Trang Tài liệu: bấm thẻ → mở; Esc → về trang Tài liệu
    page.goto(f"{base}/#/tai-lieu")
    page.wait_for_selector(".doc-card .stretched")
    page.click(".doc-card .stretched")
    page.wait_for_selector("#viewer-body[data-ready='1']", timeout=20000)
    page.keyboard.press("Escape")
    page.wait_for_function(f"!({visible})")
    if page.evaluate("location.hash") != "#/tai-lieu":
        problems.append(f"[{name}] Esc không quay về trang Tài liệu: {page.evaluate('location.hash')}")

    # Link thẻ kỹ năng trong bài học → trang kỹ năng tương tác (không mở bản .md sinh tự động)
    lesson = next(d["path"] for d in c.doc_items(cat) if d.get("kind") == "lesson")
    page.goto(f"{base}/{doc_hash(lesson)}")
    page.wait_for_selector("#viewer-body[data-ready='1']", timeout=20000)
    page.click("#viewer-body a[href^='#/ky-nang/']")
    page.wait_for_function(f"!({visible}) && location.hash.startsWith('#/ky-nang/')")
    page.wait_for_selector("#app .learn-card")

    # Đổi giao diện khi đang xem tài liệu có sơ đồ: vẽ lại, không lỗi
    page.goto(f"{base}/{doc_hash('docs/03-giai-doan-a-nen-tang/README.md')}")
    page.wait_for_selector("#viewer-body .mermaid-diagram svg", timeout=20000)
    page.click("#viewer [data-action='theme']")
    page.wait_for_timeout(500)


def check_all_docs(page, base: str, name: str, manifest: dict, problems: list[str]) -> None:
    """Mở mọi tài liệu đã render: không lỗi tải, sơ đồ + công thức vẽ được, không tràn ngang."""
    page.goto(f"{base}/#/tai-lieu")
    page.wait_for_selector("#app h1")
    for path in manifest:
        try:
            open_doc(page, path)
        except Exception as exc:  # noqa: BLE001 — gom lỗi để báo một lần
            problems.append(f"[{name}] {path}: không mở được ({type(exc).__name__})")
            continue
        state = page.evaluate(
            """() => {
              const b = document.getElementById('viewer-body');
              return {
                failedDiagrams: b.querySelectorAll('.mermaid-failed').length,
                pendingDiagrams: b.querySelectorAll('pre.mermaid:not(.mermaid-failed)').length,
                pendingMath: b.querySelectorAll('.math:not([data-done])').length,
                overflow: b.scrollWidth - b.clientWidth,
                empty: b.textContent.trim().length === 0,
              };
            }"""
        )
        if state["failedDiagrams"] or state["pendingDiagrams"]:
            problems.append(
                f"[{name}] {path}: {state['failedDiagrams'] + state['pendingDiagrams']} sơ đồ mermaid không vẽ được"
            )
        if state["pendingMath"]:
            problems.append(f"[{name}] {path}: {state['pendingMath']} công thức không vẽ được")
        if state["overflow"] > 1:
            problems.append(f"[{name}] {path}: tràn ngang {state['overflow']}px")
        if state["empty"]:
            problems.append(f"[{name}] {path}: trang trống")


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass


def serve(directory: Path) -> tuple[http.server.ThreadingHTTPServer, str]:
    handler = functools.partial(QuietHandler, directory=str(directory))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--shots", type=Path, help="lưu ảnh chụp màn hình vào thư mục này")
    args = parser.parse_args()

    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        out = site.build(Path(tmp) / "_site")
        manifest = json.loads((out / "data" / "catalog.json").read_text(encoding="utf-8"))["meta"]["pages"]
        httpd, base = serve(out)
        if args.shots:
            args.shots.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as p:
            exe = os.environ.get("PLAYWRIGHT_CHROMIUM")
            browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
            for name, viewport, scheme in VIEWPORTS:
                ctx = browser.new_context(viewport=viewport, color_scheme=scheme)
                page = ctx.new_page()
                page.on("pageerror", lambda e, n=name: problems.append(f"[{n}] lỗi JavaScript: {e}"))
                page.on(
                    "console",
                    lambda m, n=name: (
                        m.type == "error"
                        and "Failed to load resource" not in m.text  # font ngoài bị chặn không phải lỗi của trang
                        and problems.append(f"[{n}] console: {m.text}")
                    ),
                )
                for r in routes():
                    page.goto(f"{base}/#/{r}")
                    page.wait_for_selector("#app h1", timeout=5000)
                    overflow = page.evaluate(
                        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
                    )
                    if overflow > 1:
                        problems.append(f"[{name}] #/{r}: tràn ngang {overflow}px")
                    if args.shots:
                        page.screenshot(path=str(args.shots / f"{name}-{r.replace('/', '_') or 'home'}.png"))

                # Đánh dấu một mức kỹ năng ở bước đầu tiên → lưu vào localStorage
                page.goto(f"{base}/#/lo-trinh/{c.load().roadmap['stages'][0]['steps'][0]['id']}")
                btn = page.locator('[data-action="lvl"]').first
                sid = btn.get_attribute("data-id")
                btn.click()
                stored = page.evaluate("localStorage.getItem('aiarch-progress-v1') || ''")
                if f'"{sid}"' not in stored:
                    problems.append(f"[{name}] đánh dấu {sid} không được lưu: {stored!r}")

                # Quiz: trả lời "Không" đến hết → rơi về nhóm mặc định
                page.goto(f"{base}/#/nhom")
                n_questions = len(c.load().identify["questions"])
                for _ in range(n_questions):
                    page.click('[data-action="quiz"][data-answer="no"]')
                fallback = c.load().identify["fallback"]
                if f"Nhóm {fallback[1:]}" not in page.inner_text("#quiz-box"):
                    problems.append(f"[{name}] quiz không ra nhóm mặc định {fallback}")

                # Bộ lọc kỹ năng: tìm không dấu
                page.goto(f"{base}/#/ky-nang")
                page.fill('input[data-filter="q"]', "truy xuat")
                if page.locator(".skill-card").count() == 0:
                    problems.append(f"[{name}] tìm 'truy xuat' không ra kết quả")

                # Đổi giao diện sáng/tối
                before = page.evaluate("document.documentElement.getAttribute('data-theme')")
                page.click('.site-header [data-action="theme"]')
                after = page.evaluate("document.documentElement.getAttribute('data-theme')")
                if before == after:
                    problems.append(f"[{name}] nút đổi giao diện không hoạt động")

                # Khung xem tài liệu
                check_viewer(page, base, name, problems)
                started = time.monotonic()
                check_all_docs(page, base, name, manifest, problems)
                print(f"  [{name}] đã mở {len(manifest)} tài liệu trong {time.monotonic() - started:.0f} giây")
                ctx.close()
            browser.close()
        httpd.shutdown()

    if problems:
        print(f"✗ {len(problems)} vấn đề:")
        for prob in problems:
            print(f"  - {prob}")
        return 1
    print(f"✓ Trang web chạy tốt trên {len(VIEWPORTS)} cỡ màn hình × {len(routes())} trang + khung xem tài liệu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
