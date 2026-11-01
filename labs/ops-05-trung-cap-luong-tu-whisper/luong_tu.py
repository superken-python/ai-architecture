"""Phần tính toán của lab OPS-05, không cần torch hay ctranslate2: đọc phụ đề, cắt câu, so với bản gốc, kết luận.

Tách khỏi lab.py để test chạy nhanh: `uv run --with pytest --with numpy pytest labs/ops-05-trung-cap-luong-tu-whisper`.
"""

import re
from dataclasses import dataclass

import numpy as np

_TAG = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str


def seconds(stamp: str) -> float:
    """'00:01:02.500' hoặc '01:02,500' → 62.5"""
    *hours_minutes, sec = stamp.strip().replace(",", ".").split(":")
    total = float(sec)
    for power, value in enumerate(reversed(hours_minutes), 1):
        total += int(value) * 60**power
    return total


def parse_vtt(text: str) -> list[Cue]:
    """Các câu của một file WebVTT/SRT: mốc bắt đầu, kết thúc (giây) và chữ, bỏ thẻ định dạng."""
    cues: list[Cue] = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        lines = [line.strip() for line in block.strip().split("\n") if line.strip()]
        timing = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing is None:
            continue
        start, _, end = lines[timing].partition("-->")
        words = " ".join(_TAG.sub("", line) for line in lines[timing + 1 :])
        if words:
            cues.append(Cue(seconds(start), seconds(end.split()[0]), " ".join(words.split())))
    return cues


def cut(audio: np.ndarray, cue: Cue, rate: int = 16000, pad: float = 0.1) -> np.ndarray:
    """Đoạn audio của một câu, nới thêm `pad` giây mỗi đầu để không mất âm đầu, âm cuối."""
    lo = max(0, int((cue.start - pad) * rate))
    hi = min(len(audio), int((cue.end + pad) * rate))
    return audio[lo:hi]


def paired_bootstrap(
    base_errors: list[int], errors: list[int], ref_words: list[int], n: int = 2000, seed: int = 0
) -> tuple[float, float, float]:
    """Chênh WER (cách chạy − bản gốc) trên cùng các câu, kèm khoảng tin cậy 95% khi lấy mẫu lại theo câu.

    Lấy mẫu lại theo câu, không theo từ: các từ trong một câu không độc lập với nhau (giống lab A3).
    """
    base, other, words = (np.asarray(x, dtype=float) for x in (base_errors, errors, ref_words))
    delta = (other.sum() - base.sum()) / words.sum()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(words), size=(n, len(words)))
    samples = (other[idx].sum(axis=1) - base[idx].sum(axis=1)) / words[idx].sum(axis=1)
    lo, hi = np.percentile(samples, [2.5, 97.5])
    return float(delta), float(lo), float(hi)


def verdict(hi: float, rtf: float, base_rtf: float, margin: float) -> str:
    """Giữ chất lượng: cận trên của chênh WER không quá `margin`. Nhanh hơn: thời gian chạy giảm hơn 5%."""
    quality = "giữ chất lượng" if hi <= margin else "có thể kém hơn"
    speed = "nhanh hơn" if rtf < base_rtf * 0.95 else ("chậm hơn" if rtf > base_rtf * 1.05 else "nhanh như nhau")
    return f"{quality}, {speed}"


def choose(rows: list[dict], margin: float) -> dict:
    """Cách chạy nên chọn: trong các cách giữ được chất lượng, lấy file nhỏ nhất, rồi chạy nhanh nhất."""
    keep = [r for r in rows[1:] if r["hi"] <= margin]
    return min(keep, key=lambda r: (r["size_mb"], r["rtf"])) if keep else rows[0]


def markdown_table(rows: list[dict]) -> str:
    head = (
        "| Lưu | Chạy | model.bin | Nạp | RAM thêm | Thời gian / thời lượng audio | WER | Chênh WER (KTC 95%) "
        "| Câu ra chữ khác bản gốc | Nhận xét |\n|---|---|---|---|---|---|---|---|---|---|\n"
    )
    lines = []
    for r in rows:
        mem = f"{r['mem_mb']:.0f} MB" if r.get("mem_mb") is not None else "—"
        if r.get("base"):
            diff, changed, note = "—", "—", "bản gốc"
        else:
            diff = f"{r['delta']:+.3f} ({r['lo']:+.3f} … {r['hi']:+.3f})"
            changed, note = f"{r['changed']}/{r['clips']}", r["verdict"]
        lines.append(
            f"| {r['store']} | {r['compute']} | {r['size_mb']:.1f} MB | {r['load_s']:.1f} s | {mem} "
            f"| {r['rtf']:.3f} | {r['wer']:.3f} | {diff} | {changed} | {note} |"
        )
    return head + "\n".join(lines) + "\n"
