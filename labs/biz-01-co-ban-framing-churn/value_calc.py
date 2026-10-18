"""Lab A1 · BIZ-01: quy bài toán churn ra tiền TRƯỚC khi có model — một cuộc gọi đáng bao nhiêu, cần đúng bao nhiêu.

Chưa cần dữ liệu: chỉ dùng giả định nghiệp vụ trong config.py (CSKH và tài chính cung cấp). Kết quả trả lời ba câu
mà framing 1 trang phải có: giá trị của một khách giữ được, xác suất hoà vốn của một cuộc gọi, và precision@500 cần
đạt để dự án đáng làm.

    cd labs/biz-01-co-ban-framing-churn
    uv run --project ../../projects/g1-churn-telco python value_calc.py
    uv run --project ../../projects/g1-churn-telco python value_calc.py --save-rate 0.15   # giả định xấu hơn
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace

from churn_telco import config

PLAN_FEES = {
    "SX50": 198_000,
    "SX150": 269_000,
    "SX300": 320_000,
    "SX150TV": 290_000,
    "SX300TV": 365_000,
    "COMBO": 450_000,
}


@dataclass(frozen=True)
class Assumptions:
    """Giả định nghiệp vụ — gom vào một chỗ để đổi một giá trị là thấy kết luận đổi theo."""

    call_cost: float = config.CALL_COST
    save_rate: float = config.SAVE_RATE
    offer_cost: float = config.OFFER_COST
    value_months: int = config.VALUE_MONTHS
    margin: float = config.MARGIN
    capacity: int = config.CALL_CAPACITY


def customer_value(fee: float, a: Assumptions) -> float:
    """Lợi nhuận gộp giữ lại được nếu khách ở thêm `value_months` tháng."""
    return fee * a.value_months * a.margin


def call_ev(p: float, fee: float, a: Assumptions) -> float:
    """Giá trị kỳ vọng của MỘT cuộc gọi tới khách có xác suất rời mạng p."""
    return p * a.save_rate * (customer_value(fee, a) - a.offer_cost) - a.call_cost


def break_even(fee: float, a: Assumptions) -> float:
    """p tối thiểu để cuộc gọi không lỗ: giải call_ev(p) = 0."""
    return a.call_cost / (a.save_rate * (customer_value(fee, a) - a.offer_cost))


def monthly_profit(precision: float, fee: float, a: Assumptions) -> float:
    """Lợi nhuận ròng một tháng khi gọi đủ `capacity` khách và `precision` trong số đó thật sự sắp rời."""
    hits = precision * a.capacity
    return hits * a.save_rate * (customer_value(fee, a) - a.offer_cost) - a.capacity * a.call_cost


def vnd(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".") + " đ"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Quy bài toán churn ra tiền")
    parser.add_argument("--save-rate", type=float, default=config.SAVE_RATE, help="tỷ lệ khách đồng ý ở lại")
    parser.add_argument("--capacity", type=int, default=config.CALL_CAPACITY, help="số cuộc gọi mỗi tháng")
    args = parser.parse_args(argv)
    a = replace(Assumptions(), save_rate=args.save_rate, capacity=args.capacity)
    print(f"Giả định: {a}\n")

    print(f"{'Gói':8} {'Cước/tháng':>12} {'Giá trị 1 khách':>16} {'p hoà vốn':>10}")
    for plan, fee in PLAN_FEES.items():
        print(f"{plan:8} {vnd(fee):>12} {vnd(customer_value(fee, a)):>16} {break_even(fee, a):>10.1%}")

    fee = sum(PLAN_FEES.values()) / len(PLAN_FEES)  # cước trung bình (đơn giản hoá cho framing)
    # precision cần đạt = xác suất hoà vốn: trung bình mỗi người trong danh sách phải "đáng" một cuộc gọi
    print(f"\nCước trung bình {vnd(fee)} → precision@{a.capacity} phải ≥ {break_even(fee, a):.1%} mới hoà vốn")
    print(f"\n{'Kịch bản':16} {'precision':>9} {'gọi trúng':>10} {'giữ được':>9} {'lợi nhuận/tháng':>17}")
    for label, precision in [("Ngẫu nhiên", 0.02), ("Cách hiện tại?", 0.07), ("Mục tiêu", 0.15), ("Rất tốt", 0.30)]:
        hits = precision * a.capacity
        profit = monthly_profit(precision, fee, a)
        print(f"{label:16} {precision:>9.0%} {hits:>10.0f} {hits * a.save_rate:>9.0f} {vnd(profit):>17}")


if __name__ == "__main__":
    main()
