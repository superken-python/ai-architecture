"""Sinh trang web tĩnh (GitHub Pages) từ catalog/*.yaml.

Cách dùng:
    python -m aiarch.site build                 # sinh vào _site/
    python -m aiarch.site build --out public    # thư mục khác
    python -m aiarch.site serve                 # sinh rồi mở http://localhost:8000

Trang là một ứng dụng một trang (HTML/CSS/JS thuần, không cần build tool) trong web/;
dữ liệu catalog đã phân tích được nhúng thẳng vào index.html nên mở file trực tiếp cũng chạy.
Tài liệu Markdown được render sẵn vào _site/md/ (xem aiarch.docview) để đọc ngay trên trang — phần này cần phục vụ
qua HTTP (`serve`, GitHub Pages).
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from aiarch import __version__, docview
from aiarch import catalog as c

WEB_DIR = c.REPO_ROOT / "web"
DATA_MARKER = "<!--CATALOG_DATA-->"
DEFAULT_REPO = "superken-python/ai-architecture"


def learning_links(cat: c.Catalog) -> dict[str, Any]:
    """Liên kết chéo tính sẵn từ docs.yaml: mỗi bước, giai đoạn, kỹ năng, nhóm, tổ hợp, mảng, trang → tài liệu nào."""
    by: dict[str, dict[str, list[Any]]] = {
        k: {} for k in ("step", "stage", "group", "combo", "domain", "page", "skill")
    }
    stage_of = {step["id"]: st["id"] for st in cat.roadmap.get("stages", []) for step in st.get("steps", [])}
    docs: dict[str, Any] = {}
    for d in c.doc_items(cat):
        skills = c.doc_skills(d, cat)
        docs[d["key"]] = {
            "stage": d.get("stage") or stage_of.get(d.get("step")),
            "step": d.get("step"),
            "skills": skills,
            "groups": d.get("groups", []),
            "combos": d.get("combos", []),
            "domains": d.get("domains", []),
            "pages": d.get("pages", []),
        }
        for field_name, key in (("step", "step"), ("stage", "stage")):
            if d.get(field_name):
                by[key].setdefault(d[field_name], []).append(d["key"])
        for field_name, key in (("groups", "group"), ("combos", "combo"), ("domains", "domain"), ("pages", "page")):
            for value in d.get(field_name, []):
                by[key].setdefault(value, []).append(d["key"])
        for item in skills:
            by["skill"].setdefault(item["id"], []).append(
                {"key": d["key"], "level": item["level"], "step": d.get("step")}
            )
    return {"docs": docs, **{f"by_{k}": v for k, v in by.items()}}


VTT_TIME = re.compile(r"((?:\d+:)?\d\d:\d\d\.\d+)\s*-->\s*((?:\d+:)?\d\d:\d\d\.\d+)")


def vtt_seconds(stamp: str) -> float:
    total = 0.0
    for part in stamp.split(":"):
        total = total * 60 + float(part)
    return total


def parse_vtt(text: str) -> list[dict[str, Any]]:
    """Các cue của một file WebVTT: [{"t": giây bắt đầu, "end": giây kết thúc, "title": nội dung}]."""
    cues = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        lines = [line.strip() for line in block.strip().split("\n") if line.strip()]
        for i, line in enumerate(lines):
            m = VTT_TIME.search(line)
            if m:
                title = " ".join(lines[i + 1 :])
                cues.append({"t": vtt_seconds(m.group(1)), "end": vtt_seconds(m.group(2)), "title": title})
                break
    return cues


def demo_paths(group: dict[str, Any]) -> list[str]:
    demo = group.get("demo") or {}
    return [demo[k] for k in c.DEMO_FILES if demo.get(k)]


def demos(cat: c.Catalog, root: Path = c.REPO_ROOT) -> dict[str, Any]:
    """Video mẫu của từng nhóm cho trang web: đường dẫn bản sao trong _site/md/ + danh sách chương để nhảy tới."""
    out: dict[str, Any] = {}
    for g in cat.groups:
        demo = g.get("demo")
        if not demo:
            continue
        item: dict[str, Any] = {"title": demo["title"], "docs": demo.get("docs", [])}
        for key in ("video", "poster", "subtitles"):
            if demo.get(key):
                item[key] = docview.asset_url(demo[key])
        chapters = demo.get("chapters")  # file chương → danh sách nút bấm, không cần tải lúc xem
        item["chapters"] = parse_vtt((root / chapters).read_text(encoding="utf-8")) if chapters else []
        out[g["id"]] = item
    return out


def site_data(
    cat: c.Catalog, repo: str, pages: dict[str, Any] | None = None, root: Path = c.REPO_ROOT
) -> dict[str, Any]:
    """Toàn bộ dữ liệu trang web cần — đã tính sẵn tầng, đòn bẩy, thứ tự học, vị trí trong lộ trình, liên kết chéo."""
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
            "docs": {
                d["key"]: {
                    "title": d["title"],
                    "url": f"{base}/blob/main/{d['path']}",
                    "path": d["path"],
                    "desc": d["desc"],
                    "tag": d.get("tag", ""),
                    "kind": d.get("kind", "doc"),
                    "section": d["section"],
                }
                for d in c.doc_items(cat)
            },
            "doc_sections": [
                {"id": sec["id"], "title": sec["title"], "desc": sec["desc"], "items": [d["key"] for d in sec["docs"]]}
                for sec in cat.docs.get("sections", [])
            ],
            "pages": pages or {},
        },
        "learn": learning_links(cat),
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
        "demos": demos(cat, root),
    }


def build(out: Path, repo: str = DEFAULT_REPO, root: Path = c.REPO_ROOT) -> Path:
    cat = c.load(root)
    errors = c.validate(cat)
    if errors:
        raise SystemExit("Catalog có lỗi — chạy `make catalog` để xem chi tiết:\n  " + "\n  ".join(errors))

    bundle = docview.build_bundle(cat, repo, root)
    # Video mẫu của nhóm được chép như ảnh của tài liệu (chỉ file Git đang theo dõi).
    bundle.assets.update(p for g in cat.groups for p in demo_paths(g) if p in bundle.files)
    data = site_data(cat, repo, bundle.manifest(), root)
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
    bundle.write(out)
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
