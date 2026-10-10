import os

import numpy as np
from faster_whisper import WhisperModel

from rvt_ai.core.logging import logger
from rvt_ai.engines.ports import AsrEngine
from rvt_contracts.messages import Lang


class FasterWhisperEngine(AsrEngine):
    def __init__(self, model_size: str = "large-v3-turbo", device: str = "cuda", compute_type: str = "int8_float16"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

        # Verify CUDA availability if requested
        if device == "cuda" and not os.path.exists("/dev/nvidia0") and not os.environ.get("CUDA_VISIBLE_DEVICES"):
            logger.warning("No NVIDIA GPU device found, selecting CPU execution")
            self.device = "cpu"
            self.compute_type = "int8"

        try:
            logger.info(f"Loading faster-whisper model '{model_size}' on {self.device} ({self.compute_type})...")
            self.model = WhisperModel(model_size, device=self.device, compute_type=self.compute_type)
        except Exception as e:
            logger.warning(f"Failed to load model on {self.device}: {e}. Falling back to CPU int8.")
            self.device = "cpu"
            self.compute_type = "int8"
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio: bytes, language: Lang | None = None) -> tuple[str, Lang, dict[Lang, float]]:
        # Convert 16bit PCM to float32 normalized [-1, 1]
        audio_int16 = np.frombuffer(audio, np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0

        segments, info = self.model.transcribe(
            audio_float32,
            beam_size=1,
            language=language,
            vad_filter=False,
            condition_on_previous_text=False,
            without_timestamps=True,
        )

        text = "".join([s.text for s in segments]).strip()

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
