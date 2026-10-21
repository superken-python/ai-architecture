"""Dòng thời gian theo nhịp nhạc: mở đầu → mỗi chữ cái một khúc bằng nhau → kết thúc; giọng đọc vào đúng phách."""

from __future__ import annotations

from dataclasses import dataclass

from chu_cai_video.lesson import Lesson, Letter


@dataclass(frozen=True)
class Segment:
    kind: str  # "intro" | "letter" | "outro"
    start: float
    end: float
    voice_at: float  # lúc giọng đọc bắt đầu (giây, tính từ đầu video)
    letter: Letter | None = None

    @property
    def cue_id(self) -> str:
        if self.letter is not None:
            return self.letter.id
        return {"intro": "mo-dau", "outro": "ket-thuc"}[self.kind]

    def text(self, lesson: Lesson) -> str:
        if self.letter is not None:
            return self.letter.say
        return lesson.intro if self.kind == "intro" else lesson.outro


@dataclass(frozen=True)
class Timeline:
    bpm: float
    segments: tuple[Segment, ...]

    @property
    def beat(self) -> float:
        return 60.0 / self.bpm

    @property
    def bar(self) -> float:
        return 4 * self.beat

    @property
    def duration(self) -> float:
        return self.segments[-1].end

    def at(self, t: float) -> Segment:
        for seg in self.segments:
            if t < seg.end:
                return seg
        return self.segments[-1]

    def beat_phase(self, t: float) -> float:
        """Vị trí trong phách hiện tại: 0 ngay lúc gõ phách, gần 1 ngay trước phách sau."""
        return (t / self.beat) % 1.0

    def letter_segments(self) -> list[Segment]:
        return [s for s in self.segments if s.letter is not None]


def build(lesson: Lesson) -> Timeline:
    beat = 60.0 / lesson.bpm
    bar = 4 * beat
    segments: list[Segment] = []
    t = 0.0
    end = lesson.intro_bars * bar
    segments.append(Segment("intro", t, end, voice_at=t + beat))
    t = end
    for letter in lesson.letters:
        end = t + lesson.letter_bars * bar
        # Phách đầu: thẻ chữ hiện, chữ cái nhảy từ hàng trên cùng xuống sân khấu; giọng vào ở phách thứ hai.
        segments.append(Segment("letter", t, end, voice_at=t + beat, letter=letter))
        t = end
    segments.append(Segment("outro", t, t + lesson.outro_bars * bar, voice_at=t + beat))
    return Timeline(bpm=lesson.bpm, segments=tuple(segments))
