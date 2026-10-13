"""Lệnh bắt đầu bằng `/` — chạy thẳng bằng code, không gọi LLM (EFF-04: code làm được thì không gọi model).

Cú pháp `/search`:
- `/search Đà Nẵng`                   → tìm mọi cột (hoặc cột đang chọn trên bảng Excel)
- `/search Thành phố: Đà Nẵng`        → tìm theo cột (cũng nhận `Thành phố=Đà Nẵng`)
- `/search in:san_pham laptop`        → chọn dataset (cũng nhận `@san_pham`)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from excel_agent.core.text import normalize

CommandName = Literal["search", "datasets", "help", "unknown"]
_DATASET_TOKEN = re.compile(r"(?:^|\s)(?:in:|@)(\S+)")


@dataclass
class Command:
    name: CommandName
    query: str = ""
    column: str | None = None
    dataset: str | None = None
    raw: str = ""


def parse_command(text: str) -> Command | None:
    text = (text or "").strip()
    if not text.startswith("/"):
        return None
    head, _, rest = text[1:].partition(" ")
    name = normalize(head)
    if name in ("search", "s", "tim"):
        dataset = None
        match = _DATASET_TOKEN.search(rest)
        if match:
            dataset = match.group(1)
            rest = (rest[: match.start()] + " " + rest[match.end() :]).strip()
        column = None
        for sep in (":", "="):
            left, found, right = rest.partition(sep)
            if found and left.strip() and right.strip():
                column, rest = left.strip(), right.strip()
                break
        return Command("search", query=rest.strip(), column=column, dataset=dataset, raw=text)
    if name in ("datasets", "data", "dulieu"):
        return Command("datasets", raw=text)
    if name in ("help", "?", "huongdan"):
        return Command("help", raw=text)
    return Command("unknown", query=head, raw=text)
