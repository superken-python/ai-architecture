"""Tải tài nguyên một lần vào .cache/: font, hình emoji, model giọng đọc và ASR — kiểm mã băm, giải nén an toàn.

Đặt biến môi trường CHU_CAI_OFFLINE=1 để không bao giờ tải (test, máy không có mạng): font dùng bản dự phòng của hệ
điều hành, hình emoji chưa có trong .cache thì vẽ hình thay thế.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from chu_cai_video import config


class AssetError(RuntimeError):
    pass


def offline() -> bool:
    return os.environ.get("CHU_CAI_OFFLINE", "") not in ("", "0")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: Path) -> None:
    if offline():
        raise AssetError(f"Chế độ offline (CHU_CAI_OFFLINE) — chưa có {dest.name} trong .cache")
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  ↓ {url}")
    with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as tmp:
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                shutil.copyfileobj(resp, tmp)
        except OSError as e:
            Path(tmp.name).unlink(missing_ok=True)
            raise AssetError(f"Không tải được {url}: {e}") from e
    Path(tmp.name).replace(dest)


def fetch(item: config.Download, cache: Path = config.CACHE) -> Path:
    """File đã tải và đúng mã băm; tải lại nếu thiếu hoặc hỏng."""
    dest = cache / item.dest
    if dest.exists() and sha256(dest) == item.sha256:
        return dest
    _download(item.url, dest)
    got = sha256(dest)
    if got != item.sha256:
        dest.unlink()
        raise AssetError(f"Sai mã băm {dest.name}: {got} ≠ {item.sha256} — nguồn đã đổi, cần kiểm tra trước khi dùng")
    return dest


def model_dir(item: config.Download, cache: Path = config.CACHE) -> Path:
    """Thư mục model đã giải nén từ file .tar.bz2 (giải nén một lần, chặn đường dẫn ra ngoài thư mục đích)."""
    target = cache / item.dest.removesuffix(".tar.bz2")
    marker = target / ".ok"
    if marker.exists():
        return target
    archive = fetch(item, cache)
    staging = Path(tempfile.mkdtemp(dir=archive.parent))
    with tarfile.open(archive) as tar:
        tar.extractall(staging, filter="data")
    inner = [p for p in staging.iterdir() if p.is_dir()]
    if len(inner) != 1:
        raise AssetError(f"{archive.name}: cấu trúc lạ, cần đúng một thư mục gốc")
    if target.exists():
        shutil.rmtree(target)
    inner[0].replace(target)
    shutil.rmtree(staging)
    marker.write_text("ok\n", encoding="utf-8")
    return target


def font_files(cache: Path = config.CACHE) -> dict[int, Path | None]:
    """Baloo 2 theo độ đậm; không có mạng thì font dự phòng của hệ điều hành; None = font mặc định của Pillow."""
    found: dict[int, Path | None] = {}
    fallback = next((Path(p) for p in config.FALLBACK_FONTS if Path(p).exists()), None)
    for weight, item in config.FONTS.items():
        try:
            found[weight] = fetch(item, cache)
        except AssetError as e:
            if not offline():
                print(f"  ! {e} — dùng font dự phòng")
            found[weight] = fallback
    return found


def emoji_code(char: str) -> str:
    """Tên file Noto Emoji: mã Unicode viết thường nối bằng '_', bỏ ký tự chọn kiểu hiển thị U+FE0F."""
    return "_".join(f"{ord(c):x}" for c in char if ord(c) != 0xFE0F)


def emoji_png(char: str, cache: Path = config.CACHE) -> Path | None:
    """Ảnh PNG 512 px của emoji (tải một lần); None nếu không có mạng và chưa có trong .cache."""
    code = emoji_code(char)
    dest = cache / "emoji" / f"emoji_u{code}.png"
    if dest.exists():
        return dest
    try:
        _download(config.EMOJI_URL.format(code=code), dest)
    except AssetError as e:
        if not offline():
            print(f"  ! {e} — vẽ hình thay thế")
        return None
    return dest
