"""Nhạc nền tự tổng hợp bằng numpy — không dùng bản thu của ai nên không vướng bản quyền.

Giọng Đô trưởng, vòng hoà âm vui C–G–Am–F; trống nhẹ, bass nảy, đàn gảy phách lẻ, chuông "ting" mỗi khi sang chữ mới và
một câu đáp ngắn của mộc cầm sau mỗi lời đọc. Cùng kịch bản thì ra đúng cùng một bản nhạc (seed cố định).
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from chu_cai_video.timeline import Timeline

CHORDS = {  # nốt MIDI: hợp âm (quãng giữa) và nốt bass
    "C": ([60, 64, 67], 36),
    "F": ([57, 60, 65], 41),
    "G": ([59, 62, 67], 43),
    "Am": ([57, 60, 64], 45),
}
INTRO = ["C", "F", "G", "G"]
LOOP = ["C", "G", "Am", "F"]
OUTRO = ["F", "G", "C", "C"]
# Câu đáp của mộc cầm sau lời đọc: bậc trong hợp âm (0, 1, 2 = nốt 1, 3, 5; 3 = quãng tám).
ANSWERS = [(0, 1, 2, 3), (2, 1, 0, 1), (1, 2, 3, 2), (3, 2, 1, 0)]


def hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _t(dur: float, sr: int) -> np.ndarray:
    return np.arange(int(dur * sr), dtype=np.float32) / sr


def _attack(sig: np.ndarray, sr: int, seconds: float = 0.004) -> np.ndarray:
    n = min(sig.size, max(1, int(seconds * sr)))
    sig[:n] *= np.linspace(0, 1, n, dtype=np.float32)
    return sig


def partials(freq: float, dur: float, sr: int, ratios, amps, decays) -> np.ndarray:
    """Tổng các họa âm tắt dần theo hàm mũ — đủ cho tiếng đàn gảy, mộc cầm, chuông."""
    t = _t(dur, sr)
    sig = np.zeros_like(t)
    for ratio, amp, decay in zip(ratios, amps, decays, strict=True):
        if freq * ratio < sr / 2:
            sig += amp * np.sin(2 * np.pi * freq * ratio * t) * np.exp(-decay * t)
    return _attack(sig, sr)


# Các âm có cao độ được nhớ lại (cùng nốt, cùng độ dài thì cùng mảng) — Track.add chỉ đọc, không sửa mảng.
@lru_cache(maxsize=512)
def pluck(freq: float, dur: float, sr: int) -> np.ndarray:
    return partials(freq, dur, sr, (1, 2, 3, 4), (1.0, 0.45, 0.22, 0.1), (7, 10, 14, 18))


@lru_cache(maxsize=512)
def marimba(freq: float, dur: float, sr: int) -> np.ndarray:
    return partials(freq, dur, sr, (1, 3.93, 9.2), (1.0, 0.3, 0.06), (8, 22, 45))


@lru_cache(maxsize=512)
def bell(freq: float, dur: float, sr: int) -> np.ndarray:
    return partials(freq, dur, sr, (1, 2.76, 5.4, 8.93), (1.0, 0.45, 0.25, 0.12), (3.5, 6, 9, 13))


@lru_cache(maxsize=512)
def bass(freq: float, dur: float, sr: int) -> np.ndarray:
    t = _t(dur, sr)
    sig = sum(np.sin(2 * np.pi * freq * k * t) / k**2 * (-1) ** (k // 2) for k in (1, 3, 5))
    env = np.minimum(1.0, (dur - t) / 0.03).clip(0, 1) * np.exp(-2.5 * t)
    return _attack((sig * env).astype(np.float32), sr, 0.006)


@lru_cache(maxsize=4)
def kick(sr: int) -> np.ndarray:
    t = _t(0.35, sr)
    freq = 48 + 90 * np.exp(-t * 28)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    return (np.sin(phase) * np.exp(-t * 10)).astype(np.float32)


def clap(sr: int, rng: np.random.Generator) -> np.ndarray:
    t = _t(0.22, sr)
    noise = rng.standard_normal(t.size).astype(np.float32)
    noise = np.diff(noise, prepend=0.0)  # lọc thông cao đơn giản: bỏ phần trầm của nhiễu
    body = 0.4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    return ((0.5 * noise * np.exp(-t * 26)) + body).astype(np.float32)


def hat(sr: int, rng: np.random.Generator) -> np.ndarray:
    t = _t(0.06, sr)
    noise = np.diff(rng.standard_normal(t.size + 1).astype(np.float32), n=1)
    return (noise * np.exp(-t * 70)).astype(np.float32)


class Track:
    """Bản nhạc stereo; `add` đặt một âm vào thời điểm `at` với độ lớn và vị trí trái–phải."""

    def __init__(self, seconds: float, sr: int) -> None:
        self.sr = sr
        self.buf = np.zeros((int(seconds * sr) + sr, 2), dtype=np.float32)

    def add(self, at: float, sig: np.ndarray, gain: float, pan: float = 0.0) -> None:
        start = int(at * self.sr)
        if start >= self.buf.shape[0] or sig.size == 0:
            return
        sig = sig[: self.buf.shape[0] - start] * gain
        left, right = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        self.buf[start : start + sig.size, 0] += sig * left * np.sqrt(2)
        self.buf[start : start + sig.size, 1] += sig * right * np.sqrt(2)


def _bar(track: Track, at: float, beat: float, chord: str, drums: bool, rng: np.random.Generator, sr: int) -> None:
    notes, root = CHORDS[chord]
    for b in (0, 2):  # bass nảy: nốt gốc phách 1, 3 và quãng tám ở phách lẻ
        track.add(at + b * beat, bass(hz(root), 0.9 * beat, sr), 0.42)
        track.add(at + (b + 1.5) * beat, bass(hz(root + 12), 0.4 * beat, sr), 0.22)
    for k, off in enumerate((0.5, 1.5, 2.5, 3.5)):  # đàn gảy phách lẻ, rải trái phải
        for j, n in enumerate(notes):
            track.add(at + off * beat + j * 0.012, pluck(hz(n), 0.6, sr), 0.07, pan=-0.35 if k % 2 else 0.35)
    if drums:
        for b in (0, 2):
            track.add(at + b * beat, kick(sr), 0.55)
        for b in (1, 3):
            track.add(at + b * beat, clap(sr, rng), 0.16, pan=0.1)
        for e in range(8):
            track.add(at + e * beat / 2, hat(sr, rng), 0.05 if e % 2 == 0 else 0.08, pan=0.45)


def render(timeline: Timeline, sr: int = 44_100, seed: int = 7) -> np.ndarray:
    """Cả bản nhạc theo dòng thời gian: mảng float32 n×2, đỉnh ≈ 0.5."""
    rng = np.random.default_rng(seed)
    beat, bar = timeline.beat, timeline.bar
    track = Track(timeline.duration, sr)
    for seg in timeline.segments:
        n_bars = round((seg.end - seg.start) / bar)
        if seg.kind == "intro":
            chords = (INTRO * n_bars)[:n_bars]
            for i, ch in enumerate(chords):
                _bar(track, seg.start + i * bar, beat, ch, drums=i >= n_bars // 2, rng=rng, sr=sr)
                notes, _ = CHORDS[ch]
                for k in range(4):  # mộc cầm rải hợp âm đi lên, mở màn
                    track.add(seg.start + i * bar + k * beat, marimba(hz(notes[k % 3] + 12 * (1 + k // 3)), 0.8, sr),
                              0.2, pan=-0.2)  # fmt: skip
        elif seg.kind == "letter":
            idx = seg.letter.index - 1 if seg.letter else 0
            for i in range(n_bars):
                ch = LOOP[(idx * n_bars + i) % len(LOOP)]
                _bar(track, seg.start + i * bar, beat, ch, drums=True, rng=rng, sr=sr)
            # "Ting!" báo chữ mới, rồi câu đáp của mộc cầm ở hai phách cuối khúc (lúc giọng đã đọc xong).
            track.add(seg.start, bell(hz([84, 88, 91][idx % 3]), 1.4, sr), 0.16, pan=0.2)
            last = LOOP[(idx * n_bars + n_bars - 1) % len(LOOP)]
            notes, _ = CHORDS[last]
            scale = [*notes, notes[0] + 12]
            for k, step in enumerate(ANSWERS[idx % len(ANSWERS)]):
                track.add(seg.end - 2 * beat + k * beat / 2, marimba(hz(scale[step] + 12), 0.5, sr), 0.18, pan=-0.25)
        else:
            chords = (OUTRO * n_bars)[:n_bars]
            for i, ch in enumerate(chords[:-1]):
                _bar(track, seg.start + i * bar, beat, ch, drums=True, rng=rng, sr=sr)
                notes, _ = CHORDS[ch]
                for k in range(4):
                    track.add(seg.start + i * bar + k * beat, marimba(hz(notes[k % 3] + 12), 0.6, sr), 0.16, pan=-0.2)
            end = seg.start + (n_bars - 1) * bar  # hợp âm kết ngân dài + chuông
            notes, root = CHORDS[chords[-1]]
            track.add(end, kick(sr), 0.55)
            track.add(end, bass(hz(root), bar, sr), 0.45)
            for j, n in enumerate([*notes, notes[0] + 12]):
                track.add(end + j * 0.03, pluck(hz(n), bar, sr), 0.1)
                track.add(end + j * 0.09, bell(hz(n + 24), bar, sr), 0.08, pan=0.3)
    out = track.buf[: int(timeline.duration * sr)]
    fade = int(0.8 * sr)  # tắt dần ở cuối
    out[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)[:, None]
    peak = float(np.abs(out).max()) or 1.0
    return (out * (0.5 / peak)).astype(np.float32)
