"""Bộ đo dịch eval/mt_eval.py: chrF và bản dịch tham chiếu của golden_1 (docs 09 §5.1)."""

import os
import sys

import pytest

EVAL = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../eval"))
sys.path.insert(0, EVAL)
mt_eval = pytest.importorskip("mt_eval")


def test_chrf_identical_disjoint_and_partial():
    assert mt_eval.chrf_score(mt_eval.chrf_stats("Thầy đến muộn rồi.", "Thầy đến muộn rồi.")) == pytest.approx(100)
    assert mt_eval.chrf_score(mt_eval.chrf_stats("abc", "xyz")) == 0
    partial = mt_eval.chrf_score(mt_eval.chrf_stats("Thầy đến muộn.", "Thầy đến muộn rồi đấy."))
    assert 30 < partial < 100
    # β = 2: thiếu chữ bị trừ nặng hơn thừa chữ
    short = mt_eval.chrf_score(mt_eval.chrf_stats("Thầy", "Thầy đến"))
    long = mt_eval.chrf_score(mt_eval.chrf_stats("Thầy đến muộn", "Thầy đến"))
    assert long > short


def test_corpus_chrf_pools_counts():
    hyps, refs = ["Thầy đến muộn.", "abc"], ["Thầy đến muộn.", "xyz"]
    assert 0 < mt_eval.corpus_chrf(hyps, refs) < 100


def test_golden_1_references_are_complete():
    refs = mt_eval.load_references(os.path.join(EVAL, "golden_1"))
    assert len(refs) >= 141
    assert all(r["ja"].strip() and r["vi"].strip() for r in refs)
    assert not any(mt_eval.JA_REGEX.search(r["vi"]) for r in refs)
    assert [r["id"] for r in refs] == list(range(1, len(refs) + 1))


def test_hosted_payload_fits_api_limits():
    # API lưu trữ nhận tối đa 4 chuỗi dừng và không nhận top_p (docs 09 §5.6)
    from rvt_ai.engines.mt_llama import hosted_payload

    local = {"messages": [], "stream": True, "max_tokens": 64, "temperature": 0.1, "top_p": 0.7, "stop": ["\n"] * 25}
    out = hosted_payload(local, "some-model")
    assert out["model"] == "some-model" and out["stop"] == ["\n"]
    assert "top_p" not in out and "temperature" not in out and "max_tokens" not in out
    assert out["max_completion_tokens"] == 1024
    assert "model" not in hosted_payload(local, "")


def test_compare_script_rejects_different_sentence_sets(tmp_path):
    import json
    import subprocess
    import sys

    script = os.path.join(EVAL, "mt_compare.py")
    row = {"id": 1, "speaker": "x", "ja": "a", "vi": "b", "mt": "b", "chrf": 100.0}
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    summary = {"chrf_corpus": 1, "chrf_sentence_mean": 1, "with_japanese_left": 0, "retries": 0, "latency_p95_s": 0}
    a.write_text(json.dumps({**summary, "rows": [row]}), encoding="utf-8")
    b.write_text(json.dumps({**summary, "rows": [{**row, "id": 2}]}), encoding="utf-8")
    result = subprocess.run([sys.executable, script, str(a), str(b)], capture_output=True, text=True)
    assert result.returncode != 0 and "không cùng bộ câu" in result.stderr
