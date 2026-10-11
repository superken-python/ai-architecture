import os
import wave

import numpy as np
import pytest

from rvt_ai.engines.vad_silero import SileroVadEngine

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../models"))
SPEECH_WAV = os.path.join(os.path.dirname(__file__), "../fixtures/speech_16k.wav")
CHUNK = 640  # 40 ms ở 16 kHz, đúng cỡ khung AudioWorklet gửi lên


@pytest.fixture(scope="module")
def engine() -> SileroVadEngine:
    if not os.path.exists(os.path.join(MODELS_DIR, "silero_vad.onnx")):
        pytest.skip("silero_vad.onnx model not downloaded yet")
    return SileroVadEngine(model_dir=MODELS_DIR)


@pytest.fixture(scope="module")
def speech() -> np.ndarray:
    with wave.open(SPEECH_WAV) as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1
        return np.frombuffer(w.readframes(w.getnframes()), np.int16)


def chunk_probs(engine: SileroVadEngine, pcm: np.ndarray) -> np.ndarray:
    state = engine.create_state()
    return np.array(
        [engine.process(pcm[i : i + CHUNK].tobytes(), state) for i in range(0, len(pcm) - CHUNK + 1, CHUNK)]
    )


def test_silence_is_not_speech(engine):
    assert chunk_probs(engine, np.zeros(16000, dtype=np.int16)).max() < 0.1


def test_real_speech_is_detected(engine, speech):
    # Khi thiếu 64 mẫu ngữ cảnh, model v6.2 trả p ≈ 0 cho mọi khung → VAD "điếc", phải nói sát mic
    assert (chunk_probs(engine, speech) > 0.5).mean() > 0.6


def test_quiet_far_speech_is_detected(engine, speech):
    # Giảm 26 dB (~ -50 dBFS), tương đương người nói ở xa điện thoại
    quiet = (speech.astype(np.float32) * 10 ** (-26 / 20)).astype(np.int16)
    assert (chunk_probs(engine, quiet) > 0.5).mean() > 0.5


def test_steady_noise_is_not_speech(engine):
    rng = np.random.default_rng(0)
    noise = (rng.standard_normal(16000 * 3) * 10 ** (-20 / 20) * 32767).astype(np.int16)  # ồn trắng -20 dBFS
    assert (chunk_probs(engine, noise) > 0.5).mean() < 0.05


def test_state_reset_clears_context(engine, speech):
    state = engine.create_state()
    engine.process(speech[:CHUNK].tobytes(), state)
    state.reset()
    assert not state.context.any()
    assert len(state.audio_remainder) == 0
