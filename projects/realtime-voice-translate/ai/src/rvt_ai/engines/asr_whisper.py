import os
import re

import numpy as np
from faster_whisper import WhisperModel

from rvt_ai.core.config import settings
from rvt_ai.core.logging import logger
from rvt_ai.engines.ports import AsrEngine
from rvt_contracts.messages import Lang

HALLUCINATIONS = [
    # English silence / background noise hallucinations
    r"^\s*(?:you|you\.)\s*$",
    r"^\s*(?:thank you|thank you\.|thanks|thanks\.|thank you very much)\s*$",
    r"^\s*(?:thanks for watching|thank you for watching|thank you so much)[!.]*\s*$",
    r"^\s*(?:bye|goodbye|bye bye|bye-bye)\s*[\.!\?]*$",
    r"^\s*(?:please subscribe|subscribe|like and subscribe)\s*[\.!\?]*$",
    r"^\s*(?:silence|\[silence\]|\(silence\)|\.\.\.|\—)\s*$",
    # Vietnamese subtitle credits
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

# Câu ngắn chỉ gồm đúng từ đó, cho phép dấu câu hai bên: prompt ngữ cảnh nối bằng "。" làm Whisper hay ra "おわり。"
# (docs 08 §3.3). Câu thoại thật như "おわりだ" không khớp.
_JA_EDGE = r"[\s・…—\-。、！？!?]*"
JA_HALLUCINATIONS = [
    r"ご視聴(?:ありがとう|いただき)",
    r"チャンネル登録",
    rf"^{_JA_EDGE}字幕{_JA_EDGE}$",
    rf"^{_JA_EDGE}おわり{_JA_EDGE}$",
    rf"^{_JA_EDGE}終わり{_JA_EDGE}$",
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

    def transcribe(
        self,
        audio: bytes,
        language: Lang | None = None,
        vad_mean: float | None = None,
        initial_prompt: str | None = None,
        min_avg_logprob: float | None = None,
    ) -> tuple[str, Lang, dict[Lang, float]]:
        # Convert 16bit PCM to float32 normalized [-1, 1]
        audio_int16 = np.frombuffer(audio, np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0

        # Energy floor check to avoid processing pure digital silence or faint ambient room noise
        rms = float(np.sqrt(np.mean(audio_float32**2))) if len(audio_float32) > 0 else 0.0
        if rms < 0.003:
            level_dbfs = 20 * np.log10(max(rms, 1e-9))
            logger.info(f"Audio RMS energy too low ({rms:.5f} ≈ {level_dbfs:.1f} dBFS < 0.003), treating as silence")
            return "", "vi", {"ja": 0.0, "en": 0.0, "vi": 0.0}

        segments, info = self.model.transcribe(
            audio_float32,
            beam_size=1,
            language=language,
            temperature=0.0,
            vad_filter=False,
            condition_on_previous_text=False,
            initial_prompt=initial_prompt,
            without_timestamps=True,
            no_speech_threshold=0.6,
            log_prob_threshold=-1.0,
            compression_ratio_threshold=2.4,
        )

        valid_segments = []
        for s in segments:
            if s.no_speech_prob > 0.6:
                logger.info(
                    f"Filtered silent/no-speech segment: '{s.text}' "
                    f"(no_speech_prob={s.no_speech_prob:.2f}, avg_logprob={s.avg_logprob:.2f})"
                )
                continue
            # Vùng VAD bỏ sót (docs 09 §4.1) chỉ giữ chữ Whisper nghe khá chắc
            if min_avg_logprob is not None and s.avg_logprob < min_avg_logprob:
                logger.info(f"Filtered low-confidence segment: '{s.text}' (avg_logprob={s.avg_logprob:.2f})")
                continue
            valid_segments.append(s.text.strip())

        text = " ".join(valid_segments).strip()

        # Collapse excessive repeating character screams or loop hallucinations (e.g. うおおおお... 500 times)
        if text:
            text = re.sub(r"(.)\1{7,}", r"\1\1\1\1\1", text).strip()
            text = re.sub(r"(.{2,6}?)\1{5,}", r"\1\1\1", text).strip()

        # Filter out known Whisper hallucinations
        for pat in HALLUCINATIONS:
            if re.search(pat, text, re.IGNORECASE):
                # If it's a polite "thank you" / "thanks", only discard if energy was low (ambient silence)
                if re.search(r"^\s*(?:thank you|thanks)\.?\s*$", text, re.IGNORECASE) and rms >= 0.015:
                    continue
                logger.info(f"Discarded known Whisper hallucination: '{text}' (matched {pat})")
                text = ""
                break

        # Filter Japanese hallucinations if segment had low average speech probability (VAD < 0.35)
        # (Preserves genuine video endings spoken clearly by real voices)
        if text:
            for pat in JA_HALLUCINATIONS:
                if re.search(pat, text):
                    if vad_mean is not None and vad_mean < 0.35:
                        logger.info(
                            f"Discarded Japanese hallucination: '{text}' "
                            f"(matched {pat}, vad_mean={vad_mean:.2f} < 0.35)"
                        )
                        text = ""
                        break
                    elif vad_mean is None and rms < 0.008:
                        logger.info(
                            f"Discarded Japanese hallucination on low energy: '{text}' (matched {pat}, rms={rms:.4f})"
                        )
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
