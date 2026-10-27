"""WER và CER cho tiếng Việt, tiếng Anh (docs 10 §10.2).

Chuẩn hoá trước khi so: NFKC (chữ, số toàn khổ của tiếng Nhật thành nửa khổ), chữ thường, bỏ dấu câu và nhãn [nhạc],
**giữ dấu thanh** tiếng Việt ("ma" khác "mà").
WER tính theo từ (tách bằng khoảng trắng); CER tính theo ký tự sau khi bỏ khoảng trắng.
"""

import re
import unicodedata

_TAGS = re.compile(r"\[[^\]]*\]|\([^)]*\)")
# Giữ chữ cái (mọi ngôn ngữ, cả dấu thanh), chữ số và dấu nháy trong từ tiếng Anh ("don't")
_NOT_WORD = re.compile(r"[^\w\s']|_")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = _TAGS.sub(" ", text)
    text = _NOT_WORD.sub(" ", text)
    text = re.sub(r"(?<!\w)'|'(?!\w)", " ", text)  # bỏ dấu nháy đứng riêng
    return " ".join(text.split())


def _edits(ref: list[str], hyp: list[str]) -> int:
    """Khoảng cách Levenshtein giữa hai dãy (thay, xoá, chèn đều tính 1)."""
    if not ref:
        return len(hyp)
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1]


def wer(ref: str, hyp: str) -> float:
    ref_words, hyp_words = normalize(ref).split(), normalize(hyp).split()
    return _edits(ref_words, hyp_words) / max(1, len(ref_words))


def cer(ref: str, hyp: str) -> float:
    ref_chars, hyp_chars = list(normalize(ref).replace(" ", "")), list(normalize(hyp).replace(" ", ""))
    return _edits(ref_chars, hyp_chars) / max(1, len(ref_chars))


def score_text(ref_lines: list[str], skip: list[tuple[int, int]], hyp_text: str) -> dict:
    """WER, CER cả bài: nối các dòng tham chiếu (bỏ dòng trong `skip`) rồi so với toàn bộ chữ đã chốt."""
    ref = " ".join(line for no, line in enumerate(ref_lines, 1) if not any(lo <= no <= hi for lo, hi in skip))
    return {
        "wer": round(wer(ref, hyp_text), 4),
        "cer": round(cer(ref, hyp_text), 4),
        "ref_words": len(normalize(ref).split()),
        "hyp_words": len(normalize(hyp_text).split()),
    }
