"""Trình xem tài liệu của trang web: render Markdown trong repo thành HTML giống GitHub ngay lúc build.

Trang web mở tài liệu trong một khung toàn màn hình (`#/doc/<đường dẫn>`) thay vì chuyển sang GitHub. Module này:

1. **Gom tài liệu.** Bắt đầu từ `catalog/docs.yaml`, README của lab/dự án và tài liệu sinh tự động, đi theo mọi liên
   kết tương đối để gom thêm file `.md`, file code được nhắc tới (xem dạng code có tô màu, số dòng) và ảnh. Chỉ lấy file
   Git đang theo dõi, nên dữ liệu, model và `.env` (đã nằm trong `.gitignore`) không bao giờ lọt ra trang web.
2. **Render giống GitHub.** markdown-it-py + mdit-py-plugins theo GFM: bảng, task list, alert `> [!NOTE]`, autolink,
   footnote, công thức `$…$`/`$$…$$`; Pygments tô màu code theo bảng màu của GitHub. Khối ```` ```mermaid ```` và
   công thức được trình duyệt vẽ bằng mermaid và KaTeX trong `web/assets/vendor/`.
3. **Viết lại liên kết.** File trong repo → mở trong khung xem; thẻ kỹ năng/nhóm/lộ trình sinh tự động →
   trang tương tác tương ứng (`#/ky-nang/ML-02`...); ảnh, video, âm thanh, phụ đề → bản sao trong `_site/md/` (thẻ
   `<video src poster>`, `<source>`, `<track>` phát được ngay trong trang); file còn lại → GitHub.
   Mọi `id` được thêm tiền tố `md-` (như `user-content-` của GitHub) để không đụng id của trang web.
"""

from __future__ import annotations

import html
import posixpath
import re
import shutil
import subprocess
import unicodedata
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.gfm import gfm_plugin
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexer import Lexer
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
from pygments.util import ClassNotFound

from aiarch import catalog as c

GENERATED = "docs/02-skill-map/generated/"
OUT_DIR = "md"  # tài liệu đã render nằm ở _site/md/<đường dẫn>.html, ảnh ở _site/md/<đường dẫn>
MAX_CODE_BYTES = 200_000  # file code lớn hơn (lockfile, dữ liệu) mở trên GitHub
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif"}
MEDIA_EXT = {".mp4", ".webm", ".mp3", ".ogg", ".wav", ".vtt"}  # video, âm thanh, phụ đề WebVTT
ASSET_EXT = IMAGE_EXT | MEDIA_EXT  # chép nguyên file vào _site/md/ để trang phát/hiện trực tiếp
CODE_EXT = {
    ".py", ".pyi", ".toml", ".yaml", ".yml", ".json", ".jsonl", ".cfg", ".ini", ".txt", ".sh", ".bash", ".ps1",
    ".html", ".css", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".sql", ".csv", ".xml", ".env", ".example",
    ".conf", ".template", ".j2", ".jinja", ".tf", ".go", ".rs", ".java", ".kt", ".r", ".proto", ".graphql", ".http",
}  # fmt: skip
CODE_NAMES = {"Makefile", "Dockerfile", "Containerfile", ".gitignore", ".dockerignore", ".gitattributes", "LICENSE"}
FENCE_ALIASES = {
    "py3": "python", "ipython": "python", "jsonc": "json", "json5": "json", "shell-session": "console",
    "compose": "yaml", "dotenv": "", "env": "", "gitignore": "", "text": "", "txt": "", "plain": "", "plaintext": "",
}  # fmt: skip
# Thẻ HTML thô GitHub không cho chạy trong Markdown (GFM "disallowed raw HTML") — hiện ra dạng chữ.
DISALLOWED_TAG = re.compile(
    r"<(?=/?(?:title|textarea|style|xmp|iframe|noembed|noframes|script|plaintext)\b)", re.IGNORECASE
)
SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
UNSAFE_URL = re.compile(r"^\s*(?:javascript|vbscript|data):", re.IGNORECASE)
TAG = re.compile(r"<([a-zA-Z][a-zA-Z0-9-]*)(\s[^<>]*?)?(/?)>")
ATTR = re.compile(r"""\s+([^\s"'<>/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?""")
HTML_URL = re.compile(r"""\b(?:href|src|poster)\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)
FORMATTER = HtmlFormatter(nowrap=True)

# Icon Octicons (MIT) GitHub dùng cho anchor tiêu đề và 5 loại alert.
_SVG = '<svg class="octicon" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="{}"></path></svg>'
ICON_LINK = _SVG.format(
    "m7.775 3.275 1.25-1.25a3.5 3.5 0 1 1 4.95 4.95l-2.5 2.5a3.5 3.5 0 0 1-4.95 0 .751.751 0 0 1 .018"
    "-1.042.751.751 0 0 1 1.042-.018 1.998 1.998 0 0 0 2.83 0l2.5-2.5a2.002 2.002 0 0 0-2.83-2.83l-1."
    "25 1.25a.751.751 0 0 1-1.042-.018.751.751 0 0 1-.018-1.042Zm-4.69 9.64a1.998 1.998 0 0 0 2.83 0l"
    "1.25-1.25a.751.751 0 0 1 1.042.018.751.751 0 0 1 .018 1.042l-1.25 1.25a3.5 3.5 0 1 1-4.95-4.95l2"
    ".5-2.5a3.5 3.5 0 0 1 4.95 0 .751.751 0 0 1-.018 1.042.751.751 0 0 1-1.042.018 1.998 1.998 0 0 0-"
    "2.83 0l-2.5 2.5a1.998 1.998 0 0 0 0 2.83Z"
)
ALERT_ICONS = {
    "NOTE": (
        "M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8Zm8-6.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13ZM6.5 7.75A.75.75 "
        "0 0 1 7.25 7h1a.75.75 0 0 1 .75.75v2.75h.25a.75.75 0 0 1 0 1.5h-2a.75.75 0 0 1 0-1.5h.25v-2h-.25"
        "a.75.75 0 0 1-.75-.75ZM8 6a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z"
    ),
    "TIP": (
        "M8 1.5c-2.363 0-4 1.69-4 3.75 0 .984.424 1.625.984 2.304l.214.253c.223.264.47.556.673.848.284.41"
        "1.537.896.621 1.49a.75.75 0 0 1-1.484.211c-.04-.282-.163-.547-.37-.847a8.456 8.456 0 0 0-.542-.6"
        "8c-.084-.1-.173-.205-.268-.32C3.201 7.75 2.5 6.766 2.5 5.25 2.5 2.31 4.863 0 8 0s5.5 2.31 5.5 5."
        "25c0 1.516-.701 2.5-1.328 3.259-.095.115-.184.22-.268.319-.207.245-.383.453-.541.681-.208.3-.33."
        "565-.37.847a.751.751 0 0 1-1.485-.212c.084-.593.337-1.078.621-1.489.203-.292.45-.584.673-.848.07"
        "5-.088.147-.173.213-.253.561-.679.985-1.32.985-2.304 0-2.06-1.637-3.75-4-3.75ZM5.75 12h4.5a.75.7"
        "5 0 0 1 0 1.5h-4.5a.75.75 0 0 1 0-1.5ZM6 15.25a.75.75 0 0 1 .75-.75h2.5a.75.75 0 0 1 0 1.5h-2.5a"
        ".75.75 0 0 1-.75-.75Z"
    ),
    "IMPORTANT": (
        "M0 1.75C0 .784.784 0 1.75 0h12.5C15.216 0 16 .784 16 1.75v9.5A1.75 1.75 0 0 1 14.25 13H8.06l-2.5"
        "73 2.573A1.458 1.458 0 0 1 3 14.543V13H1.75A1.75 1.75 0 0 1 0 11.25Zm1.75-.25a.25.25 0 0 0-.25.2"
        "5v9.5c0 .138.112.25.25.25h2a.75.75 0 0 1 .75.75v2.19l2.72-2.72a.749.749 0 0 1 .53-.22h6.5a.25.25"
        " 0 0 0 .25-.25v-9.5a.25.25 0 0 0-.25-.25Zm7 2.25v2.5a.75.75 0 0 1-1.5 0v-2.5a.75.75 0 0 1 1.5 0Z"
        "M9 9a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"
    ),
    "WARNING": (
        "M6.457 1.047c.659-1.234 2.427-1.234 3.086 0l6.082 11.378A1.75 1.75 0 0 1 14.082 15H1.918a1.75 1."
        "75 0 0 1-1.543-2.575Zm1.763.707a.25.25 0 0 0-.44 0L1.698 13.132a.25.25 0 0 0 .22.368h12.164a.25."
        "25 0 0 0 .22-.368Zm.53 3.996v2.5a.75.75 0 0 1-1.5 0v-2.5a.75.75 0 0 1 1.5 0ZM9 11a1 1 0 1 1-2 0 "
        "1 1 0 0 1 2 0Z"
    ),
    "CAUTION": (
        "M4.47.22A.749.749 0 0 1 5 0h6c.199 0 .389.079.53.22l4.25 4.25c.141.14.22.331.22.53v6a.749.749 0 "
        "0 1-.22.53l-4.25 4.25A.749.749 0 0 1 11 16H5a.749.749 0 0 1-.53-.22L.22 11.53A.749.749 0 0 1 0 1"
        "1V5c0-.199.079-.389.22-.53Zm.84 1.28L1.5 5.31v5.38l3.81 3.81h5.38l3.81-3.81V5.31L10.69 1.5ZM8 4a"
        ".75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 8 4Zm0 8a1 1 0 1 1 0-2 1 1 0 0 1 0 "
        "2Z"
    ),
}


# ───────────────────────────── anchor kiểu GitHub ─────────────────────────────


def github_slug(text: str) -> str:
    """Anchor GitHub sinh cho một tiêu đề (thuật toán github-slugger): chữ thường, bỏ dấu câu và ký hiệu, giữ chữ có
    dấu tiếng Việt, số, `_` và `-`; mỗi khoảng trắng thành một `-`."""
    out = []
    for ch in text.lower():
        if ch == " ":
            out.append("-")
        elif ch.isalnum() or ch in "-_" or unicodedata.category(ch)[0] == "M" or unicodedata.category(ch) == "Pc":
            out.append(ch)
    return "".join(out)


class Slugger:
    """Anchor không trùng trong một tài liệu: lần lặp thứ n của cùng tiêu đề thành `<slug>-n` như GitHub."""

    def __init__(self) -> None:
        self.seen: dict[str, int] = {}

    def slug(self, text: str) -> str:
        base = result = github_slug(text)
        while result in self.seen:
            self.seen[base] += 1
            result = f"{base}-{self.seen[base]}"
        self.seen[result] = 0
        return result


EXPLICIT_ANCHOR = re.compile(r"""<a\s[^>]*?\b(?:id|name)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


def markdown_anchors(text: str) -> set[str]:
    """Mọi anchor một file Markdown có trên GitHub (và trong khung xem): slug tiêu đề + `<a id/name="...">` viết tay."""
    md = MarkdownIt("commonmark", {"html": True}).use(gfm_plugin)
    tokens = md.parse(text)
    slugger, found = Slugger(), set()
    stack = list(reversed(tokens))
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open":
            found.add(slugger.slug(inline_text(tokens[i + 1]).strip()))
    while stack:
        tok = stack.pop()
        if tok.type in ("html_block", "html_inline"):
            found.update(EXPLICIT_ANCHOR.findall(tok.content))
        stack.extend(tok.children or [])
    return found


def inline_text(token: Token) -> str:
    """Chữ hiển thị của một dòng Markdown (như `textContent` của trình duyệt): giữ chữ và code, bỏ thẻ HTML, ảnh."""
    parts = []
    for child in token.children or []:
        if child.type in ("text", "code_inline", "math_inline"):
            parts.append(child.content)
        elif child.type in ("softbreak", "hardbreak"):
            parts.append(" ")
    return "".join(parts)


# ───────────────────────────── tô màu code ─────────────────────────────


def lexer_for_fence(lang: str) -> Lexer | None:
    name = FENCE_ALIASES.get(lang, lang)
    if not name:
        return None
    try:
        return get_lexer_by_name(name, stripnl=False)
    except ClassNotFound:
        return None


def lexer_for_file(path: str) -> Lexer | None:
    try:
        return get_lexer_for_filename(posixpath.basename(path), stripnl=False)
    except ClassNotFound:
        return None


def highlighted(code: str, lexer: Lexer | None) -> str:
    code = code.rstrip("\n")
    if lexer is None:
        return html.escape(code, quote=False)
    return highlight(code, lexer, FORMATTER).rstrip("\n")


# ───────────────────────────── trang và gom tài liệu ─────────────────────────────


@dataclass
class Page:
    path: str  # đường dẫn trong repo
    kind: str  # "md" | "code"
    title: str = ""
    html: str = ""
    tokens: list[Token] = field(default_factory=list)
    env: dict[str, Any] = field(default_factory=dict)


def tracked_files(root: Path) -> set[str]:
    """File Git đang theo dõi (đường dẫn POSIX). Không có Git: mọi file, trừ thư mục môi trường/dữ liệu/kết quả."""
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True).stdout
        return {p for p in out.decode("utf-8").split("\0") if p and (root / p).is_file()}
    except (OSError, subprocess.CalledProcessError):
        skip = {".git", ".venv", "node_modules", "_site", "data", "models", "mlruns", "__pycache__"}
        return {
            p.relative_to(root).as_posix()
            for p in root.rglob("*")
            if p.is_file() and not skip & set(p.relative_to(root).parts) and not p.name.startswith(".env")
        }


def is_code_file(path: str) -> bool:
    name = posixpath.basename(path)
    return name in CODE_NAMES or name.startswith("Dockerfile") or posixpath.splitext(name)[1].lower() in CODE_EXT


class DocBundle:
    """Toàn bộ tài liệu trang web xem được: các trang (.md + code), ảnh, và cách viết lại từng liên kết."""

    def __init__(self, cat: c.Catalog, repo: str, root: Path = c.REPO_ROOT, files: set[str] | None = None) -> None:
        self.cat, self.repo, self.root = cat, repo, root
        self.files = files if files is not None else tracked_files(root)
        self.dirs = {posixpath.dirname(p) for p in self.files}
        for d in list(self.dirs):
            while d:
                d = posixpath.dirname(d)
                self.dirs.add(d)
        self.skill_ids = {s["id"] for s in cat.skills}
        self.group_ids = set(cat.group_ids)
        self.combo_ids = {x["id"] for x in cat.combinations}
        self.stage_ids = {st["id"] for st in cat.roadmap.get("stages", [])}
        self.md = MarkdownIt("commonmark", {"html": True})
        self.md.use(gfm_plugin)  # bảng, gạch ngang, task list, alert, autolink, footnote
        self.md.use(dollarmath_plugin, allow_labels=False, allow_space=False, allow_digits=False, double_inline=True)
        for name, rule in (
            ("fence", self._render_fence),
            ("heading_open", self._render_heading),
            ("math_inline", self._render_math),
            ("math_inline_double", self._render_math),
            ("math_block", self._render_math),
            ("html_block", self._render_html),
            ("html_inline", self._render_html),
            ("alert_title_open", self._render_alert_title),
        ):
            self.md.add_render_rule(name, rule)
        self.pages: dict[str, Page] = {}
        self.assets: set[str] = set()

    # ── gom ──
    def roots(self) -> list[str]:
        paths = [d["path"] for d in c.doc_items(self.cat)]
        paths += sorted(p for p in self.files if re.fullmatch(r"(labs|projects)/[^/]+/README\.md", p))
        paths += sorted(p for p in self.files if p.startswith(GENERATED) and p.endswith(".md"))
        paths += [p for p in ("README.md", "CHECKLIST.md", "HISTORY.md", "CONTRIBUTING.md") if p in self.files]
        return [p for p in dict.fromkeys(paths) if p in self.files]

    def collect(self) -> DocBundle:
        queue = deque(self.roots())
        while queue:
            while queue:
                path = queue.popleft()
                if path not in self.pages:
                    self._add_markdown(path, queue)
            # Như cây thư mục của GitHub: mở được mọi .md cùng thư mục với trang đã gom và README của thư mục con.
            queue.extend(self._neighbours())
        return self

    def _add_markdown(self, path: str, queue: deque[str]) -> None:
        page = Page(path, "md", env={"path": path, "slugger": Slugger(), "toc": [], "needs": set()})
        text = (self.root / path).read_text(encoding="utf-8", errors="replace")
        page.tokens = self.md.parse(text, page.env)
        self.pages[path] = page
        for url, is_src in self._urls(page.tokens):
            target = self.target(path, url)
            if target is None:
                continue
            kind = self.classify(target[0])
            if kind == "md":
                queue.append(target[0])
            elif kind == "readme":
                queue.append(self.readme(target[0]))
            elif kind == "asset":
                self.assets.add(target[0])
            elif kind == "code" and not is_src and target[0] not in self.pages:
                self.pages[target[0]] = Page(target[0], "code")

    def _neighbours(self) -> list[str]:
        """File .md cùng thư mục với mọi trang .md đã gom, và README.md của thư mục con trực tiếp."""
        dirs = {posixpath.dirname(p) for p, page in self.pages.items() if page.kind == "md"}
        found = []
        for f in sorted(self.files):
            if not f.endswith(".md") or f in self.pages:
                continue
            parent = posixpath.dirname(f)
            if parent in dirs or (posixpath.basename(f) == "README.md" and posixpath.dirname(parent) in dirs):
                found.append(f)
        return found

    def _urls(self, tokens: list[Token]) -> list[tuple[str, bool]]:
        found: list[tuple[str, bool]] = []
        stack = list(tokens)
        while stack:
            tok = stack.pop()
            if tok.type == "link_open":
                found.append((str(tok.attrGet("href") or ""), False))
            elif tok.type == "image":
                found.append((str(tok.attrGet("src") or ""), True))
            elif tok.type in ("html_block", "html_inline"):
                for m in HTML_URL.finditer(tok.content):
                    is_src = not m.group(0).lower().lstrip().startswith("href")
                    found.append((html.unescape(m.group(1) if m.group(1) is not None else m.group(2)), is_src))
            stack.extend(tok.children or [])
        return found

    # ── phân giải liên kết ──
    def target(self, src: str, url: str) -> tuple[str, str] | None:
        """(đường dẫn trong repo, anchor) mà `url` trong file `src` trỏ tới; None nếu trỏ ra ngoài repo."""
        url = url.strip()
        if not url or url.startswith("#/"):
            return None
        if SCHEME.match(url) or url.startswith("//"):
            # Link tuyệt đối tới chính repo trên nhánh chính → xem trong trang; link cố định theo commit giữ nguyên.
            m = re.match(
                rf"https?://github\.com/{re.escape(self.repo)}/(?:blob|tree)/(?:main|HEAD)/([^?#]*)[^#]*(?:#(.*))?$",
                url,
            )
            return (unquote(m.group(1)).strip("/"), unquote(m.group(2) or "")) if m else None
        path, _, anchor = url.partition("#")
        path = path.split("?", 1)[0]
        if not path:
            return src, unquote(anchor)
        base = "" if path.startswith("/") else posixpath.dirname(src)
        full = posixpath.normpath(posixpath.join(base, unquote(path).lstrip("/")))
        if full == ".":
            full = ""
        if full == ".." or full.startswith("../"):
            return None
        return full, unquote(anchor)

    def readme(self, directory: str) -> str:
        return f"{directory}/README.md" if directory else "README.md"

    def classify(self, path: str) -> str:
        if path in self.files:
            if path.endswith(".md"):
                return "md"
            if posixpath.splitext(path)[1].lower() in ASSET_EXT:
                return "asset"
            if is_code_file(path) and (self.root / path).stat().st_size <= MAX_CODE_BYTES:
                return "code"
            return "file"
        if path in self.dirs:
            return "readme" if self.readme(path) in self.files else "dir"
        return "missing"

    def native_route(self, path: str, anchor: str) -> str | None:
        """Tài liệu sinh tự động từ catalog có trang tương tác tương đương trên web — mở trang đó thay cho bản .md."""
        if not path.startswith(GENERATED):
            return None
        rest, key = path[len(GENERATED) :], anchor.upper()
        if rest.startswith("mang/") and key in self.skill_ids:
            return f"#/ky-nang/{key}"
        if rest.startswith("nhom/"):
            gid = posixpath.basename(rest).split("-", 1)[0].upper()
            return f"#/nhom/{gid}" if gid in self.group_ids else None
        if rest == "lo-trinh.md":
            m = re.fullmatch(r"giai-doan-([a-z])", anchor)
            if m and m.group(1).upper() in self.stage_ids:
                return f"#/lo-trinh/{m.group(1).upper()}"
            return "#/lo-trinh" if not anchor else None
        if rest == "to-hop-ky-nang.md":
            if key in self.combo_ids:
                return f"#/to-hop/{key}"
            return "#/to-hop" if not anchor else None
        if rest == "ma-tran-ky-nang.md" and anchor in ("", "chia-se"):
            return "#/ma-tran"
        return None

    def link(self, src: str, url: str) -> tuple[str, bool]:
        """Liên kết mới cho `url` trong file `src`: (href, mở tab mới?)."""
        if url.startswith("#/"):
            return url, False
        target = self.target(src, url)
        if target is None:
            return url, bool(SCHEME.match(url) or url.startswith("//"))
        if SCHEME.match(url) and target[0] not in self.pages and self.native_route(*target) is None:
            return url, True  # link tuyệt đối tới file không xem được trong trang: giữ nguyên
        path, anchor = target
        native = self.native_route(path, anchor)
        if native:
            return native, False
        kind = self.classify(path)
        if kind == "readme" and self.readme(path) in self.pages:
            path, kind = self.readme(path), "md"
        if path in self.pages:
            return doc_href(path, anchor), False
        if kind == "asset":
            return asset_url(path), True
        view = "tree" if kind == "dir" else "blob"
        return f"https://github.com/{self.repo}/{view}/main/{quote(path)}" + (
            f"#{quote(anchor)}" if anchor else ""
        ), True

    # ── render ──
    def render(self) -> DocBundle:
        for page in self.pages.values():
            if page.kind == "md":
                body = self.md.renderer.render(page.tokens, self.md.options, page.env)
                page.html = (
                    self.rewrite(page.path, body) if body.strip() else '<p class="viewer-note">(File trống.)</p>'
                )
                page.title = page.env.get("title") or posixpath.basename(page.path)
                page.tokens = []
            else:
                page.html, page.title = self.render_code(page.path), posixpath.basename(page.path)
        return self

    def render_code(self, path: str) -> str:
        raw = (self.root / path).read_bytes()
        text = raw.decode("utf-8", errors="replace")
        lexer = lexer_for_file(path)
        lines = highlighted(text, lexer).split("\n") if text.strip() else [""]
        body = "\n".join(f'<span class="cl" id="md-L{i}">{line}</span>' for i, line in enumerate(lines, 1))
        size = f"{len(raw) / 1024:.1f} KB" if len(raw) >= 1024 else f"{len(raw)} byte"
        meta = f"{len(lines)} dòng · {size}" + (f" · {html.escape(lexer.name)}" if lexer else "")
        return (
            f'<div class="code-file"><div class="code-file-meta">{meta}</div>'
            f'<div class="highlight"><pre class="code-lines"><code>{body}</code></pre></div></div>'
        )

    def rewrite(self, src: str, body: str) -> str:
        """Viết lại href/src/id của mọi thẻ HTML (chữ trong khối code đã được escape nên không bị đụng tới)."""

        def tag(m: re.Match[str]) -> str:
            name, attrs, slash = m.group(1), m.group(2) or "", m.group(3)
            items = []
            for a in ATTR.finditer(attrs):
                key = a.group(1)
                raw = next((g for g in a.groups()[1:] if g is not None), None)
                value = None if raw is None else html.unescape(raw)
                if key.lower().startswith("on"):  # như GitHub: HTML trong tài liệu không được chạy script
                    continue
                if key.lower() in ("href", "src") and value and UNSAFE_URL.match(value):
                    value = "#"
                items.append([key, value])
            external = False
            for item in items:
                key, value = item[0].lower(), item[1]
                if value is None:
                    continue
                if key == "href" and name.lower() == "a":
                    item[1], external = self.link(src, value)
                elif key in ("src", "poster"):
                    target = self.target(src, value)
                    if target and target[0] in self.assets:
                        item[1] = asset_url(target[0])
                elif key == "id" or (key == "name" and name.lower() == "a"):
                    item[1] = f"md-{value}"
            keys = {k.lower() for k, _ in items}
            if name.lower() == "a" and external:
                items += [["target", "_blank"]] if "target" not in keys else []
                items += [["rel", "noopener noreferrer"]] if "rel" not in keys else []
            if name.lower() == "img" and "loading" not in keys:
                items.append(["loading", "lazy"])
            parts = "".join(f" {k}" if v is None else f' {k}="{html.escape(v, quote=True)}"' for k, v in items)
            return f"<{name}{parts}{slash}>"

        return TAG.sub(tag, body)

    # ── luật render riêng ──
    def _render_fence(self, tokens: list[Token], idx: int, options: Any, env: dict[str, Any]) -> str:
        tok = tokens[idx]
        lang = (tok.info.strip().split(maxsplit=1) or [""])[0].lower().strip("{}.")
        if lang == "mermaid":
            env["needs"].add("mermaid")
            return f'<pre class="mermaid">{html.escape(tok.content, quote=False)}</pre>\n'
        if lang == "math":
            env["needs"].add("math")
            return f'<div class="math math-display">{html.escape(tok.content, quote=False)}</div>\n'
        code = highlighted(tok.content, lexer_for_fence(lang))
        label = f' data-lang="{html.escape(lang)}"' if lang else ""
        return f'<div class="highlight"{label}><pre><code>{code}</code></pre></div>\n'

    def _render_heading(self, tokens: list[Token], idx: int, options: Any, env: dict[str, Any]) -> str:
        tok, text = tokens[idx], inline_text(tokens[idx + 1]).strip()
        slug = env["slugger"].slug(text)
        level = int(tok.tag[1])
        if level == 1 and "title" not in env:
            env["title"] = text
        env["toc"].append((level, slug, text))
        anchor = f'<a class="anchor" aria-hidden="true" tabindex="-1" href="#{quote(slug)}">{ICON_LINK}</a>'
        return f'<{tok.tag} id="{html.escape(slug)}">{anchor}'

    def _render_math(self, tokens: list[Token], idx: int, options: Any, env: dict[str, Any]) -> str:
        tok = tokens[idx]
        env["needs"].add("math")
        tex = html.escape(tok.content.strip(), quote=False)
        if tok.type == "math_block":
            return f'<div class="math math-display">{tex}</div>\n'
        if tok.type == "math_inline_double":
            return f'<span class="math math-display">{tex}</span>'
        return f'<span class="math math-inline">{tex}</span>'

    def _render_html(self, tokens: list[Token], idx: int, options: Any, env: dict[str, Any]) -> str:
        return DISALLOWED_TAG.sub("&lt;", tokens[idx].content)

    def _render_alert_title(self, tokens: list[Token], idx: int, options: Any, env: dict[str, Any]) -> str:
        kind = next((t.info for t in reversed(tokens[:idx]) if t.type == "alert_open"), "NOTE")
        return f'<p class="markdown-alert-title">{_SVG.format(ALERT_ICONS.get(kind, ALERT_ICONS["NOTE"]))}'

    # ── ghi ra _site ──
    def write(self, out: Path) -> None:
        for page in self.pages.values():
            dest = out / OUT_DIR / f"{page.path}.html"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(page.html, encoding="utf-8")
        for path in self.assets:
            dest = out / OUT_DIR / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.root / path, dest)

    def manifest(self) -> dict[str, dict[str, str]]:
        """Danh sách trang cho trình duyệt: đường dẫn → tiêu đề và loại ("md" | "code")."""
        return {p.path: {"t": p.title, "k": p.kind} for p in sorted(self.pages.values(), key=lambda p: p.path)}


def doc_href(path: str, anchor: str = "") -> str:
    return f"#/doc/{quote(path)}" + (f"#{quote(anchor, safe='')}" if anchor else "")


def asset_url(path: str) -> str:
    return f"{OUT_DIR}/{quote(path)}"


def build_bundle(cat: c.Catalog, repo: str, root: Path = c.REPO_ROOT) -> DocBundle:
    return DocBundle(cat, repo, root).collect().render()
