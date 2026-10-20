import dataclasses
import json
import re

from aiarch import catalog as c
from aiarch import site


def test_build_embeds_catalog_and_copies_assets(tmp_path):
    out = site.build(tmp_path / "_site", repo="owner/repo")
    html = (out / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<script id="catalog-data" type="application/json">(.*?)</script>', html, re.S)
    assert m, "thiếu dữ liệu nhúng"
    embedded = json.loads(m.group(1).replace("<\\/", "</"))
    standalone = json.loads((out / "data" / "catalog.json").read_text(encoding="utf-8"))
    assert embedded == standalone
    assert (out / "assets" / "app.js").exists() and (out / "assets" / "style.css").exists()
    assert (out / ".nojekyll").exists()
    assert site.DATA_MARKER not in html
    assert embedded["meta"]["repo_url"] == "https://github.com/owner/repo"


def test_site_data_matches_catalog(tmp_path):
    cat = c.load()
    data = site.site_data(cat, "owner/repo")
    assert [s["id"] for s in data["skills"]] == [s["id"] for s in cat.skills]
    assert all(s["placements"] for s in data["skills"]), "kỹ năng nào cũng phải có trong lộ trình"
    assert {s["tier"] for s in data["skills"]} <= set(c.TIERS)
    for a in cat.group_ids:
        for b in cat.group_ids:
            assert data["sharing"][a][b] == data["sharing"][b][a]


def test_embedded_json_cannot_close_script_tag(tmp_path):
    out = site.build(tmp_path / "_site")
    html = (out / "index.html").read_text(encoding="utf-8")
    start = html.index('<script id="catalog-data"')
    end = html.index("</script>", start)
    assert "</" not in html[start + 1 : end].split(">", 1)[1]


def test_docs_menu_links_existing_files():
    data = site.site_data(c.load(), "owner/repo")
    docs, sections = data["meta"]["docs"], data["meta"]["doc_sections"]
    listed = [key for sec in sections for key in sec["items"]]
    assert len(listed) == len(set(listed)), "một tài liệu chỉ nằm ở một nhóm"
    assert set(listed) == set(docs)
    for key, doc in docs.items():
        assert (c.REPO_ROOT / doc["path"]).is_file(), f"{key}: không có file {doc['path']}"
        assert doc["url"] == f"https://github.com/owner/repo/blob/main/{doc['path']}"  # nút "GitHub ↗" phụ
        assert doc["desc"], f"{key}: thiếu mô tả"


def test_docs_catalog_is_valid():
    assert c.validate_docs(c.load()) == []


def test_every_stage_a_step_has_lesson_and_lab():
    """Từ bước lộ trình bấm "Học ngay" phải mở được bài học và lab của đúng bước đó."""
    cat = c.load()
    learn = site.learning_links(cat)
    docs = site.site_data(cat, "owner/repo")["meta"]["docs"]
    stage_a = next(st for st in cat.roadmap["stages"] if st["id"] == "A")
    for step in stage_a["steps"]:
        kinds = {docs[k]["kind"] for k in learn["by_step"].get(step["id"], [])}
        assert {"lesson", "lab"} <= kinds, f"bước {step['id']} thiếu bài học hoặc lab: {kinds}"
    # kỹ năng của bước → bài học của bước, đúng mức mục tiêu
    resources = {r["key"]: r for r in learn["by_skill"]["STAT-05"]}
    assert resources["stage_a5"]["level"] == "intermediate" and resources["stage_a5"]["step"] == "A5"
    assert "g1_churn" in learn["by_group"]["G1"]
    assert "cmb10" in learn["by_combo"]["CMB-10"]


def test_validate_docs_catches_bad_references(tmp_path):
    cat = c.load()
    bad = {
        "sections": [
            {
                "id": "x",
                "title": "X",
                "desc": "X",
                "docs": [
                    {"key": "a", "title": "A", "path": "khong-co.md", "desc": "d", "step": "Z9", "skills": ["NOPE-01"]},
                    {"key": "a", "title": "B", "path": "README.md", "desc": "d", "kind": "sach", "groups": ["G99"]},
                ],
            }
        ]
    }
    errors = "\n".join(c.validate_docs(dataclasses.replace(cat, docs=bad)))
    for expected in (
        "trùng key a",
        "không có file khong-co.md",
        "bước không tồn tại 'Z9'",
        "NOPE-01",
        "kind 'sach'",
        "G99",
    ):
        assert expected in errors


def test_build_bundles_docs_for_in_site_viewer(tmp_path):
    out = site.build(tmp_path / "_site", repo="owner/repo")
    data = json.loads((out / "data" / "catalog.json").read_text(encoding="utf-8"))
    pages = data["meta"]["pages"]
    for doc in data["meta"]["docs"].values():
        assert doc["path"] in pages, f"{doc['path']} không xem được trong trang"
    for path in pages:
        assert (out / "md" / f"{path}.html").is_file()
    lesson = (out / "md" / "docs/03-giai-doan-a-nen-tang/a2-sql-pandas-thong-ke.md.html").read_text(encoding="utf-8")
    assert '<pre class="mermaid">' in lesson and '<div class="highlight" data-lang="sql">' in lesson
    assert 'href="#/ky-nang/DATA-01"' in lesson, "thẻ kỹ năng sinh tự động phải mở trang kỹ năng tương tác"
    assert "github.com/owner/repo/blob/main/docs/03" not in lesson, "tài liệu trong repo không được dẫn ra GitHub"
    assert (out / "md" / "docs/03-giai-doan-a-nen-tang/img/tornado.png").is_file()
    assert (out / "assets" / "vendor" / "mermaid" / "mermaid.min.js").is_file()
    assert (out / "assets" / "vendor" / "katex" / "katex.min.js").is_file()


def test_parse_vtt_reads_cues():
    text = "WEBVTT\n\n00:00:00.000 --> 00:00:07.273\nMở đầu\n\n01:02.500 --> 01:05.000\nA · cái áo\n"
    assert site.parse_vtt(text) == [
        {"t": 0.0, "end": 7.273, "title": "Mở đầu"},
        {"t": 62.5, "end": 65.0, "title": "A · cái áo"},
    ]


def test_group_demo_video_is_published(tmp_path):
    """Trang Nhóm 9 phát video mẫu ngay trên web: file được chép vào _site/md/, chương đọc từ file WebVTT."""
    out = site.build(tmp_path / "_site", repo="owner/repo")
    data = json.loads((out / "data" / "catalog.json").read_text(encoding="utf-8"))
    demo = data["demos"]["G9"]
    assert demo["video"] == "md/projects/g9-video-chu-cai/media/video-chu-cai.mp4"
    for key in ("video", "poster", "subtitles"):
        assert (out / demo[key]).is_file(), key
    assert (out / "md/projects/g9-video-chu-cai/media/chuong.vtt").is_file()
    titles = [ch["title"] for ch in demo["chapters"]]
    assert len(titles) == 31 and titles[0] == "Mở đầu" and titles[1] == "A · cái áo" and titles[-1] == "Kết thúc"
    assert set(demo["docs"]) <= set(data["meta"]["docs"])


def test_demo_with_missing_file_is_rejected():
    cat = c.load()
    groups = [dict(g) for g in cat.groups]
    g9 = next(g for g in groups if g["id"] == "G9")
    g9["demo"] = {**g9["demo"], "video": "khong-co.mp4", "loai": 1}
    errors = c.validate(dataclasses.replace(cat, groups=groups))
    assert any("G9.demo: không có file khong-co.mp4" in e for e in errors)
    assert any("G9.demo: trường lạ" in e for e in errors)
