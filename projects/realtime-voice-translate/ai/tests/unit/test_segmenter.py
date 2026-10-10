from rvt_ai.pipeline.segmenter import Segmenter, SegmenterConfig


def test_segmenter_basic_flow():
    config = SegmenterConfig(sample_rate=16000, partial_interval_ms=200, min_silence_ms=300, min_speech_ms=100)
    seg = Segmenter(config)

    # 1. 100ms silence
    chunk_100ms = b"\x00" * int(16000 * 2 * 0.1)
    p, f, buf = seg.add_chunk(chunk_100ms, has_speech=False)
    assert not p
    assert not f

    # 2. 200ms speech
    chunk_200ms = b"\x01" * int(16000 * 2 * 0.2)
    p, f, buf = seg.add_chunk(chunk_200ms, has_speech=True)
    assert p is True  # partial interval triggered (100 + 200 >= 200)
    assert f is False
    assert seg.is_speaking is True

    # 3. 300ms silence -> should trigger final
    chunk_300ms = b"\x00" * int(16000 * 2 * 0.3)
    _p, f, _buf = seg.add_chunk(chunk_300ms, has_speech=False)
    assert f is True
    assert seg.is_speaking is False  # reset after final
    assert len(seg.buffer) == 0


def test_segmenter_too_short_speech():
    config = SegmenterConfig(sample_rate=16000, partial_interval_ms=200, min_silence_ms=300, min_speech_ms=200)
    seg = Segmenter(config)

    # 1. 100ms speech
    chunk_100ms = b"\x01" * int(16000 * 2 * 0.1)
    seg.add_chunk(chunk_100ms, has_speech=True)

    # 2. 300ms silence
    chunk_300ms = b"\x00" * int(16000 * 2 * 0.3)
    _p, f, _buf = seg.add_chunk(chunk_300ms, has_speech=False)

    # should NOT trigger final because speech (100ms) < min_speech_ms (200ms)
    assert f is False
    assert seg.is_speaking is False  # it was reset and ignored
