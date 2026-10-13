from fastapi import APIRouter

from excel_agent.api.v1.chat import router as chat_router
from excel_agent.api.v1.excel import router as excel_router
from excel_agent.api.v1.search import router as search_router

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(chat_router)
api_v1_router.include_router(search_router)
api_v1_router.include_router(excel_router)
