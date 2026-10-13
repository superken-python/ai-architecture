"""Dựng agent Excel bằng Agno: một `Agent` duy nhất, model OpenAI Responses (mặc định gpt-5-mini).

Vì sao một agent chứ không phải Team (agent điều phối + agent chuyên trách): công cụ Excel do add-in khai báo
qua AG-UI chỉ được gắn vào agent mà AgentOS chạy trực tiếp. Agno 3.1.3 chuyển `dependencies` sang thành viên
của Team nhưng KHÔNG chuyển `client_tools` (`team/_default_tools.py`), nên agent chuyên trách sẽ không gọi được
excel_*. Với ~8 công cụ, gpt-5-mini chọn tool tốt mà không cần điều phối, lại bớt một lượt gọi model.
"""

from __future__ import annotations

import logging

import httpx
from agno.agent import Agent
from agno.db.base import BaseDb
from agno.models.base import Model
from agno.models.openai import OpenAIResponses
from agno.run.base import RunContext

from excel_agent.agents.context import UI_CONTEXT_KEY, DepsFactory, UiState
from excel_agent.agents.tools import SystemDataTools
from excel_agent.builders.prompt_builder import load_prompt, render
from excel_agent.core.config import Settings
from excel_agent.core.exceptions import ExcelAgentError
from excel_agent.offline_llm import app as offline_llm
from excel_agent.offline_llm.brains import RuleBrain

log = logging.getLogger(__name__)
AGENT_ID = "excel-agent"
REASONING_PREFIXES = ("gpt-5", "o3", "o4")


def build_model(settings: Settings, offline_http: httpx.AsyncClient | None = None) -> Model:
    """OpenAI thật khi có key; không có key → model giả lập trong tiến trình (cùng đường code Agno)."""
    if settings.resolved_mode == "offline":
        log.warning("Chưa có OPENAI_API_KEY → chạy model offline (luật cố định).")
        return OpenAIResponses(
            id="offline-rules",
            api_key="offline",
            base_url=offline_llm.BASE_URL,
            http_client=offline_http or offline_llm.http_client(RuleBrain()),
            store=False,
        )
    if settings.openai_api_key is None or not settings.openai_api_key.get_secret_value():
        raise ValueError("AGENT_MODE=openai nhưng chưa đặt OPENAI_API_KEY")
    reasoning = settings.openai_model.startswith(REASONING_PREFIXES)
    return OpenAIResponses(
        id=settings.openai_model,
        api_key=settings.openai_api_key.get_secret_value(),
        base_url=settings.openai_base_url or None,
        reasoning_effort=settings.openai_reasoning_effort if reasoning else None,
        store=settings.openai_store,
    )


def _format_datasets(datasets: list[dict]) -> str:
    return "\n".join(
        f"- {d['name']} ({d['title']}, {d['rows']} dòng): " + ", ".join(c["name"] for c in d["columns"])
        for d in datasets
    )


def build_agent(settings: Settings, deps_factory: DepsFactory, db: BaseDb | None, model: Model | None = None) -> Agent:
    template = load_prompt("excel_agent")["instructions"]

    async def instructions(run_context: RunContext | None = None) -> str:
        dependencies = (run_context.dependencies if run_context else None) or {}
        deps = deps_factory(UiState.from_context(dependencies.get(UI_CONTEXT_KEY)))
        try:
            datasets = _format_datasets(await deps.datasets())
        except ExcelAgentError as exc:
            datasets = f"(chưa lấy được danh mục: {exc})"
        return render(template, datasets=datasets)

    return Agent(
        id=AGENT_ID,
        name="Excel Assistant",
        description="Trợ lý trong Excel: tìm và ghi dữ liệu trên sheet, tra cứu và xuất dữ liệu từ hệ thống",
        model=model or build_model(settings),
        instructions=instructions,
        tools=[SystemDataTools(deps_factory)],
        db=db,
        add_history_to_context=True,
        num_history_runs=settings.num_history_runs,
        tool_call_limit=settings.tool_call_limit,
        markdown=True,
        telemetry=False,
    )
