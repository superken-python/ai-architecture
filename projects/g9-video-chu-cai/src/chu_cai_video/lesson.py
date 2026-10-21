"""Đọc và kiểm tra kịch bản (kich-ban/*.yaml): mỗi chữ cái, cách đọc, từ ví dụ, vị trí chữ cần tô màu."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# Năm dấu thanh (huyền, sắc, ngã, hỏi, nặng). Dấu tạo chữ (ă, â, ê, ô, ơ, ư) và đ được giữ lại.
TONE_MARKS = {"̀", "́", "̃", "̉", "̣"}


class LessonError(ValueError):
    pass


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def base_letter(ch: str) -> str:
    """Chữ cái gốc của một ký tự, bỏ dấu thanh: 'ế' → 'ê', 'ằ' → 'ă', 'Đ' → 'đ' (khác 'd')."""
    decomposed = unicodedata.normalize("NFD", ch)
    return nfc("".join(c for c in decomposed if c not in TONE_MARKS)).lower()


@dataclass(frozen=True)
class Letter:
    index: int  # 1..29 theo thứ tự trong kịch bản
    letter: str  # chữ in hoa: "Ă"
    sound: str  # cách đọc: "á"
    phrase: str  # "khăn quàng"
    word: str  # "khăn"
    emoji: str = ""
    image: Path | None = None
    say: str = ""  # câu giọng đọc sẽ đọc
    speed: float | None = None  # tốc độ đọc riêng của câu này (None: theo voice.speed)

    @property
    def id(self) -> str:
        return f"chu-{self.index:02d}"

    @property
    def lower(self) -> str:
        return self.letter.lower()

    def highlight(self) -> tuple[int, int]:
        """Vị trí [đầu, cuối) của chữ cái trong phrase — tìm trong `word`, không trong cả cụm ('con' của 'con cá')."""
        start = self.phrase.find(self.word)
        for i, ch in enumerate(self.word):
            if base_letter(ch) == self.lower:
                return start + i, start + i + 1
        raise LessonError(f"{self.letter}: không thấy chữ '{self.lower}' trong từ '{self.word}'")


@dataclass(frozen=True)
class Source:
    """Đoạn video gốc để tách nhân vật (chỉ `make sprites` cần)."""

    video: Path
    start: float  # giây
    end: float
    crop: tuple[int, int, int, int]  # x, y, rộng, cao: vùng chứa nhân vật trong khung hình gốc
    radius: float  # bán kính (px, trong vùng cắt) đĩa giữ chi tiết mảnh — nhỏ hơn vòng sáng quanh nhân vật
    height: int  # chiều cao ảnh động xuất ra (px)


@dataclass(frozen=True)
class Character:
    name: str
    side: str  # "left" | "right": đứng ở góc dưới bên trái hay bên phải bảng học
    sprite: Path  # ảnh động nền trong suốt (WebP, sinh bằng `make sprites`) hoặc ảnh PNG tĩnh
    speaks: bool = False  # nhân vật đọc lời: nhún theo giọng đọc
    source: Source | None = None


@dataclass(frozen=True)
class Lesson:
    title: str
    characters: tuple[Character, ...]
    bpm: float
    intro_bars: int
    letter_bars: int
    outro_bars: int
    voice_engine: str
    voice_speed: float
    voice_pause: float  # giây im lặng thêm vào chỗ ngắt trước từ ví dụ (chỉ giọng máy)
    recordings: Path
    intro: str
    outro: str
    letters: tuple[Letter, ...]


def _require(data: dict[str, Any], key: str, where: str) -> Any:
    if key not in data or data[key] in (None, ""):
        raise LessonError(f"{where}: thiếu '{key}'")
    return data[key]


def _source(item: dict[str, Any], base: Path, where: str) -> Source:
    crop = [int(v) for v in _require(item, "crop", where)]
    if len(crop) != 4:
        raise LessonError(f"{where}.crop: cần 4 số [x, y, rộng, cao]")
    start, end = float(item.get("start", 0.0)), float(_require(item, "end", where))
    if end <= start:
        raise LessonError(f"{where}: end ({end}) phải lớn hơn start ({start})")
    return Source(
        video=(base / _require(item, "video", where)).resolve(),
        start=start,
        end=end,
        crop=(crop[0], crop[1], crop[2], crop[3]),
        radius=float(_require(item, "radius", where)),
        height=int(item.get("height", 360)),
    )


def _characters(items: list[dict[str, Any]], base: Path) -> tuple[Character, ...]:
    out: list[Character] = []
    for i, item in enumerate(items, start=1):
        where = f"characters[{i}]"
        side = _require(item, "side", where)
        if side not in ("left", "right"):
            raise LessonError(f"{where}: side '{side}' không hợp lệ (chọn: left, right)")
        source = _source(item["source"], base, f"{where}.source") if item.get("source") else None
        sprite = (base / _require(item, "sprite", where)).resolve()
        if not sprite.exists() and (source is None or not source.video.exists()):
            raise LessonError(f"{where}: không có ảnh nhân vật {sprite} (và không có video gốc để tách)")
        out.append(Character(nfc(_require(item, "name", where)), side, sprite, bool(item.get("speaks")), source))
    sides = [c.side for c in out]
    if len(set(sides)) != len(sides):
        raise LessonError("characters: mỗi góc (left, right) chỉ một nhân vật")
    if sum(c.speaks for c in out) > 1:
        raise LessonError("characters: chỉ một nhân vật có speaks: true (một giọng đọc)")
    return tuple(out)


def parse(data: dict[str, Any], base: Path) -> Lesson:
    music = data.get("music", {})
    voice = data.get("voice", {})
    line = nfc(voice.get("line", "Đây là chữ {sound}, như trong {phrase}."))
    letters: list[Letter] = []
    for i, item in enumerate(_require(data, "letters", "kịch bản"), start=1):
        where = f"letters[{i}]"
        fields = {k: nfc(str(_require(item, k, where))) for k in ("letter", "sound", "phrase", "word")}
        if fields["word"] not in fields["phrase"]:
            raise LessonError(
                f"{where} ({fields['letter']}): từ '{fields['word']}' không nằm trong '{fields['phrase']}'"
            )
        image = (base / item["image"]).resolve() if item.get("image") else None
        if not item.get("emoji") and image is None:
            raise LessonError(f"{where} ({fields['letter']}): cần 'emoji' hoặc 'image' làm hình minh họa")
        if image is not None and not image.exists():
            raise LessonError(f"{where} ({fields['letter']}): không có file ảnh {image}")
        say = nfc(item.get("say") or line.format(**fields))
        speed = float(item["speed"]) if item.get("speed") else None
        letter = Letter(index=i, emoji=item.get("emoji", ""), image=image, say=say, speed=speed, **fields)
        letter.highlight()  # báo lỗi sớm nếu chữ cái không có trong từ ví dụ
        letters.append(letter)
    seen = [x.letter for x in letters]
    duplicated = sorted({x for x in seen if seen.count(x) > 1})
    if duplicated:
        raise LessonError(f"Chữ cái bị lặp: {', '.join(duplicated)}")
    engine = voice.get("engine", "piper")
    if engine not in ("piper", "silent"):
        raise LessonError(f"voice.engine '{engine}' không hợp lệ (chọn: piper, silent)")
    return Lesson(
        title=nfc(_require(data, "title", "kịch bản")),
        characters=_characters(_require(data, "characters", "kịch bản"), base),
        bpm=float(music.get("bpm", 132)),
        intro_bars=int(music.get("intro_bars", 4)),
        letter_bars=int(music.get("letter_bars", 2)),
        outro_bars=int(music.get("outro_bars", 4)),
        voice_engine=engine,
        voice_speed=float(voice.get("speed", 0.8)),
        voice_pause=float(voice.get("pause", 0.0)),
        recordings=(base / voice.get("recordings", "../giong-thu-am")).resolve(),
        intro=nfc(_require(data, "intro", "kịch bản")),
        outro=nfc(_require(data, "outro", "kịch bản")),
        letters=tuple(letters),
    )


def load(path: Path) -> Lesson:
    with open(path, encoding="utf-8") as f:
        return parse(yaml.safe_load(f), path.parent)
