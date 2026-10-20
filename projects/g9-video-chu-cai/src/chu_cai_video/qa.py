"""Kiểm tra lời đọc bằng máy nghe lại: nhận dạng giọng nói (ASR) tiếng Việt chép lại từng câu rồi so với kịch bản.

Mỗi câu được chấm hai lần: giọng riêng (giọng máy có đọc đúng không) và trong bản trộn có nhạc (nhạc có lấn lời không).
ASR cũng có lỗi, nhất là với âm đọc đứng riêng ("bờ", "cờ"), nên kết quả là danh sách câu cần người nghe lại — không
thay được giáo viên duyệt.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from chu_cai_video import assets, config
from chu_cai_video.voice import Spoken

# Giọng Bắc đọc giống nhau nên ASR không phân biệt được: d/gi/r, s/x, ch/tr, c/k/q; chữ cái đọc tên (l, n, m).
SAME_SOUND = (("ngh", "ng"), ("gh", "g"), ("gi", "d"), ("tr", "ch"), ("qu", "cu"))
SAME_FIRST = {"r": "d", "s": "x", "k": "c", "q": "c"}
LETTER_NAMES = {"y": "i", "l": "lờ", "n": "nờ", "m": "mờ", "g": "gờ", "đ": "đờ", "b": "bờ", "p": "pờ"}


def normalize(text: str) -> list[str]:
    """Chuỗi tiếng đã quy về cách đọc: chữ thường, bỏ dấu câu, gộp các phụ âm đầu đọc giống nhau."""
    out = []
    for syl in re.findall(r"\w+", unicodedata.normalize("NFC", text.lower())):
        for a, b in SAME_SOUND:
            if syl.startswith(a):
                syl = b + syl[len(a) :]
                break
        syl = SAME_FIRST.get(syl[:1], syl[:1]) + syl[1:]
        out.append(LETTER_NAMES.get(syl, syl))
    return out


def contains(heard: list[str], expected: list[str]) -> bool:
    n = len(expected)
    return any(heard[i : i + n] == expected for i in range(len(heard) - n + 1))


def wer(ref: list[str], hyp: list[str]) -> float:
    """Tỷ lệ lỗi theo tiếng (word error rate) bằng khoảng cách sửa chuỗi."""
    if not ref:
        return 0.0 if not hyp else 1.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1] / len(ref)


@dataclass(frozen=True)
class Check:
    spoken: Spoken
    heard_voice: str
    heard_mix: str
    expect: list[tuple[str, str]]  # (tên phần, chữ cần nghe thấy): âm đọc, từ ví dụ — hoặc cả câu

    def ok(self, heard: str) -> dict[str, bool]:
        got = normalize(heard)
        return {name: contains(got, normalize(text)) for name, text in self.expect}

    def error_rate(self, heard: str) -> float:
        return wer(normalize(self.spoken.text), normalize(heard))


class Listener:
    def __init__(self, model: Path | None = None) -> None:
        import sherpa_onnx

        d = model or assets.model_dir(config.ASR)
        self.asr = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=str(next(d.glob("encoder-*.onnx"))),
            decoder=str(next(d.glob("decoder-*.onnx"))),
            joiner=str(next(d.glob("joiner-*.onnx"))),
            tokens=str(d / "tokens.txt"),
            num_threads=4,
            decoding_method="greedy_search",
        )

    def hear(self, samples: np.ndarray, sr: int = config.SAMPLE_RATE) -> str:
        stream = self.asr.create_stream()
        stream.accept_waveform(sr, np.ascontiguousarray(samples, dtype=np.float32))
        self.asr.decode_stream(stream)
        return stream.result.text.strip().lower()


def check(spoken: list[Spoken], mixed: np.ndarray, listener: Listener) -> list[Check]:
    sr = config.SAMPLE_RATE
    mono = mixed.mean(axis=1) if mixed.ndim == 2 else mixed
    results = []
    for s in spoken:
        a, b = int(max(0.0, s.start - 0.1) * sr), int((s.end + 0.25) * sr)
        letter = s.segment.letter
        expect = [("âm", letter.sound), ("từ", letter.phrase)] if letter else [("câu", s.text)]
        results.append(Check(s, listener.hear(s.samples), listener.hear(mono[a:b]), expect))
    return results


def report(results: list[Check], path: Path) -> str:
    letters = [r for r in results if r.spoken.segment.letter]
    word_ok = sum(r.ok(r.heard_voice)["từ"] for r in letters)
    sound_ok = sum(r.ok(r.heard_voice)["âm"] for r in letters)
    word_mix = sum(r.ok(r.heard_mix)["từ"] for r in letters)
    other = [r for r in results if not r.spoken.segment.letter]
    lines = [
        "# Kiểm tra lời đọc bằng máy nghe lại",
        "",
        "<!-- FILE SINH TỰ ĐỘNG bằng `make qa` — không sửa tay. -->",
        "",
        "Mô hình nhận dạng giọng nói tiếng Việt (zipformer, sherpa-onnx) chép lại từng câu của video, rồi so với kịch "
        "bản. Phụ âm đầu đọc giống nhau ở giọng Bắc (d/gi/r, s/x, ch/tr, c/k/q) tính là khớp. Mỗi câu chấm hai lần: "
        "**giọng riêng** và **trong bản trộn có nhạc**.",
        "",
        "| Chỉ số | Kết quả |",
        "|---|---|",
        f"| Từ ví dụ nghe đúng (giọng riêng) | **{word_ok}/{len(letters)}** |",
        f"| Từ ví dụ nghe đúng (có nhạc nền) | **{word_mix}/{len(letters)}** |",
        f"| Âm đọc chữ cái nghe đúng (giọng riêng) | {sound_ok}/{len(letters)} |",
    ]
    for r in other:
        name = "Câu mở đầu" if r.spoken.segment.kind == "intro" else "Câu kết"
        lines.append(f"| {name}: tỷ lệ lỗi theo tiếng (giọng riêng → có nhạc) | "
                     f"{r.error_rate(r.heard_voice):.0%} → {r.error_rate(r.heard_mix):.0%} |")  # fmt: skip
    lines += [
        "",
        'ASR hay nghe nhầm âm đọc đứng riêng ("bờ", "ca") và dấu thanh, nên ✗ nghĩa là **cần người nghe lại**, '
        "chưa chắc giọng đọc sai. Câu sai thật thì thu âm lại và đặt file vào `giong-thu-am/<id>.wav` (xem README).",
        "",
        "| Id | Câu trong kịch bản | Nguồn | Máy nghe được (giọng riêng) | Âm | Từ | Có nhạc |",
        "|---|---|---|---|:-:|:-:|:-:|",
    ]
    for r in results:
        okv, okm = r.ok(r.heard_voice), r.ok(r.heard_mix)
        if r.spoken.segment.letter:
            marks = ["✓" if okv["âm"] else "✗", "✓" if okv["từ"] else "✗", "✓" if okm["từ"] else "✗"]
        else:
            marks = ["—", "—", f"{r.error_rate(r.heard_mix):.0%} lỗi"]
        lines.append(
            f"| `{r.spoken.cue_id}` | {r.spoken.text} | {r.spoken.source} | {r.heard_voice or '(trống)'} | "
            + " | ".join(marks)
            + " |"
        )
    text = "\n".join(lines) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return text
