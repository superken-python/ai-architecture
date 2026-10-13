"""API dữ liệu giả lập — đóng vai ERP/CRM của doanh nghiệp mà agent gọi tới.

Chạy riêng: `uv run uvicorn excel_agent.mock_data_api.app:create_app --factory --port 8100`.
Mặc định được gắn vào server chính tại `/mock-api` để chỉ cần chạy một tiến trình.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

from excel_agent.core.exceptions import NotFoundError, ValidationError
from excel_agent.mock_data_api.service import DataRepository
from excel_agent.schemas.data_api import DatasetInfo, ExportRequest, SearchResponse

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def create_app(repo: DataRepository | None = None) -> FastAPI:
    repo = repo or DataRepository()
    app = FastAPI(title="Mock Data API (ERP/CRM giả lập)", version="0.1.0")

    def _http(exc: Exception) -> HTTPException:
        return HTTPException(status_code=404 if isinstance(exc, NotFoundError) else 422, detail=str(exc))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/datasets", response_model=list[DatasetInfo])
    def datasets() -> list[DatasetInfo]:
        return repo.list()

    @app.get("/search", response_model=SearchResponse)
    def search(
        q: str = Query(default="", description="Từ khóa; để trống khi chỉ muốn liệt kê"),
        dataset: str = Query(default="khach_hang"),
        column: str | None = Query(default=None, description="Chỉ tìm trong cột này"),
        limit: int = Query(default=20, ge=1, le=200),
    ) -> SearchResponse:
        try:
            return repo.search(dataset, q, column, limit)
        except (NotFoundError, ValidationError) as exc:
            raise _http(exc) from exc

    @app.post("/export")
    def export(req: ExportRequest) -> Response:
        try:
            content, filename, rows = repo.export_xlsx(req)
        except (NotFoundError, ValidationError) as exc:
            raise _http(exc) from exc
        return Response(
            content,
            media_type=XLSX,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
                "X-Row-Count": str(rows),
                "X-File-Name": quote(filename),
            },
        )

    return app
