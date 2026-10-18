"""Lab A4 · DATA-03: cố tình gây rò rỉ dữ liệu, xem nó "đẹp" tới mức nào, rồi bắt nó bằng bốn cách.

Ba lỗi rất hay gặp khi dựng bảng học từ dữ liệu vận hành:
  (a) đếm ticket trên TOÀN BỘ lịch sử, không lọc theo t  → lẫn cả ticket "Yêu cầu hủy" gọi SAU ngày t;
  (b) dùng cột trạng thái hiện tại của CRM (status = "Đã hủy")  → trạng thái tại ngày export, không phải tại t;
  (c) lọc ticket theo created_at thay vì logged_at  → ticket chưa vào hệ thống tại t (lỗi tinh vi).
Bốn cách phát hiện: kết quả "quá đẹp", AUC từng feature, độ quan trọng dồn vào một feature, test đúng thời điểm.
Cuối lab: chia ngẫu nhiên vs chia theo thời gian — cách đánh giá cũng có thể "rò" tương lai vào quá khứ.

    cd labs/data-03-trung-cap-ro-ri-du-lieu
    uv run --project ../../projects/g1-churn-telco python leakage_lab.py     # cần `make features`
"""

import lightgbm as lgb
import numpy as np
import pandas as pd
from churn_telco import config, features, split
from churn_telco.features import CATEGORICAL, KEYS, LABEL, NUMERIC
from sklearn.metrics import average_precision_score, roc_auc_score

df = features.load()
con = features.connect()
BASE = CATEGORICAL + NUMERIC

# %% 1. Dựng ba feature "ngây thơ" — câu SQL trông hoàn toàn hợp lý
naive = con.execute("""
    SELECT c.customer_id,
           (c.status = 'Đã hủy')::INT                                    AS is_cancelled_crm,         -- lỗi (b)
           count(k.ticket_id)                                            AS tickets_all_time,         -- lỗi (a)
           count(k.ticket_id) FILTER (WHERE k.category = 'Yêu cầu hủy')  AS cancel_tickets_all_time   -- lỗi (a)
    FROM customers c LEFT JOIN tickets k USING (customer_id)
    GROUP BY ALL
""").df()
leaky = df.merge(naive, on="customer_id", how="left", validate="many_to_one")
created = features.FEATURE_SQL.replace("logged_at", "created_at")  # lỗi (c): một chữ khác nhau
con.register("snapshots", pd.DataFrame({"t": config.SNAPSHOTS}))
by_created = con.execute(created).df()[[*KEYS, "tickets_30d", "network_tickets_60d", "open_tickets"]]
by_created["t"] = pd.to_datetime(by_created["t"])
leaky = leaky.merge(by_created, on=KEYS, suffixes=("", "_created"), validate="one_to_one")
parts = split.split(leaky)
train, valid = parts["train"], parts["valid"]


def fit_eval(cols: list[str]) -> tuple[float, float, pd.Series]:
    model = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, min_child_samples=100, verbose=-1)
    model.fit(train[cols], train[LABEL])
    p = model.predict_proba(valid[cols])[:, 1]
    gain = pd.Series(model.booster_.feature_importance("gain"), index=cols)
    return roc_auc_score(valid[LABEL], p), average_precision_score(valid[LABEL], p), gain / gain.sum()


# %% 2. Cách phát hiện 1 — kết quả "quá đẹp so với bài toán"
print("1) Cùng model, chỉ khác feature (đánh giá trên valid):")
experiments = {
    "as-of đúng": BASE,
    "+ ticket toàn lịch sử (a)": BASE + ["tickets_all_time", "cancel_tickets_all_time"],
    "+ trạng thái CRM (b)": BASE + ["is_cancelled_crm"],
}
importance = {}
for name, cols in experiments.items():
    auc, pr, importance[name] = fit_eval(cols)
    print(f"   {name:28} AUC {auc:.3f} · PR-AUC {pr:.3f}")
print("   → Churn hành vi khó đoán: AUC 0,97 là dấu hiệu báo động, không phải thành công.")

# %% 3. Cách phát hiện 2 — AUC của TỪNG feature một mình: feature đơn lẻ mạnh bất thường là nghi phạm số một
print("\n2) AUC của từng feature một mình (valid), 6 cao nhất:")
single = {}
for col in [c for c in leaky.columns if c in BASE + list(naive.columns[1:])]:
    if col in CATEGORICAL:
        continue
    x = valid[col].fillna(valid[col].median())
    auc = roc_auc_score(valid[LABEL], x)
    single[col] = max(auc, 1 - auc)  # feature có thể tỷ lệ nghịch với nhãn
for col, auc in sorted(single.items(), key=lambda kv: -kv[1])[:6]:
    flag = "  ← nghi rò rỉ" if auc > 0.8 else ""
    print(f"   {col:26} {auc:.3f}{flag}")

# %% 4. Cách phát hiện 3 — độ quan trọng dồn vào một feature
top = importance["+ trạng thái CRM (b)"].sort_values(ascending=False).head(3)
share, second = top.iloc[0], top.iloc[1]
print(f"\n3) Model có cột CRM: {top.index[0]} chiếm {share:.0%} tổng gain, feature thứ hai chỉ {second:.0%}")

# %% 5. Lỗi (c) — metric gần như không đổi, nên KHÔNG thể bắt bằng metric
diff = (leaky["tickets_30d"] != leaky["tickets_30d_created"]).mean()
cols_c = [c if c not in ("tickets_30d", "network_tickets_60d", "open_tickets") else f"{c}_created" for c in BASE]
auc_c, auc_ok = fit_eval(cols_c)[0], fit_eval(BASE)[0]
print(f"\n4) Lọc theo created_at: {diff:.1%} dòng có tickets_30d khác; AUC {auc_c:.3f} (as-of đúng: {auc_ok:.3f})")

# %% 6. Cách phát hiện 4 — test đúng thời điểm: dựng lại feature từ dữ liệu bị cắt về đúng ngày t
t = pd.Timestamp("2025-06-01")
for name, sql in [("logged_at (đúng)", features.FEATURE_SQL), ("created_at (sai)", created)]:
    rebuilt = []
    for con_t in (features.connect(), features.connect_as_of(config.INTERIM, t)):
        con_t.register("snapshots", pd.DataFrame({"t": [t]}))
        rebuilt.append(con_t.execute(sql).df().set_index(KEYS).sort_index()["tickets_30d"])
    mismatch = (rebuilt[0] != rebuilt[1]).sum()
    print(f"   Test đúng thời điểm tại {t:%Y-%m-%d}, {name}: {mismatch} khách lệch → {'ĐỎ' if mismatch else 'xanh'}")

# %% 7. Đánh giá theo thời gian: backtest cuốn chiếu thay cho MỘT con số chia ngẫu nhiên
#    Mỗi "gốc" T: học các tháng t < T (nhãn của chúng đã biết đủ trước T), chấm 3 tháng [T, T + 3 tháng).
model = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, min_child_samples=100, verbose=-1)
rng = np.random.default_rng(config.SEED)
in_train = rng.random(len(leaky)) < 0.8
model.fit(leaky[in_train][BASE], leaky[in_train][LABEL])
random_auc = roc_auc_score(leaky[~in_train][LABEL], model.predict_proba(leaky[~in_train][BASE])[:, 1])
print(
    f"\n5) Chia ngẫu nhiên 80/20 trên cả 18 tháng: AUC {random_auc:.3f} — một con số, không biết nó đúng cho tháng nào"
)
for origin in pd.to_datetime(["2025-01-01", "2025-04-01", "2025-07-01", "2025-10-01"]):
    past = leaky[leaky["t"] < origin]
    window = leaky[(leaky["t"] >= origin) & (leaky["t"] < origin + pd.DateOffset(months=3))]
    model.fit(past[BASE], past[LABEL])
    auc = roc_auc_score(window[LABEL], model.predict_proba(window[BASE])[:, 1])
    print(f"   Backtest gốc {origin:%Y-%m}: học {past['t'].nunique():2d} tháng → AUC 3 tháng sau {auc:.3f}")
print("   → Hiệu quả dao động theo giai đoạn (khuyến mãi của đối thủ, mùa bão...). Báo cáo dải này, không phải một số.")
