"""Khung xem tài liệu của trang web: Markdown render giống GitHub, liên kết không dẫn ra ngoài trang."""

import html
import re
from urllib.parse import unquote

import pytest

from aiarch import catalog as c
from aiarch import docview as v


@pytest.mark.parametrize(
    ("heading", "slug"),
    [
        ("Giới hạn và rủi ro", "giới-hạn-và-rủi-ro"),
        ("A5 · LightGBM", "a5--lightgbm"),
        ("1 · ĐÚNG — framing (viết trước khi code)", "1--đúng--framing-viết-trước-khi-code"),
        ("call_api.py: gọi API", "call_apipy-gọi-api"),
        ("Tự đánh giá cuối giai đoạn", "tự-đánh-giá-cuối-giai-đoạn"),
    ],
)
def test_github_slug(heading, slug):
    assert v.github_slug(heading) == slug


def test_slugger_numbers_repeated_headings_like_github():
    s = v.Slugger()
    assert [s.slug("Ví dụ"), s.slug("Ví dụ"), s.slug("Ví dụ")] == ["ví-dụ", "ví-dụ-1", "ví-dụ-2"]


@pytest.fixture(scope="module")
def mini(tmp_path_factory):
    """Repo nhỏ: một tài liệu dùng đủ cú pháp GFM + liên kết mọi kiểu."""
    root = tmp_path_factory.mktemp("repo")
    files = {
        "docs/a.md": """# Tiêu đề

| Cột | Số |
|:---|---:|
| `x` | 1 |

- [x] xong
- [ ] chưa

> [!WARNING]
> Cẩn thận.

```python
def f():
    return "chuỗi"
```

```mermaid
flowchart LR
    A --> B
```

Công thức $\\beta = 0.7$ và giá 5$ không phải công thức.

[cùng file](#tiêu-đề) · [file khác](b.md#phần-hai) · [thư mục](../labs/lab1/) · [code](../src/x.py#L2)
· [kỹ năng](../docs/02-skill-map/generated/mang/ml.md#ml-02) · [nhóm](../docs/02-skill-map/generated/nhom/g1-x.md)
· [ngoài](https://example.com) · [docx](bao-cao.docx) · ![ảnh](img/h.png)

<a id="neo"></a><script>alert(1)</script>
<a href="javascript:alert(1)" onclick="alert(2)">xấu</a>
""",
        "docs/b.md": "# B\n\n## Phần hai\n",
        "labs/lab1/README.md": "# Lab 1\n",
        "src/x.py": "a = 1\nb = 2\n",
        "docs/img/h.png": "",
        "docs/bao-cao.docx": "",
    }
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    bundle = v.DocBundle(c.load(), "owner/repo", root=root, files=set(files))
    bundle.roots = lambda: ["docs/a.md"]
    return bundle.collect().render()


def test_collects_linked_docs_code_and_images(mini):
    assert set(mini.pages) == {"docs/a.md", "docs/b.md", "labs/lab1/README.md", "src/x.py"}
    assert mini.pages["src/x.py"].kind == "code"
    assert mini.assets == {"docs/img/h.png"}


def test_renders_gfm_like_github(mini):
    out = mini.pages["docs/a.md"].html
    assert '<h1 id="md-tiêu-đề">' in out and 'class="anchor"' in out
    assert '<th style="text-align:right">Số</th>' in out
    assert 'class="task-list-item-checkbox"' in out and "checked" in out
    assert 'class="markdown-alert markdown-alert-warning"' in out and "<svg" in out
    assert '<div class="highlight" data-lang="python">' in out and '<span class="k">def</span>' in out
    assert '<pre class="mermaid">flowchart LR\n    A --&gt; B\n</pre>' in out
    assert '<span class="math math-inline">\\beta = 0.7</span>' in out
    assert "5$ không phải" in out, "dấu $ của tiền không thành công thức"
    assert "<script>" not in out and "&lt;script>" in out, "thẻ script bị vô hiệu như GitHub"
    assert 'id="md-neo"' in out
    assert "javascript:" not in out and "onclick" not in out


def test_rewrites_links_into_the_site(mini):
    out = mini.pages["docs/a.md"].html
    hrefs = [html.unescape(h) for h in re.findall(r'href="([^"]*)"', out)]
    assert "#/doc/docs/a.md#ti%C3%AAu-%C4%91%E1%BB%81" in hrefs  # anchor cùng file
    assert "#/doc/docs/b.md#ph%E1%BA%A7n-hai" in hrefs
    assert "#/doc/labs/lab1/README.md" in hrefs  # thư mục có README
    assert "#/doc/src/x.py#L2" in hrefs  # file code xem trong trang
    assert "#/ky-nang/ML-02" in hrefs and "#/nhom/G1" in hrefs  # tài liệu sinh tự động → trang tương tác
    assert "https://github.com/owner/repo/blob/main/docs/bao-cao.docx" in hrefs  # file nhị phân → GitHub
    assert re.search(r'<a href="https://example.com" target="_blank" rel="noopener noreferrer">', out)
    assert 'src="md/docs/img/h.png"' in out
    code = mini.pages["src/x.py"].html
    assert 'id="md-L1"' in code and 'id="md-L2"' in code and "2 dòng" in code


def test_video_poster_and_subtitles_play_inside_the_site(tmp_path):
    """Video trong README (thẻ <video>, <track>, ảnh bìa) và link tới file MP4 đều trỏ vào bản sao trong _site/md/."""
    files = {
        "projects/p/README.md": (
            '# Dự án\n\n<video src="media/v.mp4" poster="media/p.jpg" controls>\n'
            '  <track kind="subtitles" src="media/s.vtt" srclang="vi">\n</video>\n\n[Tải MP4](media/v.mp4)\n'
        ),
        "projects/p/media/v.mp4": "",
        "projects/p/media/p.jpg": "",
        "projects/p/media/s.vtt": "WEBVTT\n",
    }
    for path, text in files.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(text, encoding="utf-8")
    bundle = v.DocBundle(c.load(), "owner/repo", root=tmp_path, files=set(files))
    bundle.roots = lambda: ["projects/p/README.md"]
    bundle.collect().render()
    assert bundle.assets == {"projects/p/media/v.mp4", "projects/p/media/p.jpg", "projects/p/media/s.vtt"}
    out = bundle.pages["projects/p/README.md"].html
    assert 'src="md/projects/p/media/v.mp4"' in out and 'poster="md/projects/p/media/p.jpg"' in out
    assert 'src="md/projects/p/media/s.vtt"' in out
    assert 'href="md/projects/p/media/v.mp4" target="_blank"' in out
    bundle.write(tmp_path / "_site")
    assert (tmp_path / "_site/md/projects/p/media/v.mp4").exists()


def test_every_link_in_the_real_docs_resolves():
    """Mọi liên kết trong mọi tài liệu đã render: tới tài liệu có trong trang (anchor có thật), trang tương tác,
    ảnh đã chép, hoặc liên kết ngoài. Không còn file nào của repo bị dẫn ra GitHub nếu xem được trong trang."""
    bundle = v.build_bundle(c.load(), "owner/repo")
    ids = {p: {html.unescape(x) for x in re.findall(r'\sid="md-([^"]*)"', pg.html)} for p, pg in bundle.pages.items()}
    route = re.compile(r"#/(ky-nang/[A-Z]+-\d\d|nhom/G\d|lo-trinh(/[A-D])?|to-hop(/CMB-\d\d)?|ma-tran)$")
    broken = []
    for path, page in bundle.pages.items():
        tags = r'<(?:a|img|video|source|track)\b[^>]*?\s(?:href|src|poster)="([^"]*)"'
        for url in (html.unescape(u) for u in re.findall(tags, page.html)):
            if url.startswith("#/doc/"):
                target, _, anchor = (unquote(x) for x in url[6:].partition("#"))
                if target not in bundle.pages or (anchor and anchor not in ids[target] and not anchor.startswith("L")):
                    broken.append(f"{path}: {url}")
            elif url.startswith("#/"):
                if not route.match(url):
                    broken.append(f"{path}: {url}")
            elif url.startswith("md/"):
                if unquote(url[3:]) not in bundle.assets:
                    broken.append(f"{path}: {url}")
            elif not re.match(r"(https?:|mailto:)", url):
                broken.append(f"{path}: {url}")
            elif url.startswith("https://github.com/owner/repo/blob/main/"):
                file = unquote(url.split("/blob/main/", 1)[1].split("#")[0])
                if bundle.classify(file) in ("md", "code", "readme"):
                    broken.append(f"{path}: {url} (xem được trong trang mà vẫn dẫn ra GitHub)")
    assert not broken, "Liên kết hỏng:\n  " + "\n  ".join(broken[:30])


def test_only_tracked_files_are_published():
    bundle = v.build_bundle(c.load(), "owner/repo")
    tracked = v.tracked_files(c.REPO_ROOT)
    assert set(bundle.pages) <= tracked and bundle.assets <= tracked
    published = [*bundle.pages, *bundle.assets]
    assert not [p for p in published if p.split("/")[-1].startswith(".env") and not p.endswith(".example")]
    assert not [p for p in published if "data/" in p and not p.endswith("README.md")], "chỉ README mô tả dữ liệu"
