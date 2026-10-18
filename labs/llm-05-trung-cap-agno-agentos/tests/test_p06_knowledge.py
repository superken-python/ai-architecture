from agno_lab.p06_knowledge import build_agent, documents, index, knowledge
from mock_llm import call, say


def contents(results) -> list[str]:
    return [d.content for d in results]


def test_documents_have_stable_names_and_metadata():
    docs = {name: meta for name, _, meta in documents()}
    assert {"KPI_01", "KPI_02", "KPI_03", "style-Phần II"} <= set(docs)
    assert docs["KPI_02"] == {"source": "rules", "rule_id": "KPI_02", "dept_code": "CLOUD_OPS"}


def test_search_and_metadata_filter(llm):
    kb = knowledge()
    assert index(kb, documents()) == 7
    style = kb.search("Phần II bảng KPI USD Rule_ID", max_results=1, filters={"source": "style"})
    assert contents(style) == ["Phần II: Bảng KPI, USD, 2 chữ số thập phân, Rule_ID."]
    rules = kb.search("CLOUD_OPS ngưỡng", max_results=10, filters={"source": "rules"})
    assert all(d.meta_data["source"] == "rules" for d in rules) and len(rules) == 3


def test_reindex_skips_unchanged_and_replaces_changed(llm):
    kb = knowledge()
    docs = documents()
    index(kb, docs)
    calls_before = len(llm.embedding_requests)
    assert index(kb, docs) == 0 and len(llm.embedding_requests) == calls_before  # không đổi → không nhúng lại

    changed = [
        (n, t.replace("ngưỡng 10.0", "ngưỡng 15.0"), m) for n, t, m in docs if n != "KPI_03"
    ]  # đổi ngưỡng KPI_02, xoá KPI_03
    index(kb, changed)
    rules = contents(kb.search("ngưỡng", max_results=10, filters={"source": "rules"}))
    assert any("ngưỡng 15.0" in r for r in rules) and not any("ngưỡng 10.0" in r for r in rules)
    assert not any(r.startswith("KPI_03") for r in rules)  # rule đã xoá không còn được tìm thấy


def test_agent_searches_knowledge_with_a_tool(llm):
    kb = knowledge()
    index(kb, documents())
    llm.script(call("search_knowledge_base", query="Phần II trình bày"), say("Phần II là bảng KPI bằng USD."))
    run = build_agent(kb).run("Phần II của báo cáo trình bày thế nào?")
    tool_names = [t["function"]["name"] for t in llm.requests[0]["tools"]]
    assert "search_knowledge_base" in tool_names and "get_quarter_kpis" in tool_names
    (search,) = run.tools
    assert "Phần II: Bảng KPI" in search.result
