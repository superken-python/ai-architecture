from rvt_ai.core.config import settings
from rvt_ai.core.logging import logger
from rvt_ai.engines.asr_routed import LanguageRoutedAsrEngine
from rvt_ai.engines.asr_whisper import FasterWhisperEngine
from rvt_ai.engines.fake import FakeAsrEngine, FakeMtEngine, FakeVadEngine
from rvt_ai.engines.mt_llama import LlamaCppMtEngine
from rvt_ai.engines.ports import AsrEngine, MtEngine, VadEngine
from rvt_ai.engines.vad_silero import SileroVadEngine
from rvt_ai.packs.loader import AsrConfig, ProfileConfig


def build_asr_engine(asr: AsrConfig, device: str | None = None, compute_type: str | None = None) -> AsrEngine:
    """faster-whisper theo profile. Có `asr.models` thì mỗi ngôn ngữ một model (docs 10 §10.3)."""
    device = device or asr.device
    compute_type = compute_type or asr.compute_type

    def factory(model: str) -> AsrEngine:
        return FasterWhisperEngine(model_size=model, device=device, compute_type=compute_type)

    if asr.models:
        return LanguageRoutedAsrEngine(asr.model, asr.models, factory)
    return factory(asr.model)


def build_engines_from_profile(profile: ProfileConfig) -> tuple[VadEngine, AsrEngine, MtEngine | None]:
    logger.info(f"Building engines for profile '{profile.name}'...")

    # 1. VAD Engine
    if profile.vad.engine == "silero" and not settings.USE_FAKE:
        vad_engine: VadEngine = SileroVadEngine(model_dir=settings.MODELS_DIR)
    else:
        vad_engine = FakeVadEngine()

    # 2. ASR Engine
    if profile.asr.engine == "faster-whisper" and not settings.USE_FAKE:
        asr_engine: AsrEngine = build_asr_engine(profile.asr)
    else:
        asr_engine = FakeAsrEngine()

    # 3. MT Engine. "none": chế độ chỉ nghe, không dịch (docs 10 §10.3)
    mt_engine: MtEngine | None
    if profile.mt.engine == "none":
        mt_engine = None
    elif profile.mt.engine == "llama-cpp" and not settings.USE_FAKE:
        mt_engine = LlamaCppMtEngine(api_url=settings.MT_API_URL, timeout_sec=settings.MT_TIMEOUT_SEC)
    else:
        mt_engine = FakeMtEngine()

    return vad_engine, asr_engine, mt_engine
