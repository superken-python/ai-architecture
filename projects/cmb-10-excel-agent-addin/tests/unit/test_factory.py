from pathlib import Path

from agents import OpenAIResponsesModel

from excel_agent.agents.factory import build_model, build_model_settings, build_starting_agent
from excel_agent.agents.offline_model import OfflineRuleModel
from excel_agent.core.config import Settings


def _settings(tmp_path: Path, **kw: object) -> Settings:
    return Settings(_env_file=None, storage_dir=tmp_path, **kw)


def test_auto_mode_without_key_is_offline(tmp_path: Path) -> None:
    s = _settings(tmp_path, openai_api_key=None)
    assert s.resolved_mode == "offline"
    assert isinstance(build_model(s), OfflineRuleModel)


def test_openai_mode_uses_gpt5_mini_with_reasoning(tmp_path: Path) -> None:
    s = _settings(tmp_path, openai_api_key="sk-test-not-real")
    model = build_model(s)
    assert s.resolved_mode == "openai" and isinstance(model, OpenAIResponsesModel)
    assert model.model == "gpt-5-mini"
    assert build_model_settings(s).reasoning.effort == "low"


def test_openai_base_url_from_settings(tmp_path: Path) -> None:
    s = _settings(tmp_path, openai_api_key="sk-test-not-real", openai_base_url="http://gateway.local/v1")
    assert str(build_model(s)._client.base_url) == "http://gateway.local/v1/"


def test_triage_agent_hands_off_to_two_specialists(tmp_path: Path) -> None:
    agent = build_starting_agent(_settings(tmp_path, openai_api_key=None))
    assert agent.name == "Điều phối" and not agent.tools
    assert sorted(h.name for h in agent.handoffs) == ["Data Search Agent", "Excel Report Agent"]
    report = next(h for h in agent.handoffs if h.name == "Excel Report Agent")
    assert sorted(t.name for t in report.tools) == ["export_excel", "list_datasets"]


def test_single_agent_mode_has_all_tools(tmp_path: Path) -> None:
    agent = build_starting_agent(_settings(tmp_path, openai_api_key=None, use_triage=False))
    assert not agent.handoffs
    assert sorted(t.name for t in agent.tools) == ["export_excel", "list_datasets", "search_data"]
