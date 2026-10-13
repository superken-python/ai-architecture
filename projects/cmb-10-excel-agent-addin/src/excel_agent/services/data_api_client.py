"""Client HTTP gọi API dữ liệu (ERP/CRM). Agent chỉ đi qua lớp này, không đọc dữ liệu trực tiếp."""

from __future__ import annotations

from urllib.parse import unquote

import httpx

from excel_agent.core.exceptions import DataApiError
from excel_agent.schemas.data_api import DatasetInfo, ExportRequest, SearchResponse


class DataApiClient:
    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client  # tiêm từ ngoài khi test (httpx.ASGITransport)
        self._timeout = timeout

    async def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        url = f"{self.base_url}{path}"
        try:
            if self._client is not None:
                resp = await self._client.request(method, url, **kwargs)  # type: ignore[arg-type]
            else:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.request(method, url, **kwargs)  # type: ignore[arg-type]
        except httpx.HTTPError as exc:
            raise DataApiError(f"Không gọi được API dữ liệu {url}: {exc}") from exc
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except ValueError:
                detail = resp.text
            raise DataApiError(f"API dữ liệu trả lỗi {resp.status_code}: {detail}")
        return resp

    async def list_datasets(self) -> list[DatasetInfo]:
        resp = await self._request("GET", "/datasets")
        return [DatasetInfo.model_validate(item) for item in resp.json()]

    async def search(self, query: str, dataset: str, column: str | None = None, limit: int = 20) -> SearchResponse:
        params: dict[str, str | int] = {"q": query, "dataset": dataset, "limit": limit}
        if column:
            params["column"] = column
        resp = await self._request("GET", "/search", params=params)
        return SearchResponse.model_validate(resp.json())

    async def export(self, req: ExportRequest) -> tuple[bytes, str, int]:
        resp = await self._request("POST", "/export", json=req.model_dump())
        filename = unquote(resp.headers.get("X-File-Name", "export.xlsx"))
        return resp.content, filename, int(resp.headers.get("X-Row-Count", "0"))
