"""Phần 6 — Knowledge (RAG): nạp quy ước và style guide vào vector DB, agent tự tìm khi cần.

Theo Lab 00 §8: số liệu và rule BẮT BUỘC lấy chính xác bằng tool; semantic search chỉ cho hướng dẫn bổ sung.

    uv run python -m agno_lab.p06_knowledge index
    uv run python -m agno_lab.p06_knowledge ask "Phần II của báo cáo cần trình bày thế nào?"
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

from agno.agent import Agent
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.lancedb import LanceDb, SearchType

from agno_lab.p01_agent import KpiTools, inspect_rules
from agno_lab.settings import ROOT, model, vector_dir
from rules import load_rules

Doc = tuple[str, str, dict]  # (name ổn định, nội dung, metadata)


def knowledge() -> Knowledge:
    embedder = OpenAIEmbedder(
        id=os.getenv("EMBEDDING_ID", "text-embedding-3-small"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        dimensions=int(os.getenv("EMBEDDING_DIMS", "1536")),  # đổi số chiều thì phải xoá và dựng lại bảng
    )
    vector_db = LanceDb(
        uri=str(vector_dir()), table_name="report_guides", embedder=embedder, search_type=SearchType.vector
    )
    return Knowledge(
        name="report-guides", description="Quy ước KPI và hướng dẫn trình bày báo cáo", vector_db=vector_db
    )


def documents() -> list[Doc]:
    """Mỗi rule Excel và mỗi dòng style guide là một document có name ổn định và metadata để lọc."""
    docs: list[Doc] = []
    for code, rule in load_rules().items():
        text = (
            f"{rule['rule_id']} áp dụng cho {rule['dept_name']} ({code}): loại {rule['kind']}, "
            f"ngưỡng {rule['threshold']}, nhãn {rule['label']}."
        )
        docs.append((rule["rule_id"], text, {"source": "rules", "rule_id": rule["rule_id"], "dept_code": code}))
    for line in (ROOT / "data/report_style_guide.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            section = line.split(":")[0]  # "Phần I", "Phần II", ...
            docs.append((f"style-{section}", line, {"source": "style", "section": section}))
    return docs


def index(kb: Knowledge, docs: list[Doc]) -> int:
    """Nạp lại khi nguồn đổi. Trả về số document đã nhúng (0 = không có gì đổi, không tốn tiền embedding)."""
    state_file = vector_dir() / "index_state.json"
    digest = hashlib.sha256(json.dumps(docs, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    if state_file.exists() and json.loads(state_file.read_text())["hash"] == digest:
        return 0
    old = json.loads(state_file.read_text())["names"] if state_file.exists() else []
    names = [name for name, _, _ in docs]
    for name in set(old) - set(names):  # rule đã bị xoá khỏi Excel: xoá vector của nó
        kb.remove_vectors_by_name(name)
    for name, text, meta in docs:
        kb.insert(name=name, text_content=text, metadata=meta, upsert=True)  # cùng name → bản cũ bị thay
    state_file.write_text(json.dumps({"hash": digest, "names": names}))
    return len(docs)


def build_agent(kb: Knowledge) -> Agent:
    return Agent(
        id="guide-assistant",
        name="Guide Assistant",
        model=model(),
        knowledge=kb,
        search_knowledge=True,  # thêm tool search_knowledge_base; model tự quyết khi nào tìm
        tools=[KpiTools(), inspect_rules],
        instructions=[
            "Số liệu và quy ước KPI: luôn dùng get_quarter_kpis và inspect_rules (chính xác, không tìm gần đúng).",
            "Cách trình bày báo cáo: tìm bằng search_knowledge_base rồi trích đúng hướng dẫn tìm được.",
        ],
    )


if __name__ == "__main__":
    kb = knowledge()
    if sys.argv[1:2] == ["index"]:
        print(f"Đã nhúng {index(kb, documents())} document")
    else:
        print(build_agent(kb).run(sys.argv[2] if len(sys.argv) > 2 else "Phần II trình bày thế nào?").content)
