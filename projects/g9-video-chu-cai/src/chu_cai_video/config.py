"""Đường dẫn, thông số video và các tài nguyên tải về (ghim phiên bản + mã băm SHA-256)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE = PROJECT_ROOT / ".cache"  # font, hình, model tải về — không commit
OUT = PROJECT_ROOT / "out"  # khung hình xem thử, âm thanh trung gian — không commit
MEDIA = PROJECT_ROOT / "media"  # video và ảnh bìa đã dựng — commit để xem trên web
REPORTS = PROJECT_ROOT / "reports"
DEFAULT_SCRIPT = PROJECT_ROOT / "kich-ban" / "chu-cai.yaml"

WIDTH, HEIGHT, FPS = 1280, 720, 30
SAMPLE_RATE = 44_100


@dataclass(frozen=True)
class Download:
    url: str
    sha256: str
    dest: str  # đường dẫn trong CACHE


# Baloo 2 (SIL Open Font License) — có đủ dấu tiếng Việt, nét tròn hợp với thiếu nhi.
FONTS = {
    500: Download(
        "https://fonts.gstatic.com/s/baloo2/v23/wXK0E3kTposypRydzVT08TS3JnAmtdgozapv.ttf",
        "d873207e29bca5901fcb00ff3cac1ff5f5cef7b0349e631b76351a73054e3182",
        "fonts/Baloo2-Medium.ttf",
    ),
    700: Download(
        "https://fonts.gstatic.com/s/baloo2/v23/wXK0E3kTposypRydzVT08TS3JnAmtdj9yqpv.ttf",
        "99a6754d6cc35c0dd6935077d20e569cfd73c7ecd210765c43fd67819eb6f62a",
        "fonts/Baloo2-Bold.ttf",
    ),
    800: Download(
        "https://fonts.gstatic.com/s/baloo2/v23/wXK0E3kTposypRydzVT08TS3JnAmtdiayqpv.ttf",
        "db932b3668b6188413fcde58993f7667371033579f131d524cfed3f83c62d7e2",
        "fonts/Baloo2-ExtraBold.ttf",
    ),
}
# Font dự phòng khi không tải được Baloo 2 (Linux, macOS, Windows).
FALLBACK_FONTS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
)

# Giọng Piper vi_VN vais1000 (dữ liệu VAIS-1000, CC BY 4.0) đóng gói cho sherpa-onnx.
VOICE = Download(
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-vi_VN-vais1000-medium.tar.bz2",
    "fa1367710767d36ed5cf13b4a449e20c35ffd12791c2e47c2e64142bfa55551a",
    "models/vits-piper-vi_VN-vais1000-medium.tar.bz2",
)
# Nhận dạng giọng nói tiếng Việt (zipformer, ~70.000 giờ dữ liệu) — chỉ dùng để nghe lại và chấm lời đọc.
ASR = Download(
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-zipformer-vi-int8-2025-04-20.tar.bz2",
    "48d0fdc9b3515eb9b00c4dfec2883207ee5ebe5c95b1959e7afce87fc3391938",
    "models/sherpa-onnx-zipformer-vi-int8-2025-04-20.tar.bz2",
)
# Noto Emoji (Apache 2.0), ghim theo commit để hình không đổi khi kho nguồn thay đổi.
EMOJI_URL = (
    "https://raw.githubusercontent.com/googlefonts/noto-emoji/"
    "e20cbc2bbec1926686be9f9bee7d1d2cfa1fea0e/2D/png/512/emoji_u{code}.png"
)
