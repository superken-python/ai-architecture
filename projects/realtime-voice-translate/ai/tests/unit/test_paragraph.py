from rvt_ai.pipeline.paragraph import ParagraphConfig, ParagraphTracker

CFG = ParagraphConfig(gap_ms=600, soft_ms=20000, max_ms=40000)


def test_sentences_with_short_pause_share_one_paragraph_ja_joined_without_space():
    t = ParagraphTracker(CFG)
    p1 = t.add(1, "A", "ja", "人の、え、なんか就労の作業が", 0, 5000)
    p2 = t.add(2, "A", "ja", "なんか減らすんじゃないかなということです。", 5200, 9000)
    assert p1 is p2 and p2.pid == 1
    assert p2.source == "人の、え、なんか就労の作業がなんか減らすんじゃないかなということです。"
    assert p2.revision == 2


def test_vietnamese_sentences_are_joined_with_a_space():
    t = ParagraphTracker(CFG)
    t.add(1, "A", "vi", "Xin chào.", 0, 2000)
    assert t.add(2, "A", "vi", "Hôm nay họp về dự toán.", 2100, 5000).source == "Xin chào. Hôm nay họp về dự toán."


def test_long_pause_starts_a_new_paragraph_and_keeps_the_old_one_as_context():
    t = ParagraphTracker(CFG)
    t.add(1, "A", "ja", "まず一つ目です。", 0, 3000)
    p = t.add(2, "A", "ja", "次に二つ目です。", 3000 + CFG.gap_ms + 1, 6000)
    assert p.pid == 2 and p.source == "次に二つ目です。"
    assert list(t.history) == ["まず一つ目です。"]


def test_language_change_starts_a_new_paragraph():
    t = ParagraphTracker(CFG)
    t.add(1, "A", "ja", "はい。", 0, 1000)
    assert t.add(2, "A", "vi", "Vâng.", 1100, 2000).pid == 2


def test_long_paragraph_breaks_only_after_a_sentence_end():
    t = ParagraphTracker(CFG)
    t.add(1, "A", "ja", "長い説明が続いていて", 0, 21000)
    # Đã quá soft_ms nhưng câu trước chưa hết: vẫn gom
    assert t.add(2, "A", "ja", "まだ続きます。", 21100, 24000).pid == 1
    # Câu trước đã hết ("。"): mở đoạn mới
    assert t.add(3, "A", "ja", "では次に。", 24100, 26000).pid == 3


def test_paragraph_breaks_at_max_length_even_mid_sentence():
    t = ParagraphTracker(CFG)
    t.add(1, "A", "ja", "とても長い話で", 0, 40000)
    assert t.add(2, "A", "ja", "途中です", 40100, 42000).pid == 2


def test_early_committed_sentence_without_start_time_continues_the_paragraph():
    t = ParagraphTracker(CFG)
    t.add(1, "A", "ja", "一つ目。", 0, 3000)
    assert t.add(2, "A", "ja", "二つ目。", None, 10000).pid == 1


def test_first_sentence_without_start_time_starts_at_its_end_time():
    t = ParagraphTracker(CFG)
    p = t.add(1, "A", "ja", "はい。", None, 3000)
    assert p.start_ms == 3000 and p.end_ms == 3000


def test_sides_have_separate_paragraphs():
    t = ParagraphTracker(CFG)
    t.add(1, "A", "ja", "こんにちは。", 0, 1000)
    assert t.add(2, "B", "ja", "どうも。", 1100, 2000).pid == 2
    assert t.add(3, "A", "ja", "続きです。", 1200, 3000).pid == 1


def test_peek_tells_which_paragraph_a_partial_would_join():
    t = ParagraphTracker(CFG)
    assert t.peek("A", "ja", 0) is None
    t.add(5, "A", "ja", "一つ目。", 0, 3000)
    assert t.peek("A", "ja", 3100) == 5
    assert t.peek("A", "ja", 3000 + CFG.gap_ms + 1) is None
    assert t.peek("A", "vi", 3100) is None
    assert t.peek("A", "ja", None) == 5


def test_close_moves_open_paragraphs_to_history():
    t = ParagraphTracker(CFG)
    t.add(1, "A", "ja", "一つ目。", 0, 1000)
    t.add(2, "B", "vi", "Hai.", 0, 1000)
    t.close("A")
    assert t.add(3, "A", "ja", "三つ目。", 1100, 2000).pid == 3
    t.close()
    assert t.open == {} and list(t.history) == ["一つ目。", "Hai.", "三つ目。"]
