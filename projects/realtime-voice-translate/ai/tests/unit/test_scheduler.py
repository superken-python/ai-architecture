import asyncio

import pytest

from rvt_ai.pipeline.scheduler import AsrScheduler


@pytest.mark.asyncio
async def test_scheduler_prioritizes_final_over_partial():
    execution_order = []

    def mock_transcribe(audio: bytes, force_lang: str | None = None) -> tuple[str, str, dict]:
        tag = audio.decode("utf-8", errors="ignore")
        execution_order.append(tag)
        return tag, "vi", {}

    scheduler = AsrScheduler(mock_transcribe)

    # Queue a partial job, then queue a final job
    p_task = asyncio.create_task(
        scheduler.execute_transcribe(b"partial_1", force_lang="vi", is_final=False, session_id="s1")
    )
    f_task = asyncio.create_task(
        scheduler.execute_transcribe(b"final_1", force_lang="vi", is_final=True, session_id="s1")
    )

    await asyncio.gather(p_task, f_task)
    await scheduler.stop()

    # Final must execute first!
    assert execution_order[0] == "final_1"


@pytest.mark.asyncio
async def test_scheduler_coalesces_partial_jobs():
    completed_jobs = []

    def mock_transcribe(audio: bytes, force_lang: str | None = None) -> tuple[str, str, dict]:
        tag = audio.decode("utf-8", errors="ignore")
        completed_jobs.append(tag)
        return tag, "vi", {}

    scheduler = AsrScheduler(mock_transcribe)

    # Submit 3 partials for session s1 rapidly before worker can run them
    p1 = asyncio.create_task(scheduler.execute_transcribe(b"part_a", force_lang="vi", is_final=False, session_id="s1"))
    p2 = asyncio.create_task(scheduler.execute_transcribe(b"part_b", force_lang="vi", is_final=False, session_id="s1"))
    p3 = asyncio.create_task(scheduler.execute_transcribe(b"part_c", force_lang="vi", is_final=False, session_id="s1"))

    res1, res2, res3 = await asyncio.gather(p1, p2, p3)
    await scheduler.stop()

    # Outdated partials are resolved with empty result and only the latest actually transcribes
    assert scheduler.dropped_partials >= 1
    assert "part_c" in completed_jobs


@pytest.mark.asyncio
async def test_final_prompt_is_built_when_the_job_runs():
    # Ba đoạn được chốt liền nhau trong lúc GPU còn bận: prompt dựng lúc xếp hàng thì cả ba đều không có chữ của đoạn
    # trước. Dựng lúc lượt chạy (và nhường một lượt cho session ghi kết quả) thì mỗi đoạn có chữ của đoạn ngay trước
    # (docs 08 §3.8).
    prompts = []
    history: list[str] = []

    def mock_transcribe(audio: bytes, force_lang: str | None = None, initial_prompt: str | None = None):
        prompts.append(initial_prompt)
        return audio.decode(), "ja", {}

    scheduler = AsrScheduler(mock_transcribe)

    async def final(tag: str) -> None:
        text, _, _ = await scheduler.execute_transcribe(
            tag.encode(), force_lang="ja", is_final=True, initial_prompt=lambda: "。".join(history) or None
        )
        history.append(text)

    await asyncio.gather(final("一"), final("二"), final("三"))
    await scheduler.stop()

    assert prompts == [None, "一", "一。二"]


@pytest.mark.asyncio
async def test_failing_prompt_builder_does_not_drop_the_segment():
    def mock_transcribe(audio: bytes, force_lang: str | None = None, initial_prompt: str | None = None):
        return audio.decode(), "ja", {}

    def broken_prompt() -> str:
        raise RuntimeError("bug")

    scheduler = AsrScheduler(mock_transcribe)
    text, _, _ = await scheduler.execute_transcribe(b"ok", is_final=True, initial_prompt=broken_prompt)
    await scheduler.stop()
    assert text == "ok"
