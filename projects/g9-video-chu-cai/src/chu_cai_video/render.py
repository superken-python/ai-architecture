"""Vẽ từng khung hình bằng Pillow theo dòng thời gian rồi đẩy thẳng vào ffmpeg (không lưu hàng nghìn file ảnh).

Nhân vật chính là các chữ cái (actor.py). Mở đầu: các chữ nhảy lên đứng thành hàng, vẫy tay, rồi nhảy vào hàng chữ
trên cùng. Đến lượt chữ nào, chữ đó nhảy xuống sân khấu, tự giới thiệu, nhìn hình ví dụ hiện trên bảng — con vật thì
nhảy ra khỏi bảng và kêu — rồi nhảy về chỗ. Kết thúc: cả hàng nhảy xuống nhảy múa. Mọi chữ trên hình vẽ từ kịch bản
bằng font thật, nên luôn đúng chính tả và dấu tiếng Việt. Các lớp tĩnh vẽ sẵn một lần; mỗi khung hình chỉ ghép lại.
"""

from __future__ import annotations

import math
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from chu_cai_video import actor, assets, audio, character, config, sfx
from chu_cai_video.actor import Pose
from chu_cai_video.lesson import Lesson, Letter
from chu_cai_video.timeline import Segment, Timeline
from chu_cai_video.voice import Spoken

W, H = config.WIDTH, config.HEIGHT
NAVY = (30, 42, 90)
WHITE = (255, 255, 255)
YELLOW = (255, 212, 59)
ORANGE = (255, 140, 66)
PALETTE = [(232, 65, 79), (242, 124, 30), (47, 168, 79), (43, 125, 233), (123, 76, 224), (224, 69, 123), (19, 150, 160)]

# Bố cục (pixel trên khung 1280×720): chữ cái đứng sân khấu bên trái, bảng học bên phải, hàng chữ cái trên cùng
CHIP_W, CHIP_H, CHIP_GAP, CHIP_Y = 34, 40, 4, 16
CARD_W, CARD_H = 620, 500
CARD_X, CARD_Y = 600, 100
SPLIT_Y = 330  # ranh giới phần chữ cái / phần từ ví dụ trong thẻ
PIC = 140  # cạnh hình minh họa trong thẻ
PIC_C = (CARD_X + 44 + PIC / 2, CARD_Y + SPLIT_Y + (CARD_H - SPLIT_Y) / 2)  # tâm hình minh họa trong thẻ
CALL_C, CALL_SCALE = (530, 300), 1.7  # con vật nhảy ra khỏi thẻ tới đây khi kêu, to lên
STAGE = (260, 612)  # chỗ chữ cái đứng trên sân khấu (điểm chạm đất)
ACTOR_H = 230  # chiều cao thân chữ trên sân khấu
HOP_DOWN, HOP_UP = 0.45, 0.5  # giây: nhảy từ hàng chữ xuống sân khấu / nhảy về
CHAR_BOX = (290, 330)  # khung tối đa của nhân vật dẫn chuyện (Thỏ Bông, Sách Vui) — chỉ ở mở đầu và kết thúc
CHAR_X = {"left": 165, "right": W - 165}
CHAR_FOOT = 668
SUB_Y = 664  # tâm dòng phụ đề
CREDITS = (
    "Giọng đọc: Piper vi_VN vais1000 · dữ liệu VAIS-1000 (CC BY 4.0)",
    "Hình: Noto Emoji (Apache 2.0) · Chữ: Baloo 2 (OFL)",
    "Nhạc và tiếng con vật: tự tổng hợp bằng code",
)


# ───────────────────────────── tiện ích ─────────────────────────────


def clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def ease_out_back(x: float, s: float = 1.7) -> float:
    x = clamp01(x) - 1
    return 1 + (s + 1) * x**3 + s * x**2


def ease_in_out(x: float) -> float:
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def darker(color: tuple[int, int, int], k: float = 0.7) -> tuple[int, int, int]:
    return tuple(int(c * k) for c in color)  # type: ignore[return-value]


class Fonts:
    """Font theo (độ đậm, cỡ), nạp một lần."""

    def __init__(self, files: dict[int, Path | None]) -> None:
        self.files = files
        self.cache: dict[tuple[int, int], ImageFont.FreeTypeFont] = {}

    def __call__(self, weight: int, size: int) -> ImageFont.FreeTypeFont:
        key = (weight, size)
        if key not in self.cache:
            path = self.files.get(weight)
            self.cache[key] = ImageFont.truetype(str(path), size) if path else ImageFont.load_default(size)
        return self.cache[key]


def composite(base: Image.Image, im: Image.Image, x: int, y: int) -> None:
    """Dán ảnh RGBA lên nền tại góc (x, y), tự cắt phần nằm ngoài khung."""
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(base.width, x + im.width), min(base.height, y + im.height)
    if x1 > x0 and y1 > y0:
        base.alpha_composite(im, dest=(x0, y0), source=(x0 - x, y0 - y, x1 - x, y1 - y))


def place(
    base: Image.Image,
    im: Image.Image,
    center: tuple[float, float],
    scale: float = 1.0,
    alpha: float = 1.0,
    angle: float = 0.0,
) -> None:
    """Dán ảnh theo tâm, có co giãn, xoay và độ trong."""
    if scale <= 0.02 or alpha <= 0.02:
        return
    if abs(scale - 1) > 0.004:
        im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.Resampling.BILINEAR)
    if abs(angle) > 0.05:
        im = im.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    if alpha < 0.995:
        im = im.copy()
        im.putalpha(im.getchannel("A").point([int(v * alpha) for v in range(256)]))
    composite(base, im, round(center[0] - im.width / 2), round(center[1] - im.height / 2))


def text_image(
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, ...],
    stroke: int = 0,
    stroke_fill: tuple[int, ...] | None = None,
    shadow: tuple[int, ...] | None = None,
) -> Image.Image:
    """Chữ trên nền trong suốt, cắt sát, có viền và bóng tùy chọn."""
    left, top, right, bottom = font.getbbox(text, stroke_width=stroke)
    pad = stroke + 8
    img = Image.new("RGBA", (right - left + 2 * pad, bottom - top + 2 * pad), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    origin = (pad - left, pad - top)
    if shadow:
        draw.text((origin[0] + 3, origin[1] + 4), text, font=font, fill=shadow, stroke_width=stroke, stroke_fill=shadow)
    draw.text(origin, text, font=font, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill or fill)
    return img


def rounded(size: tuple[int, int], radius: int, fill: tuple[int, ...]) -> Image.Image:
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=fill)
    return img


def note_sprite(color: tuple[int, int, int], double: bool) -> Image.Image:
    """Nốt nhạc vẽ bằng hình học (không phụ thuộc font có ký tự ♪)."""
    img = Image.new("RGBA", (84, 96), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    heads = [(8, 66)] if not double else [(4, 70), (46, 62)]
    for hx, hy in heads:
        d.ellipse((hx, hy, hx + 28, hy + 20), fill=color)
        d.rectangle((hx + 23, hy - 52, hx + 28, hy + 10), fill=color)
    if double:
        d.polygon([(27, 18), (74, 10), (74, 20), (27, 28)], fill=color)
    else:
        d.polygon([(31, 14), (52, 30), (50, 44), (31, 30)], fill=color)
    return img


# ───────────────────────────── chuẩn bị các lớp ─────────────────────────────


@dataclass
class Line:
    """Một câu phụ đề vẽ sẵn: bản chữ trắng, bản chữ vàng và vị trí từng tiếng để tô dần theo lời đọc."""

    white: Image.Image
    yellow: Image.Image
    spans: list[tuple[int, int, int, float]]  # (dòng, x đầu, x cuối, giây bắt đầu đọc tính từ đầu câu)
    rows: list[tuple[int, int]]  # (y đầu, y cuối) của từng dòng trong ảnh
    spoken: Spoken


def word_times(spoken: Spoken) -> list[float]:
    """Ước lượng lúc đọc từng tiếng: chia đều theo số tiếng, dấu câu ngắt thêm; chia đôi tại chỗ ngắt trước từ ví dụ."""
    words = spoken.text.split()
    if not words:
        return []
    weights = [1.0 + (0.6 if w[-1] in ",.!?" else 0.0) for w in words]
    total = spoken.duration
    split = next((i for i, w in enumerate(words) if w.lower() == "như"), None) if spoken.word_at else None
    if split is None or not spoken.word_at:
        parts = [(0, len(words), 0.0, total)]
    else:
        parts = [(0, split, 0.0, spoken.word_at), (split, len(words), spoken.word_at, total)]
    times = [0.0] * len(words)
    for lo, hi, t0, t1 in parts:
        span = sum(weights[lo:hi]) or 1.0
        acc = t0
        for i in range(lo, hi):
            times[i] = acc
            acc += (t1 - t0) * weights[i] / span
    return times


# ───────────────────────────── chuyển động của chữ cái ─────────────────────────────


@dataclass(frozen=True)
class Move:
    """Chỗ đặt nhân vật chữ cái ở một khung hình: điểm chạm đất, độ lớn, độ bẹp (+) / giãn (−)."""

    pos: tuple[float, float]
    scale: float
    squash: float = 0.0


def hop(
    t: float, t0: float, dur: float, a: tuple[float, float], b: tuple[float, float], sa: float, sb: float, lift: float
) -> Move:
    """Nhảy từ a tới b trong `dur` giây theo đường cong (cao thêm `lift` px); giãn người khi bay, độ lớn sa → sb."""
    u = clamp01((t - t0) / dur)
    e = ease_in_out(u)
    x = a[0] + (b[0] - a[0]) * e
    y = a[1] + (b[1] - a[1]) * u - lift * 4 * u * (1 - u)
    return Move((x, y), sa + (sb - sa) * e, -0.45 * math.sin(math.pi * u))


def landing(dt: float) -> float:
    """Độ bẹp `dt` giây sau khi tiếp đất: bẹp mạnh rồi nảy nhẹ, tắt dần."""
    return 0.55 * math.exp(-dt / 0.08) * math.cos(2 * math.pi * dt / 0.24) if 0 <= dt < 0.5 else 0.0


def bump(k: float) -> float:
    """Một nhịp nhún 0 → 1 → 0 khi k đi từ 0 tới 1."""
    return math.sin(math.pi * k) if 0 < k < 1 else 0.0


def blink(t: float, i: int) -> float:
    """Chớp mắt: mỗi chữ một nhịp riêng (3–4,5 giây một lần), mỗi lần 0,14 giây."""
    period = 3.0 + 0.37 * (i % 5)
    k = (t + 0.71 * i) % period
    return max(0.0, 1 - abs(k / 0.07 - 1)) if k < 0.14 else 0.0


def lineup(n: int) -> tuple[list[tuple[float, float]], float]:
    """Chỗ đứng của n chữ cái ở mở đầu và kết thúc (tối đa 10 chữ một hàng, giữa màn hình) và độ lớn của chữ."""
    cols = min(n, 10)
    rows = math.ceil(n / cols)
    scale, dx, dy = (0.42, 150, 0) if n <= 6 else (0.34, 60, 125)
    spots = []
    for i in range(n):
        r, c = divmod(i, cols)
        in_row = min(cols, n - r * cols)
        spots.append((W / 2 + (c - (in_row - 1) / 2) * dx, 470 + (r - (rows - 1) / 2) * dy))
    return spots, scale


def sound_events(lesson: Lesson, timeline: Timeline, spoken: list[Spoken]) -> list[sfx.Event]:
    """Tiếng động theo dòng thời gian: "boing" khi chữ cái tiếp đất, tiếng con vật sau câu đọc của chữ có con vật."""
    by_id = {s.cue_id: s for s in spoken}
    events = []
    for seg in timeline.letter_segments():
        assert seg.letter is not None
        events.append(sfx.Event("boing", seg.start + HOP_DOWN, 0.35))
        line = by_id.get(seg.cue_id)
        if seg.letter.call and line is not None:
            events.append(sfx.Event(seg.letter.call, line.end + sfx.CALL_GAP, 1.0, cue=seg.cue_id))
    return events


# ───────────────────────────── dựng khung hình ─────────────────────────────


class Renderer:
    def __init__(
        self,
        lesson: Lesson,
        timeline: Timeline,
        spoken: list[Spoken],
        music: np.ndarray,
        voice: np.ndarray,
        fonts: Fonts,
        pictures: dict[str, Image.Image | None],
        events: list[sfx.Event] | None = None,
    ) -> None:
        self.lesson, self.timeline, self.fonts = lesson, timeline, fonts
        self.spoken = {s.cue_id: s for s in spoken}
        sr = config.SAMPLE_RATE
        self.music_env = self._env(music.mean(axis=1) if music.ndim == 2 else music, sr)
        self.voice_env = self._env(voice, sr)
        self.bg = self._background()
        self.notes = [note_sprite(c, double=i % 2 == 1) for i, c in enumerate([ORANGE, YELLOW, (92, 215, 255)] * 2)]
        rng = np.random.default_rng(3)
        self.note_params = [
            (rng.uniform(30, W - 30), rng.uniform(16, 34), rng.uniform(0, 1), rng.uniform(0.45, 0.8), i % 6)
            for i in range(14)
        ]
        self.chips = self._chips()
        letters = lesson.letters
        self.actors = {x.letter: actor.LetterActor(x.letter, self._color(x), fonts(800, 400), ACTOR_H) for x in letters}
        self.chip_scale = (CHIP_H - 2) / (ACTOR_H * 1.3)  # chữ cái thu nhỏ vừa ô trong hàng trên cùng
        self.spots, self.spot_scale = lineup(len(letters))
        self.shadow = self._shadow()
        self.pics = {x.letter: self._picture(x, pictures.get(x.letter)) for x in letters}
        self.card = self._card_base()
        self.tops = {x.letter: self._card_top(x) for x in letters}
        self.bottoms = {x.letter: self._card_bottom(x, self.pics[x.letter]) for x in letters}
        self.bottoms_empty = {x.letter: self._card_bottom(x, None) for x in letters}  # lúc con vật nhảy ra ngoài
        self.bubbles = {x.letter: self._bubble(x.call_text) for x in letters if x.call_text}
        self.calls = {e.cue: e for e in (events or []) if e.cue}
        self.call_len = {cue: sfx.sound(e.name, sr).size / sr for cue, e in self.calls.items()}
        self.sprites = {c.name: character.Sprite(c.sprite, CHAR_BOX) for c in lesson.characters}
        self.glows = {c.name: character.glow(int(max(CHAR_BOX) * 1.3), (110, 170, 255)) for c in lesson.characters}
        self.tags = {c.name: self._pill(c.name, ORANGE if c.speaks else (43, 125, 233)) for c in lesson.characters}
        self.appear_at = self._appear_times()
        self.lines = {cue: self._line(s) for cue, s in self.spoken.items()}
        self.title = text_image(lesson.title, fonts(800, 64), WHITE, 5, (226, 88, 34), shadow=(20, 20, 60, 140))
        self.subtitle = text_image(f"cùng {len(letters)} bạn chữ cái", fonts(700, 38), YELLOW, shadow=(20, 20, 60, 140))
        self.bravo = text_image("Giỏi quá!", fonts(800, 84), YELLOW, 5, (200, 80, 20), shadow=(20, 20, 60, 140))
        self.repeat_cue = self._pill("Bé đọc theo nào!", YELLOW, ink=NAVY, size=30)
        self.confetti = [
            (rng.uniform(0, W), rng.uniform(-400, -20), rng.uniform(90, 180), rng.uniform(0, 6.28), PALETTE[i % 7])
            for i in range(70)
        ]
        # Ghi nguồn ở cuối video (giọng đọc CC BY 4.0 bắt buộc ghi nguồn khi đăng).
        credits = CREDITS + (("Thỏ Bông, Sách Vui: video tạo bằng Gemini",) if lesson.characters else ())
        self.credits = [text_image(line, fonts(500, 20), (225, 230, 255)) for line in credits]

    # ── các lớp vẽ sẵn ──
    @staticmethod
    def _env(x: np.ndarray, sr: int) -> np.ndarray:
        level = audio.frame_rms(x, sr, 1 / config.FPS)
        ref = float(np.percentile(level, 95)) if level.size else 1.0
        return np.clip(level / (ref or 1.0), 0, 1)

    @staticmethod
    def _color(x: Letter) -> tuple[int, int, int]:
        return PALETTE[(x.index - 1) % len(PALETTE)]

    def _background(self) -> Image.Image:
        y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        top, bottom = np.array([22, 30, 88], np.float32), np.array([62, 28, 110], np.float32)
        img = np.broadcast_to(top + (bottom - top) * y, (H, W, 3)).copy()
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        for cx, cy, r, color, strength in (
            (W + 60, H + 80, 640, (255, 128, 64), 0.42),
            (-60, -60, 720, (60, 130, 255), 0.30),
        ):
            a = strength * np.clip(1 - np.hypot(xx - cx, yy - cy) / r, 0, 1)[..., None] ** 2
            img = img * (1 - a) + np.array(color, np.float32) * a
        base = Image.fromarray(img.clip(0, 255).astype(np.uint8)).convert("RGBA")
        draw = ImageDraw.Draw(base, "RGBA")
        rng = np.random.default_rng(11)
        for _ in range(70):  # chấm sao li ti
            x, y0, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.8, 2.2)
            draw.ellipse((x - r, y0 - r, x + r, y0 + r), fill=(255, 255, 255, int(rng.uniform(40, 120))))
        return base

    def _chips(self) -> dict[str, dict[str, Image.Image]]:
        font = self.fonts(700, 24)
        out = {}
        for x in self.lesson.letters:
            states = {}
            for state, fill, ink in (
                ("todo", (255, 255, 255, 38), (255, 255, 255, 170)),
                ("done", (255, 255, 255, 220), NAVY),
                ("away", (*YELLOW, 40), (*YELLOW, 120)),  # chữ đang ở sân khấu: ô trống viền vàng
            ):
                chip = rounded((CHIP_W, CHIP_H), 10, fill)
                draw = ImageDraw.Draw(chip)
                if state == "away":
                    draw.rounded_rectangle((1, 1, CHIP_W - 2, CHIP_H - 2), 10, outline=(*YELLOW, 255), width=2)
                draw.text((CHIP_W / 2, CHIP_H / 2 + 1), x.letter, font=font, fill=ink, anchor="mm")
                states[state] = chip
            out[x.letter] = states
        return out

    def _shadow(self) -> Image.Image:
        img = Image.new("RGBA", (240, 60), (0, 0, 0, 0))
        ImageDraw.Draw(img).ellipse((20, 15, 220, 45), fill=(8, 6, 30, 120))
        return img.filter(ImageFilter.GaussianBlur(6))

    def _picture(self, x: Letter, picture: Image.Image | None) -> Image.Image:
        if picture is None:  # không có hình: vòng tròn màu với chữ cái
            color = self._color(x)
            picture = rounded((PIC, PIC), PIC // 2, (*color, 60))
            ImageDraw.Draw(picture).text(
                (PIC / 2, PIC / 2), x.letter, font=self.fonts(800, 90), fill=color, anchor="mm"
            )
        return picture.resize((PIC, PIC), Image.Resampling.LANCZOS)

    def _bubble(self, text: str) -> Image.Image:
        """Bong bóng lời của con vật ("Ụm bò!"), đuôi chỉ xuống bên phải — về phía đầu con vật."""
        label = text_image(text, self.fonts(800, 46), NAVY)
        w, h = label.width + 36, label.height + 14
        img = Image.new("RGBA", (w + 10, h + 44), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((4, 4, 4 + w, 4 + h), radius=h // 2, fill=(*WHITE, 255), outline=(*NAVY, 255), width=4)
        tail = [(0.58 * w, h), (0.78 * w, h), (0.9 * w, h + 38)]
        d.polygon(tail, fill=(*WHITE, 255), outline=(*NAVY, 255), width=4)
        d.line([(0.58 * w + 4, h + 1), (0.78 * w - 4, h + 1)], fill=(*WHITE, 255), width=6)  # xoá viền chỗ nối đuôi
        composite(img, label, 22, 11)
        return img

    def _pill(
        self, text: str, color: tuple[int, int, int], ink: tuple[int, int, int] = WHITE, size: int = 26
    ) -> Image.Image:
        """Nhãn chữ trên nền bo tròn: bảng tên nhân vật, lời nhắc "Bé đọc theo nào!"."""
        label = text_image(text, self.fonts(700, size), ink)
        tag = rounded((label.width + 30, label.height + 2), (label.height + 2) // 2, (*color, 255))
        composite(tag, label, 15, 1)
        return tag

    def _appear_times(self) -> dict[str, float]:
        """Lúc nhân vật dẫn chuyện xuất hiện: khi câu mở đầu nhắc tên (ước lượng theo tiếng), nếu không thì lần lượt."""
        intro = self.spoken.get("mo-dau")
        words = [w.strip(",.!?").lower() for w in intro.text.split()] if intro else []
        times = word_times(intro) if intro else []
        out: dict[str, float] = {}
        for k, c in enumerate(self.lesson.characters):
            name = c.name.lower().split()
            at = next((i for i in range(len(words)) if words[i : i + len(name)] == name), None)
            out[c.name] = intro.start + times[at] - 0.2 if intro and at is not None else 0.3 + 0.4 * k
        return out

    def _card_base(self) -> Image.Image:
        pad = 30
        img = Image.new("RGBA", (CARD_W + 2 * pad, CARD_H + 2 * pad), (0, 0, 0, 0))
        shadow = rounded((CARD_W, CARD_H), 40, (8, 10, 40, 150))
        img.alpha_composite(shadow, (pad + 6, pad + 12))
        img = img.filter(ImageFilter.GaussianBlur(12))
        img.alpha_composite(rounded((CARD_W, CARD_H), 40, (252, 252, 255, 255)), (pad, pad))
        draw = ImageDraw.Draw(img)
        for x in range(pad + 40, pad + CARD_W - 40, 22):  # đường chấm chia hai phần thẻ
            draw.rounded_rectangle((x, pad + SPLIT_Y, x + 11, pad + SPLIT_Y + 4), 2, fill=(205, 212, 235, 255))
        return img

    def _card_top(self, x: Letter) -> Image.Image:
        color = self._color(x)
        canvas = Image.new("RGBA", (CARD_W * 2, 640), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        upper, lower = self.fonts(800, 230), self.fonts(800, 190)
        gap = 26
        total = upper.getlength(x.letter) + gap + lower.getlength(x.lower)
        left, baseline = CARD_W - total / 2, 470
        for text, font, x0 in ((x.letter, upper, left), (x.lower, lower, left + upper.getlength(x.letter) + gap)):
            draw.text((x0 + 5, baseline + 7), text, font=font, fill=(*darker(color, 0.55), 110), anchor="ls")
            draw.text((x0, baseline), text, font=font, fill=color, anchor="ls")
        letters = canvas.crop(canvas.getbbox())
        top = Image.new("RGBA", (CARD_W, SPLIT_Y), (0, 0, 0, 0))
        scale = min(1.0, 250 / letters.height, (CARD_W - 60) / letters.width)
        if scale < 1:
            size = (round(letters.width * scale), round(letters.height * scale))
            letters = letters.resize(size, Image.Resampling.LANCZOS)
        composite(top, letters, (CARD_W - letters.width) // 2, 248 - letters.height)
        label = text_image(f"đọc là: {x.sound}", self.fonts(700, 34), NAVY)
        pill = rounded((label.width + 36, label.height + 2), (label.height + 2) // 2, (*color, 46))
        composite(pill, label, 18, 1)
        composite(top, pill, (CARD_W - pill.width) // 2, 262)
        return top

    def _card_bottom(self, x: Letter, pic: Image.Image | None) -> Image.Image:
        color = self._color(x)
        bottom = Image.new("RGBA", (CARD_W, CARD_H - SPLIT_Y), (0, 0, 0, 0))
        if pic is not None:
            composite(bottom, pic, 44, (bottom.height - PIC) // 2)
        lo, hi = x.highlight()
        before, mark, after = x.phrase[:lo], x.phrase[lo:hi], x.phrase[hi:]
        room = CARD_W - 230
        size_px = 70
        font = self.fonts(800, size_px)
        while font.getlength(x.phrase) > room and size_px > 36:
            size_px -= 4
            font = self.fonts(800, size_px)
        width = font.getlength(x.phrase)
        text = Image.new("RGBA", (int(width) + 20, size_px * 2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text)
        baseline = int(size_px * 1.3)
        cursor = 10.0
        for k, (part, ink) in enumerate(((before, NAVY), (mark, color), (after, NAVY))):
            if part:
                draw.text((cursor, baseline), part, font=font, fill=ink, anchor="ls")
            if k == 1:  # gạch chân chữ cái đang học
                w = font.getlength(mark)
                draw.rounded_rectangle((cursor, baseline + 8, cursor + w, baseline + 15), 3, fill=color)
            cursor += font.getlength(part)
        text = text.crop(text.getbbox())
        composite(bottom, text, 210 + (room - text.width) // 2, (bottom.height - text.height) // 2)
        return bottom

    def _line(self, spoken: Spoken) -> Line:
        font = self.fonts(700, 32)
        words = spoken.text.split()
        times = word_times(spoken)
        space = font.getlength(" ")
        # Ở mở đầu và kết thúc, phụ đề lọt giữa hai nhân vật dẫn chuyện đứng hai góc.
        limit = 560 if self.lesson.characters and spoken.segment.letter is None else W - 200
        rows: list[list[int]] = [[]]
        width = 0.0
        for i, w in enumerate(words):  # mỗi câu một dòng (hiện lần lượt), câu quá dài thì xuống dòng
            wl = font.getlength(w)
            if rows[-1] and width + space + wl > limit:
                rows.append([])
                width = 0.0
            width += (space if rows[-1] else 0) + wl
            rows[-1].append(i)
            if w[-1] in ".!?" and i < len(words) - 1:
                rows.append([])
                width = 0.0
        ascent, descent = font.getmetrics()
        row_h = ascent + descent + 4
        img_w = int(max(sum(font.getlength(words[i]) for i in r) + space * (len(r) - 1) for r in rows)) + 24
        white = Image.new("RGBA", (img_w, row_h * len(rows) + 12), (0, 0, 0, 0))
        yellow = white.copy()
        dw, dy = ImageDraw.Draw(white), ImageDraw.Draw(yellow)
        spans, row_box = [], []
        for r, idx in enumerate(rows):
            line_w = sum(font.getlength(words[i]) for i in idx) + space * (len(idx) - 1)
            x = (img_w - line_w) / 2
            y = 6 + r * row_h
            row_box.append((y, y + row_h))
            for i in idx:
                for draw, ink in ((dw, WHITE), (dy, YELLOW)):
                    draw.text((x + 2, y + 3), words[i], font=font, fill=(10, 12, 40, 160))
                    draw.text((x, y), words[i], font=font, fill=ink)
                wl = font.getlength(words[i])
                spans.append((r, int(x), int(x + wl + space), times[i]))
                x += wl + space
        return Line(white, yellow, spans, row_box, spoken)

    # ── vẽ một khung hình ──
    def env_at(self, env: np.ndarray, t: float) -> float:
        i = int(t * config.FPS)
        return float(env[i]) if 0 <= i < env.size else 0.0

    def frame(self, t: float) -> Image.Image:
        tl = self.timeline
        seg = tl.at(t)
        img = self.bg.copy()
        draw = ImageDraw.Draw(img, "RGBA")
        self._draw_notes(img, t)
        self._draw_bars(draw, t)
        if seg.kind == "intro":
            self._draw_intro(img, t, seg)
        elif seg.kind == "letter":
            out = self.call_out(t, seg)
            self._draw_chips(img, t, seg)
            self._draw_card(img, t, seg, picture_out=out > 0.02)
            self._draw_stage(img, t, seg)
            self._draw_call(img, t, seg, out)
            self._draw_repeat(img, t, seg)
        else:
            self._draw_outro(img, t, seg)
        if seg.kind != "letter":
            self._draw_characters(img, t, seg)
        self._draw_subtitle(img, draw, t, seg)
        fade = clamp01((t - (tl.segments[-1].end - 0.6)) / 0.6)
        if fade > 0:
            img = Image.blend(img, Image.new("RGBA", img.size, (8, 8, 24, 255)), fade)
        return img.convert("RGB")

    def _draw_notes(self, img: Image.Image, t: float) -> None:
        for i, (x0, speed, phase, size, sprite) in enumerate(self.note_params):
            span = H + 160
            y = H + 80 - ((t * speed + phase * span) % span)
            x = x0 + 16 * math.sin(t * 0.9 + i)
            edge = clamp01(min(y + 60, H + 60 - y) / 140)
            place(img, self.notes[sprite], (x, y), scale=size, alpha=0.32 * edge, angle=10 * math.sin(t + i))

    def _draw_bars(self, draw: ImageDraw.ImageDraw, t: float) -> None:
        level = self.env_at(self.music_env, t)
        n = 64
        w = W / n
        for i in range(n):
            wave = (0.5 + 0.5 * math.sin(i * 0.9 + t * 7.1 + 3 * math.sin(i * 0.37))) ** 2
            h = 4 + 50 * level * (0.2 + 0.8 * wave)
            draw.rounded_rectangle((i * w + 3, H - h, (i + 1) * w - 3, H + 6), 4, fill=(110, 200, 255, 42))

    def _draw_actor(self, img: Image.Image, x: Letter, pose: Pose, move: Move) -> None:
        im, feet = self.actors[x.letter].draw(pose)
        actor.place_actor(img, im, feet, move.pos, move.scale, move.squash)

    # ── hàng chữ cái trên cùng ──
    def chip_center(self, x: Letter) -> tuple[float, float]:
        n = len(self.lesson.letters)
        x0 = (W - (n * CHIP_W + (n - 1) * CHIP_GAP)) / 2
        return x0 + (x.index - 1) * (CHIP_W + CHIP_GAP) + CHIP_W / 2, CHIP_Y + CHIP_H / 2

    def _chip_feet(self, x: Letter) -> tuple[float, float]:
        cx, _ = self.chip_center(x)
        return cx, CHIP_Y + CHIP_H - 1

    def _steps(self) -> tuple[float, float]:
        """Khoảng cách thời gian giữa hai chữ liên tiếp khi nhảy ra đứng hàng, khi nhảy vào/ra hàng chữ trên cùng."""
        n = len(self.lesson.letters)
        return min(0.12, 2.4 / n), min(0.05, 0.9 / n)

    def _intro_times(self, x: Letter, seg: Segment) -> tuple[float, float]:
        """(lúc nhảy ra chỗ đứng, lúc nhảy lên hàng chữ trên cùng) của chữ x ở mở đầu."""
        step_in, step_up = self._steps()
        i = x.index - 1
        return 0.9 + i * step_in, seg.end - 1.3 + i * step_up

    def _outro_time(self, x: Letter, seg: Segment) -> float:
        """Lúc chữ x rời hàng chữ trên cùng, nhảy xuống nhảy múa ở kết thúc."""
        return seg.start + 0.15 + (x.index - 1) * self._steps()[1]

    def _draw_chips(self, img: Image.Image, t: float, seg: Segment) -> None:
        for x in self.lesson.letters:
            if seg.kind == "intro":
                state = "todo" if t >= self._intro_times(x, seg)[1] + HOP_UP else None
            elif seg.kind == "outro":
                state = "done" if t < self._outro_time(x, seg) else None
            else:
                assert seg.letter is not None
                current = seg.letter.index
                state = "done" if x.index < current else "todo" if x.index > current else "away"
                if x.index == current and t >= seg.end - 0.05:
                    state = "done"
            if state:
                place(img, self.chips[x.letter][state], self.chip_center(x))

    # ── mở đầu ──
    def _draw_intro(self, img: Image.Image, t: float, seg: Segment) -> None:
        hide = 1 - clamp01((t - (seg.end - 1.6)) / 0.4)  # tiêu đề mờ đi trước khi các chữ nhảy lên hàng trên cùng
        place(img, self.title, (W / 2, 82), scale=ease_out_back((t - 0.15) / 0.45), alpha=hide)
        place(img, self.subtitle, (W / 2, 148), scale=ease_out_back((t - 0.55) / 0.4), alpha=hide)
        self._draw_chips(img, t, seg)
        phase = self.timeline.beat_phase(t)
        for x in self.lesson.letters:
            i = x.index - 1
            spot = self.spots[i]
            t_in, t_up = self._intro_times(x, seg)
            if t < t_in or t >= t_up + HOP_UP:
                continue
            if t < t_in + HOP_DOWN:  # nhảy từ dưới lên chỗ đứng
                move = hop(t, t_in, HOP_DOWN, (spot[0], H + 160), spot, self.spot_scale, self.spot_scale, 160)
                pose = Pose(cheer=0.7, look=(0.0, -0.4))
            elif t < t_up:  # đứng thành hàng, vẫy tay, nhún theo nhạc
                bob = 6 * math.sin(math.pi * ((phase + 0.5 * (i % 2)) % 1)) ** 2
                move = Move((spot[0], spot[1] - bob), self.spot_scale, landing(t - t_in - HOP_DOWN))
                pose = Pose(wave=0.6 * t + 0.3 * i, blink=blink(t, i), cheer=0.25 + 0.2 * (i % 2))
            else:  # nhảy lên hàng chữ trên cùng
                move = hop(t, t_up, HOP_UP, spot, self._chip_feet(x), self.spot_scale, self.chip_scale, 120)
                pose = Pose(cheer=0.6, look=(0.0, -0.7))
            self._draw_actor(img, x, pose, move)

    # ── từng chữ cái ──
    def repeat_window(self, seg: Segment) -> tuple[float, float] | None:
        """Khoảng "bé đọc theo": từ lúc phụ đề câu đọc tắt tới gần hết khúc nhạc của chữ (None nếu quá ngắn).

        Chữ có tiếng con vật thì không có: con vật kêu đã chiếm chỗ đó."""
        spoken = self.spoken.get(seg.cue_id)
        if seg.letter is None or spoken is None or seg.cue_id in self.calls:
            return None
        start, end = spoken.end + 0.75, seg.end - 0.3
        return (start, end) if end - start >= 1.0 else None

    def _draw_repeat(self, img: Image.Image, t: float, seg: Segment) -> None:
        window = self.repeat_window(seg)
        if window and window[0] <= t < window[1]:
            show = clamp01((window[1] - t) / 0.2)
            place(img, self.repeat_cue, (W / 2, SUB_Y), scale=ease_out_back((t - window[0]) / 0.35), alpha=show)

    def _draw_stage(self, img: Image.Image, t: float, seg: Segment) -> None:
        """Chữ cái đang học: nhảy xuống sân khấu, tự giới thiệu, nhìn hình ví dụ và con vật, rồi nhảy về chỗ."""
        x = seg.letter
        assert x is not None
        i = x.index - 1
        land_at, up_at = seg.start + HOP_DOWN, seg.end - HOP_UP - 0.05
        phase = self.timeline.beat_phase(t)
        if t < land_at:
            move = hop(t, seg.start, HOP_DOWN, self._chip_feet(x), STAGE, self.chip_scale, 1.0, 110)
            pose = Pose(cheer=0.6, look=(0.0, 0.5))
        elif t >= up_at:
            move = hop(t, up_at, HOP_UP, STAGE, self._chip_feet(x), 1.0, self.chip_scale, 110)
            pose = Pose(cheer=0.6, look=(0.0, -0.8))
        else:
            spoken = self.spoken.get(seg.cue_id)
            talking = spoken is not None and spoken.start <= t <= spoken.end
            look, cheer, jump = (0.25, 0.0), 0.0, 0.0
            if spoken is not None and spoken.word_at:  # từ ví dụ hiện trên thẻ: quay sang nhìn, nhún một cái
                shown_at = spoken.start + spoken.word_at
                look = (1.0, 0.3) if t >= shown_at else look
                jump += 22 * bump((t - shown_at) / 0.45)
            call = self.calls.get(seg.cue_id)
            if call is not None and t >= call.at - 0.3:  # con vật nhảy ra: nhìn theo, giơ tay, nhảy cẫng lên
                look = (1.0, -0.5)
                cheer = 0.9 if t < call.at + self.call_len[seg.cue_id] + 0.2 else 0.3
                jump += 34 * bump((t - call.at) / 0.5)
            window = self.repeat_window(seg)
            if window and window[0] <= t < window[1]:  # bé đọc theo: nhìn bé, nhún theo phách
                look, cheer = (0.0, 0.0), 0.35
            bob = 4 * math.sin(math.pi * phase) ** 2
            talk = self.env_at(self.voice_env, t) if talking else 0.0
            move = Move((STAGE[0], STAGE[1] - bob - jump), 1.0, landing(t - land_at))
            pose = Pose(talk=talk, blink=blink(t, i), look=look, cheer=cheer, wave=0.35 * t)
        height = STAGE[1] - move.pos[1]
        if move.scale > 0.5:  # bóng trên sàn, nhỏ đi khi nhảy lên cao
            place(img, self.shadow, (STAGE[0], STAGE[1] + 2), scale=max(0.4, 1 - height / 300), alpha=move.scale)
        self._draw_actor(img, x, pose, move)

    def call_out(self, t: float, seg: Segment) -> float:
        """Con vật đã nhảy ra khỏi thẻ bao xa: 0 = còn trong thẻ, 1 = đứng ngoài, cạnh chữ cái."""
        call = self.calls.get(seg.cue_id)
        if call is None:
            return 0.0
        out_at, back_at = call.at - 0.3, call.at + self.call_len[seg.cue_id] + 0.15
        if t < out_at or t > back_at + 0.35:
            return 0.0
        return ease_out_back((t - out_at) / 0.35) if t < back_at else 1 - ease_in_out((t - back_at) / 0.35)

    def _draw_call(self, img: Image.Image, t: float, seg: Segment, k: float) -> None:
        if k <= 0.02:
            return
        x, call = seg.letter, self.calls[seg.cue_id]
        assert x is not None
        length = self.call_len[seg.cue_id]
        calling = call.at <= t < call.at + length
        pos = (PIC_C[0] + (CALL_C[0] - PIC_C[0]) * k, PIC_C[1] + (CALL_C[1] - PIC_C[1]) * k)
        lift = 14 * abs(math.sin(2 * math.pi * 2.5 * (t - call.at))) if calling else 0.0
        angle = 7 * math.sin(2 * math.pi * 4 * (t - call.at)) if calling else 0.0
        place(img, self.pics[x.letter], (pos[0], pos[1] - lift), scale=1 + (CALL_SCALE - 1) * k, angle=angle)
        bubble = self.bubbles.get(x.letter)
        if bubble is not None and t >= call.at:
            show = clamp01((call.at + length + 0.15 - t) / 0.2)
            size = PIC * CALL_SCALE  # bong bóng ở phía trên bên trái con vật, tránh hàng chữ cái trên cùng
            spot = (pos[0] - 0.3 * size - 0.35 * bubble.width, pos[1] - 0.5 * size - 0.5 * bubble.height)
            place(img, bubble, spot, scale=ease_out_back((t - call.at) / 0.3), alpha=show)

    def _draw_card(self, img: Image.Image, t: float, seg: Segment, picture_out: bool) -> None:
        letter = seg.letter
        assert letter is not None
        first = self.timeline.letter_segments()[0]
        enter = ease_out_back((t - first.start) / 0.45)
        card_cx, card_cy = CARD_X + CARD_W / 2, CARD_Y + CARD_H / 2
        place(img, self.card, (card_cx, card_cy + 40 * (1 - enter)), scale=0.85 + 0.15 * enter, alpha=clamp01(enter))
        leave = clamp01((t - (seg.end - 0.14)) / 0.14)
        k = (t - seg.start) / 0.35
        window = self.repeat_window(seg)
        beat = 0.07 * (1 - self.timeline.beat_phase(t)) ** 2 if window and window[0] <= t < window[1] else 0.0
        place(
            img,
            self.tops[letter.letter],
            (card_cx, CARD_Y + SPLIT_Y / 2),
            scale=(0.6 + 0.4 * ease_out_back(k)) * (1 - 0.15 * leave) * (1 + beat),  # lúc bé đọc theo: nảy theo phách
            alpha=clamp01((t - seg.start) / 0.12) * (1 - leave),
        )
        spoken = self.spoken.get(seg.cue_id)
        word_at = seg.voice_at + (spoken.word_at if spoken and spoken.word_at else 1.0) - 0.05
        k = (t - word_at) / 0.35
        if k > 0:
            bottoms = self.bottoms_empty if picture_out else self.bottoms
            place(
                img,
                bottoms[letter.letter],
                (card_cx, CARD_Y + SPLIT_Y + (CARD_H - SPLIT_Y) / 2 + 30 * (1 - ease_out_back(k))),
                scale=(0.5 + 0.5 * ease_out_back(k)) * (1 - 0.15 * leave),
                alpha=clamp01(k * 3) * (1 - leave),
            )

    # ── kết thúc ──
    def _draw_outro(self, img: Image.Image, t: float, seg: Segment) -> None:
        local = t - seg.start
        draw = ImageDraw.Draw(img, "RGBA")
        for x, y0, speed, spin, color in self.confetti:  # giấy màu rơi
            y = y0 + local * speed
            if -20 < y < H + 20:
                a = spin + local * 3
                pts = [(x + 8 * math.cos(a + k * math.pi / 2), y + 5 * math.sin(a + k * math.pi / 2)) for k in range(4)]
                draw.polygon(pts, fill=(*color, 220))
        place(img, self.bravo, (W / 2, 80), scale=ease_out_back((local - 0.1) / 0.45))
        self._draw_chips(img, t, seg)
        phase = self.timeline.beat_phase(t)
        for x in self.lesson.letters:
            i = x.index - 1
            t_down = self._outro_time(x, seg)
            if t < t_down:
                continue
            spot = self.spots[i]
            if t < t_down + HOP_DOWN:
                move = hop(t, t_down, HOP_DOWN, self._chip_feet(x), spot, self.chip_scale, self.spot_scale, 90)
                pose = Pose(cheer=0.7, look=(0.0, 0.5))
            else:  # nhảy múa: nảy theo phách, hai hàng xen kẽ, giơ tay
                ph = (phase + 0.5 * (i % 2)) % 1
                move = Move((spot[0], spot[1] - 26 * bump(ph)), self.spot_scale, 0.4 * max(0.0, 1 - ph / 0.12))
                pose = Pose(cheer=0.8 + 0.2 * math.sin(2 * math.pi * ph), blink=blink(t, i), wave=t + 0.2 * i)
            self._draw_actor(img, x, pose, move)
        spoken = self.spoken.get(seg.cue_id)
        after = (spoken.end + 0.7) if spoken else seg.start + 3.0  # sau khi phụ đề câu kết đã tắt
        for k, line in enumerate(self.credits):  # dưới chữ "Giỏi quá!", trên các chữ cái đang nhảy múa
            place(img, line, (W / 2, 150 + 24 * k), alpha=clamp01((t - after) / 0.3))

    # ── nhân vật dẫn chuyện (Thỏ Bông, Sách Vui): chỉ ở mở đầu và kết thúc ──
    def _draw_characters(self, img: Image.Image, t: float, seg: Segment) -> None:
        """Đứng hai góc dưới: người đọc nhún theo giọng, bạn kia nhún theo phách; rời đi cuối phần mở đầu."""
        talk = self.env_at(self.voice_env, t)
        phase = self.timeline.beat_phase(t)
        beat_hop = (16 if seg.kind == "outro" else 6) * math.sin(math.pi * phase) ** 2
        for i, c in enumerate(self.lesson.characters):
            if seg.kind == "intro":
                appear = ease_out_back((t - self.appear_at[c.name]) / 0.5) * (
                    1 - ease_in_out((t - (seg.end - 0.9)) / 0.5)
                )
            else:
                appear = ease_out_back((t - seg.start - 0.4 - 0.25 * i) / 0.5)
            if appear <= 0.02:
                continue
            sprite = self.sprites[c.name]
            frame = sprite.at(t + 1.3 * i)  # lệch pha: hai nhân vật không cử động giống hệt nhau
            h = sprite.size[1]
            cx = CHAR_X[c.side]
            if c.speaks:
                hop_, scale, angle = beat_hop * 0.5, 1 + 0.05 * talk, 3 * talk * math.sin(t * 15)
                shine = 0.3 + 0.45 * talk
            else:
                hop_, scale, angle, shine = beat_hop, 1.0, 0.0, 0.3
            place(img, self.glows[c.name], (cx, CHAR_FOOT - h / 2), scale=appear, alpha=shine)
            place(img, frame, (cx, CHAR_FOOT - h / 2 - hop_), scale=scale * appear, angle=angle)
            place(img, self.tags[c.name], (cx, CHAR_FOOT + 22), scale=appear)

    def _draw_subtitle(self, img: Image.Image, draw: ImageDraw.ImageDraw, t: float, seg: Segment) -> None:
        line = self.lines.get(seg.cue_id)
        if line is None:
            return
        s = line.spoken
        show = clamp01((t - (s.start - 0.15)) / 0.15) * clamp01((min(s.end + 0.6, seg.end - 0.05) - t) / 0.15)
        if show <= 0:
            return
        reached = [sp for sp in line.spans if t - s.start >= sp[3]]  # các tiếng đã đọc tới
        row, x_end = (reached[-1][0], reached[-1][2]) if reached else (0, 0)  # dòng đang đọc, chỗ đọc tới
        y0, y1 = line.rows[row]
        spans = [(a, b) for r, a, b, _ in line.spans if r == row]
        left, right = spans[0][0], spans[-1][1]
        white = line.white.crop((left, y0, right, y1))
        x = (W - white.width) // 2
        y = round(SUB_Y - white.height / 2)
        draw.rounded_rectangle(
            (x - 18, y - 4, x + white.width + 12, y + white.height + 4), 22, fill=(10, 14, 50, int(120 * show))
        )
        place(img, white, (x + white.width / 2, y + white.height / 2), alpha=show)
        if x_end > left:
            part = line.yellow.crop((left, y0, min(x_end, right), y1))
            if show < 0.995:
                part.putalpha(part.getchannel("A").point([int(v * show) for v in range(256)]))
            composite(img, part, x, y)


# ───────────────────────────── xuất video ─────────────────────────────


def pictures_for(lesson: Lesson) -> dict[str, Image.Image | None]:
    """Hình minh họa của từng chữ: ảnh riêng trong kịch bản, hoặc Noto Emoji (tải một lần)."""
    out: dict[str, Image.Image | None] = {}
    for x in lesson.letters:
        path = x.image or (assets.emoji_png(x.emoji) if x.emoji else None)
        out[x.letter] = Image.open(path).convert("RGBA") if path else None
    return out


def ffmpeg_path() -> str:
    found = shutil.which("ffmpeg")
    if not found:
        raise RuntimeError("Chưa có ffmpeg — cài: macOS `brew install ffmpeg`, Ubuntu `sudo apt install ffmpeg`")
    return found


def encode(
    renderer: Renderer, wav: Path, out: Path, start: float = 0.0, end: float | None = None, crf: int = 27
) -> None:
    """Vẽ khung hình [start, end) và mã hoá H.264 + AAC (MP4 phát được trên mọi trình duyệt, tua được ngay)."""
    end = renderer.timeline.duration if end is None else min(end, renderer.timeline.duration)
    frames = int(round((end - start) * config.FPS))
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_path(), "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(config.FPS), "-i", "-",
        "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", str(wav),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-tune", "animation", "-crf", str(crf), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-shortest", str(out),
    ]  # fmt: skip
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    began = time.monotonic()
    try:
        for f in range(frames):
            proc.stdin.write(renderer.frame(start + f / config.FPS).tobytes())
            if f % (config.FPS * 10) == 0:
                print(f"  khung {f}/{frames} · {time.monotonic() - began:.0f}s", flush=True)
    finally:
        proc.stdin.close()
        code = proc.wait()
    if code != 0:
        raise RuntimeError(f"ffmpeg lỗi (mã {code})")
