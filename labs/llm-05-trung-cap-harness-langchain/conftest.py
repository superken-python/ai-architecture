"""Fixture chung cho test của lab. Thư mục này được pytest đưa vào sys.path nên `import harness` chạy được."""

from __future__ import annotations

import uuid

import pytest


@pytest.fixture
def thread() -> str:
    return uuid.uuid4().hex
