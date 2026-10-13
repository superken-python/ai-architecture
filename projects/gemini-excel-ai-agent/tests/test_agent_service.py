import pytest

from excel_agent.schemas.agent import ChatRequest, SlashCommandRequest
from excel_agent.schemas.search import SearchRequest
from excel_agent.services.agent_service import AgentService
from excel_agent.services.db_service import MockDatabaseService
from excel_agent.services.excel_service import ExcelService


@pytest.fixture
def services():
    db = MockDatabaseService()
    excel = ExcelService()
    agent = AgentService(db_service=db, excel_service=excel)
    return db, excel, agent


def test_db_search_sku(services):
    db, _, _ = services
    req = SearchRequest(query="SP-001")
    res = db.search_products(req)
    assert res.total_found >= 1
    assert res.items[0].sku == "SP-001"


def test_db_search_fuzzy_vietnamese(services):
    db, _, _ = services
    req = SearchRequest(query="Áo thun")
    res = db.search_products(req)
    assert res.total_found >= 1
    assert "Áo thun" in res.items[0].name


@pytest.mark.asyncio
async def test_slash_command_search(services):
    _, _, agent = services
    cmd_req = SlashCommandRequest(command_text="/search Áo thun")
    res = await agent.process_slash_command(cmd_req)
    assert res.command_type == "search"
    assert len(res.items) >= 1
    assert res.items[0].sku == "SP-001"


@pytest.mark.asyncio
async def test_chat_pipeline_insert_proposal(services):
    _, _, agent = services
    chat_req = ChatRequest(
        message="Tìm SP-002 rồi thêm vào bảng",
        session_id="test-session",
        active_sheet_name="Bán Hàng Quý 4",
        row_count=5,
    )
    res = await agent.process_chat_message(chat_req)
    assert res.suggested_action is not None
    assert res.suggested_action.target_row_index == 6
    assert res.preview_diff is not None
    assert res.preview_diff.target_row == 6
