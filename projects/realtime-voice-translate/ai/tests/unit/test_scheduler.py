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
