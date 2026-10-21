"""Tách nhân vật khỏi video gốc thành ảnh động nền trong suốt (WebP) — chạy một lần bằng `make sprites`.

Video nhân vật (tạo bằng Gemini) có nền sao, vòng sáng và nốt nhạc bay quanh. Mỗi khung hình chạy qua hai mô hình
tách nền ONNX (onnxruntime, chạy trên CPU, không cần mạng sau lần tải đầu):

- U²-Net: lấy trọn thân nhân vật, nhưng hay bỏ sót chi tiết mảnh (vòng tai nghe của thỏ);
- ISNet: giữ được chi tiết mảnh, nhưng lấy luôn cả vòng sáng quanh nhân vật.

Ghép: alpha = max(U²-Net, ISNet × đĩa tròn nằm trong vòng sáng) — mỗi mô hình bù chỗ yếu của mô hình kia. Kết quả
được commit (assets/nhan-vat/*.webp), nên dựng video không cần hai mô hình này.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageFilter

from chu_cai_video import assets, config
from chu_cai_video.lesson import Source

FPS = config.SPRITE_FPS
FLOOR, CEIL = 0.12, 0.9  # alpha dưới FLOOR coi là nền (bóng mờ, ánh sáng), trên CEIL coi là nhân vật
BG_DIST = 60.0  # khoảng cách màu (RGB 0..255) tới màu nền: gần hơn thì coi là nền


@dataclass(frozen=True)
class Model:
    item: config.Download
    size: int  # cạnh ảnh vuông đưa vào mô hình
    mean: tuple[float, float, float]
    std: tuple[float, float, float]


U2NET = Model(config.SEGMENT_U2NET, 320, (0.485, 0.456, 0.406), (0.229, 0.224, 0.225))
ISNET = Model(config.SEGMENT_ISNET, 1024, (0.5, 0.5, 0.5), (1.0, 1.0, 1.0))


def disk(shape: tuple[int, int], radius: float, soft: float = 8.0) -> np.ndarray:
    """Đĩa tròn giữa ảnh: 1 bên trong bán kính, 0 bên ngoài, mép mềm `soft` px."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    return np.clip((radius - np.hypot(xx - w / 2, yy - h / 2)) / soft + 0.5, 0, 1).astype(np.float32)


def combine(body: np.ndarray, detail: np.ndarray, radius: float, rgb: np.ndarray | None = None) -> np.ndarray:
    """Alpha cuối (0..1) từ U²-Net (`body`) và ISNet (`detail`, chỉ tin bên trong đĩa bán kính `radius`).

    U²-Net hay lấp kín vùng nền bị nhân vật bao quanh (khoảng trống giữa quai tai nghe và quyển sách). Chỗ nào U²-Net
    nhận là nhân vật mà ISNet bảo là nền, nếu màu điểm ảnh gần màu nền (`rgb`: ảnh gốc) thì trả về làm nền.
    """
    inside = disk(body.shape, radius)
    if rgb is not None:
        sure_bg = (body < 0.05) & (detail < 0.05) & (inside > 0.5)
        if sure_bg.any():
            ref = np.median(rgb[sure_bg], axis=0)
            dist = np.linalg.norm(rgb.astype(np.float32) - ref, axis=-1)
            like_bg = np.clip((BG_DIST - dist) / (BG_DIST / 2), 0, 1)  # 1: đúng màu nền, 0: khác hẳn
            disputed = np.clip((body - detail) / 0.5, 0, 1)
            body = body * (1 - disputed * like_bg)
    alpha = np.maximum(body, detail * inside)
    return np.clip((alpha - FLOOR) / (CEIL - FLOOR), 0, 1)


class Segmenter:
    """Hai mô hình tách nền (tải một lần vào .cache/models/, ~350 MB)."""

    def __init__(self) -> None:
        try:
            import onnxruntime as ort
        except ImportError as e:
            raise RuntimeError("Thiếu onnxruntime — chạy `make sprites` (tự cài nhóm phụ thuộc `sprites`)") from e
        self.sessions = []
        for model in (U2NET, ISNET):
            path = assets.fetch(model.item)
            self.sessions.append((model, ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])))

    @staticmethod
    def _predict(session: Any, model: Model, img: Image.Image) -> np.ndarray:
        x = np.asarray(img.resize((model.size, model.size), Image.Resampling.LANCZOS), dtype=np.float32)
        x = x / max(float(x.max()), 1e-6)
        x = ((x - np.array(model.mean, np.float32)) / np.array(model.std, np.float32)).transpose(2, 0, 1)[None]
        p = session.run(None, {session.get_inputs()[0].name: x.astype(np.float32)})[0][0, 0]
        p = (p - p.min()) / max(float(p.max() - p.min()), 1e-6)
        mask = Image.fromarray((p * 255).astype(np.uint8)).resize(img.size, Image.Resampling.LANCZOS)
        return np.asarray(mask, np.float32) / 255

    def cut(self, frame: Image.Image, radius: float) -> Image.Image:
        """Khung hình RGB → RGBA, nền trong suốt."""
        (m1, s1), (m2, s2) = self.sessions
        alpha = combine(self._predict(s1, m1, frame), self._predict(s2, m2, frame), radius, np.asarray(frame))
        mask = Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
        out = frame.convert("RGBA")
        out.putalpha(mask)
        return out


def read_frames(source: Source) -> list[Image.Image]:
    """Các khung hình trong [start, end) của video gốc, đã cắt vùng chứa nhân vật."""
    from chu_cai_video.render import ffmpeg_path  # nhập muộn: render nạp nhiều thứ không cần ở đây

    x, y, w, h = source.crop
    cmd = [
        ffmpeg_path(), "-v", "error", "-ss", f"{source.start:.3f}", "-t", f"{source.end - source.start:.3f}",
        "-i", str(source.video), "-vf", f"fps={FPS},crop={w}:{h}:{x}:{y}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ]  # fmt: skip
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    size = w * h * 3
    return [Image.frombytes("RGB", (w, h), raw[i : i + size]) for i in range(0, len(raw) - size + 1, size)]


def tighten(frames: list[Image.Image], height: int, pad: int = 6) -> list[Image.Image]:
    """Cắt mọi khung theo khung bao chung của nhân vật (để nhân vật không nhảy chỗ), rồi thu về cao `height` px."""
    boxes = [f.getchannel("A").point(lambda v: 255 if v > 12 else 0).getbbox() for f in frames]
    boxes = [b for b in boxes if b]
    if not boxes:
        raise RuntimeError("Không tách được nhân vật nào — kiểm tra lại crop/radius của video gốc")
    w, h = frames[0].size
    box = (
        max(0, min(b[0] for b in boxes) - pad),
        max(0, min(b[1] for b in boxes) - pad),
        min(w, max(b[2] for b in boxes) + pad),
        min(h, max(b[3] for b in boxes) + pad),
    )
    scale = height / (box[3] - box[1])
    size = (round((box[2] - box[0]) * scale), height)
    return [f.crop(box).resize(size, Image.Resampling.LANCZOS) for f in frames]


def save_webp(frames: list[Image.Image], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=round(1000 / FPS),
        loop=0,
        lossless=False,
        quality=90,
        alpha_quality=95,
        method=6,
    )


def extract(source: Source, out: Path, segmenter: Segmenter) -> int:
    """Video gốc → ảnh động WebP nền trong suốt. Trả về số khung hình."""
    frames = read_frames(source)
    if not frames:
        raise RuntimeError(f"{source.video.name}: không đọc được khung hình nào trong [{source.start}, {source.end})")
    cut = []
    for i, frame in enumerate(frames):
        cut.append(segmenter.cut(frame, source.radius))
        if i % 12 == 0:
            print(f"  {out.name}: khung {i + 1}/{len(frames)}", flush=True)
    save_webp(tighten(cut, source.height), out)
    return len(frames)
