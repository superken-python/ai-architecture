#!/usr/bin/env python3
"""Kiểm thử khói trang web bằng trình duyệt thật (Playwright + Chromium).

    make site-test
    # tương đương: uv run --with playwright python scripts/smoke_site.py [--shots thư-mục-ảnh]

Sinh trang vào thư mục tạm, phục vụ qua HTTP, rồi mở mọi trang ở cỡ desktop (sáng) và điện thoại (tối):
không lỗi JavaScript, không tràn ngang, có tiêu đề; thử đánh dấu tiến độ, quiz nhận diện, bộ lọc, đổi giao diện.
Lần đầu cần tải Chromium: `uv run --with playwright playwright install chromium`
(hoặc đặt PLAYWRIGHT_CHROMIUM=/đường/dẫn/chrome nếu máy đã có sẵn).
"""

from __future__ import annotations

import argparse
import functools
import http.server
import os
import sys
import tempfile
import threading
from pathlib import Path

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
        "tien-do",
        "khong-ton-tai",
    ]


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
                page.click('[data-action="theme"]')
                after = page.evaluate("document.documentElement.getAttribute('data-theme')")
                if before == after:
                    problems.append(f"[{name}] nút đổi giao diện không hoạt động")
                ctx.close()
            browser.close()
        httpd.shutdown()

    if problems:
        print(f"✗ {len(problems)} vấn đề:")
        for prob in problems:
            print(f"  - {prob}")
        return 1
    print(f"✓ Trang web chạy tốt trên {len(VIEWPORTS)} cỡ màn hình × {len(routes())} trang.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
