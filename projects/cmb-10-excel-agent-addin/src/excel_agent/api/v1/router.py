"""Router gốc của API v1."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from excel_agent.api.dependencies import get_settings_dep
from excel_agent.api.v1 import commands, workbooks
from excel_agent.core.config import Settings

router = APIRouter()
router.include_router(workbooks.router)
router.include_router(commands.router)


@router.get("/config", tags=["Health"])
def ui_config(settings: Annotated[Settings, Depends(get_settings_dep)]) -> dict[str, Any]:
    """Thông tin cho giao diện: đang chạy OpenAI hay offline, model nào."""
    return {
        "mode": settings.resolved_mode,
        "model": settings.openai_model if settings.resolved_mode == "openai" else "offline-rules",
        "framework": "agno",
        "default_dataset": settings.default_dataset,
        "agui_path": "/agui",
        "agent_id": "excel-agent",
    }
