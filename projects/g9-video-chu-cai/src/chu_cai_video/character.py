"""Cắt nhân vật ra khỏi ảnh gốc: lấy vùng tròn (huy hiệu) với viền mềm, phóng to và làm nét lại."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


def badge(path: Path, cx: int, cy: int, r: int, size: int) -> Image.Image:
    """Ảnh RGBA vuông `size`×`size`: vùng tròn tâm (cx, cy) bán kính r của ảnh gốc, ngoài vòng tròn trong suốt."""
    src = Image.open(path).convert("RGBA")
    box = (cx - r, cy - r, cx + r, cy + r)
    crop = src.crop(box).resize((size, size), Image.Resampling.LANCZOS)
    crop = crop.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    # Mặt nạ vẽ ở 4× rồi thu nhỏ để viền tròn mịn, thêm 1–2 px mờ cho khỏi răng cưa.
    big = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(big).ellipse((6, 6, size * 4 - 6, size * 4 - 6), fill=255)
    mask = big.resize((size, size), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(0.8))
    crop.putalpha(mask)
    return crop


def glow(size: int, color: tuple[int, int, int], strength: float = 0.75) -> Image.Image:
    """Quầng sáng tròn mờ (RGBA) đặt sau nhân vật."""
    img = Image.new("RGBA", (size, size), (*color, 0))
    alpha = Image.new("L", (size, size), 0)
    pad = size // 6
    ImageDraw.Draw(alpha).ellipse((pad, pad, size - pad, size - pad), fill=int(255 * strength))
    img.putalpha(alpha.filter(ImageFilter.GaussianBlur(size / 12)))
    return img
