import asyncio
import contextlib
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

# Prompt ngữ cảnh: chuỗi cố định, hoặc hàm dựng prompt mà worker gọi ngay trước khi nhận dạng (docs 08 §3.8)
PromptArg = str | Callable[[], str | None] | None


def _resolve_prompt(initial_prompt: PromptArg) -> str | None:
    if not callable(initial_prompt):
        return initial_prompt
    try:
        return initial_prompt()
    except Exception:
        return None  # thiếu prompt vẫn hơn mất cả đoạn


class AsrJob(BaseModel):
    priority: int  # 0 for final, 1 for partial
    session_id: str
    audio: bytes
    force_lang: str | None = None
    is_final: bool


class AsrScheduler:
    """
    GPU-wide ASR scheduler ensuring single inference at a time on GPU,
    strictly prioritizing final transcriptions over partial transcriptions,
    and coalescing/dropping stale partial jobs under load.
    """

    def __init__(self, transcribe_fn: Callable[..., Any]):
        self.transcribe_fn = transcribe_fn
        # (audio, force_lang, vad_mean, prompt, tham số thêm cho engine, future)
        self._final_queue: asyncio.Queue[tuple[bytes, str | None, float | None, PromptArg, dict, asyncio.Future]] = (
            asyncio.Queue()
        )
        self._pending_partials: dict[str, tuple[bytes, str | None, float | None, PromptArg, dict, asyncio.Future]] = {}
        self._has_work = asyncio.Event()
        self._worker_task: asyncio.Task | None = None
        self._running = False
        self.completed_finals = 0
        self.completed_partials = 0
        self.dropped_partials = 0

    def _ensure_worker(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            try:
                loop = asyncio.get_running_loop()
                self._running = True
                self._worker_task = loop.create_task(self._worker())
            except RuntimeError:
                pass

    def _run_transcribe(
        self,
        audio: bytes,
        force_lang: str | None,
        vad_mean: float | None = None,
        initial_prompt: str | None = None,
        **extra: Any,
    ) -> Any:
        kwargs: dict[str, Any] = dict(extra)
        if vad_mean is not None:
            kwargs["vad_mean"] = vad_mean
        if initial_prompt is not None:
            kwargs["initial_prompt"] = initial_prompt
        try:
            return self.transcribe_fn(audio, force_lang, **kwargs)
        except TypeError:
            return self.transcribe_fn(audio, force_lang)

    async def _worker(self) -> None:
        while self._running:
            try:
                # 1. Prioritize all Final jobs
                if not self._final_queue.empty():
                    audio, force_lang, vad_mean, initial_prompt, extra, future = await self._final_queue.get()
                    try:
                        # Dựng prompt lúc lượt này thật sự chạy, không phải lúc xếp hàng: khi GPU bận, lượt trước có thể
                        # chưa xong lúc đoạn này được chốt (docs 08 §3.8)
                        prompt = _resolve_prompt(initial_prompt)
                        res = await asyncio.to_thread(
                            self._run_transcribe, audio, force_lang, vad_mean, prompt, **extra
                        )
                        if not future.done():
                            future.set_result(res)
                        self.completed_finals += 1
                    except Exception as e:
                        if not future.done():
                            future.set_exception(e)
                    finally:
                        self._final_queue.task_done()
                    # Nhường một lượt: session nhận kết quả và ghi vào lịch sử prompt trước khi lượt sau dựng prompt
                    await asyncio.sleep(0)
                    continue

                # 2. Process latest partial job (if any)
                if self._pending_partials:
                    _, (audio, force_lang, vad_mean, initial_prompt, extra, future) = self._pending_partials.popitem()
                    try:
                        prompt = _resolve_prompt(initial_prompt)
                        res = await asyncio.to_thread(
                            self._run_transcribe, audio, force_lang, vad_mean, prompt, **extra
                        )
                        if not future.done():
                            future.set_result(res)
                        self.completed_partials += 1
                    except Exception as e:
                        if not future.done():
                            future.set_exception(e)
                    continue

                # 3. Wait for new work
                self._has_work.clear()
                await self._has_work.wait()
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(0.01)

    async def execute_transcribe(
        self,
        audio: bytes,
        force_lang: str | None = None,
        is_final: bool = True,
        session_id: str = "default",
        vad_mean: float | None = None,
        initial_prompt: PromptArg = None,
        min_avg_logprob: float | None = None,
    ) -> Any:
        self._ensure_worker()
        # Tham số chỉ một số lượt dùng: không truyền khi không đặt, để engine cũ (chỉ nhận audio, ngôn ngữ) vẫn chạy
        extra: dict[str, Any] = {} if min_avg_logprob is None else {"min_avg_logprob": min_avg_logprob}
        loop = asyncio.get_running_loop()

        if is_final:
            future: asyncio.Future = loop.create_future()
            await self._final_queue.put((audio, force_lang, vad_mean, initial_prompt, extra, future))
            self._has_work.set()
            return await future
        else:
            # Drop partial job immediately if GPU queue has 2+ final jobs waiting
            if self._final_queue.qsize() > 2:
                self.dropped_partials += 1
                return "", "vi", {}

            # Coalesce: if there is already a waiting partial for this session, resolve it with empty result
            if session_id in self._pending_partials:
                *_, old_future = self._pending_partials[session_id]
                if not old_future.done():
                    old_future.set_result(("", "vi", {}))
                self.dropped_partials += 1

            future = loop.create_future()
            self._pending_partials[session_id] = (audio, force_lang, vad_mean, initial_prompt, extra, future)
            self._has_work.set()
            return await future

    def cancel_session_partials(self, session_id: str) -> None:
        """Cancel any waiting partial jobs when a final utterance arrives."""
        if session_id in self._pending_partials:
            *_, future = self._pending_partials.pop(session_id)
            if not future.done():
                future.set_result(("", "vi", {}))
            self.dropped_partials += 1

    async def stop(self) -> None:
        self._running = False
        self._has_work.set()
        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task
