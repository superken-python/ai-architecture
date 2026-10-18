"""Lab A6 · BIZ-03, ML-04: đọc ca sai của model v1, nhóm theo nguyên nhân, sửa nhóm lớn nhất bằng DỮ LIỆU, đo lại.

Mọi phân tích làm trên tập VALID (07–09/2025) — tập đóng băng chỉ để báo cáo cuối cùng, không để "soi lỗi".
1. Ca sai ở năng lực thật: bỏ sót = rời mạng nhưng ngoài top-500 của tháng; gọi nhầm = trong top-500 nhưng ở lại.
2. Đọc 100 ca bỏ sót (in 12 ca đầu) — ngoài đời bạn ghi tay cột "nguyên nhân"; ở đây đối chiếu với lý do trên phiếu hủy.
3. Đếm theo nhóm: lý do, tỉnh, tháng → nhóm lớn nhất.
4. Lát cắt theo tỉnh: recall@500 và xác suất dự đoán so với thực tế.
5. Sửa bằng dữ liệu mới (lịch khuyến mãi của đối thủ → model v2), lập bảng "nhóm lỗi – số ca – đã sửa – trước/sau".
6. SHAP toàn cục: nhóm lý do nào đẩy rủi ro nhiều nhất; biểu đồ beeswarm → out/shap_beeswarm.png.

    cd labs/biz-03-trung-cap-phan-tich-loi
    uv run --project ../../projects/g1-churn-telco python error_analysis.py     # cần `make train train-v2`
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import shap  # noqa: E402
from churn_telco import config, explain, features, metrics, split, train  # noqa: E402
from churn_telco.features import LABEL  # noqa: E402

OUT = Path(__file__).with_name("out")
OUT.mkdir(exist_ok=True)
pd.set_option("display.width", 160)
K = config.CALL_CAPACITY
df = features.load()
va = split.split(df)["valid"].copy()
v1, v2 = train.load(config.MODELS / "lgbm-v1"), train.load(config.MODELS / "lgbm-v2")
va["p_v1"], va["p_v2"] = v1.proba(va), v2.proba(va)
va["rank_v1"] = va.groupby("t")["p_v1"].rank(ascending=False, method="first")
va["rank_v2"] = va.groupby("t")["p_v2"].rank(ascending=False, method="first")
churners = va[va[LABEL] == 1]
missed = churners[churners["rank_v1"] > K]
wrong = va[(va[LABEL] == 0) & (va["rank_v1"] <= K)]
print(f"1) Valid: {len(churners)} khách rời mạng; v1 bắt được {len(churners) - len(missed)} trong top-{K} mỗi tháng,")
print(f"   bỏ sót {len(missed)} ({len(missed) / len(churners):.0%}); gọi nhầm {len(wrong)} trên {3 * K} cuộc gọi.")

# %% 2. Đọc từng ca — đừng nhảy ngay vào biểu đồ
sample = missed.sample(min(100, len(missed)), random_state=config.SEED)
cols = ["t", "province", "contract_months", "days_to_contract_end", "usage_ratio", "outage_m1", "p_v1", "churn_reason"]
print("\n2) 12 trong 100 ca bỏ sót (đọc cả 100 khi làm thật):")
print(sample[cols].head(12).assign(t=lambda d: d["t"].dt.strftime("%Y-%m")).round(3).to_string(index=False))

# %% 3. Đếm theo nhóm — nhóm nào lớn nhất?
reason = pd.DataFrame(
    {
        "trong_100_bo_sot": sample["churn_reason"].value_counts(),
        "ty_le_bo_sot": missed["churn_reason"].value_counts(normalize=True).round(3),
        "ty_le_bat_duoc": churners[churners["rank_v1"] <= K]["churn_reason"].value_counts(normalize=True).round(3),
    }
).fillna(0)
print("\n3) Lý do hủy (từ phiếu hủy) của ca bỏ sót vs ca bắt được:\n" + reason.to_string())
SOUTH = ["TP. Hồ Chí Minh", "Bình Dương"]
hcm_bd = va["province"].isin(SOUTH)
print(f"   HCM + Bình Dương: {hcm_bd.mean():.0%} khách, nhưng {missed['province'].isin(SOUTH).mean():.0%} ca bỏ sót")

# %% 4. Lát cắt theo tỉnh: model hiểu sai rủi ro ở đâu?
by_prov = va.groupby("province", observed=True).agg(
    khach_roi=(LABEL, "sum"),
    ty_le_that=(LABEL, "mean"),
    du_doan_v1=("p_v1", "mean"),
    recall_v1=("rank_v1", lambda r: ((r <= K) & (va.loc[r.index, LABEL] == 1)).sum()),
)
by_prov["recall_v1"] = (by_prov["recall_v1"] / by_prov["khach_roi"]).round(3)
by_prov["du_doan/that"] = (by_prov["du_doan_v1"] / by_prov["ty_le_that"]).round(2)
print("\n4) Theo tỉnh (valid):\n" + by_prov.round(4).sort_values("du_doan/that").to_string())

# %% 5. Giả thuyết: đối thủ khuyến mãi ở HCM/BD từ giữa 06/2025 — hỏi marketing, có lịch khuyến mãi → feature mới (v2)
before = metrics.evaluate(metrics.rank(va["p_v1"], va[LABEL], va["t"]))
after = metrics.evaluate(metrics.rank(va["p_v2"], va[LABEL], va["t"]))
group = churners["province"].isin(SOUTH)
rows = [
    (
        "Đối thủ khuyến mãi (HCM, BD)",
        (sample["churn_reason"] == "Đối thủ khuyến mãi").sum(),
        "thêm lịch khuyến mãi (v2)",
    ),
    ("Chuyển nhà / đi xa", (sample["churn_reason"] == "Chuyển nhà/đi xa").sum(), "không — không có dấu hiệu trước"),
    ("Chất lượng mạng / khác", sample["churn_reason"].isin(["Chất lượng mạng", "Khác"]).sum(), "chưa — vòng sau"),
]
print("\n5) Bảng nhóm lỗi (100 ca bỏ sót của v1):")
print("   | Nhóm lỗi | Số ca | Đã sửa |")
for name, n, fix in rows:
    print(f"   | {name} | {n} | {fix} |")
print(
    f"   Metric valid v1 → v2: AUC {before['auc']:.3f} → {after['auc']:.3f} · PR-AUC {before['pr_auc']:.3f} → "
    f"{after['pr_auc']:.3f} · P@{K} {before['p@k']:.3f} → {after['p@k']:.3f}"
)
recall = [(churners[group][f"rank_{v}"] <= K).mean() for v in ("v1", "v2")]
pred = [va.loc[hcm_bd, f"p_{v}"].mean() for v in ("v1", "v2")]
print(
    f"   HCM+BD: recall@{K} {recall[0]:.3f} → {recall[1]:.3f}; xác suất dự đoán {pred[0]:.4f} → {pred[1]:.4f}", end=""
)
print(f" (thực tế {va.loc[hcm_bd, LABEL].mean():.4f})")

# %% 6. SHAP toàn cục: trung bình |SHAP| theo nhóm lý do, và beeswarm cho từng feature
rows_shap = va.sample(min(5000, len(va)), random_state=config.SEED)
values = explain.shap_values(v2, rows_shap)
mean_abs = explain.group_shap(values).abs().mean().sort_values(ascending=False)
print("\n6) Mức ảnh hưởng trung bình |SHAP| theo nhóm (log-odds):")
print("   " + " · ".join(f"{explain.GROUPS[g].label} {v:.3f}" for g, v in mean_abs.items()))
X = rows_shap[v2.features].apply(lambda s: s.cat.codes if s.dtype == "category" else s)  # màu cần số
shap.summary_plot(values.to_numpy(), X, max_display=12, show=False)
plt.gcf().set_size_inches(8, 6)
plt.tight_layout()
plt.savefig(OUT / "shap_beeswarm.png", dpi=110)
print(f"   Biểu đồ: {OUT.name}/shap_beeswarm.png")
