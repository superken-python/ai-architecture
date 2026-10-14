from aiarch import landscape as lc


def test_landscape_data_is_valid():
    assert lc.validate(lc.load_data()) == []


def test_generated_page_is_up_to_date():
    text = lc.render(lc.load_data(), lc.load_snapshot())
    assert (lc.REPO_ROOT / lc.OUT).read_text(encoding="utf-8") == text, "Chạy `make landscape` rồi commit"


def test_majors_skip_pre_releases():
    versions = {"1.0.0a1": "2025-01-01", "1.0.0": "2025-02-01", "1.2.0": "2025-03-01", "2.0.0rc1": "2025-04-01",
                "2.0.0": "2025-05-01", "3.0.0-beta.1": "2025-06-01"}  # fmt: skip
    assert lc._majors(versions) == {"1": "2025-02-01", "2": "2025-05-01"}


def test_flags_stale_release_new_major_and_old_review():
    entry = {"id": "x", "packages": {"pypi": ["x"]}, "reviewed": "2026-01-01", "repo": "o/x"}
    snap = {
        "date": "2026-10-01",
        "packages": {
            "pypi:x": {"version": "3.0.0", "released": "2026-01-15", "majors": {"2": "2025-01-01", "3": "2026-01-15"}}
        },
        "repos": {"o/x": {"archived": True}},
    }
    got = lc.flags(entry, snap)
    assert any("không phát hành 259 ngày" in f for f in got)
    assert any("lên major 3" in f for f in got)
    assert any("archive" in f for f in got) and any("chưa review 273 ngày" in f for f in got)
    assert lc.flags(entry, {"date": None, "packages": {}}) == []
