from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Protocol

from rvt_contracts.messages import Lang


class VadState(Protocol):
    def reset(self) -> None: ...


class VadEngine(Protocol):
    def create_state(self) -> VadState: ...

    def process(self, chunk: bytes, state: VadState) -> float:
        """Returns the highest speech probability (0..1) in the chunk"""
        ...


class AsrEngine(Protocol):
    def transcribe(
        self,
        audio: bytes,
        language: Lang | None = None,
        vad_mean: float | None = None,
        initial_prompt: str | None = None,
        min_avg_logprob: float | None = None,
        beam_size: int | None = None,
    ) -> tuple[str, Lang, dict[Lang, float]]:
        """Transcribes audio to text, optionally forcing a language and providing context prompt.
        min_avg_logprob drops decoded segments Whisper is unsure about; beam_size overrides greedy decoding.
        Returns (text, language, language_probs)"""
        ...


@dataclass
class MtHints:
    """Thông tin thêm cho một lượt dịch (docs 09 §5.2, §5.3, §9)."""

    # Các câu ngay trước: (câu nguồn, bản dịch đã chốt hoặc None nếu chưa dịch xong)
    history: list[tuple[str, str | None]] = field(default_factory=list)
    # Tên riêng, thuật ngữ có trong câu: (cách viết trong câu nguồn, bản dịch cố định)
    glossary: list[tuple[str, str]] = field(default_factory=list)
    # Quy ước xưng hô của ngôn ngữ đích
    addressing: list[str] = field(default_factory=list)
    # Lượt dịch lại sau khi bản dịch đầu còn chữ của ngôn ngữ nguồn
    strict: bool = False


class MtEngine(Protocol):
    def translate_stream(
        self, text: str, source_lang: Lang, target_lang: Lang, context: str = "", hints: MtHints | None = None
    ) -> AsyncGenerator[str, None]:
        """Async generator yielding translated text tokens"""
        ...
