import copy
import dataclasses

import pytest

from aiarch import catalog as c


@pytest.fixture(scope="module")
def cat() -> c.Catalog:
    return c.load()


def _with_skills(cat: c.Catalog, skills: list[dict]) -> c.Catalog:
    return dataclasses.replace(cat, skills=skills)


def test_repo_catalog_is_valid(cat):
    assert c.validate(cat) == []


def test_generated_docs_are_up_to_date(cat):
    changed, extra = c._stale(c.REPO_ROOT, c.render(cat))
    assert not changed and not extra, "Chạy `make catalog` rồi commit tài liệu sinh lại"


def test_render_is_deterministic(cat):
    assert c.render(cat) == c.render(cat)


def test_every_group_has_core_skills_and_learning_path(cat):
    for g in cat.groups:
        core = {s["id"] for s in cat.skills if s["used_by"].get(g["id"]) == "core"}
        assert core, g["id"]
        path = c.closure(cat, core)
        position = {sid: i for i, sid in enumerate(path)}
        for sid in path:
            for p in cat.skill_by_id[sid]["prereqs"]:
                assert position[p] < position[sid], f"{p} phải đứng trước {sid}"


def test_tier_rules(cat):
    skill = {"used_by": {g: "core" for g in cat.group_ids}}
    assert c.tier(skill, cat) == "foundation"
    assert c.tier({"used_by": {"G1": "core", "G6": "needed"}}, cat) == "bridge"
    assert c.tier({"used_by": {"G1": "core", "G2": "needed", "G6": "minor"}}, cat) == "family"
    assert c.tier({"used_by": {"G5": "core"}}, cat) == "specific"
    assert c.tier({"used_by": {"G5": "minor"}}, cat) == "supporting"


def test_detects_unknown_prereq_and_cycle(cat):
    skills = copy.deepcopy(cat.skills)
    skills[0]["prereqs"] = ["KHONG-TON-TAI"]
    assert any("tiên quyết không tồn tại" in e for e in c.validate(_with_skills(cat, skills)))

    skills = copy.deepcopy(cat.skills)
    by_id = {s["id"]: s for s in skills}
    by_id["PY-01"]["prereqs"] = ["PY-02"]  # PY-02 đã phụ thuộc PY-01
    assert any("Vòng lặp" in e for e in c.validate(_with_skills(cat, skills)))


def test_detects_duplicate_id_and_bad_relevance(cat):
    skills = copy.deepcopy(cat.skills)
    skills.append(copy.deepcopy(skills[0]))
    skills[1]["used_by"]["G1"] = "rat-quan-trong"
    errors = c.validate(_with_skills(cat, skills))
    assert any("Trùng id kỹ năng" in e for e in errors)
    assert any("mức không hợp lệ" in e for e in errors)


def test_detects_coverage_gap(cat):
    # Hạ mọi kỹ năng OPT xuống "needed" cho G8 → ô Cốt lõi OPT của G8 không còn được phủ.
    skills = copy.deepcopy(cat.skills)
    for s in skills:
        if s["domain"] == "OPT" and s["used_by"].get("G8") == "core":
            s["used_by"]["G8"] = "needed"
    errors = c.validate(_with_skills(cat, skills))
    assert any("Thiếu độ phủ: G8 cần mảng OPT" in e for e in errors)


def test_combinations_reference_existing_skills(cat):
    ids = set(cat.skill_by_id)
    for combo in cat.combinations:
        assert set(combo["skills"]) <= ids
        assert set(combo.get("glue", [])) <= ids
