"""Nạp prompt từ YAML (prompt isolation) và điền biến bằng string.Template."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from string import Template
from typing import Any

import yaml

from excel_agent.core.config import PROJECT_ROOT

PROMPTS_DIR = PROJECT_ROOT / "prompts" / "agents"


@lru_cache
def load_prompt(name: str, prompts_dir: Path = PROMPTS_DIR) -> dict[str, Any]:
    data = yaml.safe_load((prompts_dir / f"{name}.yml").read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "instructions" not in data:
        raise ValueError(f"Prompt {name}.yml thiếu trường 'instructions'")
    return data


def render(template: str, **values: str) -> str:
    """Điền $biến; biến thiếu giữ nguyên để dễ phát hiện khi review prompt."""
    return Template(template).safe_substitute(**values).strip()
