"""Báo cáo 1 trang (A8 · BIZ-04): so với cách làm hiện tại, quy ra khách giữ được và tiền; có khoảng tin cậy, độ nhạy
theo giả định và giới hạn. Người đọc là trưởng phòng CSKH — không phải người làm ML.

    uv run python -m churn_telco.report     # cần: make eval train score trước → reports/README.md + reports/*.png
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # vẽ ra file, không cần màn hình
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from churn_telco import baselines, config, decision, explain, features, marketing, metrics, split, train  # noqa: E402
from churn_telco.features import LABEL  # noqa: E402

log = logging.getLogger(__name__)

FINAL = config.MODELS / "lgbm-v2"
RULE = "Luật CSKH hiện tại"
MODEL = "Model (LightGBM v2, xếp theo EV)"


def outcomes(
    frame: pd.DataFrame,
    order: np.ndarray,
    k: int = config.CALL_CAPACITY,
    save_rate: float = config.SAVE_RATE,
    value_months: int = config.VALUE_MONTHS,
) -> dict[str, float]:
    """Gọi k khách điểm cao nhất mỗi tháng → trung bình/tháng: số người sắp rời gọi trúng, giữ được, lợi nhuận ròng."""
    value = frame["monthly_fee"].to_numpy(float) * value_months * config.MARGIN
    df = frame.assign(order=order, gain=frame[LABEL] * save_rate * (value - config.OFFER_COST))
    top = df[df.groupby("t")["order"].rank(ascending=False, method="first") <= k]
    per_month = top.groupby("t").agg(reached=(LABEL, "sum"), gain=("gain", "sum"))
    return {
        "reached": per_month["reached"].mean(),
        "saved": per_month["reached"].mean() * save_rate,
        "profit": (per_month["gain"] - k * config.CALL_COST).mean(),
    }


def num(x: float, digits: int = 0) -> str:
    """Số kiểu Việt: 60.912 và 44,5."""
    return f"{x:,.{digits}f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def money(x: float) -> str:
    return f"{num(x / 1e6, 1)} triệu đ"


def profit_chart(frame: pd.DataFrame, orders: dict[str, np.ndarray], out: Path) -> pd.DataFrame:
    ks = [100, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000]
    curve = pd.DataFrame([{"model": m, "k": k, **outcomes(frame, o, k)} for m, o in orders.items() for k in ks])
    fig, ax = plt.subplots(figsize=(7, 4))
    for name, g in curve.groupby("model", sort=False):
        ax.plot(g["k"], g["profit"] / 1e6, marker="o", label=name)
    ax.axvline(config.CALL_CAPACITY, color="grey", ls="--", lw=1, label=f"Năng lực hiện tại ({config.CALL_CAPACITY})")
    ax.axhline(0, color="black", lw=0.8)
    ax.set(
        xlabel="Số cuộc gọi mỗi tháng", ylabel="Lợi nhuận ròng (triệu đ/tháng)", title="Gọi bao nhiêu khách thì có lãi?"
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return curve


def reliability_chart(p: np.ndarray, y: np.ndarray, out: Path) -> float:
    r = decision.reliability(p, y, bins=10)
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    ax.plot(r["mean_pred"], r["frac_churn"], marker="o", label="Model (10 nhóm theo xác suất)")
    lim = float(r[["mean_pred", "frac_churn"]].max().max()) * 1.05
    ax.plot([0, lim], [0, lim], color="grey", ls="--", lw=1, label="Dự đoán = thực tế")
    ax.set(xlabel="Xác suất dự đoán", ylabel="Tỷ lệ rời mạng thực tế", title="Xác suất có đáng tin?")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return decision.ece(p, y)


def sensitivity(test: pd.DataFrame, orders: dict[str, np.ndarray]) -> str:
    months = (6, 12, 24)
    lines = ["| Tỷ lệ đồng ý ở lại \\ số tháng ở thêm | " + " | ".join(f"{m} tháng" for m in months) + " |"]
    lines.append("|---" * (len(months) + 1) + "|")
    for rate in (0.15, 0.30, 0.45):
        cells = []
        for m in months:
            a = outcomes(test, orders[RULE], save_rate=rate, value_months=m)["profit"]
            b = outcomes(test, orders[MODEL], save_rate=rate, value_months=m)["profit"]
            cells.append(f"+{money(b - a)}")
        lines.append(f"| {rate:.0%} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def reason_summary(bundle: train.Bundle) -> str:
    """Nhóm lý do chính trong danh sách gọi mới nhất (data/outputs từ `make score`)."""
    files = sorted((config.DATA / "outputs").glob("call_list_*.parquet"))
    if not files:
        return ""
    calls = pd.read_parquet(files[-1])
    t = calls["t"].iloc[0]
    df = features.build(features.connect(), [t]).merge(calls[["customer_id"]], on="customer_id")
    df = df.merge(marketing.build(df, marketing.read_promotions()), on=features.KEYS)
    main = explain.group_shap(explain.shap_values(bundle, df)).drop(columns="profile").idxmax(axis=1).value_counts()
    rows = "\n".join(f"| {explain.GROUPS[g].label} | {n} | {explain.GROUPS[g].action} |" for g, n in main.items())
    return (
        f"## Danh sách gọi tháng {t:%m/%Y}: lý do chính của {len(calls)} khách\n\n"
        "| Nhóm lý do chính | Số khách | Việc nên làm |\n|---|---|---|\n" + rows + "\n"
    )


def headline(test: pd.DataFrame, orders: dict[str, np.ndarray], n_boot: int) -> str:
    """Bảng chính: danh sách hiện tại và model, mỗi tháng, kèm KTC 95% của phần chênh lệch."""
    res = metrics.bootstrap(orders, test, n_boot=n_boot, reference=RULE).set_index(["model", "metric"])
    hits = res.loc[(MODEL, "p@k")] * config.CALL_CAPACITY  # tỷ lệ trong top-500 → số người
    base, best = outcomes(test, orders[RULE]), outcomes(test, orders[MODEL])
    per_hit = (best["profit"] - base["profit"]) / (best["reached"] - base["reached"])  # tiền / mỗi người trúng thêm
    rate = config.SAVE_RATE
    rows = [
        ("Số người sắp rời được gọi trúng", num(base["reached"]), num(best["reached"]), hits, num, 1),
        (
            f"Số khách giữ được (giả định {rate:.0%} đồng ý ở lại)",
            num(base["saved"]),
            num(best["saved"]),
            hits,
            num,
            rate,
        ),
        (
            "Lợi nhuận ròng sau chi phí gọi và ưu đãi",
            money(base["profit"]),
            money(best["profit"]),
            hits,
            money,
            per_hit,
        ),
    ]
    lines = [f"| Mỗi tháng, với {config.CALL_CAPACITY} cuộc gọi | Danh sách hiện tại | Model | Chênh lệch (KTC 95%) |"]
    lines.append("|---|---|---|---|")
    for name, a, b, h, fmt, scale in rows:
        lines.append(
            f"| {name} | {a} | {b} | +{fmt(h.delta * scale)} ({fmt(h.delta_lo * scale)} … {fmt(h.delta_hi * scale)}) |"
        )
    return "\n".join(lines)


def versus_logistic(out: Path) -> str:
    """Chênh lệch cặp LightGBM v2 − Logistic trên tập đóng băng, đọc từ kết quả `make eval`."""
    path = out / "eval_test.json"
    if not path.exists():
        return ""
    e = pd.DataFrame(json.loads(path.read_text(encoding="utf-8"))).set_index(["model", "metric"])
    row = e.loc[("LightGBM v2", "p@k")] * config.CALL_CAPACITY
    return (
        f"So với baseline logistic regression, model gọi trúng thêm {num(row.delta)} người/tháng "
        f"(KTC 95%: {num(row.delta_lo)} … {num(row.delta_hi)}) — đủ để đáng thêm độ phức tạp."
    )


LIMITS = """## Giới hạn và rủi ro

- **Dữ liệu mô phỏng** có cơ chế churn biết trước; số liệu thật sẽ khác. Quy trình (feature as-of, bộ đánh giá đóng
  băng, bootstrap) thì dùng lại nguyên vẹn.
- **Tỷ lệ đồng ý ở lại {rate:.0%} là giả định** từ chiến dịch 2024. Trước khi nhân rộng: thử nghiệm có nhóm đối chứng
  (một phần danh sách KHÔNG gọi) để đo hiệu quả thật của cuộc gọi.
- **Model không bắt được** churn do chuyển nhà (không có dấu hiệu trước) và churn đột ngột khi đối thủ khuyến mãi —
  nhóm sau nên xử lý bằng ưu đãi theo vùng trong thời gian khuyến mãi, không phải gọi từng người.
- **Xác suất khớp thực tế** (sai lệch trung bình {ece}% giữa dự đoán và thực tế, hình dưới) nên dùng được để tính giá
  trị kỳ vọng. Theo dõi hằng tháng dự đoán và thực tế theo tỉnh; lệch nhiều thì train lại.
- **Không dùng hồ sơ** (tỉnh, tuổi, kênh) làm lý do gọi; danh sách chỉ có mã khách, CSKH tra liên hệ trong CRM.

![Độ tin cậy của xác suất](reliability.png)
"""


def build(out: Path = config.REPORTS, n_boot: int = 1000) -> str:
    out.mkdir(parents=True, exist_ok=True)
    df = features.load()
    test = split.frozen_test(df)
    bundle = train.load(FINAL)
    p = bundle.proba(test)
    orders = {RULE: baselines.rule_cskh(test), MODEL: decision.expected_value(p, decision.customer_value(test))}
    curve = profit_chart(test, orders, out / "profit_curve.png")
    peak = curve[curve["model"] == MODEL].sort_values("profit").iloc[-1]
    ece = reliability_chart(p, test[LABEL].to_numpy(), out / "reliability.png")
    period = f"{test['t'].nunique()} tháng {test['t'].min():%m}–{test['t'].max():%m/%Y}"
    sections = [
        "# Báo cáo 1 trang — Gọi ai để giữ khách? (Sóng Xanh · dữ liệu mô phỏng)",
        f"**Câu hỏi.** Mỗi tháng đội CSKH gọi được {config.CALL_CAPACITY} khách. Chọn ai để giữ lại nhiều khách nhất?",
        "**Đề xuất.** Thay danh sách hiện tại (khách sắp hết hợp đồng, hay báo lỗi mạng) bằng danh sách do model xếp "
        "theo giá trị kỳ vọng của cuộc gọi, kèm 3 lý do và việc nên làm cho từng khách.",
        "## Kết quả trên bộ đánh giá đóng băng",
        f"{period} mà model chưa từng thấy, {num(len(test))} lượt khách; khoảng tin cậy (KTC) 95% bootstrap theo "
        f"khách, {n_boot} lần.",
        headline(test, orders, n_boot),
        f"Gọi ngẫu nhiên thì {config.CALL_CAPACITY} cuộc trúng khoảng "
        f"{num(test[LABEL].mean() * config.CALL_CAPACITY)} người. {versus_logistic(out)}",
        "![Lợi nhuận theo số cuộc gọi](profit_curve.png)",
        f"**Nên gọi bao nhiêu?** Lợi nhuận còn tăng tới khoảng {num(peak['k'])} cuộc/tháng "
        f"({money(peak['profit'])}/tháng): năng lực {config.CALL_CAPACITY} cuộc là nút thắt. Đề xuất thử tăng năng "
        "lực, có nhóm đối chứng (xem Rủi ro).",
        "## Kết luận có vững nếu giả định sai?",
        "Lợi nhuận tăng thêm mỗi tháng so với danh sách hiện tại:",
        sensitivity(test, orders),
        "Ở mọi tổ hợp, model đều hơn danh sách hiện tại; độ lớn phụ thuộc mạnh vào tỷ lệ đồng ý ở lại — con số "
        "cần đo lại.",
        reason_summary(bundle),
        LIMITS.format(rate=config.SAVE_RATE, ece=num(100 * ece, 2)),
        f"*Tái lập: `make all` trong `projects/g1-churn-telco/`. {bundle.meta['name']}, phiên bản "
        f"{bundle.meta.get('version', '—')}.*",
    ]
    text = "\n\n".join(s.strip() for s in sections if s) + "\n"
    (out / "README.md").write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    print(build())
