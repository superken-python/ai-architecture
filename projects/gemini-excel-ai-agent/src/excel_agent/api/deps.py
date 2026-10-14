from functools import lru_cache

from excel_agent.builders.prompt_builder import PromptBuilder
from excel_agent.services.agent_service import AgentService
from excel_agent.services.db_service import MockDatabaseService
from excel_agent.services.excel_service import ExcelService


@lru_cache
def get_db_service() -> MockDatabaseService:
    """Dependency Injection cung cấp Singleton MockDatabaseService."""
    return MockDatabaseService()


@lru_cache
def get_excel_service() -> ExcelService:
    """Dependency Injection cung cấp Singleton ExcelService."""
    return ExcelService()


@lru_cache
def get_prompt_builder() -> PromptBuilder:
    """Dependency Injection cung cấp Singleton PromptBuilder."""
    return PromptBuilder()


def get_agent_service() -> AgentService:
    """Dependency Injection cung cấp AgentService."""
    db = get_db_service()
    excel = get_excel_service()
    builder = get_prompt_builder()
    return AgentService(db_service=db, excel_service=excel, prompt_builder=builder)
