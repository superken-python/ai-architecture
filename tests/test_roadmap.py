import copy
import dataclasses

import pytest

from aiarch import catalog as c


@pytest.fixture(scope="module")
def cat() -> c.Catalog:
    return c.load()


def _with_roadmap(cat: c.Catalog, roadmap: dict) -> c.Catalog:
    return dataclasses.replace(cat, roadmap=roadmap)


def _step(rm: dict, step_id: str) -> dict:
    return next(s for st in rm["stages"] for s in st.get("steps", []) if s["id"] == step_id)


def test_roadmap_is_valid_and_covers_every_skill(cat):
    assert c.validate_roadmap(cat) == []
    placements = c.roadmap_placements(cat)
    assert all(placements[s["id"]] for s in cat.skills)


def test_detects_prerequisite_learned_too_late(cat):
    rm = copy.deepcopy(cat.roadmap)
    # ML-01 cần DATA-02, STAT-01 — đưa nó lên bước đầu tiên là "nhảy cóc"
    _step(rm, "A1")["skills"].append({"id": "ML-01", "level": "basic"})
    errors = c.validate(_with_roadmap(cat, rm))
    assert any("A1: ML-01 cần học" in e for e in errors)


def test_detects_level_going_down(cat):
    rm = copy.deepcopy(cat.roadmap)
    _step(rm, "A8")["skills"].append({"id": "ML-02", "level": "basic"})  # A5 đã đặt Trung cấp
    errors = c.validate(_with_roadmap(cat, rm))
    assert any("mức mục tiêu của ML-02 thấp hơn" in e for e in errors)


def test_detects_uncovered_skill(cat):
    rm = copy.deepcopy(cat.roadmap)
    rm["ongoing"] = [r for r in rm["ongoing"] if r["id"] != "EFF-08"]
    errors = c.validate(_with_roadmap(cat, rm))
    assert any("chưa phủ" in e and "EFF-08" in e for e in errors)


def test_detects_unquoted_comma_in_flow_mapping(cat):
    import yaml

    rm = copy.deepcopy(cat.roadmap)
    rm["t_bar"] = yaml.safe_load("- {group: G2, skills: [ML-06], note: Seasonal naive, ETS}")
    errors = c.validate(_with_roadmap(cat, rm))
    assert any("trường lạ" in e and "ngoặc kép" in e for e in errors)
