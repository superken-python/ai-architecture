"""Lab A8 · BIZ-04: kết luận có còn đúng nếu giả định sai? — phân tích độ nhạy và khung câu chuyện 3 phút.

Quyết định (gọi ai) đã chốt với giả định gốc; ở đây ta hỏi: nếu thực tế khác giả định thì lợi nhuận TĂNG THÊM so với
cách làm hiện tại còn bao nhiêu? Mỗi giả định thử một mức thấp và một mức cao → biểu đồ "lốc xoáy" (tornado):
thanh dài nhất là giả định cần đo lại trước khi nhân rộng.

    cd labs/biz-04-co-ban-trinh-bay
    uv run --project ../../projects/g1-churn-telco python sensitivity.py     # cần `make train-v2`
"""

from dataclasses import asdict, dataclass, replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from churn_telco import baselines, config, decision, features, split, train  # noqa: E402
from churn_telco.features import LABEL  # noqa: E402

OUT = Path(__file__).with_name("out")
OUT.mkdir(exist_ok=True)
K = config.CALL_CAPACITY


@dataclass(frozen=True)
class World:
    """Một "thế giới" giả định. Giá trị mặc định = giả định gốc trong config.py."""

    save_rate: float = config.SAVE_RATE
    value_months: float = config.VALUE_MONTHS
    margin: float = config.MARGIN
    offer_cost: float = config.OFFER_COST
    call_cost: float = config.CALL_COST
    hit_factor: float = 1.0  # < 1: ngoài đời model gọi trúng ít hơn trên tập đánh giá (dữ liệu trôi, quy trình khác)


LABELS = {
    "save_rate": "Tỷ lệ đồng ý ở lại",
    "value_months": "Số tháng ở thêm",
    "margin": "Biên lợi nhuận",
    "offer_cost": "Chi phí ưu đãi",
    "call_cost": "Chi phí một cuộc gọi",
    "hit_factor": "Model trúng ngoài đời / trên tập đánh giá",
}
RANGES = {  # (mức xấu, mức tốt)
    "save_rate": (0.15, 0.45),
    "value_months": (6, 24),
    "margin": (0.30, 0.60),
    "offer_cost": (300_000, 50_000),
    "call_cost": (50_000, 10_000),
    "hit_factor": (0.6, 1.0),
}


def top_k(frame: pd.DataFrame, order: np.ndarray) -> pd.DataFrame:
    """k khách điểm cao nhất của mỗi tháng."""
    return frame.assign(order=order).loc[lambda d: d.groupby("t")["order"].rank(ascending=False, method="first") <= K]


def profit(top: pd.DataFrame, w: World) -> float:
    """Lợi nhuận ròng trung bình mỗi tháng của danh sách gọi `top` trong thế giới `w`."""
    value = top["monthly_fee"] * w.value_months * w.margin
    gain = top[LABEL] * w.hit_factor * w.save_rate * (value - w.offer_cost)
    return gain.groupby(top["t"]).sum().mean() - K * w.call_cost


test = split.frozen_test(features.load())
bundle = train.load(config.MODELS / "lgbm-v2")
model_list = top_k(test, decision.expected_value(bundle.proba(test), decision.customer_value(test)))
rule_list = top_k(test, baselines.rule_cskh(test))


def uplift(w: World) -> float:
    """Model hơn danh sách hiện tại bao nhiêu tiền mỗi tháng (hit_factor chỉ áp cho model)."""
    return profit(model_list, w) - profit(rule_list, replace(w, hit_factor=1.0))


base = uplift(World())
rows = []
for name, (bad, good) in RANGES.items():
    rows.append(
        {
            "giả định": LABELS[name],
            "gốc": asdict(World())[name],
            "mức xấu": bad,
            "mức tốt": good,
            "khi xấu (tr.đ)": uplift(replace(World(), **{name: bad})) / 1e6,
            "khi tốt (tr.đ)": uplift(replace(World(), **{name: good})) / 1e6,
        }
    )
table = pd.DataFrame(rows)
table = table.assign(width=(table["khi tốt (tr.đ)"] - table["khi xấu (tr.đ)"]).abs()).sort_values("width")
print(f"1) Lợi nhuận tăng thêm mỗi tháng so với danh sách hiện tại, giả định gốc: {base / 1e6:.1f} triệu đ\n")
print(table.drop(columns="width").set_index("giả định").round(2).to_string())

fig, ax = plt.subplots(figsize=(7.5, 3.8))
y = np.arange(len(table))
ax.barh(y, table["khi xấu (tr.đ)"] - base / 1e6, left=base / 1e6, color="#d62728", label="giả định ở mức xấu")
ax.barh(y, table["khi tốt (tr.đ)"] - base / 1e6, left=base / 1e6, color="#2ca02c", label="giả định ở mức tốt")
ax.set_yticks(y, table["giả định"])
ax.axvline(base / 1e6, color="black", lw=1)
ax.set(xlabel="Lợi nhuận tăng thêm so với hiện tại (triệu đ/tháng)", title="Giả định nào đổi kết luận nhiều nhất?")
ax.legend(loc="lower right", fontsize=8)
fig.tight_layout()
fig.savefig(OUT / "tornado.png", dpi=110)

# 2. Điểm hoà vốn của CẢ CHƯƠNG TRÌNH gọi: cần bao nhiêu % khách đồng ý ở lại thì 500 cuộc gọi mới có lãi?
rates = np.linspace(0.005, 0.60, 120)
for name, calls in [("danh sách hiện tại", rule_list), ("danh sách của model", model_list)]:
    gains = np.array([profit(calls, replace(World(), save_rate=r)) for r in rates])
    need = rates[np.argmax(gains > 0)] if (gains > 0).any() else float("nan")
    print(f"\n2) {name}: có lãi khi ≥ {need:.1%} khách được gọi đồng ý ở lại")
worst = uplift(World(save_rate=0.15, value_months=6, hit_factor=0.6))
print(f"   Xấu cùng lúc (15% đồng ý, ở thêm 6 tháng, model trúng ít hơn 40%): {worst / 1e6:+.1f} triệu đ/tháng")

rule_hits = rule_list.groupby("t")[LABEL].sum().mean()
risk = table.iloc[-1]["giả định"].lower()
story = [
    f"Vấn đề   — mỗi tháng ~{100 * test[LABEL].mean():.1f}% khách rời mạng; đội gọi {K} khách theo danh sách 'sắp hết "
    f"hợp đồng', trúng khoảng {rule_hits:.0f} người thật sự sắp rời.",
    "Cách làm — model học 18 tháng lịch sử, xếp khách theo giá trị kỳ vọng của cuộc gọi, kèm 3 lý do cho từng người.",
    f"Kết quả  — trên 3 tháng model chưa thấy: lợi nhuận tăng thêm ~{base / 1e6:.0f} triệu đ/tháng (KTC: báo cáo).",
    f"Rủi ro   — kết luận nhạy nhất với '{risk}': phải đo lại trước khi nhân rộng.",
    "Đề nghị  — chạy thử 2 tháng: gọi 80% danh sách, giữ 20% làm nhóm đối chứng để đo hiệu quả thật.",
]
print("\n3) Khung câu chuyện 3 phút cho trưởng phòng CSKH:")
for i, line in enumerate(story, 1):
    print(f"   {i}. {line}")
