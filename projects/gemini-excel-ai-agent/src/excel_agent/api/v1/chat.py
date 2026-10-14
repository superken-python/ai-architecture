from typing import Annotated

from fastapi import APIRouter, Depends

from excel_agent.api.deps import get_agent_service
from excel_agent.schemas.agent import (
    ChatRequest,
    ChatResponse,
    SlashCommandRequest,
    SlashCommandResponse,
)
from excel_agent.schemas.common import ResponseEnvelope
from excel_agent.services.agent_service import AgentService

router = APIRouter(prefix="/chat", tags=["Agent Chat & Slash Commands"])


@router.post("/message", response_model=ResponseEnvelope[ChatResponse])
async def send_chat_message(
    request: ChatRequest,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> ResponseEnvelope[ChatResponse]:
    """
    Tiếp nhận tin nhắn hội thoại hoặc chỉ dẫn từ Excel Taskpane và xử lý qua ReAct Loop.
    """
    response = await agent_service.process_chat_message(request)
    return ResponseEnvelope[ChatResponse](
        success=True,
        message="Xử lý tin nhắn thành công",
        data=response,
    )


@router.post("/command", response_model=ResponseEnvelope[SlashCommandResponse])
async def execute_slash_command(
    request: SlashCommandRequest,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> ResponseEnvelope[SlashCommandResponse]:
    """
    Thực thi trực tiếp lệnh tắt Slash Command (ví dụ: '/search Áo thun').
    """
    response = await agent_service.process_slash_command(request)
    return ResponseEnvelope[SlashCommandResponse](
        success=True,
        message="Thực thi lệnh tắt thành công",
        data=response,
    )
