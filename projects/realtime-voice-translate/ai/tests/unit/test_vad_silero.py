import os

import numpy as np
import pytest

from rvt_ai.engines.vad_silero import SileroVadEngine


def test_silero_vad_engine_v5():
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../models"))
    onnx_file = os.path.join(model_path, "silero_vad.onnx")
    if not os.path.exists(onnx_file):
        pytest.skip("silero_vad.onnx model not downloaded yet")

    engine = SileroVadEngine(model_dir=model_path)
    state = engine.create_state()

    # 40ms of silence (640 samples, 1280 bytes)
    silence_pcm = np.zeros(640, dtype=np.int16).tobytes()
    has_speech_silence = engine.process(silence_pcm, state)
    assert has_speech_silence is False

    # Reset state
    state.reset()
