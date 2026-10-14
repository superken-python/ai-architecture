"""Radar framework agent cho Nhóm 7: kéo số liệu registry, sinh bảng so sánh, gắn cờ mục cần xem lại.

Cách dùng:
    python -m aiarch.landscape refresh          # cần mạng: PyPI, npm (+ GitHub nếu có GITHUB_TOKEN) → snapshot JSON
    python -m aiarch.landscape build            # không cần mạng: YAML + snapshot → docs/agent-radar/generated/
    python -m aiarch.landscape build --check    # báo lỗi nếu trang sinh ra đã cũ (dùng trong test/CI)

Dữ liệu do người duyệt nằm ở catalog/agent_landscape.yaml; số liệu tự động ở catalog/agent_landscape.snapshot.json.
Cờ cảnh báo tính theo NGÀY CỦA SNAPSHOT (không theo hôm nay) để trang sinh ra luôn tái tạo được.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA = Path("catalog/agent_landscape.yaml")
SNAPSHOT = Path("catalog/agent_landscape.snapshot.json")
OUT = Path("docs/agent-radar/generated/bang-so-sanh.md")
HEADER = (
    "<!-- FILE SINH TỰ ĐỘNG từ catalog/agent_landscape.yaml + agent_landscape.snapshot.json bằng `make landscape`. "
    "KHÔNG sửa tay. -->\n\n"
)
STALE_RELEASE_DAYS = 180  # không phát hành lâu hơn → cờ "ít cập nhật"
STALE_REVIEW_DAYS = 180  # người duyệt chưa xem lại lâu hơn → cờ "cần review"
RINGS = {"adopt": "Adopt", "trial": "Trial", "assess": "Assess", "hold": "Hold"}
FEATURE_MARK = {"yes": "✅", "partial": "◐", "no": "—", "?": "?", "both": "graph + llm", "graph": "graph", "llm": "llm"}
PRE_RELEASE = re.compile(r"[a-zA-Z]")  # 1.0.0a1, 1.0.0rc1, 1.0.0.dev1, 1.0.0-beta.1 → bản thử


# ---------------------------------------------------------------------------------------------------------- dữ liệu
def load_data(root: Path = REPO_ROOT) -> dict[str, Any]:
    return yaml.safe_load((root / DATA).read_text(encoding="utf-8"))


def load_snapshot(root: Path = REPO_ROOT) -> dict[str, Any]:
    path = root / SNAPSHOT
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"date": None, "packages": {}}


def packages_of(entry: dict[str, Any]) -> list[tuple[str, str]]:
    pk = entry.get("packages") or {}
    return [(eco, name) for eco in ("pypi", "npm") for name in pk.get(eco, [])]


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    cols = set(data.get("feature_columns", {}))
    for e in data.get("frameworks", []) + data.get("supporting", []):
        if e["id"] in ids:
            errors.append(f"trùng id {e['id']}")
        ids.add(e["id"])
        if e.get("ring") not in RINGS:
            errors.append(f"{e['id']}: ring phải là {', '.join(RINGS)}")
        if not packages_of(e):
            errors.append(f"{e['id']}: thiếu packages")
    for e in data.get("frameworks", []):
        if e.get("category") not in data.get("categories", {}):
            errors.append(f"{e['id']}: category {e.get('category')} không có trong categories")
        if set(e.get("features", {})) != cols:
            errors.append(f"{e['id']}: features phải có đủ {sorted(cols)}")
        bad = [k for k, v in e.get("features", {}).items() if str(v) not in FEATURE_MARK]
        if bad:
            errors.append(f"{e['id']}: giá trị feature không hợp lệ ở {bad}")
        for key in ("strengths", "weaknesses"):
            if not all(isinstance(x, str) for x in e.get(key, [])):
                errors.append(f"{e['id']}: {key} phải là danh sách chuỗi (đặt trong ngoặc kép nếu có dấu ': ')")
        if e.get("verified") not in ("source", "docs", "secondary"):
            errors.append(f"{e['id']}: verified phải là source | docs | secondary")
    return errors


# ---------------------------------------------------------------------------------------------------------- refresh
def _get(url: str, headers: dict[str, str] | None = None) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "ai-architecture-landscape", **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def _majors(versions: dict[str, str]) -> dict[str, str]:
    """{phiên bản: ngày} → {major: ngày phát hành bản ổn định đầu tiên của major đó}."""
    out: dict[str, str] = {}
    for version, day in sorted(versions.items(), key=lambda kv: kv[1]):
        if not day or PRE_RELEASE.search(version.split("+")[0]):
            continue
        major = version.split(".")[0]
        if major.isdigit() and major not in out:
            out[major] = day
    return out


def fetch_pypi(name: str) -> dict[str, Any]:
    d = _get(f"https://pypi.org/pypi/{name}/json")
    info = d["info"]
    days = {v: files[0]["upload_time"][:10] for v, files in d["releases"].items() if files}
    classifiers = [c.split("::")[-1].strip() for c in info.get("classifiers", []) if c.startswith("License")]
    free_text = (info.get("license") or "").strip().splitlines()
    license_ = info.get("license_expression") or ", ".join(classifiers) or (free_text[0][:40] if free_text else "")
    return {
        "version": info["version"],
        "released": days.get(info["version"], ""),
        "license": license_,
        "versions": days,
    }


def fetch_npm(name: str) -> dict[str, Any]:
    d = _get(f"https://registry.npmjs.org/{name.replace('/', '%2F')}")
    latest = d["dist-tags"]["latest"]
    times = {v: t[:10] for v, t in d["time"].items() if v not in ("created", "modified")}
    return {
        "version": latest,
        "released": times.get(latest, ""),
        "license": d["versions"][latest].get("license") or "",
        "versions": times,
    }


def fetch_github(repo: str, token: str) -> dict[str, Any]:
    d = _get(f"https://api.github.com/repos/{repo}", {"Authorization": f"Bearer {token}"})
    return {
        "stars": d.get("stargazers_count"),
        "archived": d.get("archived"),
        "pushed": (d.get("pushed_at") or "")[:10],
    }


def refresh(root: Path = REPO_ROOT, today: date | None = None) -> dict[str, Any]:
    data = load_data(root)
    entries = data["frameworks"] + data["supporting"]
    jobs = sorted({p for e in entries for p in packages_of(e)})
    fetchers = {"pypi": fetch_pypi, "npm": fetch_npm}

    def one(job: tuple[str, str]) -> tuple[str, dict[str, Any]]:
        eco, name = job
        try:
            raw = fetchers[eco](name)
        except (urllib.error.URLError, KeyError, ValueError) as exc:
            return f"{eco}:{name}", {"error": str(exc)[:120]}
        majors = _majors(raw.pop("versions"))
        return f"{eco}:{name}", {**raw, "majors": majors}

    with ThreadPoolExecutor(max_workers=8) as pool:
        packages = dict(pool.map(one, jobs))

    repos: dict[str, Any] = {}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        for repo in sorted({e["repo"] for e in data["frameworks"] if e.get("repo")}):
            try:
                repos[repo] = fetch_github(repo, token)
            except (urllib.error.URLError, KeyError, ValueError) as exc:
                repos[repo] = {"error": str(exc)[:120]}
    old = load_snapshot(root)
    snapshot = {
        "date": (today or datetime.now(UTC).date()).isoformat(),
        "packages": packages,
        # không có token (máy dev) → giữ số sao lần trước thay vì xóa
        "repos": repos or old.get("repos", {}),
    }
    (root / SNAPSHOT).write_text(json.dumps(snapshot, ensure_ascii=False, indent=1, sort_keys=True) + "\n", "utf-8")
    return snapshot


# ---------------------------------------------------------------------------------------------------------- build
def _days(a: str, b: str) -> int:
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def flags(entry: dict[str, Any], snap: dict[str, Any]) -> list[str]:
    """Cờ để người duyệt biết mục nào cần xem lại — tính theo ngày của snapshot."""
    today = snap.get("date")
    if not today:
        return []
    out: list[str] = []
    for eco, name in packages_of(entry):
        p = snap["packages"].get(f"{eco}:{name}", {})
        if p.get("error"):
            out.append(f"⚠ không lấy được số liệu {name}")
            continue
        if p.get("released") and _days(p["released"], today) > STALE_RELEASE_DAYS:
            out.append(f"⚠ {name} không phát hành {_days(p['released'], today)} ngày")
        reviewed = str(entry.get("reviewed") or "")
        new_majors = [m for m, d in p.get("majors", {}).items() if reviewed and d > reviewed]
        if new_majors:
            out.append(f"🔄 {name} lên major {', '.join(new_majors)} sau lần review")
    repo = snap.get("repos", {}).get(entry.get("repo") or "", {})
    if repo.get("archived"):
        out.append("📦 repo đã archive")
    reviewed = str(entry.get("reviewed") or "")
    if reviewed and _days(reviewed, today) > STALE_REVIEW_DAYS:
        out.append(f"🕑 chưa review {_days(reviewed, today)} ngày")
    return out


def _metrics(entry: dict[str, Any], snap: dict[str, Any]) -> tuple[str, str, str, str]:
    """(phiên bản, ngày phát hành, số bản major trong 12 tháng, giấy phép trên registry) của gói chính."""
    eco, name = packages_of(entry)[0]
    p = snap["packages"].get(f"{eco}:{name}", {})
    if not p or p.get("error"):
        return "?", "?", "?", "?"
    today = snap.get("date") or p.get("released") or "1970-01-01"
    # chỉ đếm lần LÊN major (bỏ major đầu tiên của gói); gói 0.x đổi API ở bản minor nên cột này không phản ánh được
    later = sorted(p.get("majors", {}).values())[1:]
    churn = sum(1 for d in later if 0 <= _days(d, today) <= 365)
    major0 = p["version"].startswith("0.")
    return (
        f"`{p['version']}`",
        p.get("released") or "?",
        f"{churn} (0.x)" if major0 else str(churn),
        p.get("license") or "không khai báo",
    )


def _stars(entry: dict[str, Any], snap: dict[str, Any]) -> str:
    stars = snap.get("repos", {}).get(entry.get("repo") or "", {}).get("stars")
    return f"{stars / 1000:.1f}k" if isinstance(stars, int) else "—"


def render(data: dict[str, Any], snap: dict[str, Any]) -> str:
    frameworks, supporting = data["frameworks"], data["supporting"]
    cols = data["feature_columns"]
    lines = [
        HEADER,
        "# Radar framework agent · bảng so sánh\n",
        f"Dữ liệu duyệt: **{data['reviewed']}** · số liệu registry: **{snap.get('date') or 'chưa kéo'}** · "
        f"{len(frameworks)} framework + {len(supporting)} công cụ hỗ trợ. Cách đọc và quy trình cập nhật: "
        "[README](../README.md).\n",
        "## 1. Radar\n",
        "| Vòng | Framework |",
        "|---|---|",
    ]
    for ring, label in RINGS.items():
        names = [f"[{e['name']}](#{e['id']})" for e in frameworks if e["ring"] == ring]
        lines.append(f"| **{label}** | {' · '.join(names) or '—'} |")

    lines += [
        "\n## 2. Tính năng\n",
        "✅ có · ◐ một phần / qua tích hợp · — không · ? chưa kiểm. Mức kiểm chứng: **source** đã đọc mã nguồn, "
        "**docs** tài liệu/registry chính thức, **secondary** bài viết thứ cấp — kiểm lại trước khi dựa vào.\n",
        "| Framework | Vòng | Nhóm | " + " | ".join(cols) + " | Kiểm chứng |",
        "|---|---|---|" + "---|" * len(cols) + "---|",
    ]
    for e in frameworks:
        feats = " | ".join(FEATURE_MARK[str(e["features"][c])] for c in cols)
        lines.append(
            f"| [{e['name']}](#{e['id']}) | {RINGS[e['ring']]} | {e['category']} | {feats} | {e['verified']} |"
        )
    lines.append("\n" + " · ".join(f"**{k}**: {v}" for k, v in cols.items()) + "\n")

    lines += [
        "## 3. Số liệu registry\n",
        "Major/12 tháng = số lần lên major trong 12 tháng trước ngày snapshot — đo tốc độ đổi API (gói 0.x đổi API "
        "ở bản minor nên ghi kèm `(0.x)`). Sao GitHub chỉ có khi chạy refresh với `GITHUB_TOKEN` (workflow hằng "
        "tháng).\n",
        "| Framework | Gói | Phiên bản | Phát hành | Major/12 tháng | Giấy phép (registry) | Sao GitHub | Cờ |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for e in frameworks:
        version, released, churn, license_ = _metrics(e, snap)
        pkg = packages_of(e)[0][1]
        lines.append(
            f"| {e['name']} | `{pkg}` | {version} | {released} | {churn} | {license_} | {_stars(e, snap)} | "
            f"{'<br>'.join(flags(e, snap)) or '—'} |"
        )

    lines += ["\n## 4. Từng framework\n"]
    for e in frameworks:
        lines += [
            f'<a id="{e["id"]}"></a>\n',
            f"### {e['name']} · {RINGS[e['ring']]}\n",
            f"- **Nhóm:** {data['categories'][e['category']]} · **Ngôn ngữ:** {', '.join(e['lang'])} · "
            f"**Repo:** [{e['repo']}](https://github.com/{e['repo']})",
            f"- **Giấy phép:** {e['license_note']}",
            f"- **Chọn khi:** {e['choose_when']}",
            "- **Mạnh:** " + "; ".join(e["strengths"]),
            "- **Yếu:** " + "; ".join(e["weaknesses"]),
        ]
        if e.get("used_in"):
            lines.append("- **Dùng trong repo:** " + "; ".join(e["used_in"]))
        lines.append(f"- **Review:** {e['reviewed']} · kiểm chứng: {e['verified']}\n")

    lines += [
        "## 5. Lớp hỗ trợ: giao thức, quan sát, eval, chạy bền, bộ nhớ, sandbox\n",
        "| Công cụ | Lớp | Vòng | Gói | Phiên bản | Phát hành | Giấy phép (registry) | Ghi chú |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in supporting:
        version, released, _, license_ = _metrics(s, snap)
        lines.append(
            f"| {s['name']} | {s['layer']} | {RINGS[s['ring']]} | `{packages_of(s)[0][1]}` | {version} | {released} | "
            f"{license_} | {s['note']} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def build(root: Path = REPO_ROOT, check: bool = False) -> int:
    data = load_data(root)
    errors = validate(data)
    if errors:
        print("✗ catalog/agent_landscape.yaml không hợp lệ:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1
    text = render(data, load_snapshot(root))
    path = root / OUT
    if check:
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            print(f"✗ {OUT} đã cũ — chạy `make landscape` rồi commit.", file=sys.stderr)
            return 1
        print(f"✓ {OUT} đã cập nhật.")
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"✓ Đã sinh {OUT} ({len(data['frameworks'])} framework).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aiarch.landscape", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("refresh", help="kéo số liệu PyPI/npm (+ GitHub nếu có GITHUB_TOKEN) rồi sinh lại bảng")
    b = sub.add_parser("build", help="sinh bảng từ YAML + snapshot (không cần mạng)")
    b.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.cmd == "refresh":
        snap = refresh()
        failed = [k for k, v in snap["packages"].items() if v.get("error")]
        print(f"✓ Snapshot {snap['date']}: {len(snap['packages'])} gói, lỗi {len(failed)} {failed or ''}")
        return build()
    return build(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
