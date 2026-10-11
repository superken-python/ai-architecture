import os
import re

import numpy as np
from faster_whisper import WhisperModel

from rvt_ai.core.config import settings
from rvt_ai.core.logging import logger
from rvt_ai.engines.ports import AsrEngine
from rvt_contracts.messages import Lang

VI_HALLUCINATIONS = [
    r"ghiền mì gõ",
    r"mì gõ",
    r"subscribe cho kênh",
    r"đăng ký kênh",
    r"nhấn chuông",
    r"like và share",
    r"cảm ơn các bạn đã xem",
    r"cảm ơn các bạn đã theo dõi",
    r"hẹn gặp lại các bạn",
    r"những video hấp dẫn",
    r"nhà bếp mẫu",
    r"cái nhà bếp",
    r"subtitles by",
    r"transcribed by",
    r"amara\.org",
]


class FasterWhisperEngine(AsrEngine):
    def __init__(self, model_size: str = "large-v3-turbo", device: str = "cuda", compute_type: str = "int8_float16"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

        # Persistent whisper download directory
        whisper_dir = os.path.join(settings.MODELS_DIR, "whisper")
        try:
            os.makedirs(whisper_dir, exist_ok=True)
            download_root = whisper_dir
        except OSError:
            download_root = None

        # Verify CUDA availability if requested
        if device == "cuda" and not os.path.exists("/dev/nvidia0") and not os.environ.get("CUDA_VISIBLE_DEVICES"):
            logger.warning("No NVIDIA GPU device found, selecting CPU execution")
            self.device = "cpu"
            self.compute_type = "int8"

        try:
            logger.info(f"Loading faster-whisper model '{model_size}' on {self.device} ({self.compute_type})...")
            self.model = WhisperModel(
                model_size, device=self.device, compute_type=self.compute_type, download_root=download_root
            )
        except Exception as e:
            logger.warning(f"Failed to load model on {self.device}: {e}. Falling back to CPU int8.")
            self.device = "cpu"
            self.compute_type = "int8"
            try:
                self.model = WhisperModel(model_size, device="cpu", compute_type="int8", download_root=download_root)
            except Exception as e2:
                logger.error(f"Failed to load faster-whisper model '{model_size}' on CPU: {e2}")
                raise e2

    def transcribe(self, audio: bytes, language: Lang | None = None) -> tuple[str, Lang, dict[Lang, float]]:
        # Convert 16bit PCM to float32 normalized [-1, 1]
        audio_int16 = np.frombuffer(audio, np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0

        # Energy floor check to avoid hallucinating on background silence
        rms = float(np.sqrt(np.mean(audio_float32**2))) if len(audio_float32) > 0 else 0.0
        if rms < 0.005:
            logger.debug(f"Audio RMS energy too low ({rms:.5f}), treating as silence")
            return "", "vi", {"ja": 0.0, "en": 0.0, "vi": 0.0}

        segments, info = self.model.transcribe(
            audio_float32,
            beam_size=1,
            language=language,
            vad_filter=True,
            vad_parameters=dict(threshold=0.35, min_silence_duration_ms=400),
            condition_on_previous_text=False,
            without_timestamps=True,
            no_speech_threshold=0.4,
            logprob_threshold=-1.0,
            compression_ratio_threshold=2.2,
        )

        valid_segments = []
        for s in segments:
            if s.no_speech_prob > 0.4 or s.avg_logprob < -1.2:
                logger.debug(
                    f"Filtered silent/low-confidence segment: '{s.text}' (no_speech_prob={s.no_speech_prob:.2f})"
                )
                continue
            valid_segments.append(s.text.strip())

        text = " ".join(valid_segments).strip()

        # Filter out known YouTube subtitle credit hallucinations
        for pat in VI_HALLUCINATIONS:
            if re.search(pat, text, re.IGNORECASE):
                logger.info(f"Discarded known Whisper hallucination: '{text}' (matched {pat})")
                text = ""
                break

        detected_lang: Lang = "vi"
        if info.language in ("ja", "en", "vi"):
            detected_lang = info.language  # type: ignore

        lang_probs: dict[Lang, float] = {"ja": 0.0, "en": 0.0, "vi": 0.0}

        if hasattr(info, "all_language_probs") and info.all_language_probs:
            for l_code, prob in info.all_language_probs:
                if l_code in lang_probs:
                    lang_probs[l_code] = float(prob)
        else:
            if detected_lang in lang_probs:
                lang_probs[detected_lang] = float(info.language_probability)

        return text, detected_lang, lang_probs
