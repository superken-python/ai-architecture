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

# Tài liệu viết tay, nhóm theo chủ đề — hiển thị ở trang "Tài liệu" (#/tai-lieu).
# Mỗi nhóm: (id, tiêu đề, mô tả, [(khóa, tiêu đề, đường dẫn trong repo, mô tả, nhãn)]). Nhãn rỗng = không có.
DOC_SECTIONS = [
    (
        "nen-tang",
        "Nền tảng lộ trình",
        "Bài toán AI trong doanh nghiệp, kỹ năng cần có và cách học.",
        [
            (
                "setup",
                "Setup môi trường",
                "docs/00-setup/README.md",
                "Chuẩn bị máy và công cụ một lần trước khi học.",
                "",
            ),
            (
                "problem_map",
                "Bản đồ bài toán (giai đoạn 1)",
                "docs/01-problem-map/README.md",
                "8 nhóm bài toán AI trong doanh nghiệp, cách nhận diện.",
                "",
            ),
            (
                "skill_map",
                "Bản đồ kỹ năng (giai đoạn 2)",
                "docs/02-skill-map/README.md",
                "65 kỹ năng theo mảng, mức cần cho từng nhóm bài toán.",
                "",
            ),
            (
                "architecture",
                "Kiến trúc kỹ năng",
                "docs/02-skill-map/01-kien-truc-ky-nang.md",
                "Tầng nền tảng, cầu nối, chuyên sâu và quan hệ tiên quyết.",
                "",
            ),
            (
                "combining",
                "Kỹ năng kết hợp",
                "docs/02-skill-map/02-ky-nang-ket-hop.md",
                "Tổ hợp kỹ năng cho bài toán thật nhiều nhóm.",
                "",
            ),
            (
                "tokens",
                "Tiết kiệm token, chính xác tuyệt đối",
                "docs/02-skill-map/03-tiet-kiem-token-chinh-xac.md",
                "Giảm chi phí LLM mà không đánh đổi độ chính xác.",
                "",
            ),
            (
                "roadmap",
                "Lộ trình học (Markdown)",
                "docs/02-skill-map/04-lo-trinh-hoc.md",
                "Bản Markdown của lộ trình 4 giai đoạn.",
                "",
            ),
        ],
    ),
    (
        "giai-doan-a",
        "Giai đoạn A · Nền tảng",
        "8 bài lý thuyết + lab cùng xây một dự án churn từ dữ liệu thô tới API. Học theo thứ tự A1 → A8.",
        [
            (
                "stage_a",
                "Tổng quan giai đoạn A",
                "docs/03-giai-doan-a-nen-tang/README.md",
                "Real case nhà mạng Sóng Xanh, lộ trình 8 bài, cách học, bảng tự đánh giá.",
                "Bắt đầu ở đây",
            ),
            (
                "stage_a1",
                "A1 · Python, Git và framing",
                "docs/03-giai-doan-a-nen-tang/a1-python-git-framing.md",
                "Từ 'giảm churn' tới precision@500, giá trị kỳ vọng một cuộc gọi; dự án uv, config, Makefile.",
                "",
            ),
            (
                "stage_a2",
                "A2 · SQL, pandas và thống kê mô tả",
                "docs/03-giai-doan-a-nen-tang/a2-sql-pandas-thong-ke.md",
                "DuckDB, ASOF JOIN, làm sạch có quy tắc, tiếng Việt NFC/NFD, phân phối lệch, 5 nhận xét.",
                "",
            ),
            (
                "stage_a3",
                "A3 · Baseline và bộ đánh giá cố định",
                "docs/03-giai-doan-a-nen-tang/a3-baseline-bo-danh-gia.md",
                "Chia theo thời gian, đóng băng tập test bằng mã băm, precision@k, bootstrap theo khách.",
                "",
            ),
            (
                "stage_a4",
                "A4 · Dữ liệu đúng thời điểm và feature",
                "docs/03-giai-doan-a-nen-tang/a4-feature-as-of-ro-ri.md",
                "Bảng học as-of bằng một câu SQL, bốn loại rò rỉ, test đúng thời điểm, pandera.",
                "",
            ),
            (
                "stage_a5",
                "A5 · LightGBM, mất cân bằng, ngưỡng theo chi phí",
                "docs/03-giai-doan-a-nen-tang/a5-lightgbm-nguong-chi-phi.md",
                "Early stopping, class weight phá xác suất, hiệu chỉnh, giá trị kỳ vọng, đường lợi nhuận.",
                "",
            ),
            (
                "stage_a6",
                "A6 · Phân tích lỗi, SHAP và kiểm thử",
                "docs/03-giai-doan-a-nen-tang/a6-phan-tich-loi-shap-test.md",
                "Đọc 100 ca sai, sửa bằng dữ liệu mới, 3 lý do tiếng Việt cho từng khách, test cả pipeline.",
                "",
            ),
            (
                "stage_a7",
                "A7 · API, Docker, MLflow và bảo mật",
                "docs/03-giai-doan-a-nen-tang/a7-api-docker-mlflow-bao-mat.md",
                "FastAPI có khoá và version, container chỉ đọc, lịch sử thí nghiệm, rà secret và PII.",
                "",
            ),
            (
                "stage_a8",
                "A8 · Trình bày kết quả — mốc giai đoạn A",
                "docs/03-giai-doan-a-nen-tang/a8-trinh-bay-ket-qua.md",
                "Báo cáo 1 trang, độ nhạy (tornado), demo 3 phút, CI và tái lập từ đầu.",
                "",
            ),
            (
                "g1_churn",
                "Dự án G1 · Churn nhà mạng Sóng Xanh",
                "projects/g1-churn-telco/README.md",
                "Code hoàn chỉnh của 8 bài: dữ liệu thô → bảng học → LightGBM → API Docker → báo cáo.",
                "Có code chạy được",
            ),
            (
                "g1_report",
                "Báo cáo 1 trang của dự án churn",
                "projects/g1-churn-telco/reports/README.md",
                "So với cách làm hiện tại: +103 người gọi trúng, +44,5 triệu đ/tháng, kèm KTC và độ nhạy.",
                "Kết quả",
            ),
        ],
    ),
    (
        "agent",
        "AI Agent (Nhóm 7)",
        "Chọn framework, hiểu harness bên trong, rồi tự code. Thứ tự gợi ý: radar → cơ chế → harness → tự học.",
        [
            (
                "agent_landscape",
                "Radar framework agent",
                "docs/agent-radar/README.md",
                "Kết luận chọn framework, tiêu chí, xu hướng 2026, kiến trúc tham chiếu.",
                "Tài liệu sống",
            ),
            (
                "agent_table",
                "Bảng so sánh framework",
                "docs/agent-radar/generated/bang-so-sanh.md",
                "19 framework × 8 tiêu chí, số liệu registry cập nhật hằng tháng.",
                "Tự sinh",
            ),
            (
                "agent_mechanics",
                "Cơ chế agent của 4 framework",
                "docs/agent-radar/01-co-che-agent.md",
                "Vòng lặp tool, điểm can thiệp, tạm dừng/chạy tiếp, nhiều agent, bộ nhớ.",
                "",
            ),
            (
                "agent_harness",
                "Harness: Agno → LangChain → Claude Code",
                "docs/agent-radar/02-harness-agno-sang-langchain.md",
                "Một run của Agno chạy ra sao (đã đo), dựng lại bằng LangChain có code đầy đủ, cải tiến harness.",
                "Có code chạy được",
            ),
            (
                "lab_llm05",
                "Lab LLM-05 · harness bằng LangChain",
                "labs/llm-05-trung-cap-harness-langchain/README.md",
                "Code của tài liệu harness + phần còn lại của Lab 01 (workflow, MCP, team...), 72 test, bộ đo vàng.",
                "Lab",
            ),
            (
                "lab_agno",
                "Lab LLM-05 · Agno + AgentOS từng phần",
                "labs/llm-05-trung-cap-agno-agentos/README.md",
                "Project tham chiếu của Lab 01: 16 module, model giả lập không cần API key, 117 test.",
                "Lab",
            ),
            (
                "self_lab00",
                "Tự học · Lab 00 nền tảng Report Agent",
                "docs/self-practices/agent_framework_learning_from_scratch.md",
                "Dữ liệu, service, hợp đồng báo cáo, MCP — chung cho ba bài framework.",
                "Tự học",
            ),
            (
                "self_lab01",
                "Tự học · Lab 01 Agno và AgentOS",
                "docs/self-practices/guide_01_agno.md",
                "Baseline + 16 phần có code đầy đủ: agent, tool, memory, HITL, workflow, MCP, AG-UI, A2A, eval.",
                "Tự học",
            ),
            (
                "self_lab02",
                "Tự học · Lab 02 Pydantic AI + Temporal",
                "docs/self-practices/guide_02_pydantic_ai_temporal.md",
                "Pydantic AI chạy độc lập, rồi chạy bền với Temporal.",
                "Tự học",
            ),
            (
                "self_lab03",
                "Tự học · Lab 03 LangGraph",
                "docs/self-practices/guide_03_langgraph.md",
                "Workflow agent: đồ thị trạng thái, checkpoint, người duyệt.",
                "Tự học",
            ),
        ],
    ),
    (
        "thuc-hanh",
        "Lab và dự án",
        "Nơi luyện tay theo kỹ năng (lab) và áp dụng vào bài toán thật (dự án).",
        [
            ("labs", "Danh sách lab", "labs/README.md", "Quy ước và danh sách lab theo kỹ năng.", ""),
            ("projects", "Danh sách dự án", "projects/README.md", "Dự án luyện tập theo nhóm bài toán và tổ hợp.", ""),
            (
                "cmb10",
                "CMB-10 · Excel Agent Add-in",
                "projects/cmb-10-excel-agent-addin/README.md",
                "Trợ lý AI trong Excel nối với agent của hệ thống (Agno + AG-UI + Office.js).",
                "Có POC",
            ),
        ],
    ),
    (
        "theo-doi",
        "Theo dõi công việc",
        "Việc sắp làm và việc đã làm của repo.",
        [
            ("checklist", "Checklist việc sắp làm", "CHECKLIST.md", "Việc theo giai đoạn và mức ưu tiên.", ""),
            ("history", "Lịch sử công việc", "HISTORY.md", "Đã làm gì, quyết định gì, mới nhất ở trên.", ""),
        ],
    ),
]
DOCS = {key: (title, path) for *_, items in DOC_SECTIONS for key, title, path, _, _ in items}


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
            "docs": {
                key: {"title": title, "url": f"{base}/blob/main/{path}", "path": path, "desc": desc, "tag": tag}
                for *_, items in DOC_SECTIONS
                for key, title, path, desc, tag in items
            },
            "doc_sections": [
                {"id": sid, "title": title, "desc": desc, "items": [item[0] for item in items]}
                for sid, title, desc, items in DOC_SECTIONS
            ],
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
