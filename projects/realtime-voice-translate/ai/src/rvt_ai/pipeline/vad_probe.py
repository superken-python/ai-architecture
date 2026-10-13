"""Dò vùng audio to mà VAD bỏ sót (docs 09 §4.1).

Có những câu thoại to, rõ, nhưng Silero VAD cho xác suất gần 0 suốt nhiều giây: lời nói lẫn nhạc nền, tiếng hét. Trên
golden_1, câu "引っかかった!…" ở giây 31–45 bị mất vì vậy. Khi thu âm tab, vùng audio to hơn −30 dBFS mà VAD dưới 0,25
và không nằm trong đoạn nào, dài 2–6 s, được gửi đi nhận dạng như một đoạn chốt không prompt. Kết quả chỉ được giữ khi
qua `probe_text_ok` và `avg_logprob` ≥ −0,5.

Không bật với mic: tiếng TV, nhạc trong phòng sẽ bị nhận dạng.
"""

import re
from collections import Counter

import numpy as np
from pydantic import BaseModel

from rvt_ai.pipeline.mt_validator import JA_REGEX


class VadProbeConfig(BaseModel):
    sample_rate: int = 16000
    min_level_dbfs: float = -30.0  # khung to hơn mức này
    max_speech_prob: float = 0.25  # mà VAD dưới mức này
    max_gap_ms: int = 480  # cho phép hở tối đa 12 khung 40 ms trong một vùng
    min_ms: int = 2000  # vùng ngắn hơn bị bỏ
    max_ms: int = 6000  # vùng dài hơn được cắt thành khúc 6 s
    min_tail_ms: int = 1000  # khúc cuối của vùng dài ngắn hơn mức này bị bỏ
    preroll_ms: int = 400  # VAD bắt đầu bắt: bỏ phần cuối vùng, vì segmenter đã lấy nó làm preroll
    min_avg_logprob: float = -0.5


def _level_dbfs(chunk: bytes) -> float:
    x = np.frombuffer(chunk, np.int16).astype(np.float32) / 32768.0
    if not len(x):
        return -120.0
    return 20 * float(np.log10(np.sqrt(np.mean(x**2)) + 1e-9))


class VadProbe:
    """Gom các khung to mà VAD không bắt thành vùng. `add` trả về audio của một khúc cần nhận dạng, hoặc None."""

    def __init__(self, config: VadProbeConfig | None = None):
        self.config = config or VadProbeConfig()
        self.buffer = bytearray()  # audio của vùng đang gom, tới khung to cuối cùng
        self.gap = bytearray()  # các khung không to sau khung to cuối cùng
        self.region_ms = 0  # độ dài cả vùng, gồm các khúc đã gửi đi

    def _ms(self, n_bytes: int) -> int:
        return n_bytes * 1000 // (self.config.sample_rate * 2)

    def _bytes(self, ms: int) -> int:
        return ms * self.config.sample_rate * 2 // 1000

    def reset(self) -> None:
        self.buffer = bytearray()
        self.gap = bytearray()
        self.region_ms = 0

    def _close(self, trim_ms: int = 0) -> bytes | None:
        audio = bytes(self.buffer[: max(0, len(self.buffer) - self._bytes(trim_ms))])
        # Khúc đầu phải dài 2 s; khúc cuối của vùng dài hơn 6 s chỉ cần 1 s
        min_ms = self.config.min_ms if self.region_ms == 0 else self.config.min_tail_ms
        self.reset()
        return audio if self._ms(len(audio)) >= min_ms else None

    def add(self, chunk: bytes, speech_prob: float, speaking: bool) -> bytes | None:
        cfg = self.config
        if speaking:
            # VAD đã bắt: vùng kết thúc ở đây, phần preroll thuộc về đoạn của segmenter
            return self._close(trim_ms=cfg.preroll_ms) if self.buffer else None
        loud = speech_prob < cfg.max_speech_prob and _level_dbfs(chunk) > cfg.min_level_dbfs
        if loud:
            self.buffer.extend(self.gap)
            self.gap = bytearray()
            self.buffer.extend(chunk)
            if self._ms(len(self.buffer)) >= cfg.max_ms:
                piece = bytes(self.buffer[: self._bytes(cfg.max_ms)])
                self.buffer = self.buffer[self._bytes(cfg.max_ms) :]
                self.region_ms += cfg.max_ms
                return piece
            return None
        if not self.buffer and not self.region_ms:
            return None
        self.gap.extend(chunk)
        if self._ms(len(self.gap)) > cfg.max_gap_ms:
            return self._close()
        return None


_PUNCT = re.compile(r"[\s.。,，、!?！？・…~～—\-「」『』()（）\"']")
_SCREAM_MARKS = re.compile(r"[ーぁぃぅぇぉっゃゅょァィゥェォッャュョ]")


def probe_text_ok(text: str, force_lang: str | None) -> bool:
    """Chữ nghe được ở một vùng VAD bỏ sót có đáng hiện lên không: đủ dài, đúng ngôn ngữ, không chỉ là tiếng hét."""
    core = _PUNCT.sub("", text)
    if len(core) < 4:
        return False
    if force_lang == "ja" and not JA_REGEX.search(core):
        return False
    # Tiếng hét, tiếng cười: "あーーーっ", "うわあああ", "ははは" — sau khi bỏ trường âm và chữ nhỏ, chỉ còn 1–2 chữ
    # khác nhau, hoặc một chữ chiếm từ 60% trở lên
    base = _SCREAM_MARKS.sub("", core)
    if not base:
        return False
    top = Counter(base).most_common(1)[0][1]
    return len(set(base)) > 2 and top / len(base) < 0.6
