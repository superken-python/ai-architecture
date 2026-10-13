from abc import ABC, abstractmethod

from excel_agent.models.product import Product
from excel_agent.schemas.search import ProductItemDTO


class SearchStrategy(ABC):
    """Giao diện Strategy cho thuật toán tìm kiếm dữ liệu."""

    @abstractmethod
    def search(self, products: list[Product], query: str, limit: int = 10) -> list[ProductItemDTO]:
        """Thực hiện tìm kiếm trên danh sách sản phẩm."""


class KeywordAndFuzzySearchStrategy(SearchStrategy):
    """
    Chiến lược tìm kiếm kết hợp từ khóa, mã SKU và chuẩn hóa chuỗi tiếng Việt.
    Hỗ trợ tìm kiếm theo token và chuỗi con trong câu tự nhiên.
    """

    def search(self, products: list[Product], query: str, limit: int = 10) -> list[ProductItemDTO]:
        query_norm = self._normalize(query)
        query_tokens = set(query_norm.split())
        matches: list[Product] = []

        # 1. Tìm chính xác theo SKU hoặc nếu câu chứa SKU (ví dụ: query chứa 'sp-002')
        for p in products:
            sku_norm = self._normalize(p.sku)
            if (sku_norm == query_norm or sku_norm in query_norm or sku_norm in query_tokens) and p not in matches:
                matches.append(p)

        # 2. Tìm theo tên hoặc danh mục
        for p in products:
            if p in matches:
                continue
            name_norm = self._normalize(p.name)
            cat_norm = self._normalize(p.category)
            desc_norm = self._normalize(p.description or "")

            # Khớp chuỗi con đầy đủ
            if query_norm in name_norm or query_norm in cat_norm or query_norm in desc_norm:
                matches.append(p)
                continue

            # Khớp theo các token có nghĩa (> 2 ký tự)
            meaningful_tokens = [
                t for t in query_tokens if len(t) > 2 and t not in ["tìm", "rồi", "thêm", "bảng", "giúp", "dòng"]
            ]
            if any(t in name_norm or t in cat_norm for t in meaningful_tokens):
                matches.append(p)

        # Cắt theo giới hạn limit
        limited_matches = matches[:limit]

        # Chuyển đổi sang Pydantic DTO (Universal Response Rule)
        return [
            ProductItemDTO(
                id=p.id or 0,
                sku=p.sku,
                name=p.name,
                category=p.category,
                unit_price=p.unit_price,
                stock_quantity=p.stock_quantity,
                unit=p.unit,
                status=p.status,
                description=p.description,
            )
            for p in limited_matches
        ]

    @staticmethod
    def _normalize(text: str) -> str:
        """Chuẩn hóa ký tự: viết thường, loại bỏ khoảng trắng thừa."""
        return " ".join(text.lower().strip().split())
