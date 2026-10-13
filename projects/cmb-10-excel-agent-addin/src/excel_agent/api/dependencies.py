"""FastAPI dependencies: lấy service dùng chung đã gắn vào `app.state` lúc khởi tạo."""

from fastapi import Request

from excel_agent.agents.context import DepsFactory
from excel_agent.core.config import Settings
from excel_agent.services.workbook_service import WorkbookService


def get_workbooks(request: Request) -> WorkbookService:
    return request.app.state.workbooks


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_deps_factory(request: Request) -> DepsFactory:
    return request.app.state.deps_factory
