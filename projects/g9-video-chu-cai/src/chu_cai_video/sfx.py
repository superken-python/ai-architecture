"""Tiếng con vật và tiếng động hoạt hình, tổng hợp bằng numpy — không dùng bản thu của ai.

Tiếng kêu có cao độ (bò, gà, mèo, sư tử, gấu) dựng như giọng nói: một chuỗi họa âm của cao độ f0 đi qua các "formant"
(vùng tần số được khuếch đại, quyết định âm "ừm", "ò", "meo"…), cộng thêm tiếng thở/tiếng rè. Mỗi tiếng là một công
thức (`Call`): cao độ, formant và độ lớn theo thời gian. Tiếng không có cao độ (bong bóng, gõ mai rùa) viết thành hàm
riêng. Mô hình nhận dạng tiếng động (`make qa`) nghe lại để kiểm tra tiếng tổng hợp có giống con vật thật không.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

Track = tuple[tuple[float, float], ...]  # các điểm (giây, giá trị), nội suy tuyến tính ở giữa


@dataclass(frozen=True)
class Call:
    """Công thức một tiếng kêu có cao độ."""

    duration: float
    pitch: Track  # cao độ f0 (Hz)
    loudness: Track  # độ lớn 0..1 (về 0 ở giữa các tiếng nếu kêu nhiều tiếng)
    formants: tuple[tuple[float, tuple[float, ...]], ...]  # (giây, (F1, F2, F3…)) — tần số formant (Hz)
    widths: tuple[float, ...]  # độ rộng từng formant (Hz)
    gains: tuple[float, ...]  # độ lớn từng formant (dB)
    tilt: float = 9.0  # họa âm cao nhỏ dần bao nhiêu dB mỗi quãng tám
    noise: float = 0.05  # tỉ lệ tiếng thở/tiếng rè (0..1)
    rough: float = 0.0  # độ khàn: điều biên ở nửa tần số f0 (0..1)
    vibrato: tuple[float, float] = (5.0, 0.01)  # (lần/giây, độ rung tương đối)
    jitter: float = 0.004  # dao động cao độ ngẫu nhiên
    seed: int = 1  # hạt giống của phần ngẫu nhiên (tiếng thở, jitter) — cố định để dựng lại ra y hệt


def _track(points: Track, t: np.ndarray) -> np.ndarray:
    xs, ys = zip(*points, strict=True)
    return np.interp(t, xs, ys).astype(np.float32)


def _formant_tracks(call: Call, t: np.ndarray) -> list[np.ndarray]:
    times = [p[0] for p in call.formants]
    return [np.interp(t, times, [p[1][i] for p in call.formants]).astype(np.float32) for i in range(len(call.widths))]


def _envelope(freq: np.ndarray, centers: list[np.ndarray], call: Call) -> np.ndarray:
    """Độ lớn (tuyến tính) tại tần số `freq` theo các formant và độ nghiêng phổ."""
    amp = np.zeros_like(freq)
    for center, width, gain in zip(centers, call.widths, call.gains, strict=True):
        amp += 10 ** (gain / 20) / (1 + ((freq - center) / (width / 2)) ** 2)
    return amp * (np.maximum(freq, 80) / 150) ** (-call.tilt / 6.02)


def _smooth_noise(n: int, rate: float, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Dao động ngẫu nhiên chậm (khoảng `rate` lần/giây), biên độ ~1."""
    k = max(2, int(n * rate / sr) + 2)
    return np.interp(np.arange(n), np.linspace(0, n, k), rng.standard_normal(k)).astype(np.float32)


def _shaped_noise(
    n: int, sr: int, shape: Callable[[np.ndarray, float], np.ndarray], rng: np.random.Generator
) -> np.ndarray:
    """Tiếng ồn trắng lọc theo phổ `shape(tần số, giây)` — chồng các khung có cửa sổ Hann."""
    frame, hop = 1024, 256
    win = np.hanning(frame).astype(np.float32)
    freqs = np.fft.rfftfreq(frame, 1 / sr).astype(np.float32)
    out = np.zeros(n + frame, np.float32)
    for start in range(0, n, hop):
        spec = np.fft.rfft(rng.standard_normal(frame).astype(np.float32) * win)
        out[start : start + frame] += (
            np.fft.irfft(spec * shape(freqs, (start + frame / 2) / sr)).astype(np.float32) * win
        )
    return out[:n]


def synth(call: Call, sr: int, seed: int = 1) -> np.ndarray:
    """Công thức → âm thanh mono float32, đỉnh 0,9.

    Giọng thật không đều: mỗi chu kỳ dài ngắn khác nhau một chút (jitter), to nhỏ khác nhau (shimmer). Dao động thời
    gian δ(t) làm lệch pha họa âm thứ k một lượng k·2π·f0·δ — họa âm càng cao càng nhòe thành tiếng rè, như tiếng thật.
    """
    rng = np.random.default_rng(seed)
    n = int(call.duration * sr)
    t = np.arange(n, dtype=np.float32) / sr
    rate, depth = call.vibrato
    f0 = _track(call.pitch, t) * (
        1 + depth * np.sin(2 * np.pi * rate * t) + call.jitter * _smooth_noise(n, 25, sr, rng)
    )
    phase = 2 * np.pi * np.cumsum(f0, dtype=np.float64) / sr
    wobble = 2 * np.pi * call.jitter * _smooth_noise(n, float(np.median(f0)), sr, rng)  # jitter từng chu kỳ (radian/k)
    shimmer = 1 + 2 * call.jitter * _smooth_noise(n, float(np.median(f0)) / 2, sr, rng)
    offsets = rng.uniform(0, 2 * np.pi, 1024)  # pha ban đầu của từng họa âm — rút một lần, giống nhau ở mọi tần số mẫu
    centers = _formant_tracks(call, t)
    sig = np.zeros(n, np.float32)
    for k in range(1, min(1024, int(0.45 * sr / float(f0.min()))) + 1):
        freq = k * f0
        amp = np.where(freq < 0.45 * sr, _envelope(freq, centers, call), 0.0)
        sig += (amp * np.sin(k * (phase + wobble) + offsets[k - 1])).astype(np.float32)
    sig *= shimmer
    if call.rough:  # khàn: điều biên ở f0/2 tạo họa âm phụ, nghe rè như tiếng gà gáy, sư tử gầm
        sig *= 1 + call.rough * np.sin(phase / 2 + wobble / 2).astype(np.float32)
    sig /= max(float(np.abs(sig).max()), 1e-9)
    if call.noise:
        times = [p[0] for p in call.formants]

        def shape(freqs: np.ndarray, sec: float) -> np.ndarray:
            centers_now = [np.full_like(freqs, np.interp(sec, times, [p[1][i] for p in call.formants]))
                           for i in range(len(call.widths))]  # fmt: skip
            return _envelope(freqs, centers_now, call)

        breath = _shaped_noise(n, sr, shape, rng)
        sig += call.noise * breath / max(float(np.abs(breath).max()), 1e-9)
    sig *= _track(call.loudness, t)
    return (0.9 * sig / max(float(np.abs(sig).max()), 1e-9)).astype(np.float32)


def tract(length: float, count: int, open_: float = 1.0) -> tuple[float, ...]:
    """Formant của ống thanh quản dài `length` mét (một đầu kín): (2n−1)·c/4L. Ống dài (bò, sư tử) → formant dày.

    `open_` < 1: miệng ngậm hơn, formant thấp xuống (tiếng "ừm" của bò)."""
    return tuple(round((2 * i - 1) * 350 / (4 * length) * (0.75 + 0.25 * open_)) for i in range(1, count + 1))


# ───────────────────────────── tiếng con vật ─────────────────────────────

# Thông số chọn bằng phép đo: thử ~900 bộ cho mỗi con vật, mỗi bộ dựng với 3 hạt giống khác nhau, giữ bộ mà mô hình
# nhận dạng tiếng động (AudioSet, 527 loại tiếng) nghe ra đúng con vật đều nhất. Kết quả: reports/kiem-tra-giong.md.
CALLS: dict[str, Call] = {
    # Bò: "ừm" (ngậm miệng, formant thấp) mở dần ra "ò"; cổ dài nên formant dày; cao độ lên rồi xuống.
    "bo": Call(
        duration=1.76,
        pitch=((0, 107), (1.06, 211), (1.41, 170), (1.76, 130)),
        loudness=((0, 0), (0.16, 0.6), (0.79, 1), (1.53, 0.85), (1.76, 0)),
        formants=(
            (0, tract(0.45, 6, 0.52)),
            (0.29, tract(0.45, 6, 0.52)),
            (0.54, tract(0.45, 6)),
            (1.76, tract(0.45, 6)),
        ),
        widths=(50,) * 6,
        gains=(0, -2.5, -5, -7.5, -10, -12.6),
        tilt=8.3,
        noise=0.36,
        rough=0.35,
        vibrato=(5.7, 0.007),
        jitter=0.0135,
        seed=4,
    ),
    # Gà trống: "ò ó o" — ba tiếng, tiếng sau cao hơn, tiếng cuối trượt xuống; nhiều tiếng thở, chói.
    "ga": Call(
        duration=1.08,
        pitch=((0, 442), (0.24, 465), (0.31, 442), (0.52, 520), (0.58, 882), (0.91, 855), (1.08, 567)),
        loudness=(
            (0, 0),
            (0.02, 1),
            (0.22, 0.8),
            (0.24, 0.05),
            (0.31, 0.05),
            (0.33, 1),
            (0.5, 0.9),
            (0.52, 0.05),
            (0.58, 0.05),
            (0.61, 1),
            (0.83, 0.85),
            (1.08, 0),
        ),  # fmt: skip
        formants=((0, (1080, 3020, 4240)), (1.08, (1080, 3020, 4240))),
        widths=(160, 160, 160),
        gains=(0, -4, -10),
        tilt=6.0,
        noise=0.6,
        rough=0.08,
        vibrato=(6.8, 0.03),
        jitter=0.02,
        seed=3,
    ),
    # Mèo: "meo" — cao độ lên rồi xuống, formant đi từ "e" qua "a" về "o".
    "meo": Call(
        duration=1.2,
        pitch=((0, 457), (0.49, 598), (1.2, 405)),
        loudness=((0, 0), (0.08, 0.7), (0.42, 1), (0.96, 0.8), (1.2, 0)),
        formants=((0, (578, 2660, 4640)), (0.42, (1371, 1812, 4640)), (1.2, (520, 991, 4640))),
        widths=(180, 180, 180),
        gains=(0, -3, -12),
        tilt=6.6,
        noise=0.39,
        rough=0.45,
        jitter=0.02,
        seed=1,
    ),
}


def bubbles(sr: int, seed: int = 3) -> np.ndarray:
    """Cá: "búp búp" — vài bọt nước, mỗi bọt là tiếng huýt ngắn vút lên rồi tắt."""
    rng = np.random.default_rng(seed)
    out = np.zeros(int(0.9 * sr), np.float32)
    for at in (0.0, 0.16, 0.37, 0.52, 0.7):
        n = int(0.09 * sr)
        t = np.arange(n, dtype=np.float32) / sr
        f0 = rng.uniform(350, 550) * (1 + 2.5 * (1 - np.exp(-t / 0.02)))
        blip = np.sin(2 * np.pi * np.cumsum(f0) / sr) * np.exp(-t / 0.025)
        i = int(at * sr)
        out[i : i + n] += blip[: out.size - i].astype(np.float32)
    return (0.9 * out / max(float(np.abs(out).max()), 1e-9)).astype(np.float32)


def boing(sr: int) -> np.ndarray:
    """Tiếp đất: "boing" — tiếng vút lên có rung, ngắn."""
    n = int(0.16 * sr)
    t = np.arange(n, dtype=np.float32) / sr
    f0 = 240 * (1 + 0.9 * (1 - np.exp(-t / 0.03))) * (1 + 0.06 * np.sin(2 * np.pi * 28 * t))
    sig = np.sin(2 * np.pi * np.cumsum(f0) / sr) * np.exp(-t / 0.06)
    return (0.9 * sig / max(float(np.abs(sig).max()), 1e-9)).astype(np.float32)


OTHERS: dict[str, Callable[[int], np.ndarray]] = {"ca": bubbles, "boing": boing}
ANIMALS = (*CALLS, "ca")  # tên dùng được cho `call` của chữ cái trong kịch bản
NAMES = tuple(CALLS) + tuple(OTHERS)
CALL_GAP = 0.3  # giây lặng sau câu đọc rồi con vật mới kêu (máy nghe lại câu đọc không bị lẫn tiếng kêu)
TARGET_RMS_DB = -20.0  # tiếng kêu to ngang lời đọc


@lru_cache(maxsize=16)
def sound(name: str, sr: int) -> np.ndarray:
    """Tiếng theo tên trong kịch bản (`call: bo`)."""
    if name in CALLS:
        return synth(CALLS[name], sr, CALLS[name].seed)
    if name in OTHERS:
        return OTHERS[name](sr)
    raise KeyError(f"Không có tiếng '{name}' (có: {', '.join(NAMES)})")


@dataclass(frozen=True)
class Event:
    """Một tiếng động trên dòng thời gian."""

    name: str
    at: float  # giây
    gain: float = 1.0
    cue: str = ""  # id câu của chữ cái nếu là tiếng con vật ("chu-04"); hình con vật nhảy ra theo tiếng này


def render(events: list[Event], seconds: float, sr: int) -> np.ndarray:
    """Rãnh tiếng động (mono): mỗi tiếng chỉnh về cùng độ lớn với lời đọc rồi nhân `gain`, đặt đúng giây."""
    track = np.zeros(int(seconds * sr) + 1, np.float32)
    for e in events:
        x = sound(e.name, sr)
        rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2))) or 1.0
        x = x * (10 ** (TARGET_RMS_DB / 20) / rms * e.gain)
        peak = float(np.abs(x).max())
        if peak > 0.95:
            x = x * (0.95 / peak)
        i = int(e.at * sr)
        part = x[: max(0, track.size - i)]
        track[i : i + part.size] += part
    return track
