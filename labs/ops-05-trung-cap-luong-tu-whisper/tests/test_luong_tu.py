import luong_tu as lt
import numpy as np
import pytest


def test_seconds_reads_hours_minutes_and_comma():
    assert lt.seconds("00:01:02.500") == pytest.approx(62.5)
    assert lt.seconds("01:02,500") == pytest.approx(62.5)
    assert lt.seconds("1:00:00.000") == pytest.approx(3600)


def test_parse_vtt_g9_has_31_sentences_with_times(g9_vtt):
    cues = lt.parse_vtt(g9_vtt.read_text(encoding="utf-8"))
    assert len(cues) == 31  # câu mở đầu, 29 chữ cái, câu kết
    assert cues[0].start == pytest.approx(0.682) and cues[0].end == pytest.approx(7.746)
    assert cues[0].text.startswith("Xin chào các bạn nhỏ!")
    assert cues[1].text == "Đây là chữ a, như trong cái áo."
    assert cues[-1].text.startswith("Giỏi quá!")
    assert all(c.end > c.start for c in cues)


def test_parse_vtt_skips_ids_settings_tags_and_empty_cues():
    text = (
        "WEBVTT\n\nNOTE ghi chú\n\n1\n00:00:01.000 --> 00:00:02.500 align:start\n<i>Xin</i> chào\nbạn\n\n"
        "2\n00:03.000 --> 00:04.000\n\n00:00:05,000 --> 00:00:06,000\nhết\n"
    )
    assert lt.parse_vtt(text) == [lt.Cue(1.0, 2.5, "Xin chào bạn"), lt.Cue(5.0, 6.0, "hết")]


def test_cut_pads_and_stays_inside_audio():
    audio = np.arange(16000 * 3, dtype=np.float32)
    assert len(lt.cut(audio, lt.Cue(1.0, 2.0, "x"))) == int(2.1 * 16000) - int(0.9 * 16000)
    assert len(lt.cut(audio, lt.Cue(0.0, 0.5, "x"))) == int(0.6 * 16000)
    assert len(lt.cut(audio, lt.Cue(2.5, 3.5, "x"))) == 16000 * 3 - int(2.4 * 16000)


def test_paired_bootstrap_same_errors_is_zero():
    assert lt.paired_bootstrap([1, 0, 2], [1, 0, 2], [5, 5, 5]) == (0.0, 0.0, 0.0)


def test_paired_bootstrap_worse_everywhere_is_clearly_positive():
    delta, lo, hi = lt.paired_bootstrap([0] * 10, [1] * 10, [5] * 10)
    assert delta == pytest.approx(0.2) and lo == pytest.approx(0.2) and hi == pytest.approx(0.2)
    delta, lo, hi = lt.paired_bootstrap([0] * 10, [1, 0] * 5, [5] * 10)
    assert delta == pytest.approx(0.1) and 0 <= lo < 0.1 < hi <= 0.2


def test_verdict_combines_quality_and_speed():
    assert lt.verdict(0.01, 0.05, 0.10, margin=0.02) == "giữ chất lượng, nhanh hơn"
    assert lt.verdict(0.05, 0.10, 0.10, margin=0.02) == "có thể kém hơn, nhanh như nhau"
    assert lt.verdict(0.0, 0.20, 0.10, margin=0.02) == "giữ chất lượng, chậm hơn"


def test_choose_smallest_that_keeps_quality_else_baseline():
    base = {"store": "float32", "size_mb": 150, "rtf": 0.1, "hi": 0.0}
    fp16 = {"store": "float16", "size_mb": 75, "rtf": 0.1, "hi": 0.005}
    int8 = {"store": "int8_float16", "size_mb": 40, "rtf": 0.05, "hi": 0.05}
    assert lt.choose([base, fp16, int8], margin=0.02) is fp16
    assert lt.choose([base, fp16, int8], margin=0.1) is int8
    assert lt.choose([base, {**int8, "hi": 0.5}], margin=0.02) is base


def test_markdown_table_marks_baseline_and_differences():
    rows = [
        {
            "base": True,
            "store": "float32",
            "compute": "float32",
            "size_mb": 151.0,
            "load_s": 0.4,
            "mem_mb": 300.0,
            "rtf": 0.1,
            "wer": 0.2,
        },
        {
            "store": "float32",
            "compute": "int8",
            "size_mb": 151.0,
            "load_s": 0.3,
            "mem_mb": None,
            "rtf": 0.05,
            "wer": 0.21,
            "delta": 0.01,
            "lo": -0.01,
            "hi": 0.03,
            "changed": 4,
            "clips": 31,
            "verdict": "x",
        },
    ]
    table = lt.markdown_table(rows)
    assert "| float32 | float32 | 151.0 MB | 0.4 s | 300 MB | 0.100 | 0.200 | — | — | bản gốc |" in table
    assert "| +0.010 (-0.010 … +0.030) | 4/31 | x |" in table
