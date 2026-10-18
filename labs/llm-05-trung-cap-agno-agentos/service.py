import re
import sqlite3
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "enterprise.db"


def read_metrics(quarter: str) -> list[dict]:
    if not re.fullmatch(r"\d{4}-Q[1-4]", quarter):
        raise ValueError("quarter phải có dạng YYYY-Q1..Q4")
    # mode=ro không được tự tạo DB trống khi gõ sai đường dẫn.
    with closing(sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        rows = conn.execute(
            "SELECT * FROM department_metrics WHERE quarter = ? ORDER BY dept_code",
            (quarter,),
        ).fetchall()
        return [dict(row) for row in rows]
