"""Endpoint workbook: xem dữ liệu, tải file, áp kết quả tìm kiếm, hoàn tác. Chỉ routing — logic ở service."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from excel_agent.api.dependencies import get_workbooks
from excel_agent.schemas.workbook import ApplyRequest, ApplyResponse, PreviewResponse, WorkbookInfo
from excel_agent.services.workbook_service import WorkbookService

router = APIRouter(prefix="/workbooks", tags=["Workbooks"])
Workbooks = Annotated[WorkbookService, Depends(get_workbooks)]
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("", response_model=list[WorkbookInfo])
def list_workbooks(service: Workbooks, limit: int = Query(default=20, ge=1, le=100)) -> list[WorkbookInfo]:
    return service.list(limit)


@router.get("/{workbook_id}", response_model=WorkbookInfo)
def get_workbook(workbook_id: str, service: Workbooks) -> WorkbookInfo:
    return service.info(workbook_id)


@router.get("/{workbook_id}/preview", response_model=PreviewResponse)
def preview(
    workbook_id: str,
    service: Workbooks,
    sheet: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
) -> PreviewResponse:
    return service.preview(workbook_id, sheet, offset, limit)


@router.get("/{workbook_id}/download")
def download(workbook_id: str, service: Workbooks) -> FileResponse:
    return FileResponse(service.file_path(workbook_id), media_type=XLSX, filename=service.download_name(workbook_id))


@router.post("/{workbook_id}/apply", response_model=ApplyResponse)
def apply(workbook_id: str, req: ApplyRequest, service: Workbooks) -> ApplyResponse:
    return service.apply(workbook_id, req)


@router.post("/{workbook_id}/undo", response_model=WorkbookInfo)
def undo(workbook_id: str, service: Workbooks) -> WorkbookInfo:
    return service.undo(workbook_id)
