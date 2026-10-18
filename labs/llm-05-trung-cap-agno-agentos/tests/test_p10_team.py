from agno_lab.p10_team import ANALYST, LEAD, RISK, WRITER, build_team
from mock_llm import call, calls, say


def test_coordinate_leader_delegates_then_synthesizes(llm):
    llm.script(
        call("delegate_task_to_member", member_id="kpi-analyst", task="Lấy KPI 2026-Q2 kèm rule_id"),
        call(
            "delegate_task_to_member",
            member_id="narrative-writer",
            task="Viết 2 ý tóm tắt: Cloud vàng, FinTech giải trình",
        ),
        say("Báo cáo: Cloud cảnh báo vàng (KPI_02), FinTech cần giải trình (KPI_03)."),
        match=LEAD,
    )
    llm.script(call("get_quarter_kpis", quarter="2026-Q2"), say("CLOUD_OPS: CẢNH BÁO VÀNG (KPI_02)."), match=ANALYST)
    llm.script(say("- Chi phí Cloud tăng 18%.\n- Doanh thu FinTech giảm."), match=WRITER)

    run = build_team("coordinate").run("Lập báo cáo KPI 2026-Q2", session_id="t1")
    assert [m.agent_id for m in run.member_responses] == ["kpi-analyst", "narrative-writer"]
    assert run.content.startswith("Báo cáo: Cloud cảnh báo vàng")
    leader_system = llm.requests_for(LEAD)[0]["messages"][0]["content"]
    assert "kpi-analyst" in leader_system and "Lấy số liệu KPI" in leader_system  # thành viên + role
    assert len(llm.requests_for(LEAD)) == 3  # giao, giao, tổng hợp


def test_route_returns_the_member_answer_directly(llm):
    llm.script(call("delegate_task_to_member", member_id="kpi-analyst", task="Ngưỡng KPI_02?"), match=LEAD)
    llm.script(call("inspect_rules"), say("KPI_02: chi phí tăng quá 10% là CẢNH BÁO VÀNG."), match=ANALYST)
    run = build_team("route").run("Ngưỡng của KPI_02 là bao nhiêu?", session_id="t2")
    assert run.content == "KPI_02: chi phí tăng quá 10% là CẢNH BÁO VÀNG."
    assert len(llm.requests_for(LEAD)) == 1  # trưởng nhóm không gọi model thêm để tổng hợp


def test_broadcast_sends_the_same_task_to_every_member(llm):
    llm.script(
        calls(("delegate_task_to_members", {"task": "Đánh giá rủi ro 2026-Q2"})),
        say("Tổng hợp 2 góc nhìn."),
        match=LEAD,
    )
    llm.script(call("get_quarter_kpis", quarter="2026-Q2"), say("Góc số liệu: Cloud vàng."), match=ANALYST)
    llm.script(
        call("get_quarter_kpis", quarter="2026-Q2"), say("Rủi ro: chi phí Cloud, doanh thu FinTech."), match=RISK
    )
    run = build_team("broadcast").run("Đánh giá rủi ro quý 2026-Q2", session_id="t3")
    assert sorted(m.agent_id for m in run.member_responses) == ["kpi-analyst", "risk-reviewer"]
    assert run.content == "Tổng hợp 2 góc nhìn."
