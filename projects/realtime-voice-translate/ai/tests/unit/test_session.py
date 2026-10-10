import asyncio

import pytest

from rvt_ai.engines.fake import FakeAsrEngine, FakeMtEngine, FakeVadEngine
from rvt_ai.pipeline.session import RVTSession
from rvt_contracts.messages import AsrFinal, MtFinal, Vad


@pytest.mark.asyncio
async def test_session_basic_flow():
    vad = FakeVadEngine()
    asr = FakeAsrEngine()
    mt = FakeMtEngine()

    events = []

    async def mock_send_event(event):
        events.append(event)

    session = RVTSession("test-1", vad, asr, mt, mock_send_event)

    # 1. Turn start A
    await session.handle_turn_start("A")

    # 2. Add speech chunk
    # Create 300ms of speech
    chunk_speech = b"\x01" * int(16000 * 2 * 0.3)
    await session.handle_audio_chunk(chunk_speech)

    # Wait to make sure MT tasks don't get triggered early
    await asyncio.sleep(0.1)

    # 3. Add silence to trigger final
    chunk_silence = b"\x00" * int(16000 * 2 * 0.6)  # 600ms silence
    await session.handle_audio_chunk(chunk_silence)

    # Give MT tasks time to run
    await asyncio.sleep(0.5)

    # Check emitted events
    assert any(isinstance(e, Vad) and e.speaking is True for e in events)
    assert any(isinstance(e, Vad) and e.speaking is False for e in events)

    asr_finals = [e for e in events if isinstance(e, AsrFinal)]
    assert len(asr_finals) == 1
    assert asr_finals[0].side == "A"
    assert asr_finals[0].lang == "vi"  # Default from fake ASR

    mt_finals = [e for e in events if isinstance(e, MtFinal)]
    assert len(mt_finals) == 2
    targets = [e.target for e in mt_finals]
    assert "en" in targets
    assert "ja" in targets
