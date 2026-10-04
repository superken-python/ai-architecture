"""Danh mục kỹ năng: đọc, kiểm tra và sinh tài liệu từ các file YAML trong catalog/.

Cách dùng:
    python -m aiarch.catalog validate        # chỉ kiểm tra
    python -m aiarch.catalog build           # kiểm tra + sinh lại docs/02-skill-map/generated/
    python -m aiarch.catalog build --check   # báo lỗi nếu tài liệu sinh ra đã cũ (dùng trong CI)
"""

from __future__ import annotations

import argparse
import heapq
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
GEN_DIR = Path("docs/02-skill-map/generated")

RELEVANCE = {"core": "Cốt lõi", "needed": "Cần", "minor": "Ít"}
SYMBOL = {"core": "●", "needed": "◐", "minor": "○"}
WEIGHT = {"core": 2, "needed": 1, "minor": 0}
LEVELS = {"basic": "Cơ bản", "intermediate": "Trung cấp", "advanced": "Nâng cao"}
TIERS = {
    "foundation": ("Nền tảng chung", "Cốt lõi/Cần ở cả 8 nhóm — học một lần, dùng mọi nơi."),
    "bridge": (
        "Cầu nối liên họ",
        "Cốt lõi/Cần ở cả hai họ bài toán nhưng chưa đủ 8 nhóm — giúp chuyển qua lại giữa ML cổ điển và GenAI.",
    ),
    "family": ("Dùng chung trong họ", "Cốt lõi/Cần ở ≥ 2 nhóm của cùng một họ."),
    "specific": ("Chuyên biệt", "Cốt lõi/Cần ở đúng 1 nhóm — học khi đi sâu nhóm đó."),
    "supporting": ("Bổ trợ", "Chỉ ở mức Ít — nâng hiệu quả làm việc, không chặn nhóm nào."),
}
SKILL_FIELDS = ("id", "name", "domain", "summary", "levels", "used_by", "prereqs", "tools", "done_when")
HEADER = "<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->\n\n"


@dataclass(frozen=True)
class Catalog:
    blocks: dict[str, str]
    families: list[dict[str, Any]]
    groups: list[dict[str, Any]]
    domains: list[dict[str, Any]]
    skills: list[dict[str, Any]]
    combinations: list[dict[str, Any]]

    @property
    def group_ids(self) -> list[str]:
        return [g["id"] for g in self.groups]

    @property
    def group_by_id(self) -> dict[str, dict[str, Any]]:
        return {g["id"]: g for g in self.groups}

    @property
    def skill_by_id(self) -> dict[str, dict[str, Any]]:
        return {s["id"]: s for s in self.skills}

    @property
    def domain_by_code(self) -> dict[str, dict[str, Any]]:
        return {d["code"]: d for d in self.domains}


def load(root: Path = REPO_ROOT) -> Catalog:
    def read(name: str) -> dict[str, Any]:
        with open(root / "catalog" / name, encoding="utf-8") as f:
            return yaml.safe_load(f)

    problems = read("problems.yaml")
    skills = read("skills.yaml")
    combos = read("combinations.yaml")
    return Catalog(
        blocks=problems["blocks"],
        families=problems["families"],
        groups=problems["groups"],
        domains=skills["domains"],
        skills=skills["skills"],
        combinations=combos["combinations"],
    )


# ───────────────────────────── phân tích ─────────────────────────────


def strong_groups(skill: dict[str, Any]) -> set[str]:
    """Các nhóm mà kỹ năng ở mức Cốt lõi hoặc Cần."""
    return {g for g, r in skill["used_by"].items() if r in ("core", "needed")}


def tier(skill: dict[str, Any], cat: Catalog) -> str:
    strong = strong_groups(skill)
    if len(strong) == len(cat.groups):
        return "foundation"
    families_hit = sum(1 for f in cat.families if strong & set(f["groups"]))
    if families_hit >= 2:
        return "bridge"
    if len(strong) >= 2:
        return "family"
    if len(strong) == 1:
        return "specific"
    return "supporting"


def leverage(skill: dict[str, Any]) -> int:
    """Điểm đòn bẩy: Cốt lõi = 2, Cần = 1 cho mỗi nhóm."""
    return sum(WEIGHT[r] for r in skill["used_by"].values())


def topo_order(cat: Catalog) -> list[str]:
    """Thứ tự học: tiên quyết trước, giữ thứ tự trong file khi không ràng buộc."""
    index = {s["id"]: i for i, s in enumerate(cat.skills)}
    indegree = {s["id"]: len(s["prereqs"]) for s in cat.skills}
    children: dict[str, list[str]] = {s["id"]: [] for s in cat.skills}
    for s in cat.skills:
        for p in s["prereqs"]:
            children[p].append(s["id"])
    heap = [(index[sid], sid) for sid, d in indegree.items() if d == 0]
    heapq.heapify(heap)
    order: list[str] = []
    while heap:
        _, sid = heapq.heappop(heap)
        order.append(sid)
        for child in children[sid]:
            indegree[child] -= 1
            if indegree[child] == 0:
                heapq.heappush(heap, (index[child], child))
    return order


def depths(cat: Catalog) -> dict[str, int]:
    by_id = cat.skill_by_id
    result: dict[str, int] = {}
    for sid in topo_order(cat):
        prereqs = by_id[sid]["prereqs"]
        result[sid] = 1 + max(result[p] for p in prereqs) if prereqs else 0
    return result


def closure(cat: Catalog, skill_ids: set[str]) -> list[str]:
    """Các kỹ năng đã cho + toàn bộ tiên quyết, theo thứ tự học."""
    by_id = cat.skill_by_id
    needed = set()
    stack = list(skill_ids)
    while stack:
        sid = stack.pop()
        if sid in needed:
            continue
        needed.add(sid)
        stack.extend(by_id[sid]["prereqs"])
    return [sid for sid in topo_order(cat) if sid in needed]


def unlocks(cat: Catalog) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {s["id"]: [] for s in cat.skills}
    for s in cat.skills:
        for p in s["prereqs"]:
            result[p].append(s["id"])
    return result


# ───────────────────────────── kiểm tra ─────────────────────────────


def _duplicates(ids: list[str]) -> set[str]:
    seen: set[str] = set()
    return {i for i in ids if i in seen or seen.add(i)}


def validate(cat: Catalog) -> list[str]:
    errors: list[str] = []
    group_ids = set(cat.group_ids)
    domain_codes = {d["code"] for d in cat.domains}
    skill_ids = {s.get("id") for s in cat.skills}

    for kind, ids in (
        ("nhóm", cat.group_ids),
        ("mảng", [d["code"] for d in cat.domains]),
        ("kỹ năng", [s.get("id") for s in cat.skills]),
        ("tổ hợp", [c["id"] for c in cat.combinations]),
    ):
        for dup in sorted(_duplicates(ids)):
            errors.append(f"Trùng id {kind}: {dup}")

    membership = [g for f in cat.families for g in f["groups"]]
    for g in sorted(set(membership) - group_ids):
        errors.append(f"Họ bài toán chứa nhóm không tồn tại '{g}'")
    for g in sorted(_duplicates(membership)):
        errors.append(f"Nhóm {g} thuộc nhiều hơn một họ")
    for g in sorted(group_ids - set(membership)):
        errors.append(f"Nhóm {g} chưa thuộc họ nào")

    for g in cat.groups:
        if g.get("block") not in cat.blocks:
            errors.append(f"{g['id']}: khối '{g.get('block')}' không tồn tại")
        for code, rel in g.get("skill_areas", {}).items():
            if code not in domain_codes:
                errors.append(f"{g['id']}: skill_areas dùng mảng không tồn tại '{code}'")
            if rel not in RELEVANCE:
                errors.append(f"{g['id']}: skill_areas.{code} có mức không hợp lệ '{rel}'")

    for s in cat.skills:
        sid = s.get("id", "<thiếu id>")
        missing = [f for f in SKILL_FIELDS if f not in s]
        if missing:
            errors.append(f"{sid}: thiếu trường {', '.join(missing)}")
            continue
        if s["domain"] not in domain_codes:
            errors.append(f"{sid}: mảng '{s['domain']}' không tồn tại")
        elif not sid.startswith(f"{s['domain']}-"):
            errors.append(f"{sid}: id phải bắt đầu bằng mã mảng '{s['domain']}-'")
        if set(s["levels"]) != set(LEVELS) or not all(isinstance(v, str) and v.strip() for v in s["levels"].values()):
            errors.append(f"{sid}: levels phải có đủ basic/intermediate/advanced, không rỗng")
        if not s["used_by"]:
            errors.append(f"{sid}: used_by rỗng — kỹ năng không phục vụ nhóm nào")
        for g, rel in s["used_by"].items():
            if g not in group_ids:
                errors.append(f"{sid}: used_by có nhóm không tồn tại '{g}'")
            if rel not in RELEVANCE:
                errors.append(f"{sid}: used_by.{g} có mức không hợp lệ '{rel}'")
        for p in s["prereqs"]:
            if p == sid:
                errors.append(f"{sid}: tự làm tiên quyết của chính mình")
            elif p not in skill_ids:
                errors.append(f"{sid}: tiên quyết không tồn tại '{p}'")

    if errors:
        return errors

    order = topo_order(cat)
    if len(order) != len(cat.skills):
        stuck = sorted(skill_ids - set(order))
        errors.append(f"Vòng lặp tiên quyết giữa: {', '.join(stuck)}")

    # Độ phủ: mọi ô "Cốt lõi" của ma trận giai đoạn 1 phải có kỹ năng cốt lõi tương ứng.
    for g in cat.groups:
        for code, rel in g["skill_areas"].items():
            if rel != "core":
                continue
            if not any(s["domain"] == code and s["used_by"].get(g["id"]) == "core" for s in cat.skills):
                errors.append(
                    f"Thiếu độ phủ: {g['id']} cần mảng {code} ở mức Cốt lõi "
                    "nhưng chưa có kỹ năng nào của mảng này là core cho nhóm đó"
                )
        if not any(s["used_by"].get(g["id"]) == "core" for s in cat.skills):
            errors.append(f"{g['id']}: không có kỹ năng cốt lõi nào")

    for c in cat.combinations:
        if len(c["groups"]) < 2:
            errors.append(f"{c['id']}: tổ hợp phải ghép ít nhất 2 nhóm")
        for g in c["groups"]:
            if g not in group_ids:
                errors.append(f"{c['id']}: nhóm không tồn tại '{g}'")
        for sid in [*c["skills"], *c.get("glue", [])]:
            if sid not in skill_ids:
                errors.append(f"{c['id']}: kỹ năng không tồn tại '{sid}'")
    return errors


# ───────────────────────────── sinh tài liệu ─────────────────────────────


def cell(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def anchor(sid: str) -> str:
    return sid.lower()


def domain_file(code: str) -> str:
    return f"mang/{code.lower()}.md"


def group_file(group: dict[str, Any]) -> str:
    return f"nhom/{group['slug']}.md"


def group_label(group: dict[str, Any]) -> str:
    return f"{group['id'][1:]}·{group['short']}"


class Renderer:
    def __init__(self, cat: Catalog) -> None:
        self.cat = cat
        self.n = len(cat.groups)
        self.by_id = cat.skill_by_id
        self.tier = {s["id"]: tier(s, cat) for s in cat.skills}
        self.unlocks = unlocks(cat)
        self.depth = depths(cat)

    # liên kết tới thẻ kỹ năng, tính từ thư mục `base` bên trong generated/
    def link(self, sid: str, base: str = "") -> str:
        s = self.by_id[sid]
        prefix = "../" if base else ""
        return f"[{sid}]({prefix}{domain_file(s['domain'])}#{anchor(sid)})"

    def link_named(self, sid: str, base: str = "") -> str:
        return f"{self.link(sid, base)} {self.by_id[sid]['name']}"

    def tier_name(self, sid: str) -> str:
        return TIERS[self.tier[sid]][0]

    def render(self) -> dict[str, str]:
        files = {
            "README.md": self.index(),
            "ma-tran-ky-nang.md": self.matrix(),
            "thu-tu-hoc.md": self.learning_order(),
            "to-hop-ky-nang.md": self.combinations(),
            "tu-danh-gia.md": self.self_assessment(),
        }
        for d in self.cat.domains:
            files[domain_file(d["code"])] = self.domain_page(d)
        for g in self.cat.groups:
            files[group_file(g)] = self.group_page(g)
        return {str(GEN_DIR / k): HEADER + v.rstrip() + "\n" for k, v in files.items()}

    # ── README của thư mục generated ──
    def index(self) -> str:
        counts = {t: sum(1 for v in self.tier.values() if v == t) for t in TIERS}
        lines = [
            "# Bản đồ kỹ năng — phần sinh tự động",
            "",
            f"Danh mục hiện có **{len(self.cat.skills)} kỹ năng** trong **{len(self.cat.domains)} mảng**, "
            f"phủ **{self.n} nhóm bài toán** và **{len(self.cat.combinations)} tổ hợp** dự án thực tế.",
            "",
            "| Tầng | Số kỹ năng | Ý nghĩa |",
            "|---|---:|---|",
        ]
        for t, (name, desc) in TIERS.items():
            lines.append(f"| {name} | {counts[t]} | {desc} |")
        lines += ["", "## Hai họ bài toán", ""]
        groups = self.cat.group_by_id
        for f in self.cat.families:
            members = ", ".join(f"Nhóm {g[1:]} {groups[g]['short']}" for g in f["groups"])
            lines.append(f"- **{f['name']}:** {members}")
        lines += ["", "## Kỹ năng theo tầng", ""]
        for t, (name, _) in TIERS.items():
            ids = [s["id"] for s in self.cat.skills if self.tier[s["id"]] == t]
            lines.append(f"- **{name}:** " + (", ".join(self.link(sid) for sid in ids) or "—"))
        lines += [
            "",
            "## Các trang",
            "",
            "- [Ma trận kỹ năng × nhóm bài toán](ma-tran-ky-nang.md) — kỹ năng nào dùng cho nhóm nào, "
            "mức chia sẻ giữa các nhóm, đối chiếu với giai đoạn 1.",
            "- [Thứ tự học & kỹ năng đòn bẩy](thu-tu-hoc.md) — học gì trước, kỹ năng nào dùng được nhiều nhất.",
            '- [Tổ hợp kỹ năng](to-hop-ky-nang.md) — dự án ghép nhiều nhóm và kỹ năng "keo" ở điểm nối.',
            "- [Bảng tự đánh giá](tu-danh-gia.md) — đánh dấu từng mức của từng kỹ năng.",
            "",
            "### Thẻ kỹ năng theo mảng",
            "",
        ]
        for d in self.cat.domains:
            n = sum(1 for s in self.cat.skills if s["domain"] == d["code"])
            lines.append(f"- [{d['code']} · {d['name']}]({domain_file(d['code'])}) — {n} kỹ năng")
        lines += ["", "### Lộ trình theo nhóm bài toán", ""]
        for g in self.cat.groups:
            lines.append(f"- [Nhóm {g['id'][1:]} · {g['name']}]({group_file(g)})")
        return "\n".join(lines)

    # ── Ma trận ──
    def matrix(self) -> str:
        groups = self.cat.groups
        head = "| Kỹ năng | Tầng | " + " | ".join(group_label(g) for g in groups) + " |"
        sep = "|---|---|" + "|".join(":-:" for _ in groups) + "|"
        lines = [
            "# Ma trận kỹ năng × nhóm bài toán",
            "",
            "Chú giải: ● Cốt lõi · ◐ Cần · ○ Ít · ô trống = không liên quan. "
            "Tầng được tính tự động từ mức sử dụng (xem [README](README.md)).",
            "",
        ]
        for d in self.cat.domains:
            lines += [f"## {d['code']} · {d['name']}", "", d["description"], "", head, sep]
            for s in self.cat.skills:
                if s["domain"] != d["code"]:
                    continue
                marks = " | ".join(SYMBOL.get(s["used_by"].get(g["id"], ""), "") for g in groups)
                lines.append(f"| {self.link_named(s['id'])} | {self.tier_name(s['id'])} | {marks} |")
            lines.append("")

        lines += [
            '<a id="chia-se"></a>',
            "",
            "## Mức chia sẻ kỹ năng giữa các nhóm",
            "",
            "Số kỹ năng ở mức Cốt lõi/Cần cho **cả hai** nhóm. Đường chéo = tổng số kỹ năng "
            "Cốt lõi/Cần của nhóm đó. Ô càng lớn, càng tận dụng được kỹ năng khi chuyển giữa hai nhóm.",
            "",
            "| | " + " | ".join(group_label(g) for g in groups) + " |",
            "|---|" + "|".join("--:" for _ in groups) + "|",
        ]
        strong = {g["id"]: {s["id"] for s in self.cat.skills if g["id"] in strong_groups(s)} for g in groups}
        for a in groups:
            row = [str(len(strong[a["id"]] & strong[b["id"]])) for b in groups]
            lines.append(f"| **{group_label(a)}** | " + " | ".join(row) + " |")

        family_of = {g: f["id"] for f in self.cat.families for g in f["groups"]}
        buckets: dict[str, list[int]] = {}
        for i, a in enumerate(self.cat.group_ids):
            for b in self.cat.group_ids[i + 1 :]:
                key = family_of[a] if family_of[a] == family_of[b] else "cross"
                buckets.setdefault(key, []).append(len(strong[a] & strong[b]))
        n_foundation = sum(1 for t in self.tier.values() if t == "foundation")
        lines += [
            "",
            f"Trung bình số kỹ năng chung của một cặp nhóm (trong đó {n_foundation} kỹ năng nền tảng chung "
            "luôn có mặt ở mọi cặp):",
            "",
            "| Cặp nhóm | Số cặp | Trung bình | Thấp nhất – cao nhất | Ngoài nền tảng chung |",
            "|---|--:|--:|--:|--:|",
        ]
        names = {f["id"]: f"Cùng họ: {f['name']}" for f in self.cat.families} | {"cross": "Khác họ"}
        for key in [*(f["id"] for f in self.cat.families), "cross"]:
            values = buckets.get(key, [])
            if not values:
                continue
            avg = sum(values) / len(values)
            lines.append(
                f"| {names[key]} | {len(values)} | {avg:.1f} | {min(values)} – {max(values)} "
                f"| {avg - n_foundation:.1f} |"
            )

        lines += [
            "",
            '<a id="doi-chieu-giai-doan-1"></a>',
            "",
            "## Đối chiếu với ma trận giai đoạn 1 (theo mảng)",
            "",
            "Mỗi ô: mức cao nhất trong các kỹ năng của mảng / mức ở ma trận giai đoạn 1. "
            "Bộ kiểm tra bảo đảm mọi ô Cốt lõi của giai đoạn 1 đều có ít nhất một kỹ năng Cốt lõi.",
            "",
            "| Mảng | " + " | ".join(group_label(g) for g in groups) + " |",
            "|---|" + "|".join(":-:" for _ in groups) + "|",
        ]
        rank = {"": 0, "minor": 1, "needed": 2, "core": 3}
        for d in self.cat.domains:
            row = []
            for g in groups:
                rels = [s["used_by"].get(g["id"], "") for s in self.cat.skills if s["domain"] == d["code"]]
                best = max(rels, key=rank.__getitem__, default="")
                phase1 = g["skill_areas"].get(d["code"])
                row.append(f"{SYMBOL.get(best, '·')} / {SYMBOL[phase1] if phase1 else '—'}")
            lines.append(f"| {d['code']} · {d['name']} | " + " | ".join(row) + " |")
        lines += ["", "Ký hiệu “—”: mảng mới bổ sung ở giai đoạn 2, không có trong ma trận giai đoạn 1."]
        return "\n".join(lines)

    # ── Thứ tự học ──
    def learning_order(self) -> str:
        order = topo_order(self.cat)
        position = {sid: i for i, sid in enumerate(order)}
        ranked = sorted(self.cat.skills, key=lambda s: (-leverage(s), position[s["id"]]))
        lines = [
            "# Thứ tự học & kỹ năng đòn bẩy",
            "",
            "## Kỹ năng đòn bẩy cao nhất",
            "",
            "Điểm đòn bẩy = Σ (Cốt lõi = 2, Cần = 1) trên 8 nhóm. "
            "Học trước các kỹ năng điểm cao: một lần học, dùng cho nhiều bài toán nhất.",
            "",
            "| # | Kỹ năng | Tầng | Điểm | Cốt lõi ở | Cần ở |",
            "|--:|---|---|--:|---|---|",
        ]
        for i, s in enumerate(ranked[:20], 1):
            core = ", ".join(g[1:] for g, r in s["used_by"].items() if r == "core") or "—"
            needed = ", ".join(g[1:] for g, r in s["used_by"].items() if r == "needed") or "—"
            lines.append(
                f"| {i} | {self.link_named(s['id'])} | {self.tier_name(s['id'])} | {leverage(s)} | {core} | {needed} |"
            )

        lines += [
            "",
            "## Thứ tự học theo vòng tiên quyết",
            "",
            "Vòng *k* = cần học xong ít nhất một chuỗi *k* kỹ năng tiên quyết trước. "
            "Trong cùng một vòng có thể học song song.",
            "",
        ]
        max_depth = max(self.depth.values())
        for k in range(max_depth + 1):
            title = "không cần tiên quyết" if k == 0 else f"sau {k} bước tiên quyết"
            lines += [f"### Vòng {k} — {title}", ""]
            for sid in order:
                if self.depth[sid] != k:
                    continue
                s = self.by_id[sid]
                pre = ", ".join(s["prereqs"]) if s["prereqs"] else "—"
                lines.append(f"- {self.link_named(sid)} · *{self.tier_name(sid)}* · tiên quyết: {pre}")
            lines.append("")

        lines += ["## Lộ trình riêng cho từng nhóm", ""]
        for g in self.cat.groups:
            lines.append(f"- [Nhóm {g['id'][1:]} · {g['name']}]({group_file(g)})")
        return "\n".join(lines)

    # ── Trang mảng (thẻ kỹ năng) ──
    def domain_page(self, d: dict[str, Any]) -> str:
        skills = [s for s in self.cat.skills if s["domain"] == d["code"]]
        lines = [
            f"# {d['code']} · {d['name']}",
            "",
            d["description"],
            "",
            "| Kỹ năng | Tầng | Tóm tắt |",
            "|---|---|---|",
        ]
        for s in skills:
            lines.append(
                f"| [{s['id']}](#{anchor(s['id'])}) {s['name']} | {self.tier_name(s['id'])} | {cell(s['summary'])} |"
            )
        lines.append("")
        for s in skills:
            lines += self.card(s)
        return "\n".join(lines)

    def card(self, s: dict[str, Any]) -> list[str]:
        sid = s["id"]
        groups = self.cat.group_by_id
        uses = " · ".join(
            f"{SYMBOL[r]} {RELEVANCE[r]}: Nhóm {g[1:]} {groups[g]['short']}"
            for r in ("core", "needed", "minor")
            for g in self.cat.group_ids
            if s["used_by"].get(g) == r
        )
        lines = [
            f'<a id="{anchor(sid)}"></a>',
            "",
            f"### {sid} · {s['name']}",
            "",
            f"> {s['summary']}",
            "",
            f"**Tầng:** {self.tier_name(sid)} · **Điểm đòn bẩy:** {leverage(s)}  ",
            f"**Dùng cho:** {uses}",
            "",
            "| Mức | Làm được |",
            "|---|---|",
        ]
        for key, label in LEVELS.items():
            lines.append(f"| {label} | {cell(s['levels'][key])} |")
        pre = ", ".join(self.link_named(p, "mang") for p in s["prereqs"]) or "—"
        nxt = ", ".join(self.link(p, "mang") for p in self.unlocks[sid]) or "—"
        lines += [
            "",
            f"- **Tiên quyết:** {pre}",
            f"- **Mở khóa:** {nxt}",
            f"- **Công cụ:** {', '.join(s['tools'])}",
            f"- **Đạt khi:** {s['done_when']}",
        ]
        if s.get("efficiency_note"):
            lines.append(f"- **Token & độ chính xác:** {s['efficiency_note']}")
        lines.append("")
        return lines

    # ── Trang nhóm bài toán ──
    def group_page(self, g: dict[str, Any]) -> str:
        gid = g["id"]
        flow = g["flow"]
        lines = [
            f"# Nhóm {gid[1:]} · {g['name']}",
            "",
            f"> “{g['question']}” — Khối {g['block']} · {self.cat.blocks[g['block']]}",
            "",
            f"**Ví dụ trong doanh nghiệp:** {', '.join(g['examples'])}.",
            "",
            "| Đầu vào | Kỹ thuật chính | Đầu ra | Quyết định kinh doanh |",
            "|---|---|---|---|",
            "| " + " | ".join(cell(flow[k]) for k in ("input", "technique", "output", "decision")) + " |",
            "",
            "## Mức năng lực của nhóm (từ bản đồ bài toán)",
            "",
            "| Mức | Nội dung |",
            "|---|---|",
        ]
        for key, label in LEVELS.items():
            lines.append(f"| {label} | {cell(g['levels'][key])} |")
        lines += [
            "",
            f"- **Metric chính:** {g['metrics']}",
            f"- **Công cụ:** {', '.join(g['tools'])}",
            f"- **Bẫy thường gặp:** {g['pitfalls']}",
            f"- **Dự án luyện tập:** {g['practice_project']}",
        ]
        if g.get("principle"):
            lines.append(f"- **Nguyên tắc:** {g['principle']}")

        lines += ["", "## Kỹ năng cần cho nhóm này", ""]
        for rel in ("core", "needed", "minor"):
            skills = [s for s in self.cat.skills if s["used_by"].get(gid) == rel]
            if not skills:
                continue
            lines += [
                f"### {SYMBOL[rel]} {RELEVANCE[rel]} ({len(skills)})",
                "",
                "| Kỹ năng | Tầng | Dùng chung với nhóm |",
                "|---|---|---|",
            ]
            for s in skills:
                others = [o[1:] for o, r in s["used_by"].items() if o != gid and r in ("core", "needed")]
                lines.append(
                    f"| {self.link_named(s['id'], 'nhom')} | {self.tier_name(s['id'])} | {', '.join(others) or '—'} |"
                )
            lines.append("")

        targets = {s["id"] for s in self.cat.skills if s["used_by"].get(gid) in ("core", "needed")}
        path = closure(self.cat, targets)
        lines += [
            "## Lộ trình học cho nhóm này",
            "",
            "Thứ tự đã tôn trọng tiên quyết. Kỹ năng đánh dấu *(tiên quyết)* không trực tiếp thuộc nhóm "
            "nhưng cần để học các kỹ năng phía sau. Gợi ý: đạt **Cơ bản** cho cả danh sách trước, "
            "rồi mới lên **Trung cấp** ở các kỹ năng Cốt lõi.",
            "",
        ]
        for i, sid in enumerate(path, 1):
            rel = self.by_id[sid]["used_by"].get(gid)
            mark = f"{SYMBOL[rel]} {RELEVANCE[rel]}" if rel in ("core", "needed") else "*(tiên quyết)*"
            lines.append(f"{i}. {self.link_named(sid, 'nhom')} — {mark}")

        combos = [c for c in self.cat.combinations if gid in c["groups"]]
        if combos:
            lines += ["", "## Tổ hợp có nhóm này", ""]
            for c in combos:
                lines.append(f"- [{c['id']} · {c['name']}](../to-hop-ky-nang.md#{anchor(c['id'])}) — {c['flow']}")
        return "\n".join(lines)

    # ── Tổ hợp ──
    def combinations(self) -> str:
        groups = self.cat.group_by_id
        lines = [
            "# Tổ hợp kỹ năng — dự án ghép nhiều nhóm",
            "",
            "Dự án thật hiếm khi thuộc một nhóm. Mỗi tổ hợp dưới đây nêu luồng giữa các nhóm, "
            "kỹ năng cần, kỹ năng **keo** (🔗) ở điểm nối, bẫy khi ghép và metric đo từ đầu đến cuối. "
            "Nguyên tắc ghép: xem [02-ky-nang-ket-hop.md](../02-ky-nang-ket-hop.md).",
            "",
            "| Tổ hợp | Nhóm |",
            "|---|---|",
        ]
        for c in self.cat.combinations:
            names = " → ".join(f"{g[1:]}·{groups[g]['short']}" for g in c["groups"])
            lines.append(f"| [{c['id']} · {c['name']}](#{anchor(c['id'])}) | {names} |")
        lines.append("")
        for c in self.cat.combinations:
            glue = set(c.get("glue", []))
            ordered = list(dict.fromkeys([*c["skills"], *c.get("glue", [])]))
            lines += [
                f'<a id="{anchor(c["id"])}"></a>',
                "",
                f"## {c['id']} · {c['name']}",
                "",
                f"**Luồng:** {c['flow']}  ",
                f"**Ví dụ:** {', '.join(c['examples'])}",
                "",
                "| Kỹ năng | Tầng | Vai trò |",
                "|---|---|---|",
            ]
            for sid in ordered:
                role = "🔗 keo ở điểm nối" if sid in glue else ""
                lines.append(f"| {self.link_named(sid)} | {self.tier_name(sid)} | {role} |")
            lines += ["", "**Bẫy khi ghép:**", ""]
            lines += [f"- {p}" for p in c["pitfalls"]]
            lines += ["", f"**Metric end-to-end:** {c['end_to_end_metric']}", ""]
        return "\n".join(lines)

    # ── Tự đánh giá ──
    def self_assessment(self) -> str:
        lines = [
            "# Bảng tự đánh giá kỹ năng",
            "",
            "Sao chép file này sang ghi chú cá nhân (hoặc một issue GitHub) rồi đánh dấu. "
            "Chỉ đánh dấu một mức khi bạn tự làm được nội dung mức đó trên dữ liệu thật và giải thích "
            "được kết quả cho người ngoài ngành. Tiêu chí “Đạt khi” nằm trong thẻ kỹ năng.",
            "",
        ]
        for d in self.cat.domains:
            lines += [f"## {d['code']} · {d['name']}", ""]
            for s in self.cat.skills:
                if s["domain"] != d["code"]:
                    continue
                lines.append(f"- {self.link_named(s['id'])}")
                lines += [f"  - [ ] {label}" for label in LEVELS.values()]
            lines.append("")
        return "\n".join(lines)


def render(cat: Catalog) -> dict[str, str]:
    return Renderer(cat).render()


# ───────────────────────────── CLI ─────────────────────────────


def _stale(root: Path, outputs: dict[str, str]) -> tuple[list[str], list[str]]:
    changed = [
        p
        for p, content in outputs.items()
        if not (root / p).exists() or (root / p).read_text(encoding="utf-8") != content
    ]
    existing = (
        {str(p.relative_to(root)) for p in (root / GEN_DIR).rglob("*.md")} if (root / GEN_DIR).exists() else set()
    )
    extra = sorted(existing - set(outputs))
    return changed, extra


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aiarch.catalog", description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["validate", "build"])
    parser.add_argument("--check", action="store_true", help="build: chỉ kiểm tra tài liệu đã cập nhật chưa")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="thư mục gốc repo")
    args = parser.parse_args(argv)

    cat = load(args.root)
    errors = validate(cat)
    if errors:
        print(f"✗ Catalog có {len(errors)} lỗi:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"✓ Catalog hợp lệ: {len(cat.groups)} nhóm, {len(cat.skills)} kỹ năng, {len(cat.combinations)} tổ hợp.")
    if args.command == "validate":
        return 0

    outputs = render(cat)
    changed, extra = _stale(args.root, outputs)
    if args.check:
        if changed or extra:
            print("✗ Tài liệu sinh tự động đã cũ — chạy `make catalog` rồi commit:", file=sys.stderr)
            for p in [*changed, *extra]:
                print(f"  - {p}", file=sys.stderr)
            return 1
        print("✓ Tài liệu sinh tự động đã cập nhật.")
        return 0

    for p in extra:
        (args.root / p).unlink()
    for p, content in outputs.items():
        target = args.root / p
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    print(f"✓ Đã sinh {len(outputs)} file vào {GEN_DIR}/ ({len(changed)} thay đổi, {len(extra)} file cũ bị xóa).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
