"""Sinh trang web tĩnh (GitHub Pages) từ catalog/*.yaml.

Cách dùng:
    python -m aiarch.site build                 # sinh vào _site/
    python -m aiarch.site build --out public    # thư mục khác
    python -m aiarch.site serve                 # sinh rồi mở http://localhost:8000

Trang là một ứng dụng một trang (HTML/CSS/JS thuần, không cần build tool) trong web/;
dữ liệu catalog đã phân tích được nhúng thẳng vào index.html nên mở file trực tiếp cũng chạy.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from aiarch import __version__
from aiarch import catalog as c

WEB_DIR = c.REPO_ROOT / "web"
DATA_MARKER = "<!--CATALOG_DATA-->"
DEFAULT_REPO = "superken-python/ai-architecture"

# Tài liệu viết tay được liên kết từ trang web (đường dẫn trong repo).
DOCS = {
    "setup": ("Setup môi trường", "docs/00-setup/README.md"),
    "problem_map": ("Bản đồ bài toán (giai đoạn 1)", "docs/01-problem-map/README.md"),
    "skill_map": ("Bản đồ kỹ năng (giai đoạn 2)", "docs/02-skill-map/README.md"),
    "architecture": ("Kiến trúc kỹ năng", "docs/02-skill-map/01-kien-truc-ky-nang.md"),
    "combining": ("Kỹ năng kết hợp", "docs/02-skill-map/02-ky-nang-ket-hop.md"),
    "tokens": ("Tiết kiệm token, chính xác tuyệt đối", "docs/02-skill-map/03-tiet-kiem-token-chinh-xac.md"),
    "roadmap": ("Lộ trình học (Markdown)", "docs/02-skill-map/04-lo-trinh-hoc.md"),
    "checklist": ("Checklist việc sắp làm", "CHECKLIST.md"),
    "history": ("Lịch sử công việc", "HISTORY.md"),
}


def site_data(cat: c.Catalog, repo: str) -> dict[str, Any]:
    """Toàn bộ dữ liệu trang web cần — đã tính sẵn tầng, đòn bẩy, thứ tự học, vị trí trong lộ trình."""
    order = c.topo_order(cat)
    depth = c.depths(cat)
    unlocks = c.unlocks(cat)
    placements = c.roadmap_placements(cat)
    strong = {g: {s["id"] for s in cat.skills if g in c.strong_groups(s)} for g in cat.group_ids}

    skills = []
    for s in cat.skills:
        skills.append(
            {
                **s,
                "tier": c.tier(s, cat),
                "leverage": c.leverage(s),
                "depth": depth[s["id"]],
                "order": order.index(s["id"]),
                "unlocks": unlocks[s["id"]],
                "placements": placements[s["id"]],
            }
        )

    base = f"https://github.com/{repo}"
    return {
        "meta": {
            "version": __version__,
            "repo": repo,
            "repo_url": base,
            "commit": os.environ.get("GITHUB_SHA", "")[:7],
            "docs": {k: {"title": t, "url": f"{base}/blob/main/{p}"} for k, (t, p) in DOCS.items()},
        },
        "levels": c.LEVELS,
        "relevance": c.RELEVANCE,
        "tiers": {k: {"name": n, "desc": d} for k, (n, d) in c.TIERS.items()},
        "blocks": cat.blocks,
        "families": cat.families,
        "identify": cat.identify,
        "groups": cat.groups,
        "domains": cat.domains,
        "skills": skills,
        "combinations": cat.combinations,
        "roadmap": cat.roadmap,
        "sharing": {a: {b: len(strong[a] & strong[b]) for b in cat.group_ids} for a in cat.group_ids},
    }


def build(out: Path, repo: str = DEFAULT_REPO, root: Path = c.REPO_ROOT) -> Path:
    cat = c.load(root)
    errors = c.validate(cat)
    if errors:
        raise SystemExit("Catalog có lỗi — chạy `make catalog` để xem chi tiết:\n  " + "\n  ".join(errors))

    data = site_data(cat, repo)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # Không để chuỗi "</" kết thúc thẻ <script> sớm.
    inline = payload.replace("</", "<\\/")

    web = root / "web"
    template = (web / "index.html").read_text(encoding="utf-8")
    if DATA_MARKER not in template:
        raise SystemExit(f"web/index.html thiếu {DATA_MARKER}")

    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(web / "assets", out / "assets")
    (out / "data").mkdir(parents=True)
    (out / "data" / "catalog.json").write_text(payload, encoding="utf-8")
    html = template.replace(DATA_MARKER, f'<script id="catalog-data" type="application/json">{inline}</script>')
    (out / "index.html").write_text(html, encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aiarch.site", description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["build", "serve"])
    parser.add_argument("--out", type=Path, default=c.REPO_ROOT / "_site")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPO))
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    out = build(args.out, args.repo)
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"✓ Đã sinh trang web vào {out} ({size / 1024:.0f} KB).")
    if args.command == "serve":
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(out))
        with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as httpd:
            print(f"→ Mở http://localhost:{args.port}  (Ctrl+C để dừng)")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
