"""Lab A2 · DATA-01, DATA-02, STAT-01: khám phá dữ liệu nguồn bằng SQL (DuckDB) và pandas → 5 nhận xét có số liệu.

Chạy cả file, hoặc từng ô `# %%` trong VS Code (Run Cell) để xem kết quả từng bước. Biểu đồ ghi vào out/.

    cd labs/data-01-co-ban-kham-pha-du-lieu
    uv run --project ../../projects/g1-churn-telco python eda.py     # cần `make data clean-data` trong dự án trước
"""

# %% 0. Kết nối — DuckDB đọc thẳng file CSV/parquet, không cần "nạp vào database"
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import duckdb  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from churn_telco import config  # noqa: E402

OUT = Path(__file__).with_name("out")
OUT.mkdir(exist_ok=True)
pd.set_option("display.width", 140)
con = duckdb.connect()
for table in ["customers", "subscriptions", "usage", "tickets", "cancellations"]:  # mỗi bảng sạch là một view
    con.execute(f"CREATE VIEW {table} AS SELECT * FROM read_parquet('{config.INTERIM / table}.parquet')")
raw_customers = f"read_csv('{config.RAW / 'customers.csv'}')"

# %% 1. Dữ liệu thô "bẩn" tới mức nào? (đếm TRƯỚC khi làm sạch)
raw_quality = con.execute(f"""
    SELECT count(*)                                                AS so_dong,
           count(DISTINCT customer_id)                             AS so_khach,
           count(*) - count(DISTINCT customer_id)                  AS dong_trung,
           count(*) FILTER (WHERE channel IS NULL)                 AS thieu_kenh,
           count(*) FILTER (WHERE date_of_birth = DATE '1900-01-01') AS ngay_sinh_mac_dinh,
           count(DISTINCT province)                                AS cach_viet_tinh
    FROM {raw_customers}
""").df()
print("1) Bảng khách hàng thô:\n", raw_quality.to_string(index=False))

ticket_lag = con.execute("""
    SELECT date_diff('day', created_at::DATE, logged_at::DATE) AS tre_ngay, count(*) AS so_ticket
    FROM tickets GROUP BY ALL ORDER BY 1
""").df()
late_share = ticket_lag.loc[ticket_lag["tre_ngay"] > 0, "so_ticket"].sum() / ticket_lag["so_ticket"].sum()
print(f"\n   Ticket vào hệ thống trễ ≥ 1 ngày so với lúc khách gọi: {late_share:.1%}")

# %% 2. Bảng "khách-tháng": mỗi dòng = một khách đang hoạt động đầu tháng m, churn = gửi yêu cầu hủy trong tháng m
PANEL = """
WITH months AS (SELECT unnest(range(DATE '2024-02-01', DATE '2026-01-01', INTERVAL 1 MONTH)) AS m),
done AS (SELECT customer_id, request_date FROM cancellations WHERE status = 'Hoàn tất'),
panel AS (
    SELECT mo.m, c.customer_id, c.province, c.signup_date,
           EXISTS (SELECT 1 FROM done d WHERE d.customer_id = c.customer_id
                   AND d.request_date >= mo.m AND d.request_date < mo.m + INTERVAL 1 MONTH)::INT AS churn
    FROM months mo JOIN customers c ON c.signup_date < mo.m
    WHERE NOT EXISTS (SELECT 1 FROM done d WHERE d.customer_id = c.customer_id AND d.request_date < mo.m)
)
"""
monthly = con.execute(
    PANEL
    + """
    SELECT m AS thang, count(*) AS dang_hoat_dong, sum(churn)::INT AS roi_mang, round(100 * avg(churn), 2) AS ty_le_pct
    FROM panel GROUP BY ALL ORDER BY m
"""
).df()
print("\n2) Tỷ lệ rời mạng theo tháng:\n", monthly.to_string(index=False))
base_rate = monthly["roi_mang"].sum() / monthly["dang_hoat_dong"].sum()

fig, ax = plt.subplots(figsize=(8, 3.5))
ax.plot(monthly["thang"], monthly["ty_le_pct"], marker="o")
ax.axhline(100 * base_rate, color="grey", ls="--", lw=1, label=f"Trung bình {base_rate:.2%}")
ax.set(title="Tỷ lệ khách rời mạng mỗi tháng", ylabel="%")
ax.legend()
fig.tight_layout()
fig.savefig(OUT / "churn_theo_thang.png", dpi=110)

# %% 3. Theo loại hợp đồng — ASOF JOIN: kỳ thuê bao đang hiệu lực ở đầu mỗi tháng
by_contract = con.execute(
    PANEL
    + """
    SELECT s.contract_months AS hop_dong_thang, count(*) AS khach_thang, round(100 * avg(p.churn), 2) AS ty_le_pct
    FROM panel p ASOF LEFT JOIN subscriptions s ON p.customer_id = s.customer_id AND p.m >= s.start_date
    GROUP BY ALL ORDER BY 1
"""
).df()
print("\n3) Theo hợp đồng đang hiệu lực:\n", by_contract.to_string(index=False))

# %% 4. Theo tỉnh và quý — pivot bằng pandas
by_province = con.execute(
    PANEL
    + """
    SELECT province AS tinh, strftime(m, '%Y') || '-Q' || quarter(m) AS quy, avg(churn) AS ty_le FROM panel GROUP BY ALL
"""
).df()
pivot = by_province.pivot(index="tinh", columns="quy", values="ty_le").mul(100).round(1)
print("\n4) Tỷ lệ rời mạng (%) theo tỉnh × quý:\n", pivot.to_string())
peak = by_province.loc[by_province["ty_le"].idxmax()]

# %% 5. Dấu hiệu trước khi rời: data tháng ngay trước tháng rời / trung bình 3 tháng trước đó
usage_signal = con.execute(
    PANEL
    + """,
    ratio AS (
        SELECT p.churn,
               max(u.data_gb) FILTER (WHERE u.month = p.m - INTERVAL 1 MONTH)
               / avg(u.data_gb) FILTER (WHERE u.month < p.m - INTERVAL 1 MONTH) AS ty_le_dung
        FROM panel p JOIN usage u ON u.customer_id = p.customer_id
             AND u.month >= p.m - INTERVAL 4 MONTH AND u.month < p.m
        WHERE p.m >= DATE '2024-06-01'
        GROUP BY p.m, p.customer_id, p.churn
    )
    SELECT churn, count(*) AS so_dong, median(ty_le_dung) AS trung_vi,
           quantile_cont(ty_le_dung, 0.25) AS p25, avg((ty_le_dung < 0.75)::INT) AS ty_le_giam_manh
    FROM ratio WHERE ty_le_dung IS NOT NULL GROUP BY ALL ORDER BY churn
"""
).df()
print("\n5) Tỷ lệ dùng data (tháng trước / 3 tháng trước đó):\n", usage_signal.round(3).to_string(index=False))

# %% 6. Thống kê mô tả bằng pandas: phân phối lệch → trung bình đánh lừa, nhìn trung vị và phân vị
usage = pd.read_parquet(config.INTERIM / "usage.parquet")
outage = usage["outage_minutes"]
print("\n6) Phút mất mạng mỗi khách-tháng:\n", outage.describe(percentiles=[0.5, 0.9, 0.99]).round(1).to_string())
fig, ax = plt.subplots(figsize=(6, 3.5))
ax.hist(outage.clip(upper=600), bins=60)
ax.axvline(outage.mean(), color="red", label=f"trung bình {outage.mean():.0f}")
ax.axvline(outage.median(), color="black", ls="--", label=f"trung vị {outage.median():.0f}")
ax.set(title="Phút mất mạng / tháng (cắt ở 600)", xlabel="phút", ylabel="số khách-tháng")
ax.legend()
fig.tight_layout()
fig.savefig(OUT / "mat_mang_hist.png", dpi=110)

# %% 7. Năm nhận xét — mỗi câu một con số, tính từ kết quả ở trên (không gõ tay)
no_contract = by_contract.set_index("hop_dong_thang")["ty_le_pct"]
churn_row, stay_row = usage_signal.set_index("churn").loc[1], usage_signal.set_index("churn").loc[0]
notes = [
    f"Tỷ lệ rời mạng nền {base_rate:.2%}/tháng: model 'đoán không ai rời' đúng {1 - base_rate:.1%} — accuracy vô dụng.",
    f"Khách không kỳ hạn rời {no_contract[0]:.2f}%/tháng, gấp {no_contract[0] / no_contract[24]:.1f} lần khách hợp "
    f"đồng 24 tháng ({no_contract[24]:.2f}%).",
    f"Đỉnh bất thường: {peak['tinh']} quý {peak['quy']} rời {peak['ty_le']:.1%}/tháng — phải hỏi nghiệp vụ chuyện gì "
    "đã xảy ra.",
    f"Trước khi rời, {churn_row['ty_le_giam_manh']:.0%} khách dùng data giảm dưới 75% (khách ở lại: "
    f"{stay_row['ty_le_giam_manh']:.0%}) — dấu hiệu sớm, nhưng không phải ai giảm cũng rời.",
    f"Phút mất mạng lệch phải: trung bình {outage.mean():.0f} phút nhưng trung vị {outage.median():.0f}, "
    f"1% khách-tháng mất ≥ {outage.quantile(0.99):.0f} phút — báo cáo bằng trung vị/phân vị.",
]
print("\n7) Năm nhận xét:")
for i, note in enumerate(notes, 1):
    print(f"   {i}. {note}")
print(f"\nBiểu đồ: {sorted(p.name for p in OUT.glob('*.png'))}")
