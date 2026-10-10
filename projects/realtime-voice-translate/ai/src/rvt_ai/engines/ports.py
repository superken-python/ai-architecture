from collections.abc import AsyncGenerator
from typing import Protocol

from rvt_contracts.messages import Lang


class VadState(Protocol):
    def reset(self) -> None: ...


class VadEngine(Protocol):
    def create_state(self) -> VadState: ...

    def process(self, chunk: bytes, state: VadState) -> bool:
        """Returns True if speech is detected in the chunk"""
        ...


class AsrEngine(Protocol):
    def transcribe(self, audio: bytes, language: Lang | None = None) -> tuple[str, Lang, dict[Lang, float]]:
        """Transcribes audio to text, optionally forcing a language.
        Returns (text, language, language_probs)"""
        ...


class MtEngine(Protocol):
    def translate_stream(
        self, text: str, source_lang: Lang, target_lang: Lang, context: str = ""
    ) -> AsyncGenerator[str, None]:
        """Async generator yielding translated text tokens"""
        ...
