"""Nhân vật chữ cái: chữ in hoa vẽ từ font (luôn đúng dấu) có mắt, miệng, má hồng, tay chân — chạy, nhảy, nói.

Thân nhân vật chính là con chữ, vẽ một lần cho mỗi chữ. Mỗi khung hình chỉ vẽ lại mặt (mắt chớp, nhìn theo, miệng mở
theo lời đọc) và tay chân theo tư thế, rồi bóp/giãn cả người: bẹp xuống khi tiếp đất, giãn dài khi bay lên (squash &
stretch — nguyên tắc cơ bản của hoạt hình, làm chuyển động mềm và vui mắt).
"""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

INK = (34, 30, 60)  # màu viền mắt, miệng, giày
SKIN = (255, 255, 255)  # găng tay, lòng trắng mắt


@dataclass(frozen=True)
class Pose:
    run: float = 0.0  # pha bước chạy (vòng); chân tay vung theo
    stride: float = 0.0  # độ vung chân tay khi chạy, 0 = đứng yên
    squash: float = 0.0  # > 0: bẹp xuống (tiếp đất), < 0: giãn dài (đang bay)
    lean: float = 0.0  # nghiêng người (độ), dương = ngả về phía trước (bên phải)
    talk: float = 0.0  # miệng mở 0..1 (theo độ lớn giọng đọc)
    blink: float = 0.0  # mắt nhắm 0..1
    look: tuple[float, float] = (0.0, 0.0)  # hướng nhìn (x, y) trong -1..1
    cheer: float = 0.0  # giơ hai tay 0..1
    wave: float = 0.0  # pha vẫy tay khi đứng (vòng)


def base_shape(letter: str) -> str:
    """Chữ cái bỏ mọi dấu (Ă → A, Ơ → O) — phần thân để đặt mặt; dấu nằm trên như chiếc mũ."""
    return "".join(c for c in unicodedata.normalize("NFD", letter) if not unicodedata.combining(c))


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], k: float) -> tuple[int, int, int]:
    return tuple(round(x + (y - x) * k) for x, y in zip(a, b, strict=True))  # type: ignore[return-value]


class LetterActor:
    """Một chữ cái thành nhân vật. `height`: chiều cao thân (chưa tính chân) — tính theo pixel khi scale = 1."""

    def __init__(self, letter: str, color: tuple[int, int, int], font: ImageFont.FreeTypeFont, height: int) -> None:
        self.letter, self.color = letter, color
        size = 1000
        canvas = Image.new("L", (size, size), 0)
        ImageDraw.Draw(canvas).text((size // 2, size * 3 // 4), letter, font=font, fill=255, anchor="ms")
        body = Image.new("L", (size, size), 0)
        ImageDraw.Draw(body).text((size // 2, size * 3 // 4), base_shape(letter), font=font, fill=255, anchor="ms")
        bx0, by0, bx1, by1 = body.getbbox() or (0, 0, 1, 1)
        x0, y0, x1, y1 = canvas.getbbox() or (0, 0, 1, 1)
        k = height / (by1 - by0)  # phóng sao cho phần thân cao đúng `height`
        self.k = k
        self.unit = height  # đơn vị đo tay chân, mặt
        pad = int(0.45 * height)  # chỗ cho tay chân thò ra ngoài thân
        w, h = round((x1 - x0) * k), round((y1 - y0) * k)
        self.size = (w + 2 * pad, h + 2 * pad)
        self.origin = (pad, pad)  # góc trên trái của chữ trong ảnh nhân vật
        mask = canvas.crop((x0, y0, x1, y1)).resize((w, h), Image.Resampling.LANCZOS)
        self.mask = mask
        # Hộp thân (bỏ dấu) trong toạ độ ảnh nhân vật
        self.body = (
            pad + (bx0 - x0) * k,
            pad + (by0 - y0) * k,
            pad + (bx1 - x0) * k,
            pad + (by1 - y0) * k,
        )
        self._layout(mask, (bx0 - x0) * k, (by0 - y0) * k)
        self.skin = self._paint(mask)

    # ── chuẩn bị ──
    def _ink_span(self, mask: Image.Image, y: float) -> tuple[float, float, float]:
        """(trái, phải, giữa) của phần mực trên hàng y (toạ độ trong `mask`)."""
        row = np.asarray(mask)[int(min(max(y, 0), mask.height - 1))]
        xs = np.flatnonzero(row > 128)
        if xs.size == 0:
            return 0.0, float(mask.width), mask.width / 2
        return float(xs[0]), float(xs[-1]), float(xs.mean())

    def _layout(self, mask: Image.Image, bx: float, by: float) -> None:
        u = self.unit
        ox, oy = self.origin
        bx0, by0, bx1, by1 = self.body
        bw, bh = bx1 - bx0, by1 - by0
        eye_y = by + 0.34 * bh
        left, right, mid = self._ink_span(mask, eye_y)
        cx = ox + (left + right) / 2 if right - left > 0.35 * bw else ox + mid
        self.eye_r = max(12.0, min(0.105 * max(bw, 0.62 * bh), 30.0))
        gap = max(2.5 * self.eye_r, min(0.32 * bw, 3.4 * self.eye_r))
        self.eyes = ((cx - gap / 2, oy + eye_y), (cx + gap / 2, oy + eye_y))
        self.mouth = (cx, oy + eye_y + 0.2 * bh)
        self.mouth_w = max(22.0, min(0.24 * bw, 2.4 * self.eye_r))
        hip_dx = max(0.11 * u, min(0.2 * bw, 0.16 * u))
        self.hips = ((cx - hip_dx, by1 - 0.02 * bh), (cx + hip_dx, by1 - 0.02 * bh))
        sh_y = by + 0.6 * bh
        sl, sr, _ = self._ink_span(mask, sh_y)
        self.shoulders = ((ox + sl + 0.03 * u, oy + sh_y), (ox + sr - 0.03 * u, oy + sh_y))
        self.feet = (cx, by1 + 0.24 * u)  # điểm chạm đất (giữa hai bàn chân khi đứng)

    def _paint(self, mask: Image.Image) -> Image.Image:
        """Thân chữ: viền đậm, lòng chữ khép kín tô nhạt (để mặt có chỗ đặt), vệt bóng, má hồng."""
        color, dark = self.color, _mix(self.color, INK, 0.45)
        w, h = mask.size
        img = Image.new("RGBA", self.size, (0, 0, 0, 0))
        ox, oy = self.origin
        stroke = max(3, round(0.026 * self.unit))
        outline = mask.filter(ImageFilter.MaxFilter(2 * stroke + 1))  # nở chữ ra `stroke` px làm viền
        img.paste((*dark, 255), (ox, oy), outline)
        # Lòng chữ khép kín (A, B, D, O, P, Q, R…): phần nền không thông ra ngoài. Thêm viền nền 2 px để điểm (0, 0)
        # chắc chắn nằm ngoài chữ rồi loang màu từ đó; chỗ nền còn lại là lòng chữ.
        holes = Image.new("L", (w + 4, h + 4), 0)
        holes.paste(Image.eval(mask, lambda v: 255 if v > 128 else 0), (2, 2))
        ImageDraw.floodfill(holes, (0, 0), 128)
        hole = Image.eval(holes, lambda v: 255 if v == 0 else 0).crop((2, 2, w + 2, h + 2))
        img.paste((*_mix(color, (255, 255, 255), 0.72), 255), (ox, oy), hole)
        img.paste((*color, 255), (ox, oy), mask)
        shine = Image.new("L", (w, h), 0)  # vệt bóng ở góc trên trái của thân (không tính dấu)
        bx0, by0, bx1, by1 = (v - o for v, o in zip(self.body, (ox, oy, ox, oy), strict=True))
        bw, bh = bx1 - bx0, by1 - by0
        ImageDraw.Draw(shine).ellipse((bx0 + 0.08 * bw, by0 + 0.05 * bh, bx0 + 0.55 * bw, by0 + 0.32 * bh), fill=70)
        shine = Image.composite(shine, Image.new("L", (w, h), 0), mask)
        img.paste((255, 255, 255, 255), (ox, oy), shine)
        cheeks = Image.new("L", self.size, 0)
        r = 0.55 * self.eye_r
        for ex, _ in self.eyes:
            mx, my = ex + (ex - self.mouth[0]) * 0.35, self.mouth[1] - 0.25 * self.eye_r
            ImageDraw.Draw(cheeks).ellipse((mx - r, my - r * 0.7, mx + r, my + r * 0.7), fill=120)
        body_area = Image.new("L", self.size, 0)
        body_area.paste(mask, (ox, oy))
        body_area.paste(hole, (ox, oy), hole)
        cheeks = Image.composite(cheeks, Image.new("L", self.size, 0), body_area)
        img.paste((255, 120, 150, 255), (0, 0), cheeks)
        return img

    # ── vẽ một tư thế ──
    def draw(self, pose: Pose) -> tuple[Image.Image, tuple[float, float]]:
        """Ảnh RGBA của nhân vật ở tư thế `pose`, kèm toạ độ điểm chạm đất trong ảnh (để đặt nhân vật lên sàn)."""
        u = self.unit
        img = Image.new("RGBA", self.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        swing = math.sin(2 * math.pi * pose.run)
        # Chân (sau thân): vung ngược chiều nhau khi chạy
        leg_len, leg_w = 0.22 * u, max(6, round(0.06 * u))
        for i, (hx, hy) in enumerate(self.hips):
            angle = math.radians(32 * pose.stride * swing * (1 if i == 0 else -1))
            fx, fy = hx + leg_len * math.sin(angle), hy + leg_len * math.cos(angle)
            d.line((hx, hy, fx, fy), fill=(*INK, 255), width=leg_w)
            sw, shh = 0.075 * u, 0.04 * u
            d.ellipse((fx - sw * 0.6, fy - shh, fx + sw * 1.2, fy + shh), fill=(*_mix(self.color, INK, 0.55), 255))
        img.alpha_composite(self.skin)
        # Tay: vung khi chạy, giơ lên khi vui, đung đưa nhẹ khi đứng
        arm_len, arm_w = 0.24 * u, max(6, round(0.05 * u))
        for i, (sx, sy) in enumerate(self.shoulders):
            side = -1 if i == 0 else 1
            down = 25 + 10 * math.sin(2 * math.pi * pose.wave + i)
            run_swing = -40 * pose.stride * swing * (1 if i == 0 else -1)
            angle = math.radians(side * (down + run_swing * side) + side * 130 * pose.cheer)
            ex, ey = sx + side * 0.04 * u, sy
            hx, hy = ex + arm_len * math.sin(angle), ey + arm_len * math.cos(angle)
            d.line((ex, ey, hx, hy), fill=(*INK, 255), width=arm_w)
            hr = 0.05 * u
            d.ellipse((hx - hr, hy - hr, hx + hr, hy + hr), fill=(*SKIN, 255), outline=(*INK, 255), width=2)
        self._face(d, pose)
        return img, self.feet

    def _face(self, d: ImageDraw.ImageDraw, pose: Pose) -> None:
        r = self.eye_r
        lx, ly = pose.look
        for ex, ey in self.eyes:
            open_ = max(0.0, 1 - pose.blink)
            if open_ < 0.15:  # nhắm mắt: một nét cong
                d.arc(
                    (ex - r, ey - r * 0.6, ex + r, ey + r * 0.6), 20, 160, fill=(*INK, 255), width=max(2, round(r / 5))
                )
                continue
            ry = 1.15 * r * open_
            d.ellipse(
                (ex - r, ey - ry, ex + r, ey + ry), fill=(*SKIN, 255), outline=(*INK, 255), width=max(2, round(r / 7))
            )
            pr = 0.55 * r
            px, py = ex + lx * 0.38 * r, ey + ly * 0.4 * ry
            d.ellipse((px - pr, py - pr * open_, px + pr, py + pr * open_), fill=(*INK, 255))
            hl = 0.22 * r
            d.ellipse(
                (px + 0.15 * r - hl, py - 0.3 * r - hl, px + 0.15 * r + hl, py - 0.3 * r + hl),
                fill=(255, 255, 255, 255),
            )
        mx, my = self.mouth
        mw = self.mouth_w
        if pose.talk > 0.08:  # miệng mở: hình bán nguyệt có lưỡi
            mh = (0.18 + 0.5 * min(pose.talk, 1)) * mw
            box = (mx - mw / 2, my - mh * 0.25, mx + mw / 2, my + mh)
            d.chord(box, 0, 180, fill=(150, 30, 50, 255), outline=(*INK, 255), width=2)
            tr = mw * 0.22
            d.chord((mx - tr, my + mh * 0.45, mx + tr, my + mh * 0.95), 180, 360, fill=(240, 110, 130, 255))
        else:  # cười mỉm
            d.arc(
                (mx - mw / 2, my - mw * 0.35, mx + mw / 2, my + mw * 0.35),
                15,
                165,
                fill=(*INK, 255),
                width=max(3, round(mw / 9)),
            )


def place_actor(base: Image.Image, actor_img: Image.Image, feet: tuple[float, float], at: tuple[float, float],
                scale: float = 1.0, squash: float = 0.0, lean: float = 0.0, alpha: float = 1.0) -> None:  # fmt: skip
    """Đặt nhân vật sao cho điểm chạm đất trùng `at`: co giãn (bẹp/giãn quanh bàn chân), nghiêng quanh bàn chân."""
    if scale <= 0.02 or alpha <= 0.02:
        return
    sx, sy = scale * (1 + 0.22 * squash), scale * (1 - 0.22 * squash)
    w, h = max(1, round(actor_img.width * sx)), max(1, round(actor_img.height * sy))
    im = actor_img.resize((w, h), Image.Resampling.BILINEAR) if (w, h) != actor_img.size else actor_img
    fx, fy = feet[0] * sx, feet[1] * sy
    if abs(lean) > 0.3:
        cx, cy = w / 2, h / 2
        im = im.rotate(-lean, resample=Image.Resampling.BICUBIC, expand=True)
        a = math.radians(-lean)  # Pillow xoay ngược chiều kim đồng hồ với góc dương
        dx, dy = fx - cx, fy - cy
        fx = im.width / 2 + dx * math.cos(a) + dy * math.sin(a)
        fy = im.height / 2 - dx * math.sin(a) + dy * math.cos(a)
    if alpha < 0.995:
        im = im.copy()
        im.putalpha(im.getchannel("A").point([int(v * alpha) for v in range(256)]))
    x, y = round(at[0] - fx), round(at[1] - fy)
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(base.width, x + im.width), min(base.height, y + im.height)
    if x1 > x0 and y1 > y0:
        base.alpha_composite(im, dest=(x0, y0), source=(x0 - x, y0 - y, x1 - x, y1 - y))
