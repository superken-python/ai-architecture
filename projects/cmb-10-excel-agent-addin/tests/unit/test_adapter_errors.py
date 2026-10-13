import httpx
import openai
from agents.exceptions import MaxTurnsExceeded

from excel_agent.agents.runtime.agentos_adapter import friendly_error


def test_connection_error_message_suggests_slash_commands() -> None:
    exc = openai.APIConnectionError(request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
    msg = str(friendly_error(exc))
    assert "Không kết nối được OpenAI API" in msg and "/search" in msg


def test_auth_error_points_to_env_file() -> None:
    resp = httpx.Response(401, request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
    exc = openai.AuthenticationError("bad key", response=resp, body=None)
    assert "OPENAI_API_KEY" in str(friendly_error(exc))


def test_max_turns_and_unknown_errors() -> None:
    assert "MAX_TURNS" in str(friendly_error(MaxTurnsExceeded("too many")))
    other = ValueError("x")
    assert friendly_error(other) is other
