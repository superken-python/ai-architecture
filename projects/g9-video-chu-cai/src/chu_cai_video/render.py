"""Vẽ từng khung hình bằng Pillow theo dòng thời gian rồi đẩy thẳng vào ffmpeg (không lưu hàng nghìn file ảnh).

Mọi chữ trên hình được vẽ từ kịch bản bằng font thật, nên luôn đúng chính tả và dấu tiếng Việt. Các lớp tĩnh (nền, thẻ
chữ, phụ đề, nhân vật) vẽ sẵn một lần; mỗi khung hình chỉ ghép lại với vị trí, độ lớn, độ trong theo thời gian.
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

from chu_cai_video import assets, audio, character, config
from chu_cai_video.lesson import Lesson, Letter
from chu_cai_video.timeline import Segment, Timeline
from chu_cai_video.voice import Spoken

W, H = config.WIDTH, config.HEIGHT
NAVY = (30, 42, 90)
WHITE = (255, 255, 255)
YELLOW = (255, 212, 59)
ORANGE = (255, 140, 66)
PALETTE = [(232, 65, 79), (242, 124, 30), (47, 168, 79), (43, 125, 233), (123, 76, 224), (224, 69, 123), (19, 150, 160)]

# Bố cục (pixel trên khung 1280×720): bảng học ở giữa, hai nhân vật đứng hai góc dưới, phụ đề giữa hai nhân vật
CHIP_W, CHIP_H, CHIP_GAP, CHIP_Y = 34, 40, 4, 16
CARD_W, CARD_H = 620, 500
CARD_X, CARD_Y = (W - CARD_W) // 2, 100
SPLIT_Y = 330  # ranh giới phần chữ cái / phần từ ví dụ trong thẻ
CHAR_BOX = (290, 330)  # khung tối đa của mỗi nhân vật (rộng, cao)
CHAR_X = {"left": CARD_X / 2, "right": W - CARD_X / 2}  # tâm ngang nhân vật: giữa khoảng trống hai bên bảng
CHAR_FOOT = 668  # chân nhân vật; bảng tên ngay bên dưới
DISC_C, DISC_D = (W / 2, 400), 200  # đĩa chữ "Aa" giữa màn hình lúc mở đầu: tâm, đường kính
SUB_Y, SUB_W = 664, 600  # tâm dòng phụ đề, bề ngang tối đa (lọt giữa hai nhân vật)
CREDITS = (
    "Giọng đọc: Piper vi_VN vais1000 · dữ liệu VAIS-1000 (CC BY 4.0)",
    "Nhân vật: tạo bằng Gemini · Hình: Noto Emoji (Apache 2.0)",
    "Chữ: Baloo 2 (OFL) · Nhạc: tự tổng hợp bằng code",
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
        self.sprites = {c.name: character.Sprite(c.sprite, CHAR_BOX) for c in lesson.characters}
        self.glows = {c.name: character.glow(int(max(CHAR_BOX) * 1.3), (110, 170, 255)) for c in lesson.characters}
        self.tags = {c.name: self._pill(c.name, ORANGE if c.speaks else (43, 125, 233)) for c in lesson.characters}
        self.appear_at = self._appear_times()
        self.disc = self._disc()
        self.card = self._card_base()
        self.tops = {x.letter: self._card_top(x) for x in lesson.letters}
        self.bottoms = {x.letter: self._card_bottom(x, pictures.get(x.letter)) for x in lesson.letters}
        self.lines = {cue: self._line(s) for cue, s in self.spoken.items()}
        self.title = text_image(lesson.title, fonts(800, 64), WHITE, 5, (226, 88, 34), shadow=(20, 20, 60, 140))
        names = " và ".join(c.name for c in lesson.characters)
        self.subtitle = text_image(f"cùng {names}", fonts(700, 38), YELLOW, shadow=(20, 20, 60, 140))
        self.bravo = text_image("Giỏi quá!", fonts(800, 84), YELLOW, 5, (200, 80, 20), shadow=(20, 20, 60, 140))
        self.repeat_cue = self._pill("Bé đọc theo nào!", YELLOW, ink=NAVY, size=30)
        self.orbit = [self._ball(x, PALETTE[i % len(PALETTE)], 64, 36) for i, x in enumerate(lesson.letters[:8])]
        self.grid = [
            self._ball(x, PALETTE[i % len(PALETTE)], 80, 50, square=True) for i, x in enumerate(lesson.letters)
        ]
        self.confetti = [
            (rng.uniform(0, W), rng.uniform(-400, -20), rng.uniform(90, 180), rng.uniform(0, 6.28), PALETTE[i % 7])
            for i in range(70)
        ]
        # Ghi nguồn ở cuối video (giọng đọc CC BY 4.0 bắt buộc ghi nguồn khi đăng).
        self.credits = [text_image(line, fonts(500, 20), (225, 230, 255)) for line in CREDITS]

    # ── các lớp vẽ sẵn ──
    @staticmethod
    def _env(x: np.ndarray, sr: int) -> np.ndarray:
        level = audio.frame_rms(x, sr, 1 / config.FPS)
        ref = float(np.percentile(level, 95)) if level.size else 1.0
        return np.clip(level / (ref or 1.0), 0, 1)

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
                ("now", (*YELLOW, 255), NAVY),
            ):
                chip = rounded((CHIP_W, CHIP_H), 10, fill)
                ImageDraw.Draw(chip).text((CHIP_W / 2, CHIP_H / 2 + 1), x.letter, font=font, fill=ink, anchor="mm")
                states[state] = chip
            out[x.letter] = states
        return out

    def _pill(
        self, text: str, color: tuple[int, int, int], ink: tuple[int, int, int] = WHITE, size: int = 26
    ) -> Image.Image:
        """Nhãn chữ trên nền bo tròn: bảng tên nhân vật, lời nhắc "Bé đọc theo nào!"."""
        label = text_image(text, self.fonts(700, size), ink)
        tag = rounded((label.width + 30, label.height + 2), (label.height + 2) // 2, (*color, 255))
        composite(tag, label, 15, 1)
        return tag

    def _appear_times(self) -> dict[str, float]:
        """Lúc mỗi nhân vật xuất hiện: khi câu mở đầu nhắc tới tên (ước lượng theo tiếng), không có tên thì lần lượt."""
        intro = self.spoken.get("mo-dau")
        words = [w.strip(",.!?").lower() for w in intro.text.split()] if intro else []
        times = word_times(intro) if intro else []
        out: dict[str, float] = {}
        for k, c in enumerate(self.lesson.characters):
            name = c.name.lower().split()
            at = next((i for i in range(len(words)) if words[i : i + len(name)] == name), None)
            out[c.name] = intro.start + times[at] - 0.2 if intro and at is not None else 0.3 + 0.4 * k
        return out

    def _disc(self) -> Image.Image:
        """Đĩa trắng có chữ "Aa" — biểu tượng của bài học, đứng giữa màn hình lúc mở đầu."""
        pad = 30
        size = DISC_D + 2 * pad
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ImageDraw.Draw(img).ellipse((pad + 4, pad + 10, pad + DISC_D + 4, pad + DISC_D + 10), fill=(8, 10, 40, 150))
        img = img.filter(ImageFilter.GaussianBlur(10))
        draw = ImageDraw.Draw(img)
        draw.ellipse((pad, pad, pad + DISC_D, pad + DISC_D), fill=(252, 252, 255, 255))
        draw.ellipse((pad + 10, pad + 10, pad + DISC_D - 10, pad + DISC_D - 10), outline=(*YELLOW, 255), width=6)
        font = self.fonts(800, 120)
        gap = 4
        total = font.getlength("A") + gap + font.getlength("a")
        x0 = size / 2 - total / 2
        baseline = size / 2 + 42
        for text, x, color in (("A", x0, PALETTE[0]), ("a", x0 + font.getlength("A") + gap, PALETTE[3])):
            draw.text((x + 4, baseline + 5), text, font=font, fill=(*darker(color, 0.55), 110), anchor="ls")
            draw.text((x, baseline), text, font=font, fill=color, anchor="ls")
        return img

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
        color = PALETTE[(x.index - 1) % len(PALETTE)]
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

    def _card_bottom(self, x: Letter, picture: Image.Image | None) -> Image.Image:
        color = PALETTE[(x.index - 1) % len(PALETTE)]
        bottom = Image.new("RGBA", (CARD_W, CARD_H - SPLIT_Y), (0, 0, 0, 0))
        size = 140
        if picture is None:  # không có hình: vòng tròn màu với chữ cái
            picture = rounded((size, size), size // 2, (*color, 60))
            ImageDraw.Draw(picture).text(
                (size / 2, size / 2), x.letter, font=self.fonts(800, 90), fill=color, anchor="mm"
            )
        pic = picture.resize((size, size), Image.Resampling.LANCZOS)
        composite(bottom, pic, 44, (bottom.height - size) // 2)
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
        rows: list[list[int]] = [[]]
        width = 0.0
        for i, w in enumerate(words):  # mỗi câu một dòng (hiện lần lượt), câu quá dài thì xuống dòng
            wl = font.getlength(w)
            if rows[-1] and width + space + wl > SUB_W - 40:
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

    def _ball(
        self, x: Letter, color: tuple[int, int, int], size: int, font_px: int, square: bool = False
    ) -> Image.Image:
        img = rounded((size, size), 18 if square else size // 2, (*color, 255))
        ImageDraw.Draw(img).text(
            (size / 2, size / 2 + 2), x.letter, font=self.fonts(800, font_px), fill=WHITE, anchor="mm"
        )
        return img

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
        intro = tl.segments[0]
        outro = tl.segments[-1]
        to_main = ease_in_out((t - (intro.end - 0.8)) / 0.8)  # cuối phần mở đầu: tiêu đề và đĩa chữ mờ dần
        if seg.kind == "intro":
            self._draw_orbit(img, t, to_main, front=False)
            self._draw_disc(img, t, to_main)
            self._draw_orbit(img, t, to_main, front=True)
            self._draw_intro(img, t, to_main)
        if seg.kind == "letter" or (seg.kind == "intro" and to_main > 0):
            self._draw_chips(img, t, seg, to_main)
        if seg.kind == "letter":
            self._draw_card(img, t, seg)
            self._draw_repeat(img, t, seg)
        if seg.kind == "outro":
            self._draw_outro(img, t, seg)
        self._draw_characters(img, t, seg)
        self._draw_subtitle(img, draw, t, seg)
        fade = clamp01((t - (outro.end - 0.6)) / 0.6)
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

    def _draw_characters(self, img: Image.Image, t: float, seg: Segment) -> None:
        """Hai nhân vật ở hai góc dưới: người đọc nhún theo giọng; bạn kia nhún theo phách, nhảy khi hiện từ ví dụ."""
        talk = self.env_at(self.voice_env, t)
        phase = self.timeline.beat_phase(t)
        beat_hop = (16 if seg.kind == "outro" else 6) * math.sin(math.pi * phase) ** 2
        spoken = self.spoken.get(seg.cue_id)
        jump = 0.0
        if seg.letter is not None and spoken is not None and spoken.word_at:
            k = (t - (spoken.start + spoken.word_at)) / 0.5
            jump = 26 * math.sin(math.pi * k) if 0 < k < 1 else 0.0
        for i, c in enumerate(self.lesson.characters):
            appear = ease_out_back((t - self.appear_at[c.name]) / 0.5)
            if appear <= 0.02:
                continue
            sprite = self.sprites[c.name]
            frame = sprite.at(t + 1.3 * i)  # lệch pha: hai nhân vật không cử động giống hệt nhau
            h = sprite.size[1]
            cx = CHAR_X[c.side]
            if c.speaks:
                hop, scale, angle = beat_hop * 0.5, 1 + 0.05 * talk, 3 * talk * math.sin(t * 15)
                shine = 0.3 + 0.45 * talk
            else:
                hop, scale, angle, shine = beat_hop + jump, 1.0, 0.0, 0.3
            place(img, self.glows[c.name], (cx, CHAR_FOOT - h / 2), scale=appear, alpha=shine)
            place(img, frame, (cx, CHAR_FOOT - h / 2 - hop), scale=scale * appear, angle=angle)
            place(img, self.tags[c.name], (cx, CHAR_FOOT + 22), scale=appear)

    def _draw_chips(self, img: Image.Image, t: float, seg: Segment, to_main: float) -> None:
        letters = self.lesson.letters
        total = len(letters) * CHIP_W + (len(letters) - 1) * CHIP_GAP
        x0 = (W - total) // 2
        drop = -70 * (1 - (ease_in_out((to_main - 0.4) / 0.6) if seg.kind == "intro" else 1))  # sau khi tiêu đề mờ đi
        current = seg.letter.index if seg.letter else 0
        for x in letters:
            cx = x0 + (x.index - 1) * (CHIP_W + CHIP_GAP) + CHIP_W / 2
            cy = CHIP_Y + CHIP_H / 2 + drop
            if x.index == current:
                pop = ease_out_back((t - seg.start) / 0.3)
                place(img, self.chips[x.letter]["now"], (cx, cy + 3 * (1 - pop)), scale=1.0 + 0.18 * pop)
            else:
                place(img, self.chips[x.letter]["done" if x.index < current else "todo"], (cx, cy))

    def repeat_window(self, seg: Segment) -> tuple[float, float] | None:
        """Khoảng "bé đọc theo": từ lúc phụ đề câu đọc tắt tới gần hết khúc nhạc của chữ (None nếu quá ngắn)."""
        spoken = self.spoken.get(seg.cue_id)
        if seg.letter is None or spoken is None:
            return None
        start, end = spoken.end + 0.75, seg.end - 0.3
        return (start, end) if end - start >= 1.0 else None

    def _draw_repeat(self, img: Image.Image, t: float, seg: Segment) -> None:
        window = self.repeat_window(seg)
        if window and window[0] <= t < window[1]:
            show = clamp01((window[1] - t) / 0.2)
            place(img, self.repeat_cue, (W / 2, SUB_Y), scale=ease_out_back((t - window[0]) / 0.35), alpha=show)

    def _draw_card(self, img: Image.Image, t: float, seg: Segment) -> None:
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
            place(
                img,
                self.bottoms[letter.letter],
                (card_cx, CARD_Y + SPLIT_Y + (CARD_H - SPLIT_Y) / 2 + 30 * (1 - ease_out_back(k))),
                scale=(0.5 + 0.5 * ease_out_back(k)) * (1 - 0.15 * leave),
                alpha=clamp01(k * 3) * (1 - leave),
            )

    def _draw_intro(self, img: Image.Image, t: float, to_main: float) -> None:
        hide = 1 - clamp01(to_main * 2.5)  # tiêu đề mờ đi trước khi hàng chữ cái trượt xuống
        place(img, self.title, (W / 2, 82), scale=ease_out_back((t - 0.15) / 0.45), alpha=hide)
        place(img, self.subtitle, (W / 2, 148), scale=ease_out_back((t - 0.55) / 0.4), alpha=hide)

    def _draw_disc(self, img: Image.Image, t: float, to_main: float) -> None:
        hide = 1 - clamp01(to_main * 2.5)
        pulse = 0.04 * (1 - self.timeline.beat_phase(t)) ** 2  # nảy nhẹ theo phách
        angle = 4 * math.sin(2 * math.pi * t / 3.2)
        place(img, self.disc, DISC_C, scale=ease_out_back((t - 0.7) / 0.5) * (1 + pulse), alpha=hide, angle=angle)

    def _draw_orbit(self, img: Image.Image, t: float, to_main: float, front: bool) -> None:
        """Chữ cái bay vòng quanh đĩa "Aa": nửa sau vẽ trước đĩa (nhỏ, mờ), nửa trước vẽ sau — như quỹ đạo 3D."""
        hide = 1 - clamp01(to_main * 2.5)
        cx, cy = DISC_C
        n = len(self.orbit)
        for i, ball in enumerate(self.orbit):
            angle = 2 * math.pi * i / n + 0.55 * t
            depth = math.sin(angle)  # > 0: phía trước
            if (depth > 0) != front:
                continue
            pop = ease_out_back((t - 1.0 - 0.18 * i) / 0.35)
            pos = (cx + 240 * math.cos(angle), cy + 125 * depth)
            place(img, ball, pos, scale=pop * hide * (0.85 + 0.2 * depth), alpha=hide * (0.75 + 0.25 * depth))

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
        cols, size, gap = 6, 80, 14
        x0 = (W - (cols * size + (cols - 1) * gap)) / 2 + size / 2
        y0 = 156 + size / 2
        for i, ball in enumerate(self.grid):
            pop = ease_out_back((local - 0.35 - 0.07 * i) / 0.35)
            wave = 5 * math.sin(2 * math.pi * 0.8 * t + 0.5 * i)
            place(img, ball, (x0 + (i % cols) * (size + gap), y0 + (i // cols) * (size + gap) + wave), scale=pop)
        spoken = self.spoken.get(seg.cue_id)
        after = (spoken.end + 0.7) if spoken else seg.start + 3.0  # sau khi phụ đề câu kết đã tắt
        for k, line in enumerate(self.credits):
            place(img, line, (W / 2, SUB_Y - 26 + 25 * k), alpha=clamp01((t - after) / 0.3))

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
