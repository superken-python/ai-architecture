"""Dựng agent bằng OpenAI Agents SDK: agent điều phối (triage) + 2 agent chuyên trách qua handoff."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from agents import Agent, ModelSettings, OpenAIResponsesModel, RunContextWrapper, set_tracing_disabled
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.models.interface import Model
from openai import AsyncOpenAI
from openai.types.shared import Reasoning

from excel_agent.agents.context import AgentDeps
from excel_agent.agents.offline_model import OfflineRuleModel
from excel_agent.agents.tools import export_excel, list_datasets, search_data
from excel_agent.builders.prompt_builder import load_prompt, render
from excel_agent.core.config import Settings
from excel_agent.core.exceptions import ExcelAgentError

log = logging.getLogger(__name__)


def build_model(settings: Settings) -> Model:
    if settings.resolved_mode == "offline":
        log.warning("Chưa có OPENAI_API_KEY → chạy model offline (luật cố định).")
        return OfflineRuleModel()
    if settings.openai_api_key is None or not settings.openai_api_key.get_secret_value():
        raise ValueError("AGENT_MODE=openai nhưng chưa đặt OPENAI_API_KEY")
    client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value(), base_url=settings.openai_base_url or None)
    return OpenAIResponsesModel(model=settings.openai_model, openai_client=client)


def build_model_settings(settings: Settings) -> ModelSettings:
    if settings.resolved_mode == "openai" and settings.openai_model.startswith(("gpt-5", "o")):
        return ModelSettings(reasoning=Reasoning(effort=settings.openai_reasoning_effort))
    return ModelSettings()


def _format_datasets(datasets: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"- {d['name']} ({d['title']}, {d['rows']} dòng): " + ", ".join(c["name"] for c in d["columns"])
        for d in datasets
    )


def _instructions(prompt_name: str) -> Callable[[RunContextWrapper[AgentDeps], Agent[AgentDeps]], Awaitable[str]]:
    template = load_prompt(prompt_name)["instructions"]

    async def build(ctx: RunContextWrapper[AgentDeps], agent: Agent[AgentDeps]) -> str:
        deps = ctx.context
        try:
            datasets = _format_datasets(await deps.datasets())
        except ExcelAgentError as exc:
            datasets = f"(chưa lấy được danh mục: {exc})"
        return render(
            template, handoff_prefix=RECOMMENDED_PROMPT_PREFIX, datasets=datasets, ui_state=deps.describe_ui()
        )

    return build


def build_starting_agent(settings: Settings, model: Model | None = None) -> Agent[AgentDeps]:
    """Agent bắt đầu mỗi lượt chạy: điều phối (mặc định) hoặc một agent đủ tool (USE_TRIAGE=false)."""
    set_tracing_disabled(not settings.openai_tracing)
    model = model or build_model(settings)
    model_settings = build_model_settings(settings)

    report_prompt = load_prompt("excel_report")
    search_prompt = load_prompt("data_search")
    report = Agent[AgentDeps](
        name=report_prompt["name"],
        handoff_description=report_prompt["handoff_description"],
        instructions=_instructions("excel_report"),
        tools=[list_datasets, export_excel],
        model=model,
        model_settings=model_settings,
    )
    search = Agent[AgentDeps](
        name=search_prompt["name"],
        handoff_description=search_prompt["handoff_description"],
        instructions=_instructions("data_search"),
        tools=[list_datasets, search_data],
        model=model,
        model_settings=model_settings,
    )
    if not settings.use_triage:
        return Agent[AgentDeps](
            name="Excel Assistant",
            instructions=_instructions("single"),
            tools=[list_datasets, export_excel, search_data],
            model=model,
            model_settings=model_settings,
        )
    triage_prompt = load_prompt("triage")
    return Agent[AgentDeps](
        name=triage_prompt["name"],
        instructions=_instructions("triage"),
        handoffs=[report, search],
        model=model,
        model_settings=model_settings,
    )
