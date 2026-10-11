import asyncio
import os
import wave

import numpy as np
import pytest

from rvt_ai.engines.fake import FakeAsrEngine, FakeMtEngine, FakeVadEngine
from rvt_ai.engines.vad_silero import SileroVadEngine
from rvt_ai.pipeline.session import RVTSession
from rvt_contracts.messages import AsrFinal, MtFinal, Vad

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../models"))
SPEECH_WAV = os.path.join(os.path.dirname(__file__), "../fixtures/speech_16k.wav")


@pytest.mark.asyncio
async def test_session_detects_quiet_far_speech_with_real_vad():
    if not os.path.exists(os.path.join(MODELS_DIR, "silero_vad.onnx")):
        pytest.skip("silero_vad.onnx model not downloaded yet")
    with wave.open(SPEECH_WAV) as w:
        speech = np.frombuffer(w.readframes(w.getnframes()), np.int16)
    # Giảm 26 dB (~ -50 dBFS): trước đây luật `rms > 0.04` không bao giờ nhận đoạn này là tiếng nói
    far = (speech.astype(np.float32) * 10 ** (-26 / 20)).astype(np.int16)
    audio = np.concatenate([far, np.zeros(16000, dtype=np.int16)]).tobytes()

    events = []

    async def mock_send_event(event):
        events.append(event)

    session = RVTSession(
        "test-far", SileroVadEngine(model_dir=MODELS_DIR), FakeAsrEngine(), FakeMtEngine(), mock_send_event
    )
    await session.handle_turn_start("A")
    for i in range(0, len(audio), 1280):  # khung 40 ms như AudioWorklet
        await session.handle_audio_chunk(audio[i : i + 1280])
    await asyncio.sleep(0.3)

    assert any(isinstance(e, Vad) and e.speaking for e in events)
    assert len([e for e in events if isinstance(e, AsrFinal)]) >= 1


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


@pytest.mark.asyncio
async def test_session_vad_event_follows_segmenter_through_short_pause():
    vad = FakeVadEngine()
    events = []

    async def mock_send_event(event):
        events.append(event)

    session = RVTSession("test-3", vad, FakeAsrEngine(), FakeMtEngine(), mock_send_event)
    await session.handle_turn_start("A")

    await session.handle_audio_chunk(b"\x01" * int(16000 * 2 * 0.3))  # 300ms speech
    await session.handle_audio_chunk(b"\x00" * int(16000 * 2 * 0.2))  # 200ms pause < min_silence_ms

    # Khoảng lặng ngắn giữa câu không được báo "ngừng nói" (trước đây event vad nhấp nháy theo từng chunk)
    vad_events = [e.speaking for e in events if isinstance(e, Vad)]
    assert all(vad_events) and len(vad_events) >= 1


@pytest.mark.asyncio
async def test_session_turn_stop_flushes_audio():
    vad = FakeVadEngine()
    asr = FakeAsrEngine()
    mt = FakeMtEngine()

    events = []

    async def mock_send_event(event):
        events.append(event)

    session = RVTSession("test-2", vad, asr, mt, mock_send_event)

    await session.handle_turn_start("A")
    # Add 400ms of speech without adding silence
    chunk_speech = b"\x01" * int(16000 * 2 * 0.4)
    await session.handle_audio_chunk(chunk_speech)

    # Immediately stop turn before any silence detection occurs
    await session.handle_turn_stop()

    await asyncio.sleep(0.5)

    asr_finals = [e for e in events if isinstance(e, AsrFinal)]
    assert len(asr_finals) == 1
    assert asr_finals[0].side == "A"
