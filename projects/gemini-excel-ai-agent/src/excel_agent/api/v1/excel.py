from typing import Annotated

from fastapi import APIRouter, Depends

from excel_agent.api.deps import get_excel_service
from excel_agent.schemas.common import ResponseEnvelope
from excel_agent.schemas.excel import InsertRowRequest, InsertRowResponse
from excel_agent.services.excel_service import ExcelService

router = APIRouter(prefix="/excel", tags=["Excel Operations & Audit"])


@router.post("/prepare-insert", response_model=ResponseEnvelope[InsertRowResponse])
def prepare_insert_row(
    request: InsertRowRequest,
    excel_service: Annotated[ExcelService, Depends(get_excel_service)],
) -> ResponseEnvelope[InsertRowResponse]:
    """
    Xác thực và cấp token Undo cho hành động chèn dòng bảng tính.
    """
    result = excel_service.prepare_insert_action(request)
    return ResponseEnvelope[InsertRowResponse](
        success=True,
        message=f"Đã chuẩn bị chèn dòng {result.inserted_at_row}",
        data=result,
    )


@router.get("/audit-summary", response_model=ResponseEnvelope[int])
def get_audit_summary(
    excel_service: Annotated[ExcelService, Depends(get_excel_service)],
) -> ResponseEnvelope[int]:
    """
    Lấy tổng số thao tác bảng tính đã được ghi vết kiểm toán.
    """
    return excel_service.get_audit_logs_summary()
