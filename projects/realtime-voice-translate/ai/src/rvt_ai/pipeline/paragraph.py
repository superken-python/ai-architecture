"""Gom các câu chốt liền nhau của một người nói thành một đoạn, để dịch cả đoạn (chế độ Video & Họp, docs 10 §13.9).

VAD cắt lời nói thành đoạn 4–6 giây, nên một câu dài bị chẻ làm hai và mỗi mảnh từng được dịch riêng. Ở chế độ dịch theo
đoạn, các câu nối tiếp nhau được gom lại tới khi người nói nghỉ lâu, và mỗi lần có câu mới thì dịch lại cả đoạn.
"""

from collections import deque
from dataclasses import dataclass, field

SENTENCE_END = ("。", "！", "？", ".", "!", "?", "…")


@dataclass(frozen=True)
class ParagraphConfig:
    # Khoảng cách giữa audio của hai câu chốt. Audio mỗi câu đã kèm ~0,4 s trước lời nói (preroll) và ~0,5 s lặng sau
    # (min_silence), nên 600 ms ở đây ứng với người nói nghỉ khoảng 1,5 s
    gap_ms: int = 600
    # Đoạn dài hơn: câu mới hết câu trước mới mở đoạn mới, cho thẻ dễ đọc và lượt dịch lại không quá dài
    soft_ms: int = 20000
    # Đoạn dài hơn: mở đoạn mới dù câu trước chưa hết
    max_ms: int = 40000


@dataclass
class Paragraph:
    pid: int  # = số câu (utterance_id) của câu đầu tiên trong đoạn
    side: str
    lang: str
    start_ms: int
    end_ms: int
    texts: list[str] = field(default_factory=list)
    revision: int = 0  # tăng mỗi lần thêm câu: web chỉ giữ bản dịch của lần mới nhất

    @property
    def source(self) -> str:
        # Tiếng Nhật viết liền, không có khoảng trắng giữa các câu
        sep = "" if self.lang == "ja" else " "
        return sep.join(t.strip() for t in self.texts if t.strip())

    def accepts(self, lang: str, start_ms: int | None, cfg: ParagraphConfig) -> bool:
        """Câu mới (ngôn ngữ `lang`, audio bắt đầu ở `start_ms`; None là nói liền câu trước) có vào đoạn này không."""
        if lang != self.lang:
            return False
        if start_ms is not None and start_ms - self.end_ms > cfg.gap_ms:
            return False
        duration = self.end_ms - self.start_ms
        if duration >= cfg.max_ms:
            return False
        return not (duration >= cfg.soft_ms and self.source.endswith(SENTENCE_END))


class ParagraphTracker:
    """Đoạn đang mở của mỗi bên, và chữ của vài đoạn đã đóng (ngữ cảnh cho lượt dịch của đoạn sau)."""

    def __init__(self, config: ParagraphConfig | None = None):
        self.config = config or ParagraphConfig()
        self.open: dict[str, Paragraph] = {}
        self.history: deque[str] = deque(maxlen=3)

    def add(self, uid: int, side: str, lang: str, text: str, start_ms: int | None, end_ms: int) -> Paragraph:
        """Thêm một câu chốt; trả về đoạn chứa nó (đoạn đang mở, hoặc đoạn mới bắt đầu bằng câu này)."""
        para = self.open.get(side)
        if para is None or not para.accepts(lang, start_ms, self.config):
            self.close(side)
            para = Paragraph(uid, side, lang, end_ms if start_ms is None else start_ms, end_ms)
            self.open[side] = para
        para.texts.append(text)
        para.end_ms = max(para.end_ms, end_ms)
        para.revision += 1
        return para

    def peek(self, side: str, lang: str, start_ms: int | None) -> int | None:
        """Số đoạn mà chữ tạm đang nói sẽ vào nếu được chốt bây giờ; None nếu sẽ mở đoạn mới."""
        para = self.open.get(side)
        return para.pid if para is not None and para.accepts(lang, start_ms, self.config) else None

    def close(self, side: str | None = None) -> None:
        """Đóng đoạn đang mở của một bên (hoặc mọi bên): câu sau sẽ mở đoạn mới."""
        for s in [side] if side is not None else list(self.open):
            para = self.open.pop(s, None)
            if para is not None and para.source:
                self.history.append(para.source)
