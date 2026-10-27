from rvt_ai.core.config import settings
from rvt_ai.core.logging import logger
from rvt_ai.engines.asr_routed import LanguageRoutedAsrEngine
from rvt_ai.engines.asr_whisper import FasterWhisperEngine
from rvt_ai.engines.fake import FakeAsrEngine, FakeMtEngine, FakeVadEngine
from rvt_ai.engines.mt_llama import LlamaCppMtEngine, deployment_from_url
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


def build_mt_engine(profile: ProfileConfig) -> MtEngine | None:
    """Bộ dịch theo profile: "none" (chỉ nghe), "llama-cpp" (Qwen cục bộ), "api" (API trên cloud, docs 10 §13)."""
    engine = profile.mt.engine
    if engine == "none":
        return None
    if settings.USE_FAKE or engine not in ("llama-cpp", "api"):
        return FakeMtEngine()
    if engine == "llama-cpp":
        return LlamaCppMtEngine(api_url=settings.MT_API_URL, timeout_sec=settings.MT_TIMEOUT_SEC)
    mt = LlamaCppMtEngine(
        api_url=settings.MT_API_URL,
        timeout_sec=settings.MT_TIMEOUT_SEC,
        api_key=settings.MT_API_KEY,
        # URL deployment của Azure đã có tên deployment; URL gốc thì cần tên model, mặc định lấy theo profile
        model=settings.MT_MODEL or ("" if deployment_from_url(settings.MT_API_URL) else profile.mt.model),
        provider=settings.MT_PROVIDER,
        reasoning_effort=settings.MT_REASONING_EFFORT,
        max_completion_tokens=settings.MT_MAX_COMPLETION_TOKENS,
    )
    if not mt.hosted or not settings.MT_API_KEY or not mt.model:
        logger.error(
            "Profile api-mt cần RVT_MT_API_URL (URL của API hoặc deployment), RVT_MT_API_KEY, và RVT_MT_MODEL nếu URL "
            "không có tên deployment. Thiếu thì mọi câu dịch sẽ lỗi."
        )
    else:
        logger.info(
            f"MT via {mt.provider} API: model={mt.model}, reasoning_effort={mt.reasoning_effort or '(not sent)'}"
        )
    return mt


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
    return vad_engine, asr_engine, build_mt_engine(profile)
