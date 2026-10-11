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
        assert text == ""  # Blocked by HALLUCINATIONS


def test_faster_whisper_english_silence_hallucinations():
    mock_model = MagicMock()
    mock_info = MagicMock()
    mock_info.language = "en"
    mock_info.language_probability = 0.99
    mock_info.all_language_probs = [("en", 0.99)]

    with patch("rvt_ai.engines.asr_whisper.WhisperModel", return_value=mock_model):
        engine = FasterWhisperEngine(model_size="tiny", device="cpu", compute_type="int8")

        # 1. "you" on faint audio -> must be discarded
        mock_seg_you = MagicMock()
        mock_seg_you.text = " you"
        mock_seg_you.no_speech_prob = 0.4
        mock_model.transcribe.return_value = ([mock_seg_you], mock_info)

        t = np.linspace(0, 1.0, 16000, False)
        # Faint room noise: amplitude 200 (RMS ~ 0.004)
        audio_faint = (np.sin(2 * np.pi * 300 * t) * 200).astype(np.int16).tobytes()

        text_you, _, _ = engine.transcribe(audio_faint, language="en")
        assert text_you == ""

        # 2. "Thank you." on faint audio -> must be discarded
        mock_seg_ty = MagicMock()
        mock_seg_ty.text = " Thank you."
        mock_seg_ty.no_speech_prob = 0.4
        mock_model.transcribe.return_value = ([mock_seg_ty], mock_info)

        text_ty_faint, _, _ = engine.transcribe(audio_faint, language="en")
        assert text_ty_faint == ""

        # 3. "Thank you." on clear audible speech (RMS ~ 0.35) -> must be preserved
        audio_loud = (np.sin(2 * np.pi * 300 * t) * 16000).astype(np.int16).tobytes()
        mock_seg_real = MagicMock()
        mock_seg_real.text = " Thank you."
        mock_seg_real.no_speech_prob = 0.02
        mock_model.transcribe.return_value = ([mock_seg_real], mock_info)

        text_real, _, _ = engine.transcribe(audio_loud, language="en")
        assert text_real == "Thank you."
