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


def test_vtt_to_lines_keeps_manual_cue_text_once():
    fetch = pytest.importorskip("fetch_golden")
    vtt = """WEBVTT
Kind: captions
Language: vi

1
00:00:01.000 --> 00:00:03.500
<c>Xin chào</c> các bạn,

2
00:00:03.500 --> 00:00:06.000 align:start position:0%
hôm nay chúng ta nói về
chữ viết.

00:00:06.000 --> 00:00:07.000
hôm nay chúng ta nói về chữ viết.
"""
    assert fetch.vtt_to_lines(vtt) == ["Xin chào các bạn,", "hôm nay chúng ta nói về chữ viết."]


def test_cer_for_japanese_ignores_punctuation_and_width():
    assert wer_mod.cer("今日は、いい天気ですね。", "今日はいい天気ですね") == 0
    assert wer_mod.cer("ＡＢＣ１２３です", "ABC123です") == 0  # toàn khổ và nửa khổ là một
    assert wer_mod.cer("里の長", "里の蝶") == pytest.approx(1 / 3)
