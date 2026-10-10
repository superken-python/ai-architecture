from rvt_ai.core.config import settings
from rvt_ai.core.logging import logger
from rvt_ai.engines.asr_whisper import FasterWhisperEngine
from rvt_ai.engines.fake import FakeAsrEngine, FakeMtEngine, FakeVadEngine
from rvt_ai.engines.mt_llama import LlamaCppMtEngine
from rvt_ai.engines.ports import AsrEngine, MtEngine, VadEngine
from rvt_ai.engines.vad_silero import SileroVadEngine
from rvt_ai.packs.loader import ProfileConfig


def build_engines_from_profile(profile: ProfileConfig) -> tuple[VadEngine, AsrEngine, MtEngine]:
    logger.info(f"Building engines for profile '{profile.name}'...")

    # 1. VAD Engine
    if profile.vad.engine == "silero" and not settings.USE_FAKE:
        vad_engine: VadEngine = SileroVadEngine(model_dir=settings.MODELS_DIR, threshold=profile.vad.threshold)
    else:
        vad_engine = FakeVadEngine()

    # 2. ASR Engine
    if profile.asr.engine == "faster-whisper" and not settings.USE_FAKE:
        asr_engine: AsrEngine = FasterWhisperEngine(
            model_size=profile.asr.model, device=profile.asr.device, compute_type=profile.asr.compute_type
        )
    else:
        asr_engine = FakeAsrEngine()

    # 3. MT Engine
    if profile.mt.engine == "llama-cpp" and not settings.USE_FAKE:
        mt_engine: MtEngine = LlamaCppMtEngine(api_url=settings.MT_API_URL, timeout_sec=settings.MT_TIMEOUT_SEC)
    else:
        mt_engine = FakeMtEngine()

    return vad_engine, asr_engine, mt_engine
