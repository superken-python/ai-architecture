from datetime import date

import pytest

from excel_agent.agents.commands import parse_command
from excel_agent.core.text import find_name, normalize
from excel_agent.core.values import parse_date, to_number
from excel_agent.offline_llm.rules import (
    detect_intent,
    map_record,
    record_query,
    report_args,
    search_args,
    sheet_find_args,
    update_args,
)


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


def test_offline_rules_for_excel_intents() -> None:
    assert detect_intent("Thêm khách hàng KH-0012 vào bảng") == "append"
    assert detect_intent("chèn sản phẩm SP-003 vào sheet") == "append"
    assert detect_intent('Ghi "VIP" vào cột Phân khúc cho các dòng đang chọn') == "update"
    assert detect_intent("Tìm dòng có Thành phố là Đà Nẵng trong bảng") == "find_sheet"
    assert detect_intent("tìm khách hàng KH-0012") == "search"

    assert record_query("Thêm khách hàng kh-0012 vào bảng")["query"] == "KH-0012"
    headers = ["Mã KH", "Tên khách hàng", "Thành phố"]
    args = sheet_find_args("Tìm dòng có Thành phố là Đà Nẵng trong bảng", headers)
    assert (args["column"], args["query"]) == ("Thành phố", "Đà Nẵng")
    assert sheet_find_args("tìm Cần Thơ trong bảng", headers) == {
        "query": "Cần Thơ",
        "column": None,
        "match": "contains",
        "limit": 20,
    }
    assert update_args('Ghi "VIP" vào cột Thành phố cho các dòng đang chọn', headers, [3, 4]) == {
        "column": "Thành phố",
        "rows": [3, 4],
        "values": ["VIP"],
        "create_column": False,
    }
    assert update_args("ghi VIP vào cột Thành phố", headers, [3]) is None  # thiếu ngoặc kép


def test_map_record_keeps_only_sheet_columns() -> None:
    record = {"Mã KH": "KH-0001", "Tên khách hàng": "A", "Email": "a@x.vn", "Thành phố": "Huế"}
    assert map_record(record, ["Mã KH", "thanh pho", "Ghi chú"]) == {"Mã KH": "KH-0001", "thanh pho": "Huế"}


def test_sheet_find_keeps_value_after_la() -> None:
    args = sheet_find_args("Tìm dòng có Trạng thái là Đang giao trong bảng", ["Mã ĐH", "Trạng thái"])
    assert (args["column"], args["query"]) == ("Trạng thái", "Đang giao")
