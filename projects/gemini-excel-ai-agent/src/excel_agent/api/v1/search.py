from typing import Annotated

from fastapi import APIRouter, Depends, Query

from excel_agent.api.deps import get_db_service
from excel_agent.schemas.common import ResponseEnvelope
from excel_agent.schemas.search import SearchRequest, SearchResponse
from excel_agent.services.db_service import MockDatabaseService

router = APIRouter(prefix="/search", tags=["Enterprise Database Search"])


@router.post("", response_model=ResponseEnvelope[SearchResponse])
def search_database_post(
    request: SearchRequest,
    db_service: Annotated[MockDatabaseService, Depends(get_db_service)],
) -> ResponseEnvelope[SearchResponse]:
    """
    Tìm kiếm danh mục sản phẩm doanh nghiệp qua POST payload.
    """
    result = db_service.search_products(request)
    return ResponseEnvelope[SearchResponse](
        success=True,
        message=f"Tìm thấy {result.total_found} sản phẩm",
        data=result,
    )


@router.get("/products", response_model=ResponseEnvelope[SearchResponse])
def search_database_get(
    db_service: Annotated[MockDatabaseService, Depends(get_db_service)],
    q: str = Query(..., description="Từ khóa tìm kiếm"),
    limit: int = Query(default=10, description="Số lượng tối đa"),
) -> ResponseEnvelope[SearchResponse]:
    """
    Tìm kiếm danh mục sản phẩm doanh nghiệp qua GET query param.
    """
    req = SearchRequest(query=q, limit=limit)
    result = db_service.search_products(req)
    return ResponseEnvelope[SearchResponse](
        success=True,
        message=f"Tìm thấy {result.total_found} sản phẩm",
        data=result,
    )
