"""Khởi tạo server: AgentOS + giao diện AG-UI + agent Agno + API workbook + web UI + task pane Excel.

Chạy: `uv run uvicorn excel_agent.main:create_app --factory --port 7777` (hoặc `make dev`).

Một tiến trình phục vụ:
- `POST /agui`                 AG-UI endpoint của AgentOS → agent Agno (tool Excel chạy ở client: tạm dừng/tiếp tục)
- `/api/v1/commands`           lệnh `/search`, `/datasets`, `/help` (chạy bằng code, không gọi model)
- `/api/v1/workbooks/...`      web POC: xem dữ liệu, tải file, ghi có kiểm chứng, hoàn tác
- `/mock-api/...`              API dữ liệu giả lập (ERP/CRM) mà agent gọi tới — tắt bằng MOUNT_MOCK_API=false
- `/`                          web POC: khung chat + bảng Excel mô phỏng
- `/static/taskpane.html`      task pane của Office add-in (chạy trong Excel thật, xem addin/manifest.xml)
- các endpoint chuẩn của AgentOS: `/health`, `/info`, `/agents/excel-agent/runs`, `/sessions`…
"""

from __future__ import annotations

import httpx
from agno.db.sqlite import SqliteDb
from agno.models.base import Model
from agno.os import AgentOS
from agno.os.interfaces.agui import AGUI
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from excel_agent.agents.context import AgentDeps, UiState
from excel_agent.agents.excel_agent import build_agent
from excel_agent.api.v1.router import router as api_v1
from excel_agent.core.config import PROJECT_ROOT, Settings, get_settings
from excel_agent.core.exceptions import DataApiError, NotFoundError, ValidationError
from excel_agent.core.logging import setup_logging
from excel_agent.mock_data_api.app import create_app as create_mock_api
from excel_agent.services.data_api_client import DataApiClient
from excel_agent.services.workbook_service import WorkbookService

WEB_DIR = PROJECT_ROOT / "web"


def create_app(
    settings: Settings | None = None, data_api_http: httpx.AsyncClient | None = None, model: Model | None = None
) -> FastAPI:
    """`data_api_http` / `model` cho phép test tiêm API giả lập và model "kịch bản" (không mạng, không key)."""
    settings = settings or get_settings()
    setup_logging()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)

    workbooks = WorkbookService(settings.workbooks_dir, settings.max_preview_rows, settings.max_apply_rows)
    mock_api = create_mock_api() if settings.mount_mock_api else None
    data_api_url = settings.resolved_data_api_url
    if mock_api is not None and not settings.data_api_url and data_api_http is None:
        # API giả lập gắn cùng server → gọi thẳng trong tiến trình (chạy được cả khi server dùng HTTPS)
        data_api_url = "http://mock-api"
        data_api_http = httpx.AsyncClient(transport=httpx.ASGITransport(app=mock_api), base_url=data_api_url)
    data_api = DataApiClient(data_api_url, client=data_api_http)

    def deps_factory(ui: UiState) -> AgentDeps:
        return AgentDeps(settings=settings, data_api=data_api, workbooks=workbooks, ui=ui)

    base = FastAPI(title=settings.app_name, version="0.2.0")
    base.state.settings, base.state.workbooks, base.state.deps_factory = settings, workbooks, deps_factory
    _register_errors(base)
    base.include_router(api_v1, prefix="/api/v1")
    if mock_api is not None:
        base.mount("/mock-api", mock_api)
    base.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @base.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    db = SqliteDb(db_file=str(settings.db_file))
    agent = build_agent(settings, deps_factory, db=db, model=model)
    agent_os = AgentOS(
        id="excel-agent-os",
        name=settings.app_name,
        description="POC CMB-10: AgentOS + AG-UI + agent Agno, công cụ Excel chạy ở add-in",
        agents=[agent],
        interfaces=[AGUI(agent=agent)],
        db=db,
        base_app=base,
        on_route_conflict="preserve_base_app",  # "/" là giao diện của POC thay cho trang JSON mặc định
        cors_allowed_origins=settings.cors_origins,
        telemetry=False,
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
