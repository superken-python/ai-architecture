import numpy as np
import pytest

from chu_cai_video import audio, lesson, music, timeline

SR = 44_100


def test_three_minutes_and_segments_follow_the_beat(full_lesson):
    tl = timeline.build(full_lesson)
    assert tl.duration == pytest.approx((4 + 2 * 29 + 4) * tl.bar)
    assert tl.duration == pytest.approx(180.0)
    for a, b in zip(tl.segments, tl.segments[1:], strict=False):
        assert a.end == pytest.approx(b.start)
    for seg in tl.segments:
        assert seg.start < seg.voice_at < seg.end
    assert tl.at(0.0).kind == "intro"
    assert tl.at(tl.segments[1].start + 0.01).letter.letter == "A"
    assert tl.at(tl.duration + 5).kind == "outro"
    assert tl.segments[1].cue_id == "chu-01" and tl.segments[-1].cue_id == "ket-thuc"


def test_wav_roundtrip_and_resample(tmp_path):
    t = np.arange(SR) / SR
    tone = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    audio.write_wav(tmp_path / "a.wav", tone, SR)
    back, sr = audio.read_wav(tmp_path / "a.wav")
    assert sr == SR and np.allclose(back, tone, atol=1e-3)
    low = (0.5 * np.sin(2 * np.pi * 440 * np.arange(22050) / 22050)).astype(np.float32)  # giọng Piper: 22,05 kHz
    up = audio.resample(low, 22050, SR)
    assert up.size == SR
    peak_hz = np.argmax(np.abs(np.fft.rfft(up))) * SR / up.size
    assert peak_hz == pytest.approx(440, abs=2)


def test_trim_and_pause_detection():
    t = np.arange(int(0.3 * SR)) / SR
    burst = (0.5 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
    silence = np.zeros(int(0.2 * SR), np.float32)
    x = np.concatenate([silence, burst, np.zeros(int(0.12 * SR), np.float32), burst, silence])
    y = audio.trim(x, SR)
    assert y.size < x.size - int(0.3 * SR)
    start, end = audio.longest_gap(y, SR)
    assert end == pytest.approx(0.03 + 0.3 + 0.12, abs=0.03)
    assert end - start == pytest.approx(0.12, abs=0.03)


def test_insert_silence_widens_the_pause():
    x = np.ones(SR, np.float32) * 0.5
    y = audio.insert_silence(x, SR, 0.4, 0.35)
    assert y.size == x.size + int(0.35 * SR)
    assert np.abs(y[int(0.41 * SR) : int(0.74 * SR)]).max() == 0  # khoảng lặng mới
    assert y[int(0.2 * SR)] == pytest.approx(0.5) and y[-1] == pytest.approx(0.5)  # hai phần câu giữ nguyên


def test_music_ducks_under_voice_and_mix_peaks_at_minus_1_dbfs():
    voice_track = np.zeros(2 * SR, np.float32)
    voice_track[SR : SR + SR // 2] = 0.3 * np.sin(np.arange(SR // 2) / 5)
    gain = audio.duck_gain(voice_track, SR)
    assert gain[SR // 2] == pytest.approx(1.0)  # chưa có lời: nhạc giữ nguyên
    assert gain[SR + SR // 4] == pytest.approx(10 ** (-9 / 20), rel=0.05)  # đang có lời: nhạc hạ 9 dB
    out = audio.mix(voice_track, np.full((2 * SR, 2), 0.2, np.float32), SR)
    assert out.shape == (2 * SR, 2)
    assert np.abs(out).max() == pytest.approx(10 ** (-1 / 20), rel=1e-3)


def test_music_is_deterministic_and_fills_every_segment(make_script):
    tl = timeline.build(lesson.load(make_script(3)))
    a = music.render(tl, SR)
    b = music.render(tl, SR)
    assert a.shape == (int(tl.duration * SR), 2)
    assert np.array_equal(a, b)
    assert np.isfinite(a).all() and np.abs(a).max() == pytest.approx(0.5, rel=1e-3)
    for seg in tl.segments:
        part = a[int(seg.start * SR) : int(seg.end * SR)]
        assert np.sqrt(np.mean(part**2)) > 0.01, seg.kind
