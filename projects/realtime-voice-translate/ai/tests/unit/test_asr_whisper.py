from unittest.mock import MagicMock, patch

import numpy as np

from rvt_ai.engines.asr_whisper import FasterWhisperEngine


def test_faster_whisper_rms_silence_floor():
    with patch("rvt_ai.engines.asr_whisper.WhisperModel"):
        engine = FasterWhisperEngine(model_size="tiny", device="cpu", compute_type="int8")
        # Silence audio (all zeros)
        silence = b"\x00" * 3200
        text, lang, probs = engine.transcribe(silence)
        assert text == ""
        assert lang == "vi"


def test_faster_whisper_transcribe_params_and_output():
    mock_model = MagicMock()
    # Mock segment
    mock_seg = MagicMock()
    mock_seg.text = " Xin chào"
    mock_seg.no_speech_prob = 0.05
    mock_seg.avg_logprob = -0.4

    mock_info = MagicMock()
    mock_info.language = "vi"
    mock_info.language_probability = 0.99
    mock_info.all_language_probs = [("vi", 0.99), ("en", 0.01), ("ja", 0.0)]

    mock_model.transcribe.return_value = ([mock_seg], mock_info)

    with patch("rvt_ai.engines.asr_whisper.WhisperModel", return_value=mock_model):
        engine = FasterWhisperEngine(model_size="tiny", device="cpu", compute_type="int8")

        # Create audio tone with audible RMS
        t = np.linspace(0, 1.0, 16000, False)
        audio = (np.sin(2 * np.pi * 300 * t) * 16000).astype(np.int16).tobytes()

        text, lang, probs = engine.transcribe(audio, language="vi")

        # Verify transcribe kwargs (specifically no invalid logprob_threshold)
        mock_model.transcribe.assert_called_once()
        _, kwargs = mock_model.transcribe.call_args
        assert "logprob_threshold" not in kwargs
        assert kwargs.get("log_prob_threshold") == -1.0
        assert kwargs.get("vad_filter") is False

        assert text == "Xin chào"
        assert lang == "vi"
        assert probs["vi"] == 0.99


def test_faster_whisper_hallucination_filter():
    mock_model = MagicMock()
    mock_seg = MagicMock()
    mock_seg.text = " Hãy đăng ký kênh và bấm chuông theo dõi Ghiền Mì Gõ nhé"
    mock_seg.no_speech_prob = 0.05
    mock_seg.avg_logprob = -0.4

    mock_info = MagicMock()
    mock_info.language = "vi"
    mock_info.language_probability = 0.99
    mock_info.all_language_probs = [("vi", 0.99)]

    mock_model.transcribe.return_value = ([mock_seg], mock_info)

    with patch("rvt_ai.engines.asr_whisper.WhisperModel", return_value=mock_model):
        engine = FasterWhisperEngine(model_size="tiny", device="cpu", compute_type="int8")
        t = np.linspace(0, 1.0, 16000, False)
        audio = (np.sin(2 * np.pi * 300 * t) * 16000).astype(np.int16).tobytes()

        text, lang, probs = engine.transcribe(audio, language="vi")
        assert text == ""  # Blocked by VI_HALLUCINATIONS
