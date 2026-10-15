"""WER, CER cho tiếng Việt, tiếng Anh trong bộ đo (docs 10 §10.2)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../eval")))
wer_mod = pytest.importorskip("wer")


def test_normalize_keeps_vietnamese_tones_and_english_apostrophes():
    assert wer_mod.normalize("Xin chào, các BẠN! [nhạc] Mà ma?") == "xin chào các bạn mà ma"
    assert wer_mod.normalize("Don't stop — it's 5 o'clock.") == "don't stop it's 5 o'clock"
    # NFD và NFC là cùng một chữ
    assert wer_mod.normalize("Việt") == wer_mod.normalize("Việt")


def test_wer_counts_substitution_insertion_deletion():
    assert wer_mod.wer("tôi đi học", "tôi đi học") == 0
    assert wer_mod.wer("tôi đi học", "tôi đi hoc") == pytest.approx(1 / 3)  # mất dấu là sai từ
    assert wer_mod.wer("tôi đi học", "tôi học") == pytest.approx(1 / 3)
    assert wer_mod.wer("tôi đi học", "tôi đã đi học") == pytest.approx(1 / 3)
    assert wer_mod.cer("tôi đi học", "tôi đi hoc") == pytest.approx(1 / 8)


def test_score_text_skips_lines():
    ref = ["xin chào", "[nhạc mở đầu]", "hôm nay trời đẹp"]
    result = wer_mod.score_text(ref, [(2, 2)], "Xin chào. Hôm nay trời đẹp!")
    assert result["wer"] == 0 and result["ref_words"] == 6
