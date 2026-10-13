"""Sinh dữ liệu mẫu (giả lập) cho API dữ liệu của POC.

Chạy: `uv run python scripts/generate_sample_data.py` — kết quả cố định (seed), ghi vào
`src/excel_agent/mock_data_api/data/`. Dữ liệu hoàn toàn bịa, không có thông tin thật.
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "src" / "excel_agent" / "mock_data_api" / "data"
SEED = 20261013

CITIES = ["Hà Nội", "TP. Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ", "Nha Trang", "Huế", "Bắc Ninh"]
SEGMENTS = ["Doanh nghiệp", "Đại lý", "Cá nhân"]
LAST = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Vũ", "Đặng", "Bùi", "Đỗ", "Ngô"]
MIDDLE = ["Văn", "Thị", "Minh", "Đức", "Thu", "Hải", "Quốc", "Ngọc"]
FIRST = ["An", "Bình", "Châu", "Dũng", "Giang", "Hà", "Khánh", "Lan", "Long", "Mai", "Nam", "Phúc", "Quân", "Tâm"]
COMPANY_WORDS = ["Sao Mai", "Hưng Thịnh", "Phú Gia", "Thành Công", "Đại Việt", "Hòa Bình", "Minh Long", "An Phát"]
COMPANY_TYPES = ["Công ty TNHH", "Công ty CP", "Đại lý"]
PRODUCTS = [
    ("Laptop văn phòng 14 inch", "Máy tính", "Chiếc", 15_900_000),
    ("Laptop đồ họa 16 inch", "Máy tính", "Chiếc", 32_500_000),
    ("Màn hình 24 inch", "Màn hình", "Chiếc", 3_450_000),
    ("Màn hình 27 inch 2K", "Màn hình", "Chiếc", 6_200_000),
    ("Bàn phím cơ", "Phụ kiện", "Chiếc", 1_250_000),
    ("Chuột không dây", "Phụ kiện", "Chiếc", 390_000),
    ("Tai nghe hội nghị", "Phụ kiện", "Chiếc", 1_890_000),
    ("Webcam Full HD", "Phụ kiện", "Chiếc", 990_000),
    ("Máy in laser A4", "Thiết bị văn phòng", "Chiếc", 4_750_000),
    ("Giấy in A4 70gsm", "Văn phòng phẩm", "Thùng", 520_000),
    ("Mực in laser", "Văn phòng phẩm", "Hộp", 860_000),
    ("Router Wi-Fi 6", "Thiết bị mạng", "Chiếc", 2_350_000),
    ("Switch 24 cổng", "Thiết bị mạng", "Chiếc", 5_400_000),
    ("Ổ cứng SSD 1TB", "Linh kiện", "Chiếc", 1_990_000),
    ("RAM 16GB", "Linh kiện", "Thanh", 1_150_000),
    ("Bộ lưu điện 1000VA", "Thiết bị văn phòng", "Bộ", 2_890_000),
    ("Máy chiếu văn phòng", "Thiết bị văn phòng", "Chiếc", 11_500_000),
    ("Ghế công thái học", "Nội thất", "Chiếc", 4_200_000),
    ("Bàn nâng hạ", "Nội thất", "Chiếc", 7_900_000),
    ("Phần mềm diệt virus 1 năm", "Phần mềm", "Bản quyền", 450_000),
]
ORDER_STATUS = ["Mới", "Đang giao", "Đã giao", "Đã hủy"]


def _phone(rnd: random.Random) -> str:
    return "09" + "".join(str(rnd.randint(0, 9)) for _ in range(8))


def customers(rnd: random.Random, n: int = 60) -> list[dict]:
    rows = []
    start = date(2024, 1, 1)
    for i in range(1, n + 1):
        segment = SEGMENTS[i % 3]
        if segment == "Cá nhân":
            name = f"{rnd.choice(LAST)} {rnd.choice(MIDDLE)} {rnd.choice(FIRST)}"
            limit = rnd.choice([0, 10_000_000, 20_000_000])
        else:
            kind = "Đại lý" if segment == "Đại lý" else rnd.choice(COMPANY_TYPES[:2])
            name = f"{kind} {rnd.choice(COMPANY_WORDS)} {i:02d}"
            limit = rnd.choice([100_000_000, 200_000_000, 500_000_000])
        slug = f"kh{i:04d}"
        rows.append(
            {
                "Mã KH": f"KH-{i:04d}",
                "Tên khách hàng": name,
                "Phân khúc": segment,
                "Thành phố": CITIES[(i * 7 + rnd.randint(0, 2)) % len(CITIES)],
                "Điện thoại": _phone(rnd),
                "Email": f"{slug}@example.vn",
                "Hạn mức nợ (VND)": limit,
                "Ngày tạo": (start + timedelta(days=rnd.randint(0, 600))).isoformat(),
            }
        )
    return rows


def products(rnd: random.Random) -> list[dict]:
    return [
        {
            "Mã SP": f"SP-{i:03d}",
            "Tên sản phẩm": name,
            "Nhóm hàng": group,
            "Đơn vị": unit,
            "Đơn giá (VND)": price,
            "Tồn kho": rnd.randint(0, 250),
        }
        for i, (name, group, unit, price) in enumerate(PRODUCTS, start=1)
    ]


def orders(rnd: random.Random, kh: list[dict], sp: list[dict], n: int = 150) -> list[dict]:
    rows = []
    start = date(2026, 6, 1)
    for i in range(1, n + 1):
        c = rnd.choice(kh)
        p = rnd.choice(sp)
        qty = rnd.randint(1, 40)
        rows.append(
            {
                "Mã ĐH": f"DH-{i:05d}",
                "Ngày đặt": (start + timedelta(days=rnd.randint(0, 120))).isoformat(),
                "Mã KH": c["Mã KH"],
                "Tên khách hàng": c["Tên khách hàng"],
                "Mã SP": p["Mã SP"],
                "Tên sản phẩm": p["Tên sản phẩm"],
                "Số lượng": qty,
                "Đơn giá (VND)": p["Đơn giá (VND)"],
                "Thành tiền (VND)": qty * p["Đơn giá (VND)"],
                "Trạng thái": rnd.choices(ORDER_STATUS, weights=[3, 3, 8, 1])[0],
            }
        )
    return rows


def main() -> None:
    rnd = random.Random(SEED)
    kh = customers(rnd)
    sp = products(rnd)
    dh = orders(rnd, kh, sp)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in {"khach_hang": kh, "san_pham": sp, "don_hang": dh}.items():
        (OUT / f"{name}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{name}: {len(rows)} dòng")


if __name__ == "__main__":
    main()
