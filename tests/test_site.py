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
