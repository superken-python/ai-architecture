"""Endpoint lệnh `/search`, `/datasets`, `/help`. Chỉ routing — logic ở `agents/commands.py`."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from excel_agent.agents.commands import parse_command, run_command
from excel_agent.agents.context import DepsFactory, UiState
from excel_agent.api.dependencies import get_deps_factory
from excel_agent.schemas.commands import CommandRequest, CommandResponse

router = APIRouter(prefix="/commands", tags=["Commands"])


@router.post("", response_model=CommandResponse)
async def execute(
    req: CommandRequest, deps_factory: Annotated[DepsFactory, Depends(get_deps_factory)]
) -> CommandResponse:
    command = parse_command(req.text)
    if command is None:
        return CommandResponse(handled=False)
    out = await run_command(command, deps_factory(UiState.from_context(req.ui)))
    return CommandResponse(handled=True, result=out.result, text=out.text)
