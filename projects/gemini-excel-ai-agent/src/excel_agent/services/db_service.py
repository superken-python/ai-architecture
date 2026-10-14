from excel_agent.core.decorators import measure_execution_time
from excel_agent.core.logging import app_logger
from excel_agent.models.product import Product
from excel_agent.schemas.search import ProductItemDTO, SearchRequest, SearchResponse
from excel_agent.strategies.search_strategy import KeywordAndFuzzySearchStrategy


class MockDatabaseService:
    """
    Dịch vụ quản lý cơ sở dữ liệu doanh nghiệp giả lập (Mock Enterprise DB).
    Chứa 100% business logic dữ liệu và luôn trả về Pydantic v2 models.
    """

    def __init__(self):
        self._products: list[Product] = []
        self._search_strategy = KeywordAndFuzzySearchStrategy()
        self._seed_mock_data()

    def _seed_mock_data(self) -> None:
        """Nạp dữ liệu mẫu danh mục sản phẩm doanh nghiệp."""
        sample_items = [
            Product(
                id=1,
                sku="SP-001",
                name="Áo thun Polo Nam Cotton Cao Cấp",
                category="Thời trang nam",
                unit_price=250000.0,
                stock_quantity=150,
                unit="Cái",
                status="Kinh doanh",
                description="Áo polo thoáng khí, co giãn 4 chiều, thêu logo ngực",
            ),
            Product(
                id=2,
                sku="SP-002",
                name="Quần Jean Nam Slimfit Co Giãn",
                category="Thời trang nam",
                unit_price=450000.0,
                stock_quantity=80,
                unit="Cái",
                status="Kinh doanh",
                description="Vải denim cao cấp bền màu, form ôm vừa vặn",
            ),
            Product(
                id=3,
                sku="SP-003",
                name="Áo Sơ Mi Nữ Công Sở Dài Tay",
                category="Thời trang nữ",
                unit_price=320000.0,
                stock_quantity=120,
                unit="Cái",
                status="Kinh doanh",
                description="Chất lụa ngọc trai chống nhăn, kiểu dáng thanh lịch",
            ),
            Product(
                id=4,
                sku="SP-004",
                name="Vải Sợi Kháng Khuẩn Eco-Fabric",
                category="Nguyên phụ liệu",
                unit_price=85000.0,
                stock_quantity=1200,
                unit="Mét",
                status="Kinh doanh",
                description="Vải dệt công nghệ nano kháng khuẩn đạt chuẩn xuất khẩu",
            ),
            Product(
                id=5,
                sku="SP-005",
                name="Chỉ May Công Nghiệp Spun Polyester 40/2",
                category="Nguyên phụ liệu",
                unit_price=35000.0,
                stock_quantity=500,
                unit="Cuộn",
                status="Kinh doanh",
                description="Độ bền kéo cao, chống xơ sợi dùng cho máy may tự động",
            ),
            Product(
                id=6,
                sku="SP-006",
                name="Thùng Carton 5 Lớp Đóng Gói Xuất Khẩu",
                category="Bao bì",
                unit_price=18000.0,
                stock_quantity=2000,
                unit="Thùng",
                status="Kinh doanh",
                description="Kích thước 60x40x40 cm, chịu lực nén chuẩn quốc tế",
            ),
            Product(
                id=7,
                sku="SP-007",
                name="Máy Quét Mã Vạch Không Dây 2D",
                category="Thiết bị kho",
                unit_price=1250000.0,
                stock_quantity=25,
                unit="Bộ",
                status="Kinh doanh",
                description="Quét nhanh QR code và barcode, kết nối Bluetooth 5.0",
            ),
        ]
        self._products = sample_items
        app_logger.info(f"Đã khởi tạo Mock Enterprise DB thành công với {len(self._products)} sản phẩm.")

    def get_all_products(self) -> list[Product]:
        """Lấy toàn bộ danh sách thực thể sản phẩm nội bộ."""
        return self._products

    @measure_execution_time(action_name="Truy vấn danh mục sản phẩm")
    def search_products(self, request: SearchRequest) -> SearchResponse:
        """
        Tìm kiếm sản phẩm theo từ khóa và bộ lọc.
        Bắt buộc trả về Pydantic v2 SearchResponse.
        """
        matched_dtos = self._search_strategy.search(
            products=self._products,
            query=request.query,
            limit=request.limit,
        )

        return SearchResponse(
            query=request.query,
            total_found=len(matched_dtos),
            items=matched_dtos,
        )

    def get_product_by_sku(self, sku: str) -> ProductItemDTO | None:
        """Tra cứu chi tiết 1 sản phẩm theo SKU."""
        clean_sku = sku.strip().upper()
        for p in self._products:
            if p.sku.upper() == clean_sku:
                return ProductItemDTO(
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
        return None
