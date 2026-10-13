"""Fixture cho test giao diện: server POC chạy thật (offline, không API key) + Chromium của Playwright."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

PROJECT = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    port = _free_port()
    env = {
        **os.environ,
        "AGENT_MODE": "offline",
        "OPENAI_API_KEY": "",
        "PORT": str(port),
        "STORAGE_DIR": str(tmp_path_factory.mktemp("var")),
    }
    cmd = [sys.executable, "-m", "uvicorn", "excel_agent.main:create_app", "--factory", "--port", str(port)]
    proc = subprocess.Popen(cmd, cwd=PROJECT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            try:
                if httpx.get(f"{base}/health", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.5)
        else:
            raise RuntimeError("server không khởi động được")
        yield base
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.fixture(scope="session")
def browser() -> Iterator[Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    exe = os.environ.get("CHROMIUM_PATH")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        yield b
        b.close()


def shot(page: Any, name: str) -> None:
    """Đặt E2E_SCREENSHOTS=<thư mục> để lưu ảnh chụp từng bước."""
    folder = os.environ.get("E2E_SCREENSHOTS")
    if folder:
        Path(folder).mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(Path(folder) / f"{name}.png"), full_page=True)
