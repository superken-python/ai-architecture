import asyncio
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel


class AsrJob(BaseModel):
    priority: int  # 0 for final, 1 for partial
    session_id: str
    utterance_id: int
    audio: bytes
    force_lang: str | None = None
    is_final: bool


class AsrScheduler:
    """Đảm bảo chỉ có 1 tác vụ suy luận ASR chạy cùng lúc trên GPU, ưu tiên final > partial."""

    def __init__(self, transcribe_fn: Callable[[bytes, str | None], Any]):
        self.transcribe_fn = transcribe_fn
        self._lock = asyncio.Lock()

    async def execute_transcribe(self, audio: bytes, force_lang: str | None = None, is_final: bool = True) -> Any:
        async with self._lock:
            return await asyncio.to_thread(self.transcribe_fn, audio, force_lang)
