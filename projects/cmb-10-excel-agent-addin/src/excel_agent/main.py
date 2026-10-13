"""Khởi tạo server: AgentOS (Agno) + giao diện AG-UI + agent OpenAI Agents SDK + API workbook + web UI.

Chạy: `uv run uvicorn excel_agent.main:create_app --factory --port 7777` (hoặc `make dev`).

Một tiến trình phục vụ:
- `POST /agui`                 AG-UI endpoint của AgentOS → agent (OpenAI Agents SDK, qua adapter)
- `/api/v1/workbooks/...`      xem dữ liệu, tải file, áp kết quả tìm kiếm, hoàn tác
- `/mock-api/...`              API dữ liệu giả lập (ERP/CRM) mà agent gọi tới — tắt bằng MOUNT_MOCK_API=false
- `/`                          giao diện chat + bảng Excel (web/)
- các endpoint chuẩn của AgentOS: `/health`, `/info`, `/agents/excel-agent/runs`, `/sessions`…
"""

from __future__ import annotations

import httpx
from agno.db.sqlite import SqliteDb
from agno.os import AgentOS
from agno.os.interfaces.agui import AGUI
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from excel_agent.agents.context import AgentDeps, UiState
from excel_agent.agents.factory import build_starting_agent
from excel_agent.agents.runtime.agentos_adapter import OpenAIAgentsAdapter, build_run_config
from excel_agent.api.v1.router import router as api_v1
from excel_agent.core.config import PROJECT_ROOT, Settings, get_settings
from excel_agent.core.exceptions import DataApiError, NotFoundError, ValidationError
from excel_agent.core.logging import setup_logging
from excel_agent.mock_data_api.app import create_app as create_mock_api
from excel_agent.services.data_api_client import DataApiClient
from excel_agent.services.workbook_service import WorkbookService

WEB_DIR = PROJECT_ROOT / "web"
AGENT_ID = "excel-agent"


def create_app(settings: Settings | None = None, data_api_http: httpx.AsyncClient | None = None) -> FastAPI:
    """`data_api_http` cho phép test tiêm client gọi thẳng API giả lập (httpx.ASGITransport)."""
    settings = settings or get_settings()
    setup_logging()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)

    workbooks = WorkbookService(settings.workbooks_dir, settings.max_preview_rows, settings.max_apply_rows)
    data_api = DataApiClient(settings.resolved_data_api_url, client=data_api_http)

    base = FastAPI(title=settings.app_name, version="0.1.0")
    base.state.settings, base.state.workbooks, base.state.data_api = settings, workbooks, data_api
    _register_errors(base)
    base.include_router(api_v1, prefix="/api/v1")
    if settings.mount_mock_api:
        base.mount("/mock-api", create_mock_api())
    base.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @base.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    db = SqliteDb(db_file=str(settings.db_file))
    agent = OpenAIAgentsAdapter(
        id=AGENT_ID,
        name="Excel Agent (OpenAI Agents SDK)",
        description="Xuất file Excel từ API dữ liệu, tìm kiếm và áp kết quả vào cột",
        db=db,
        starting_agent=build_starting_agent(settings),
        deps_factory=lambda ui: AgentDeps(
            settings=settings, data_api=data_api, workbooks=workbooks, ui=ui or UiState()
        ),
        max_turns=settings.max_turns,
        run_config=build_run_config("excel-agent-poc", tracing_disabled=not settings.openai_tracing),
    )
    agent_os = AgentOS(
        id="excel-agent-os",
        name=settings.app_name,
        description="POC CMB-10: AgentOS + AG-UI + OpenAI Agents SDK",
        agents=[agent],
        interfaces=[AGUI(agent=agent)],
        db=db,
        base_app=base,
        on_route_conflict="preserve_base_app",  # "/" là giao diện của POC thay cho trang JSON mặc định
        cors_allowed_origins=settings.cors_origins,
    )
    return agent_os.get_app()


def _register_errors(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def invalid(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(DataApiError)
    async def upstream(_: Request, exc: DataApiError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})
