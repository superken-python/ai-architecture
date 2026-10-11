from rvt_ai.pipeline.segmenter import Segmenter, SegmenterConfig

CHUNK_40MS = int(16000 * 2 * 0.04)


def feed(seg: Segmenter, speech_prob: float, ms: int) -> list[tuple[bool, bool, bytes]]:
    """Nạp `ms` mili-giây âm thanh theo khung 40 ms với cùng một xác suất VAD."""
    return [seg.add_chunk(b"\x01" * CHUNK_40MS, speech_prob) for _ in range(ms // 40)]


def test_segmenter_basic_flow():
    config = SegmenterConfig(sample_rate=16000, partial_interval_ms=200, min_silence_ms=300, min_speech_ms=100)
    seg = Segmenter(config)

    # 1. 100ms silence
    chunk_100ms = b"\x00" * int(16000 * 2 * 0.1)
    p, f, buf = seg.add_chunk(chunk_100ms, speech_prob=0.0)
    assert not p
    assert not f

    # 2. 200ms speech
    chunk_200ms = b"\x01" * int(16000 * 2 * 0.2)
    p, f, buf = seg.add_chunk(chunk_200ms, speech_prob=1.0)
    assert p is True  # partial interval triggered (100 + 200 >= 200)
    assert f is False
    assert seg.is_speaking is True

    # 3. 300ms silence -> should trigger final
    chunk_300ms = b"\x00" * int(16000 * 2 * 0.3)
    _p, f, _buf = seg.add_chunk(chunk_300ms, speech_prob=0.0)
    assert f is True
    assert seg.is_speaking is False  # reset after final
    assert len(seg.buffer) == 0


def test_segmenter_too_short_speech():
    config = SegmenterConfig(sample_rate=16000, partial_interval_ms=200, min_silence_ms=300, min_speech_ms=200)
    seg = Segmenter(config)

    # 1. 100ms speech
    chunk_100ms = b"\x01" * int(16000 * 2 * 0.1)
    seg.add_chunk(chunk_100ms, speech_prob=1.0)

    # 2. 300ms silence
    chunk_300ms = b"\x00" * int(16000 * 2 * 0.3)
    _p, f, _buf = seg.add_chunk(chunk_300ms, speech_prob=0.0)

    # should NOT trigger final because speech (100ms) < min_speech_ms (200ms)
    assert f is False
    assert seg.is_speaking is False  # it was reset and ignored
    assert seg.last_stats is None


def test_segmenter_does_not_start_below_threshold():
    seg = Segmenter(SegmenterConfig(threshold=0.5, neg_threshold=0.35))
    feed(seg, 0.45, 400)
    assert seg.is_speaking is False


def test_segmenter_hysteresis_keeps_far_speech_in_one_utterance():
    # Giọng ở xa: p dao động 0.4–0.6. Một ngưỡng 0.5 sẽ chốt câu giữa chừng; hysteresis giữ trọn câu.
    seg = Segmenter(SegmenterConfig(threshold=0.5, neg_threshold=0.35, min_silence_ms=500))
    results = feed(seg, 0.6, 200) + feed(seg, 0.4, 800) + feed(seg, 0.6, 200)
    assert not any(final for _, final, _ in results)
    assert seg.is_speaking is True

    results = feed(seg, 0.1, 520)
    finals = [r for r in results if r[1]]
    assert len(finals) == 1
    assert len(finals[0][2]) == CHUNK_40MS * (5 + 20 + 5 + 13)  # trọn câu + khoảng lặng cuối


def test_segmenter_records_stats_for_final():
    seg = Segmenter(SegmenterConfig(threshold=0.5, neg_threshold=0.35, min_silence_ms=500, min_speech_ms=200))
    feed(seg, 0.9, 200)
    feed(seg, 0.5, 200)
    feed(seg, 0.0, 520)
    stats = seg.last_stats
    assert stats is not None
    assert stats.speech_ms == 400  # từ đầu khung tiếng đầu tiên tới cuối khung tiếng cuối cùng
    assert stats.prob_max == 0.9
    assert abs(stats.prob_mean - 0.7) < 1e-9


def test_force_final_returns_audio_and_stats():
    seg = Segmenter(SegmenterConfig(min_speech_ms=200))
    feed(seg, 0.8, 400)
    out = seg.force_final()
    assert len(out) > 0
    assert seg.last_stats is not None and seg.last_stats.prob_max == 0.8
    assert seg.is_speaking is False


def test_segmenter_dynamic_silence_threshold_for_long_speech():
    # Long speech (> 4000ms) should finalize on 250ms silence instead of waiting 500ms
    seg = Segmenter(SegmenterConfig(min_speech_ms=200, min_silence_ms=500))
    feed(seg, 0.9, 4500)
    # At 4.5s speech, 280ms of silence should finalize!
    finals = [r for r in feed(seg, 0.0, 280) if r[1]]
    assert len(finals) == 1
