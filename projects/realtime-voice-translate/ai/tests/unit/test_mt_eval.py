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
