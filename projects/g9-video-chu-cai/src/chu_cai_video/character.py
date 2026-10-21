"""Nhân vật trên hình: ảnh động nền trong suốt (WebP từ `make sprites`) phát xuôi rồi ngược, và quầng sáng phía sau."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from chu_cai_video import config


class Sprite:
    """Các khung hình RGBA của một nhân vật, co vừa khung `box` (rộng, cao).

    Phát xuôi rồi ngược (ping-pong): đoạn video gốc không nối vòng được, đi qua đi lại thì chuyển động vẫn liền mạch.
    """

    def __init__(self, path: Path, box: tuple[int, int]) -> None:
        if not path.exists():
            raise RuntimeError(f"Chưa có ảnh nhân vật {path.name} — chạy `make sprites` để tách từ video gốc")
        frames: list[Image.Image] = []
        with Image.open(path) as im:
            for i in range(getattr(im, "n_frames", 1)):
                im.seek(i)
                frames.append(im.convert("RGBA"))
        scale = min(box[0] / frames[0].width, box[1] / frames[0].height)
        size = (round(frames[0].width * scale), round(frames[0].height * scale))
        self.frames = [f.resize(size, Image.Resampling.LANCZOS) for f in frames]

    @property
    def size(self) -> tuple[int, int]:
        return self.frames[0].size

    def at(self, t: float) -> Image.Image:
        """Khung hình lúc `t` giây."""
        n = len(self.frames)
        if n == 1:
            return self.frames[0]
        k = int(t * config.SPRITE_FPS) % (2 * n - 2)
        return self.frames[k if k < n else 2 * n - 2 - k]


def glow(size: int, color: tuple[int, int, int], strength: float = 0.75) -> Image.Image:
    """Quầng sáng tròn mờ (RGBA) đặt sau nhân vật."""
    img = Image.new("RGBA", (size, size), (*color, 0))
    alpha = Image.new("L", (size, size), 0)
    pad = size // 6
    ImageDraw.Draw(alpha).ellipse((pad, pad, size - pad, size - pad), fill=int(255 * strength))
    img.putalpha(alpha.filter(ImageFilter.GaussianBlur(size / 12)))
    return img
