from datetime import date

import pytest

from excel_agent.agents.commands import parse_command
from excel_agent.agents.intent import detect_intent, report_args, search_args
from excel_agent.core.text import find_name, normalize
from excel_agent.core.values import parse_date, to_number


def test_normalize_vietnamese() -> None:
    assert normalize("  Thành   PHỐ ") == "thanh pho"
    assert normalize("Mã ĐH") == "ma dh"
    assert normalize("Hà Nội") == normalize("ha noi")
    assert normalize(None) == ""


def test_find_name_ignores_accents_and_case() -> None:
    cols = ["Mã KH", "Thành phố"]
    assert find_name(cols, "thanh pho") == "Thành phố"
    assert find_name(cols, "Email") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1.234.567", 1234567), ("1.234,5", 1234.5), ("1,234.5", 1234.5), ("12,5", 12.5), ("12.5", 12.5), ("abc", None)],
)
def test_to_number(raw: str, expected: float | None) -> None:
    assert to_number(raw) == expected


def test_parse_date_formats() -> None:
    assert parse_date("2026-09-28") == date(2026, 9, 28)
    assert parse_date("28/09/2026") == date(2026, 9, 28)
    assert parse_date("hôm qua") is None


def test_parse_search_command_variants() -> None:
    assert parse_command("xin chào") is None
    cmd = parse_command("/search Đà Nẵng")
    assert (cmd.name, cmd.query, cmd.column, cmd.dataset) == ("search", "Đà Nẵng", None, None)
    cmd = parse_command("/search Thành phố: Đà Nẵng")
    assert (cmd.column, cmd.query) == ("Thành phố", "Đà Nẵng")
    cmd = parse_command("/search in:san_pham laptop")
    assert (cmd.dataset, cmd.query) == ("san_pham", "laptop")
    cmd = parse_command("/search @don_hang Trạng thái=Đang giao")
    assert (cmd.dataset, cmd.column, cmd.query) == ("don_hang", "Trạng thái", "Đang giao")
    assert parse_command("/help").name == "help"
    assert parse_command("/xyz").name == "unknown"


def test_offline_intent_rules() -> None:
    assert detect_intent("Tạo file Excel khách hàng ở Hà Nội") == "report"
    assert detect_intent("tìm khách hàng ở Đà Nẵng") == "search"
    assert detect_intent("chào bạn") == "help"
    args = report_args("Xuất danh sách khách hàng doanh nghiệp ở TP. Hồ Chí Minh")
    assert args["dataset"] == "khach_hang"
    assert {"column": "Thành phố", "op": "eq", "value": "TP. Hồ Chí Minh"} in args["filters"]
    assert {"column": "Phân khúc", "op": "eq", "value": "Doanh nghiệp"} in args["filters"]
    assert report_args("đơn hàng đang giao")["filters"] == [{"column": "Trạng thái", "op": "eq", "value": "Đang giao"}]
    assert search_args("tìm khách hàng ở Đà Nẵng")["query"] == "Đà Nẵng"
