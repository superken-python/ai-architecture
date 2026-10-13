from pathlib import Path

import pytest
from agno.models.openai import OpenAIResponses

from excel_agent.agents.excel_agent import build_agent, build_model
from excel_agent.core.config import Settings


def _settings(tmp_path: Path, **kw: object) -> Settings:
    return Settings(_env_file=None, storage_dir=tmp_path, **kw)


def test_offline_mode_uses_in_process_mock(tmp_path: Path) -> None:
    model = build_model(_settings(tmp_path, openai_api_key=None))
    assert isinstance(model, OpenAIResponses) and model.id == "offline-rules" and model.store is False
    assert str(model.base_url).startswith("http://offline-llm")


def test_openai_mode_gpt5_mini_reasoning_no_store(tmp_path: Path) -> None:
    s = _settings(tmp_path, openai_api_key="sk-test-not-real", openai_base_url="http://gateway.local/v1")
    model = build_model(s)
    assert s.resolved_mode == "openai"
    assert (model.id, model.reasoning_effort, model.store) == ("gpt-5-mini", "low", False)
    assert model.base_url == "http://gateway.local/v1"
    # model không phải dòng suy luận → không gửi reasoning_effort
    assert build_model(_settings(tmp_path, openai_api_key="sk-x", openai_model="gpt-4.1-mini")).reasoning_effort is None


def test_openai_mode_requires_key(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        build_model(_settings(tmp_path, agent_mode="openai", openai_api_key=""))


def test_single_agno_agent_with_server_tools(tmp_path: Path) -> None:
    agent = build_agent(_settings(tmp_path, openai_api_key=None), deps_factory=lambda ui: None, db=None)
    assert agent.id == "excel-agent" and agent.telemetry is False and agent.add_history_to_context
    (toolkit,) = agent.tools
    assert set(toolkit.get_async_functions()) == {"list_datasets", "search_data", "export_excel"}
