import uuid

from excel_agent.core.decorators import measure_execution_time
from excel_agent.core.logging import app_logger
from excel_agent.models.audit_log import AuditLog
from excel_agent.schemas.common import ResponseEnvelope
from excel_agent.schemas.excel import (
    InsertRowRequest,
    InsertRowResponse,
    PreviewDiffCard,
    PreviewDiffItem,
)


class ExcelService:
    """
    Dịch vụ xử lý nghiệp vụ liên quan đến tương tác bảng tính Excel và kiểm toán.
    100% tuân thủ Universal Response Rule (trả về Pydantic v2).
    """

    def __init__(self):
        self._audit_logs: list[AuditLog] = []

    @measure_execution_time(action_name="Xác thực & sinh lệnh chèn dòng Excel")
    def prepare_insert_action(self, request: InsertRowRequest) -> InsertRowResponse:
        """
        Xác thực tính hợp lệ của yêu cầu chèn dòng và cấp phát Undo token.
        """
        row_idx = request.target_row_index or 2
        cells_count = len(request.row_values)
        token = str(uuid.uuid4())

        # Ghi log kiểm toán
        summary = f"Chèn dòng {row_idx} với {cells_count} ô dữ liệu"
        self._record_audit(
            session_id="excel-session",
            action="INSERT_ROW",
            sheet=request.sheet_name or "ActiveSheet",
            row_or_range=str(row_idx),
            summary=summary,
        )

        return InsertRowResponse(
            success=True,
            inserted_at_row=row_idx,
            cells_updated_count=cells_count,
            undo_token=token,
        )

    def generate_preview_card(self, request: InsertRowRequest) -> PreviewDiffCard:
        """
        Sinh thẻ xem trước thay đổi Preview Diff Card phục vụ Human-in-the-Loop.
        """
        row_idx = request.target_row_index or 2
        diff_items = [
            PreviewDiffItem(
                column_name=val.column_name,
                current_value=None,
                new_value=str(val.value) if val.value is not None else str(val.formula),
                is_new_row=True,
            )
            for val in request.row_values
        ]

        return PreviewDiffCard(
            action_type="INSERT_ROW",
            sheet_name=request.sheet_name or "Sheet1",
            target_row=row_idx,
            summary=f"Thao tác đề xuất: Chèn 1 dòng mới vào vị trí dòng {row_idx}",
            diff_items=diff_items,
            can_apply=True,
        )

    def _record_audit(
        self,
        session_id: str,
        action: str,
        sheet: str,
        row_or_range: str,
        summary: str,
    ) -> None:
        log_entry = AuditLog(
            session_id=session_id,
            action_type=action,
            target_sheet=sheet,
            target_row_or_range=row_or_range,
            payload_summary=summary,
            executed_by="agent",
        )
        self._audit_logs.append(log_entry)
        app_logger.bind(action=action, sheet=sheet).info(f"Đã lưu audit log: {summary}")

    def get_audit_logs_summary(self) -> ResponseEnvelope[int]:
        """Trả về số lượng bản ghi kiểm toán đã lưu."""
        return ResponseEnvelope[int](
            success=True,
            message=f"Tổng số bản ghi audit log: {len(self._audit_logs)}",
            data=len(self._audit_logs),
        )
