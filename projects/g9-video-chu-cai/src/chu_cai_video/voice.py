"""Giọng đọc cho từng câu của kịch bản.

Thứ tự ưu tiên cho mỗi câu: file thu âm thật `giong-thu-am/<id>.wav` (nếu có) → giọng Piper vi_VN chạy offline
(sherpa-onnx) → im lặng (engine `silent`, để xem thử nhanh hoặc chạy test). Giọng máy được nhớ trong .cache/voice/ theo
nội dung câu, nên dựng lại video không phải đọc lại câu không đổi.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from chu_cai_video import assets, audio, config
from chu_cai_video.lesson import Lesson
from chu_cai_video.timeline import Segment, Timeline

TARGET_RMS_DB = -20.0  # mọi câu cùng độ lớn, dù là giọng máy hay thu âm


@dataclass(frozen=True)
class Spoken:
    segment: Segment
    text: str
    samples: np.ndarray  # mono float32 ở config.SAMPLE_RATE, đã cắt lặng hai đầu
    source: str  # "piper" | "thu-am" | "silent"
    word_at: float | None = None  # giây tính từ đầu câu: chỗ bắt đầu "như trong <từ ví dụ>"

    @property
    def cue_id(self) -> str:
        return self.segment.cue_id

    @property
    def duration(self) -> float:
        return self.samples.size / config.SAMPLE_RATE

    @property
    def start(self) -> float:
        return self.segment.voice_at

    @property
    def end(self) -> float:
        return self.start + self.duration


class PiperEngine:
    """Giọng Piper vi_VN vais1000 qua sherpa-onnx — chạy trên CPU, không cần mạng sau lần tải đầu.

    Tắt phần ngẫu nhiên của model (noise_scale = 0): cùng câu luôn ra cùng một giọng, nên video dựng ở máy nào cũng
    giống nhau; đo bằng ASR, cách này còn đọc rõ hơn mặc định (28/29 so với 24/29 từ ví dụ nghe đúng).
    """

    name = "piper"

    def __init__(self, speed: float, model: Path | None = None) -> None:
        import sherpa_onnx  # nhập muộn: engine `silent` và test không cần thư viện này

        self.model = model or assets.model_dir(config.VOICE)
        self.speed = speed
        onnx = next(self.model.glob("*.onnx"))
        self.key = f"{onnx.name}|{speed}|noise0"
        self.tts = sherpa_onnx.OfflineTts(
            sherpa_onnx.OfflineTtsConfig(
                model=sherpa_onnx.OfflineTtsModelConfig(
                    vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                        model=str(onnx),
                        tokens=str(self.model / "tokens.txt"),
                        data_dir=str(self.model / "espeak-ng-data"),
                        noise_scale=0.0,
                        noise_scale_w=0.0,
                    ),
                    num_threads=4,
                )
            )
        )

    def synth(self, text: str) -> tuple[np.ndarray, int]:
        result = self.tts.generate(text, sid=0, speed=self.speed)
        return np.asarray(result.samples, dtype=np.float32), result.sample_rate


class SilentEngine:
    """Không lời: mỗi tiếng ~0,3 giây im lặng — giữ đúng nhịp để xem thử hình mà không cần model."""

    name = "silent"
    key = "silent"

    def synth(self, text: str) -> tuple[np.ndarray, int]:
        syllables = max(1, len(text.split()))
        return np.zeros(int(0.3 * syllables * config.SAMPLE_RATE), dtype=np.float32), config.SAMPLE_RATE


def engine_for(lesson: Lesson, name: str | None = None) -> PiperEngine | SilentEngine:
    name = name or lesson.voice_engine
    return SilentEngine() if name == "silent" else PiperEngine(lesson.voice_speed)


def _normalize(x: np.ndarray) -> np.ndarray:
    rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2))) if x.size else 0.0
    if rms < 1e-6:
        return x
    y = x * (10 ** (TARGET_RMS_DB / 20) / rms)
    peak = float(np.abs(y).max())
    return (y * (0.95 / peak) if peak > 0.95 else y).astype(np.float32)


def _machine(engine: PiperEngine | SilentEngine, text: str, cache: Path) -> np.ndarray:
    if engine.name == "silent":
        return engine.synth(text)[0]
    path = cache / "voice" / f"{hashlib.sha1(f'{engine.key}|{text}'.encode()).hexdigest()[:16]}.wav"
    if path.exists():
        samples, sr = audio.read_wav(path)
    else:
        samples, sr = engine.synth(text)
        audio.write_wav(path, samples, sr)
    return audio.resample(samples, sr, config.SAMPLE_RATE)


def speak(
    lesson: Lesson, timeline: Timeline, engine: PiperEngine | SilentEngine, cache: Path = config.CACHE
) -> list[Spoken]:
    """Giọng đọc của mọi câu theo dòng thời gian; báo lỗi nếu câu nào dài hơn khúc nhạc của nó."""
    spoken: list[Spoken] = []
    problems: list[str] = []
    for seg in timeline.segments:
        text = seg.text(lesson)
        recording = lesson.recordings / f"{seg.cue_id}.wav"
        if recording.exists():
            raw, sr = audio.read_wav(recording)
            samples, source = audio.resample(raw, sr, config.SAMPLE_RATE), "thu-am"
        else:
            samples, source = _machine(engine, text, cache), engine.name
        if source != "silent":
            samples = _normalize(audio.trim(samples, config.SAMPLE_RATE))
        word_at = None
        if seg.letter is not None:
            word_at = audio.longest_pause(samples, config.SAMPLE_RATE) if source != "silent" else None
            if word_at is None:  # không tìm thấy chỗ ngắt: từ ví dụ hiện ở giữa câu
                word_at = 0.5 * samples.size / config.SAMPLE_RATE
        item = Spoken(seg, text, samples, source, word_at)
        room = seg.end - seg.voice_at - 0.1
        if item.duration > room:
            problems.append(f"{seg.cue_id} ({text!r}) dài {item.duration:.2f}s, khúc nhạc chỉ còn {room:.2f}s")
        spoken.append(item)
    if problems:
        raise ValueError(
            "Lời đọc dài hơn khúc nhạc — giảm music.bpm, tăng số ô nhịp, hoặc rút gọn câu:\n  " + "\n  ".join(problems)
        )
    return spoken


def voice_track(spoken: list[Spoken], seconds: float) -> np.ndarray:
    """Một rãnh mono chứa mọi câu đọc đặt đúng thời điểm."""
    track = np.zeros(int(seconds * config.SAMPLE_RATE) + 1, dtype=np.float32)
    for item in spoken:
        start = int(item.start * config.SAMPLE_RATE)
        part = item.samples[: max(0, track.size - start)]
        track[start : start + part.size] += part
    return track
