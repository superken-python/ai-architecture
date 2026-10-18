import sqlite3
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
STORAGE = ROOT / "storage"


def main():
    DATA.mkdir(exist_ok=True)
    STORAGE.mkdir(exist_ok=True)
    with sqlite3.connect(DATA / "enterprise.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS department_metrics (
                dept_code TEXT NOT NULL,
                quarter TEXT NOT NULL,
                revenue_usd INTEGER NOT NULL CHECK(revenue_usd >= 0),
                cost_usd INTEGER NOT NULL CHECK(cost_usd >= 0),
                active_projects INTEGER NOT NULL,
                PRIMARY KEY (dept_code, quarter)
            )
        """)
        conn.executemany(
            "INSERT OR IGNORE INTO department_metrics VALUES (?, ?, ?, ?, ?)",
            [
                ("AI_LAB", "2026-Q1", 450000, 310000, 5),
                ("AI_LAB", "2026-Q2", 620000, 340000, 7),
                ("CLOUD_OPS", "2026-Q1", 890000, 720000, 12),
                ("CLOUD_OPS", "2026-Q2", 910000, 850000, 14),
                ("FIN_TECH", "2026-Q1", 1200000, 600000, 9),
                ("FIN_TECH", "2026-Q2", 1050000, 790000, 8),
            ],
        )
    excel = DATA / "internal_rules.xlsx"
    if not excel.exists():
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "rules"
        sheet.append(["rule_id", "dept_code", "dept_name", "kind", "threshold", "label"])
        for row in [
            ("KPI_01", "AI_LAB", "Khối Nghiên cứu Trí tuệ Nhân tạo", "margin_below", 30, "CẢNH BÁO ĐỎ"),
            ("KPI_02", "CLOUD_OPS", "Khối Hạ tầng Đám mây", "cost_growth_above", 10, "CẢNH BÁO VÀNG"),
            ("KPI_03", "FIN_TECH", "Khối Công nghệ Tài chính", "revenue_growth_below", 0, "YÊU CẦU GIẢI TRÌNH"),
        ]:
            sheet.append(row)
        workbook.save(excel)
    style = DATA / "report_style_guide.txt"
    if not style.exists():
        style.write_text(
            "Phần I: Tóm tắt điều hành, tối đa 5 gạch đầu dòng.\n"
            "Phần II: Bảng KPI, USD, 2 chữ số thập phân, Rule_ID.\n"
            "Phần III: Nguồn thị trường; phải phân biệt fixture và live.\n"
            "Phần IV: Hành động và lịch sử phiên bản.\n",
            encoding="utf-8",
        )
    print("Seed hoàn tất; dữ liệu có sẵn được giữ nguyên.")


if __name__ == "__main__":
    main()
