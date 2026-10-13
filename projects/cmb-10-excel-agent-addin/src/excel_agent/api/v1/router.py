"""Router gốc của API v1."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from excel_agent.api.dependencies import get_settings_dep
from excel_agent.api.v1 import workbooks
from excel_agent.core.config import Settings

router = APIRouter()
router.include_router(workbooks.router)


@router.get("/config", tags=["Health"])
def ui_config(settings: Annotated[Settings, Depends(get_settings_dep)]) -> dict[str, Any]:
    """Thông tin cho giao diện: đang chạy OpenAI hay offline, model nào, có agent điều phối không."""
    return {
        "mode": settings.resolved_mode,
        "model": settings.openai_model if settings.resolved_mode == "openai" else "offline-rules",
        "triage": settings.use_triage,
        "default_dataset": settings.default_dataset,
        "agui_path": "/agui",
        "agent_id": "excel-agent",
    }
