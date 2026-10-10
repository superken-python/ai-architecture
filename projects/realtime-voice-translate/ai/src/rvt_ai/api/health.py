from fastapi import APIRouter

from rvt_ai.api.stream import active_sessions
from rvt_ai.core.config import settings
from rvt_ai.packs.loader import get_pack_registry
from rvt_contracts.messages import HealthResponse, MetricsResponse, ReadyResponse

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=HealthResponse)
async def health_live() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/ready", response_model=ReadyResponse)
async def health_ready() -> ReadyResponse:
    pack_reg = get_pack_registry()
    profile = pack_reg.get_profile(settings.PROFILE)
    return ReadyResponse(
        ready=True,
        profile=profile.name,
        pack_revision=pack_reg.revision,
        models={"vad": profile.vad.engine, "asr": profile.asr.engine, "mt": profile.mt.engine},
    )


@router.get("/metrics", response_model=MetricsResponse)
async def metrics() -> MetricsResponse:
    pack_reg = get_pack_registry()
    profile = pack_reg.get_profile(settings.PROFILE)
    return MetricsResponse(
        active_sessions=len(active_sessions),
        max_sessions=settings.MAX_SESSIONS,
        profile=profile.name,
        pack_revision=pack_reg.revision,
    )
