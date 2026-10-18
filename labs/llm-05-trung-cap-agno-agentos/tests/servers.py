"""Chạy server thật cho test: một tiến trình riêng như production, trên cổng còn trống."""

import contextlib
import os
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator

from settings_paths import ROOT


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def process_server(args: list[str], port: int, **env: str) -> Iterator[str]:
    """Chạy `python <args>` ở gốc project (thêm biến môi trường `env`), đợi cổng mở, trả http://127.0.0.1:PORT."""
    with tempfile.TemporaryFile() as log:
        proc = subprocess.Popen([sys.executable, *args], cwd=ROOT, env={**os.environ, **env}, stdout=log, stderr=log)
        try:
            deadline = time.time() + 60
            while True:
                try:
                    socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                    break
                except OSError:
                    if proc.poll() is not None or time.time() > deadline:
                        log.seek(0)
                        raise RuntimeError(f"server không khởi động: {args}\n{log.read().decode()[-3000:]}") from None
                    time.sleep(0.1)
            yield f"http://127.0.0.1:{port}"
        finally:
            proc.terminate()
            proc.wait(timeout=10)
