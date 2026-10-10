from fastapi import APIRouter

from rvt_ai.api.health import router as health_router
from rvt_ai.api.session import router as session_router
from rvt_ai.api.stream import router as stream_router
from rvt_ai.api.translate import router as translate_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/api")
api_router.include_router(session_router, prefix="/api")
api_router.include_router(translate_router, prefix="/api")
api_router.include_router(stream_router)

__all__ = ["api_router"]
