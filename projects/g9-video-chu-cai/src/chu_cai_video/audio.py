"""Xử lý âm thanh bằng numpy: đọc/ghi WAV, đổi tần số lấy mẫu, cắt khoảng lặng, tìm chỗ ngắt, trộn giọng với nhạc."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    """WAV PCM 16 bit → mảng float32 mono trong [-1, 1] và tần số lấy mẫu."""
    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2:
            raise ValueError(f"{path.name}: chỉ đọc WAV PCM 16 bit (thu âm rồi xuất lại bằng ffmpeg: -c:a pcm_s16le)")
        sr, channels = w.getframerate(), w.getnchannels()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    return data, sr


def write_wav(path: Path, samples: np.ndarray, sr: int) -> None:
    """Mảng float (mono hoặc n×2) → WAV PCM 16 bit."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.clip(np.asarray(samples, dtype=np.float32), -1.0, 1.0)
    channels = 1 if data.ndim == 1 else data.shape[1]
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((data * 32767).astype("<i2").tobytes())


def resample(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    """Đổi tần số lấy mẫu bằng FFT (giới hạn dải, không cần scipy)."""
    if sr_in == sr_out or x.size == 0:
        return x.astype(np.float32)
    n_out = round(x.size * sr_out / sr_in)
    spec = np.fft.rfft(x)
    out = np.zeros(n_out // 2 + 1, dtype=complex)
    keep = min(spec.size, out.size)
    out[:keep] = spec[:keep]
    return (np.fft.irfft(out, n_out) * (n_out / x.size)).astype(np.float32)


def frame_rms(x: np.ndarray, sr: int, hop: float) -> np.ndarray:
    """Độ lớn RMS theo từng khung dài `hop` giây."""
    n = max(1, int(sr * hop))
    frames = x[: x.size // n * n].reshape(-1, n)
    return np.sqrt((frames.astype(np.float64) ** 2).mean(axis=1)).astype(np.float32)


def trim(x: np.ndarray, sr: int, threshold_db: float = -45.0, pad: float = 0.03) -> np.ndarray:
    """Bỏ khoảng lặng đầu và cuối (giữ lại `pad` giây), làm mềm hai đầu để không nghe tiếng 'tạch'."""
    if x.size == 0:
        return x
    level = frame_rms(x, sr, 0.01)
    loud = np.flatnonzero(level > 10 ** (threshold_db / 20) * max(float(np.abs(x).max()), 1e-9))
    if loud.size == 0:
        return x
    hop = int(sr * 0.01)
    start = max(0, loud[0] * hop - int(pad * sr))
    end = min(x.size, (loud[-1] + 1) * hop + int(pad * sr))
    y = x[start:end].copy()
    fade = min(int(0.01 * sr), y.size // 2)
    if fade:
        ramp = np.linspace(0, 1, fade, dtype=np.float32)
        y[:fade] *= ramp
        y[-fade:] *= ramp[::-1]
    return y


def longest_pause(x: np.ndarray, sr: int, lo: float = 0.25, hi: float = 0.8, min_len: float = 0.04) -> float | None:
    """Thời điểm (giây) kết thúc khoảng ngắt dài nhất nằm giữa câu — chỗ dấu phẩy trước từ ví dụ."""
    level = frame_rms(x, sr, 0.01)
    if level.size == 0:
        return None
    quiet = level < 0.08 * level.max()
    best: tuple[int, int] | None = None
    i = int(lo * level.size)
    stop = int(hi * level.size)
    while i < stop:
        if quiet[i]:
            j = i
            while j < level.size and quiet[j]:
                j += 1
            if best is None or j - i > best[1] - best[0]:
                best = (i, j)
            i = j
        else:
            i += 1
    if best is None or (best[1] - best[0]) * 0.01 < min_len:
        return None
    return best[1] * 0.01


def smooth_envelope(x: np.ndarray, sr: int, attack: float = 0.03, release: float = 0.25) -> np.ndarray:
    """Đường bao độ lớn (0..1) đi lên nhanh, xuống chậm — dùng để hạ nhạc khi có lời (ducking)."""
    hop = 0.005
    level = frame_rms(x, sr, hop)
    if level.size == 0:
        return np.zeros_like(x)
    level = level / max(float(level.max()), 1e-9)
    up, down = np.exp(-hop / attack), np.exp(-hop / release)
    env = np.empty_like(level)
    cur = 0.0
    for k, v in enumerate(level):
        coef = up if v > cur else down
        cur = coef * cur + (1 - coef) * float(v)
        env[k] = cur
    return np.repeat(env, int(sr * hop))[: x.size].astype(np.float32).clip(0, 1)


def duck_gain(voice: np.ndarray, sr: int, duck_db: float = 9.0) -> np.ndarray:
    """Hệ số nhân cho nhạc theo từng mẫu: 1 khi im lặng, hạ `duck_db` khi có lời (vào nhanh, nhả chậm)."""
    env = np.zeros(voice.size, dtype=np.float32)
    e = smooth_envelope(voice, sr)
    env[: e.size] = e
    return 1.0 - (1.0 - 10 ** (-duck_db / 20)) * np.clip(env * 3.0, 0, 1)


def mix(voice: np.ndarray, music: np.ndarray, sr: int, duck_db: float = 9.0) -> np.ndarray:
    """Trộn giọng (mono) với nhạc (n×2): nhạc tự hạ `duck_db` khi có lời, rồi chuẩn hoá đỉnh về -1 dBFS."""
    n = max(voice.size, music.shape[0])
    v = np.zeros(n, dtype=np.float32)
    v[: voice.size] = voice
    m = np.zeros((n, 2), dtype=np.float32)
    m[: music.shape[0]] = music
    out = m * duck_gain(v, sr, duck_db)[:, None] + v[:, None]
    peak = float(np.abs(out).max()) or 1.0
    out *= 10 ** (-1 / 20) / peak
    return out.astype(np.float32)
