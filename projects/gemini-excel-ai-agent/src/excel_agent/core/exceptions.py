class ExcelAgentException(Exception):
    """Lớp ngoại lệ cơ sở của Excel AI Agent."""

    def __init__(self, message: str, code: str = "EXCEL_AGENT_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class LLMInferenceException(ExcelAgentException):
    """Ngoại lệ khi gọi mô hình LLM (Azure OpenAI / Agno)."""

    def __init__(self, message: str):
        super().__init__(message, code="LLM_INFERENCE_ERROR")


class MockDatabaseException(ExcelAgentException):
    """Ngoại lệ khi truy vấn Mock Database."""

    def __init__(self, message: str):
        super().__init__(message, code="MOCK_DB_ERROR")


class InvalidCommandException(ExcelAgentException):
    """Ngoại lệ khi cú pháp lệnh Slash command không hợp lệ."""

    def __init__(self, message: str):
        super().__init__(message, code="INVALID_COMMAND_ERROR")
