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
    # Trung bình trên mọi khung từ lúc bắt đầu nói tới lúc chốt: 5 × 0,9 + 5 × 0,5 + 13 khung lặng (docs 08 §3.3)
    assert abs(stats.prob_mean - 7.0 / 23) < 1e-9


def test_segment_vad_mean_counts_quiet_frames():
    # Đoạn chỉ có một khung rõ, còn lại nửa vời (tiếng động, nhạc) rồi lặng: trước đây chỉ tính các khung
    # ≥ neg_threshold nên trung bình là 0,386 và bộ lọc câu bịa (< 0,35) không bao giờ áp được (docs 08 §3.3)
    seg = Segmenter(SegmenterConfig(threshold=0.4, neg_threshold=0.25, min_silence_ms=200))
    finals = [seg.add_chunk(b"\x00\x00" * 640, p)[1] for p in [0.9] + [0.3] * 6 + [0.1] * 8]
    assert any(finals)
    assert seg.last_stats is not None and seg.last_stats.prob_mean < 0.35


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


def test_segmenter_mincut_incomplete_preroll_and_consecutive_cuts():
    # Config: max_ms=2000ms, window 1500ms (frames up to 200ms tail)
    config = SegmenterConfig(max_ms=2000, hard_max_ms=4000, preroll_ms=400, min_speech_ms=200, neg_threshold=0.25)
    seg = Segmenter(config)

    # 1. Preroll thiếu: chỉ có 2 khung 40ms (80ms < 400ms)
    feed(seg, 0.0, 80)
    # Khung preroll có 80 * 32 = 2560 bytes

    # 2. 1600ms speech (40 frames, prob 0.85)
    feed(seg, 0.85, 1600)

    # 3. 1 khung lặng 40ms tại vị trí biết trước (prob 0.05 < neg_threshold)
    quiet_chunk_1 = b"\x07" * CHUNK_40MS
    seg.add_chunk(quiet_chunk_1, 0.05)

    # 4. 400ms speech (prob 0.85) để vượt ngưỡng max_ms (2000ms)
    # Tail là 200ms (5 frames), nên khung quiet_chunk_1 nằm trước tail 200ms và trong window 1500ms
    res = feed(seg, 0.85, 400)
    finals = [r for r in res if r[1]]
    assert len(finals) == 1
    final_1 = finals[0][2]

    # Kiểm tra điểm cắt 1: phải chứa đúng 80ms preroll + 1600ms speech + 40ms quiet chunk = 1720ms
    expected_len_1 = int(16000 * 2 * (0.08 + 1.6 + 0.04))
    assert len(final_1) == expected_len_1
    # Đoạn cắt phải kết thúc đúng bằng quiet_chunk_1
    assert final_1.endswith(quiet_chunk_1)

    # 5. Lần cắt thứ 2 nối tiếp: buffer còn lại bắt đầu ngay mà không có preroll
    # Tiếp tục feed 1600ms speech (prob 0.85)
    feed(seg, 0.85, 1600)

    # 1 khung lặng 40ms thứ hai (prob 0.08)
    quiet_chunk_2 = b"\x09" * CHUNK_40MS
    seg.add_chunk(quiet_chunk_2, 0.08)

    # 400ms speech để vượt max_ms lần thứ 2
    res2 = feed(seg, 0.85, 400)
    finals2 = [r for r in res2 if r[1]]
    assert len(finals2) == 1
    final_2 = finals2[0][2]

    # Kiểm tra điểm cắt 2: không có preroll drift!
    # Buffer còn lại từ đoạn 1 là 400ms speech, cộng thêm 1600ms speech + 40ms quiet = 2040ms
    expected_len_2 = int(16000 * 2 * (0.4 + 1.6 + 0.04))
    assert len(final_2) == expected_len_2
    assert final_2.endswith(quiet_chunk_2)
