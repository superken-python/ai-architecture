"""Dữ liệu khách hàng nhỏ trong bộ nhớ — thay cho API hệ thống của CMB-10."""

from __future__ import annotations

import copy

FIELDS = ("name", "city", "credit_limit", "debt", "status")

SEED = {
    "KH-0012": {
        "name": "Công ty An Phát",
        "city": "Hà Nội",
        "credit_limit": 300_000_000,
        "debt": 120_000_000,
        "status": "Đang giao",
    },
    "KH-0031": {
        "name": "Minh Long",
        "city": "Đà Nẵng",
        "credit_limit": 150_000_000,
        "debt": 20_000_000,
        "status": "Hoàn tất",
    },
    "KH-0047": {
        "name": "Hải Đăng",
        "city": "Hà Nội",
        "credit_limit": 80_000_000,
        "debt": 79_000_000,
        "status": "Đang giao",
    },
}


class CustomerDB:
    def __init__(self, rows: dict[str, dict] | None = None) -> None:
        self.rows = copy.deepcopy(rows if rows is not None else SEED)
        self.writes: list[tuple[str, str, str]] = []

    def search(self, query: str) -> list[dict]:
        q = query.strip().lower()
        return [
            {"id": cid, **row}
            for cid, row in self.rows.items()
            if q in cid.lower() or q in row["name"].lower() or q in row["city"].lower()
        ]

    def get(self, customer_id: str) -> dict | None:
        row = self.rows.get(customer_id)
        return {"id": customer_id, **row} if row else None

    def update(self, customer_id: str, field: str, value: str) -> None:
        if customer_id not in self.rows:
            raise KeyError(f"không có khách hàng {customer_id}")
        if field not in FIELDS:
            raise KeyError(f"không có trường '{field}'")
        current = self.rows[customer_id][field]
        self.rows[customer_id][field] = int(value) if isinstance(current, int) else value
        self.writes.append((customer_id, field, value))
