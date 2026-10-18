"""Lab A5 · ML-02, ML-03, STAT-05: từ model tới quyết định "gọi ai" khi sự kiện hiếm và năng lực có hạn.

1. Bẫy accuracy khi chỉ ~2% khách rời mạng.
2. LightGBM mặc định vs cấu hình của dự án + early stopping.
3. Trọng số lớp (class weight): xếp hạng gần như không đổi nhưng XÁC SUẤT sai lệch nặng.
4. Hiệu chỉnh xác suất: thô vs Platt vs isotonic, đo trên tập đóng băng.
5. Ngưỡng: hoà vốn theo gói cước, ngưỡng do năng lực 500 cuộc, đường coverage–precision–lợi nhuận.
6. Xếp theo xác suất hay theo giá trị kỳ vọng?

    cd labs/stat-05-trung-cap-nguong-chi-phi
    uv run --project ../../projects/g1-churn-telco python threshold_lab.py     # cần `make features train`
"""

from pathlib import Path

import lightgbm as lgb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from churn_telco import config, decision, features, metrics, split, train  # noqa: E402
from churn_telco.features import LABEL  # noqa: E402
from sklearn.isotonic import IsotonicRegression  # noqa: E402
from sklearn.metrics import accuracy_score, average_precision_score, brier_score_loss  # noqa: E402

OUT = Path(__file__).with_name("out")
OUT.mkdir(exist_ok=True)
df = features.load()
parts = split.split(df)
tr, va = parts["train"], parts["valid"]
te = split.frozen_test(df)
bundle = train.load(config.MODELS / "lgbm-v1")
cols = bundle.features

# %% 1. Accuracy đánh lừa: "không ai rời mạng" đúng 98% mà không giúp được ai
y = te[LABEL].to_numpy()
print(f"1) Tỷ lệ churn trong tập đánh giá: {y.mean():.2%}")
print(f"   Đoán 'không ai rời' → accuracy {accuracy_score(y, np.zeros_like(y)):.1%}, gọi trúng 0 người")
random_ap = average_precision_score(y, np.random.default_rng(0).random(len(y)))
print(f"   PR-AUC của điểm ngẫu nhiên ≈ tỷ lệ nền: {random_ap:.3f} — đây là 'mức 0' của PR-AUC, không phải 0,5")


# %% 2. LightGBM mặc định vs cấu hình dự án (lá ≥ 100 dòng, học chậm, dừng sớm theo PR-AUC trên valid)
def datasets() -> tuple[lgb.Dataset, lgb.Dataset]:
    """Dataset MỚI cho mỗi lần train: LightGBM chia bin lúc dựng Dataset theo tham số của lần train đầu tiên."""
    dtrain = lgb.Dataset(tr[cols], tr[LABEL])
    return dtrain, lgb.Dataset(va[cols], va[LABEL], reference=dtrain)  # valid chia bin giống train


default = lgb.train({"objective": "binary", "verbose": -1}, datasets()[0], num_boost_round=100)
default_ap = average_precision_score(va[LABEL], default.predict(va[cols]))
history: dict = {}
dtrain, dvalid = datasets()
lgb.train(
    train.PARAMS,
    dtrain,
    num_boost_round=1500,
    valid_sets=[dvalid],
    valid_names=["valid"],
    callbacks=[lgb.record_evaluation(history)],  # không dừng sớm ở đây, để xem cả đường cong
)
curve = history["valid"]["average_precision"]
best = int(np.argmax(curve)) + 1
print(f"\n2) PR-AUC valid — LightGBM mặc định (100 cây): {default_ap:.3f}")
for n in (50, 100, best, 500, 1500):
    note = "  ← tốt nhất: early stopping dừng ở đây" if n == best else ""
    print(f"   cấu hình dự án, {n:4d} cây: {curve[n - 1]:.3f}{note}")

# %% 3. Trọng số lớp: "cân bằng" hai lớp khi train — thứ hạng gần như giữ nguyên, xác suất thì phình to
ratio = (tr[LABEL] == 0).sum() / tr[LABEL].sum()
weighted = lgb.train(
    {**train.PARAMS, "scale_pos_weight": ratio}, datasets()[0], num_boost_round=bundle.meta["best_iteration"]
)
print(f"\n3) Trọng số lớp (tập đóng băng, xác suất trung bình thật = {y.mean():.3f}):")
for name, p in [("không trọng số", bundle.score(te)), (f"scale_pos_weight={ratio:.0f}", weighted.predict(te[cols]))]:
    m = metrics.evaluate(metrics.rank(p, y, te["t"]))
    print(f"   {name:22} PR-AUC {m['pr_auc']:.3f} · P@500 {m['p@k']:.3f} · xác suất trung bình {p.mean():.3f}")

# %% 4. Hiệu chỉnh: học trên valid, đo trên tập đóng băng
raw_va, raw_te = bundle.score(va), bundle.score(te)
platt = decision.apply_platt(raw_te, **decision.fit_platt(raw_va, va[LABEL].to_numpy()))
iso = IsotonicRegression(out_of_bounds="clip").fit(raw_va, va[LABEL]).predict(raw_te)
w_raw = weighted.predict(te[cols])
w_platt = decision.apply_platt(w_raw, **decision.fit_platt(weighted.predict(va[cols]), va[LABEL].to_numpy()))
print("\n4) Hiệu chỉnh (đo trên tập đóng băng):   ECE      Brier")
for name, p in [
    ("thô", raw_te),
    ("Platt", platt),
    ("isotonic", iso),
    ("class weight thô", w_raw),
    ("class weight + Platt", w_platt),
]:
    print(f"   {name:22} {decision.ece(p, y):.4f}   {brier_score_loss(y, p):.5f}")
table = decision.reliability(raw_te, y)
print("   Bảng độ tin cậy (model thô, 10 nhóm):\n" + table.round(4).to_string(index=False))

# %% 5. Ngưỡng: hoà vốn theo giá trị khách, rồi ràng buộc 500 cuộc/tháng
calls = decision.call_list(te, bundle.proba(te))
fee = te.groupby("plan_code", observed=True)["monthly_fee"].mean()
value = fee * config.VALUE_MONTHS * config.MARGIN  # = decision.customer_value cho một khách mỗi gói
print("\n5) Xác suất hoà vốn theo gói (chỉ gọi khi p cao hơn mức này):")
print("   " + " · ".join(f"{plan} {decision.break_even(np.array([v]))[0]:.1%}" for plan, v in value.items()))
positive = calls[calls["ev"] > 0].groupby("t").size()
edge = calls[calls["rank"] == config.CALL_CAPACITY][["t", "p", "ev"]]
print(f"   Mỗi tháng có {positive.mean():.0f} khách EV > 0, nhưng chỉ gọi được {config.CALL_CAPACITY}.")
print(
    f"   Người thứ 500: p ≈ {edge['p'].mean():.1%}, EV ≈ {edge['ev'].mean():,.0f} đ → năng lực mới là ràng buộc chặt."
)

curve_k = decision.profit_curve(te, bundle.proba(te), ks=[100, 250, 500, 1000, 2000, 3000, 5000])
print("\n   Đường coverage–precision–lợi nhuận (trung bình mỗi tháng):")
print(curve_k.round({"coverage": 3, "precision": 3, "recall": 3, "profit": 0, "ev_at_k": 0}).to_string(index=False))
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(curve_k["coverage"] * 100, curve_k["precision"] * 100, marker="o", label="precision (%)")
ax.plot(curve_k["coverage"] * 100, curve_k["recall"] * 100, marker="s", label="recall (%)")
ax.axvline(100 * config.CALL_CAPACITY / (len(te) / te["t"].nunique()), color="grey", ls="--", label="500 cuộc/tháng")
ax.set(xlabel="Tỷ lệ khách được gọi (%)", ylabel="%", title="Gọi càng nhiều: bắt được nhiều hơn, trúng ít hơn")
ax.legend()
fig.tight_layout()
fig.savefig(OUT / "coverage_precision.png", dpi=110)

# %% 6. Xếp theo xác suất hay theo giá trị kỳ vọng (EV = p × giá trị khách...)?
p_cal = bundle.proba(te)
for name, order in [("xếp theo xác suất", p_cal), ("xếp theo EV", calls["ev"].to_numpy())]:
    frame = te.assign(order=order, value=decision.customer_value(te))
    top = frame[frame.groupby("t")["order"].rank(ascending=False, method="first") <= config.CALL_CAPACITY]
    gain = top[LABEL] * config.SAVE_RATE * (top["value"] - config.OFFER_COST)
    profit = gain.groupby(top["t"]).sum().mean() - config.CALL_CAPACITY * config.CALL_COST
    hits = top[LABEL].mean() * config.CALL_CAPACITY
    print(f"\n6) {name:18} gọi trúng {hits:.0f} người/tháng · lợi nhuận {profit:,.0f} đ/tháng")
print("   Xếp theo EV gọi trúng ít người hơn một chút nhưng là những người đáng giữ hơn (cước cao).")
