"""Sinh icon PNG cho Office add-in (16, 32, 64, 80 px): ô vuông xanh Excel, chữ X trắng. Chỉ dùng thư viện chuẩn.

Chạy: `uv run python scripts/generate_addin_icons.py` → web/assets/icon-*.png
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "web" / "assets"
GREEN, WHITE, CLEAR = (33, 115, 70, 255), (255, 255, 255, 255), (0, 0, 0, 0)


def pixel(x: int, y: int, size: int) -> tuple[int, int, int, int]:
    r = max(2, size // 6)  # bo góc
    inside = r <= x < size - r or r <= y < size - r
    for cx, cy in ((r, r), (size - r - 1, r), (r, size - r - 1), (size - r - 1, size - r - 1)):
        if (x < r or x >= size - r) and (y < r or y >= size - r) and (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
            inside = True
    if not inside:
        return CLEAR
    pad, stroke = size * 0.26, max(1.0, size * 0.09)
    u, v = x + 0.5, y + 0.5
    if pad <= u <= size - pad and pad <= v <= size - pad and (abs(u - v) <= stroke or abs(u + v - size) <= stroke):
        return WHITE
    return GREEN


def png(size: int) -> bytes:
    raw = b"".join(b"\x00" + b"".join(bytes(pixel(x, y, size)) for x in range(size)) for y in range(size))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for size in (16, 32, 64, 80):
        (OUT / f"icon-{size}.png").write_bytes(png(size))
        print(f"✓ {OUT / f'icon-{size}.png'}")
