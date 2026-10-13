"""Exception nghiệp vụ — tầng API đổi thành mã HTTP, agent đổi thành thông báo cho người dùng."""


class ExcelAgentError(Exception):
    """Lỗi gốc của ứng dụng."""


class NotFoundError(ExcelAgentError):
    """Không tìm thấy workbook, sheet hoặc dataset."""


class ValidationError(ExcelAgentError):
    """Dữ liệu ghi vào workbook không qua được lớp kiểm chứng (EFF-07)."""


class DataApiError(ExcelAgentError):
    """API dữ liệu trả lỗi hoặc không kết nối được."""
