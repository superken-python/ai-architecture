"""Lab A3 · STAT-02: một con số đánh giá không có khoảng tin cậy thì chưa phải kết quả.

Năm thí nghiệm trên bộ đánh giá đóng băng của dự án:
1. Công thức nhanh cho một tỷ lệ (precision@500) và so với bootstrap.
2. Tập đánh giá nhỏ hơn → khoảng tin cậy rộng hơn theo √n.
3. Bootstrap theo DÒNG vs theo KHÁCH: nhân bản dữ liệu không làm tăng thông tin.
4. So hai model: hai KTC chồng nhau nhưng chênh lệch CẶP vẫn có ý nghĩa.
5. Thử nhiều rồi chọn cái tốt nhất: 100 model ngẫu nhiên, cái "giỏi" nhất trông hơn hẳn mức nền.

    cd labs/stat-02-co-ban-bootstrap
    uv run --project ../../projects/g1-churn-telco python bootstrap_lab.py     # cần `make features` trong dự án
"""

import numpy as np
import pandas as pd
from churn_telco import baselines, features, metrics, split
from churn_telco.features import LABEL

K = 500
df = features.load()
parts = split.split(df)
test = split.frozen_test(df)
logistic = baselines.fit_logistic(parts["train"])
scores = {
    "Logistic": logistic.predict_proba(test[logistic.feature_names_in_])[:, 1],
    "Luật giảm sử dụng": baselines.rule_usage_drop(test),
}


def p_at_k(frame: pd.DataFrame, score: np.ndarray) -> float:
    return metrics.evaluate(metrics.rank(score, frame[LABEL], frame["t"]), k=K)["p@k"]


def auc_half_width(frame: pd.DataFrame, score: np.ndarray, k: int, cluster: str | None = "customer_id") -> float:
    r = metrics.bootstrap({"m": score}, frame, n_boot=500, k=k, cluster=cluster).set_index("metric")
    return (r.at["auc", "hi"] - r.at["auc", "lo"]) / 2


# 1. Precision@500 là một TỶ LỆ trên n = 500 × số tháng lần gọi → sai số chuẩn ≈ √(p(1−p)/n)
p = p_at_k(test, scores["Logistic"])
n = K * test["t"].nunique()
half = 1.96 * np.sqrt(p * (1 - p) / n)
boot = metrics.bootstrap({"Logistic": scores["Logistic"]}, test, n_boot=1000, k=K).set_index("metric").loc["p@k"]
print(f"1) P@{K} logistic = {p:.3f}; công thức nhanh: ±{half:.3f} → [{p - half:.3f}, {p + half:.3f}]")
print(f"   bootstrap theo khách (1.000 lần): [{boot.lo:.3f}, {boot.hi:.3f}]")

# 2. Chỉ đánh giá trên 1 tháng thay vì 3 → n giảm 3 lần → khoảng tin cậy rộng ra ≈ √3 lần
last = test[test["t"] == test["t"].max()]
one = metrics.bootstrap({"m": scores["Logistic"][test["t"] == test["t"].max()]}, last, n_boot=1000, k=K)
one = one.set_index("metric").loc["p@k"]
ratio = (one.hi - one.lo) / (boot.hi - boot.lo)
print(f"\n2) Chỉ 1 tháng: [{one.lo:.3f}, {one.hi:.3f}] — rộng gấp {ratio:.2f} lần khi dùng 3 tháng (√3 ≈ 1,73)")

# 3. Bootstrap phải rút theo ĐƠN VỊ ĐỘC LẬP. Thí nghiệm cực đoan: chép tập test 3 lần (cùng khách, cùng nhãn — không
#    thêm chút thông tin nào). Rút theo dòng → KTC hẹp đi √3 lần, như thể có thêm dữ liệu; rút theo khách → không đổi.
tripled = pd.concat([test] * 3, ignore_index=True)
tripled_score = np.tile(scores["Logistic"], 3)
print(f"\n3) Tập gốc:              AUC ±{auc_half_width(test, scores['Logistic'], K):.4f}")
print(f"   Chép 3 lần, rút theo khách: AUC ±{auc_half_width(tripled, tripled_score, 3 * K):.4f}  ← đúng: không đổi")
print(f"   Chép 3 lần, rút theo dòng:  AUC ±{auc_half_width(tripled, tripled_score, 3 * K, None):.4f}  ← hẹp giả tạo")

# 4. Hai model: nhìn hai KTC riêng thì chồng nhau, nhưng đo CẶP trên cùng mẫu thì chênh lệch rõ ràng
res = metrics.bootstrap(scores, test, n_boot=1000, k=K, reference="Luật giảm sử dụng").set_index(["model", "metric"])
a, b = res.loc[("Logistic", "p@k")], res.loc[("Luật giảm sử dụng", "p@k")]
print(f"\n4) Logistic {a.value:.3f} [{a.lo:.3f}–{a.hi:.3f}] vs luật giảm sử dụng {b.value:.3f} [{b.lo:.3f}–{b.hi:.3f}]")
print(
    f"   chênh lệch cặp: {a.delta:+.3f} [{a.delta_lo:+.3f}…{a.delta_hi:+.3f}], P(logistic tốt hơn) = {a.p_better:.3f}"
)

# 5. "Lời nguyền người thắng": thử 100 model toàn điểm NGẪU NHIÊN rồi giữ cái có P@500 cao nhất trên tập đánh giá.
rng = np.random.default_rng(0)
random_p = np.array([p_at_k(test, rng.random(len(test))) for _ in range(100)])
print(
    f"\n5) Tỷ lệ churn nền {test[LABEL].mean():.3f}; 100 model ngẫu nhiên có P@{K} từ {random_p.min():.3f} tới "
    f"{random_p.max():.3f}"
)
print(
    f"   Chọn cái tốt nhất → báo cáo {random_p.max():.3f}, cao hơn nền {random_p.max() / test[LABEL].mean() - 1:.0%} — "
    "toàn là may rủi."
)
print("   → Chốt trước MỘT metric chính và vài phương án; tập đóng băng không phải chỗ thử hàng chục ý tưởng.")
