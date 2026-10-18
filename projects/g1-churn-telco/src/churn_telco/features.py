"""Bảng học as-of (A4): mỗi dòng = (ngày chấm điểm t, khách). Feature CHỈ dùng dữ liệu đã có trong hệ thống trước t;
nhãn = khách gửi yêu cầu hủy (không hoàn tác) trong [t, t + 30 ngày).

Ba quy tắc chống rò rỉ dữ liệu, mỗi quy tắc có test riêng:
1. Mọi bảng sự kiện lọc theo thời điểm dữ liệu VÀO HỆ THỐNG trước t (ticket: logged_at, không phải created_at).
2. Giá trị "thay đổi theo thời gian" lấy theo trạng thái tại t (ASOF JOIN kỳ thuê bao, bảng giá), không lấy trạng thái
   hiện tại (cột status/cancel_date của CRM là trạng thái ngày export — tuyệt đối không dùng).
3. Ticket "Yêu cầu hủy" không phải feature: khách đã tự nói muốn hủy, đó gần như chính là nhãn (proxy của nhãn).

    uv run python -m churn_telco.features      # data/interim → data/processed/features.parquet
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

import duckdb
import pandas as pd

from churn_telco import config

log = logging.getLogger(__name__)

KEYS = ["t", "customer_id"]
LABEL = "churn_30d"
META = ["churn_reason"]  # chỉ để phân tích lỗi (A6) — không bao giờ là feature
CATEGORICAL = ["segment", "channel", "province", "plan_code", "payment_method"]
NUMERIC = [
    "tenure_days",
    "age",
    "monthly_fee",
    "fee_change_90d",
    "speed_mbps",
    "has_tv",
    "has_mobile",
    "contract_months",
    "days_to_contract_end",
    "autopay",
    "data_gb_m1",
    "data_gb_m2_m4",
    "usage_ratio",
    "usage_missing_m1",
    "tv_hours_m1",
    "outage_m1",
    "outage_avg_3m",
    "tickets_30d",
    "network_tickets_60d",
    "billing_tickets_90d",
    "open_tickets",
    "min_csat_90d",
    "days_since_last_ticket",
    "late_or_unpaid_90d",
    "unpaid_at_t",
    "max_days_late_90d",
    "refunds_90d",
]

FEATURE_SQL = """
WITH snap AS (SELECT CAST(t AS TIMESTAMP) AS t FROM snapshots),
done AS (SELECT customer_id, request_date, reason FROM cancellations WHERE status = 'Hoàn tất'),
pop AS (  -- khách đã vào mạng trước t và chưa gửi yêu cầu hủy nào trước t
    SELECT s.t, c.customer_id, c.signup_date, c.segment, c.channel, c.province, c.date_of_birth
    FROM snap s JOIN customers c ON c.signup_date < s.t
    WHERE NOT EXISTS (SELECT 1 FROM done d WHERE d.customer_id = c.customer_id AND d.request_date < s.t)
),
sub AS (  -- kỳ thuê bao đang hiệu lực tại t: kỳ gần nhất bắt đầu trước hoặc đúng t
    SELECT p.t, p.customer_id, s.plan_code, s.contract_months, s.start_date AS sub_start, s.payment_method
    FROM pop p ASOF LEFT JOIN subscriptions s ON p.customer_id = s.customer_id AND p.t >= s.start_date
),
fee AS (  -- giá tại t và giá CÙNG GÓI 90 ngày trước t (bảng giá cũng là dữ liệu thay đổi theo thời gian)
    SELECT u.t, u.customer_id, p_now.monthly_fee, p_90.monthly_fee AS fee_90d
    FROM (SELECT *, t - INTERVAL 90 DAY AS t90 FROM sub) u
    ASOF LEFT JOIN plan_prices p_now ON u.plan_code = p_now.plan_code AND u.t >= p_now.effective_from
    ASOF LEFT JOIN plan_prices p_90 ON u.plan_code = p_90.plan_code AND u.t90 >= p_90.effective_from
),
use AS (  -- tháng m1 = tháng liền trước t (đã chốt số liệu tại t); m2..m4 = ba tháng trước đó
    -- round(avg(...), 4): cộng số thực song song cho kết quả lệch ở chữ số thứ 13 giữa các lần chạy; làm tròn để
    -- bảng học giống hệt từng bit mỗi lần dựng (mã băm dữ liệu ổn định — A7)
    SELECT p.t, p.customer_id,
        max(u.data_gb) FILTER (WHERE u.month = p.t - INTERVAL 1 MONTH) AS data_gb_m1,
        round(avg(u.data_gb) FILTER (WHERE u.month < p.t - INTERVAL 1 MONTH), 4) AS data_gb_m2_m4,
        max(u.tv_hours) FILTER (WHERE u.month = p.t - INTERVAL 1 MONTH) AS tv_hours_m1,
        max(u.outage_minutes) FILTER (WHERE u.month = p.t - INTERVAL 1 MONTH) AS outage_m1,
        round(avg(u.outage_minutes) FILTER (WHERE u.month >= p.t - INTERVAL 3 MONTH), 4) AS outage_avg_3m
    FROM pop p LEFT JOIN usage u
        ON u.customer_id = p.customer_id AND u.month >= p.t - INTERVAL 4 MONTH AND u.month < p.t
    GROUP BY ALL
),
tix AS (  -- chỉ ticket đã VÀO HỆ THỐNG trước t; bỏ ticket "Yêu cầu hủy" (proxy của nhãn)
    SELECT p.t, p.customer_id,
        count(k.ticket_id) FILTER (WHERE k.logged_at >= p.t - INTERVAL 30 DAY) AS tickets_30d,
        count(k.ticket_id) FILTER (
            WHERE k.category IN ('Mất kết nối', 'Mạng chậm') AND k.logged_at >= p.t - INTERVAL 60 DAY
        ) AS network_tickets_60d,
        count(k.ticket_id) FILTER (
            WHERE k.category = 'Cước phí' AND k.logged_at >= p.t - INTERVAL 90 DAY
        ) AS billing_tickets_90d,
        count(k.ticket_id) FILTER (WHERE k.resolved_at IS NULL OR k.resolved_at >= p.t) AS open_tickets,
        min(k.csat) FILTER (WHERE k.resolved_at < p.t AND k.logged_at >= p.t - INTERVAL 90 DAY) AS min_csat_90d,
        min(date_diff('day', k.logged_at, p.t)) AS days_since_last_ticket
    FROM pop p LEFT JOIN tickets k
        ON k.customer_id = p.customer_id AND k.category <> 'Yêu cầu hủy'
        AND k.logged_at < p.t AND k.logged_at >= p.t - INTERVAL 180 DAY
    GROUP BY ALL
),
pay AS (  -- hoá đơn đã phát hành trước t; "trả trễ" xét theo những gì biết tại t
    SELECT p.t, p.customer_id,
        count(i.invoice_id) FILTER (
            WHERE NOT i.is_adjustment AND i.due_date < p.t AND i.due_date >= p.t - INTERVAL 90 DAY
            AND (i.paid_date IS NULL OR i.paid_date > i.due_date)
        ) AS late_or_unpaid_90d,
        count(i.invoice_id) FILTER (
            WHERE NOT i.is_adjustment AND i.due_date < p.t AND (i.paid_date IS NULL OR i.paid_date >= p.t)
        ) AS unpaid_at_t,
        max(greatest(date_diff('day', i.due_date, least(coalesce(i.paid_date, p.t), p.t)), 0)) FILTER (
            WHERE NOT i.is_adjustment AND i.due_date < p.t AND i.due_date >= p.t - INTERVAL 90 DAY
        ) AS max_days_late_90d,
        count(i.invoice_id) FILTER (WHERE i.is_adjustment AND i.issued_date >= p.t - INTERVAL 90 DAY) AS refunds_90d
    FROM pop p LEFT JOIN invoices i
        ON i.customer_id = p.customer_id AND i.issued_date < p.t AND i.issued_date >= p.t - INTERVAL 120 DAY
    GROUP BY ALL
),
lab AS (  -- nhãn: yêu cầu hủy hoàn tất trong [t, t + 30 ngày) — chỉ nhãn được nhìn vào tương lai
    SELECT p.t, p.customer_id, d.customer_id IS NOT NULL AS churn_30d, d.reason AS churn_reason
    FROM pop p LEFT JOIN done d
        ON d.customer_id = p.customer_id AND d.request_date >= p.t AND d.request_date < p.t + INTERVAL 30 DAY
)
SELECT
    p.t, p.customer_id,
    p.segment, p.channel, p.province, s.plan_code, s.payment_method,
    date_diff('day', p.signup_date, p.t) AS tenure_days,
    year(p.t) - year(p.date_of_birth) AS age,
    f.monthly_fee,
    f.monthly_fee / f.fee_90d - 1 AS fee_change_90d,
    pl.speed_mbps, pl.has_tv::INT AS has_tv, pl.has_mobile::INT AS has_mobile,
    s.contract_months,
    CASE WHEN s.contract_months > 0
        THEN date_diff('day', p.t, s.sub_start + to_days(CAST(s.contract_months * 30 AS INTEGER))) END
        AS days_to_contract_end,
    (s.payment_method = 'Tự động trừ thẻ')::INT AS autopay,
    u.data_gb_m1, u.data_gb_m2_m4, u.data_gb_m1 / nullif(u.data_gb_m2_m4, 0) AS usage_ratio,
    (u.data_gb_m1 IS NULL)::INT AS usage_missing_m1, u.tv_hours_m1, u.outage_m1, u.outage_avg_3m,
    k.tickets_30d, k.network_tickets_60d, k.billing_tickets_90d, k.open_tickets, k.min_csat_90d,
    k.days_since_last_ticket,
    y.late_or_unpaid_90d, y.unpaid_at_t, y.max_days_late_90d, y.refunds_90d,
    l.churn_30d::INT AS churn_30d, l.churn_reason
FROM pop p
JOIN sub s USING (t, customer_id)
JOIN fee f USING (t, customer_id)
LEFT JOIN plans pl ON pl.plan_code = s.plan_code
JOIN use u USING (t, customer_id)
JOIN tix k USING (t, customer_id)
JOIN pay y USING (t, customer_id)
JOIN lab l USING (t, customer_id)
ORDER BY p.t, p.customer_id
"""

TABLES = ["customers", "subscriptions", "plans", "plan_prices", "invoices", "usage", "tickets", "cancellations"]


def connect(interim: Path = config.INTERIM) -> duckdb.DuckDBPyConnection:
    """Một kết nối DuckDB trong bộ nhớ; mỗi bảng sạch là một view đọc thẳng file parquet (không nạp hết vào RAM)."""
    con = duckdb.connect()
    con.execute("SET enable_progress_bar = false")
    for name in TABLES:
        con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{interim / name}.parquet')")
    return con


def connect_as_of(interim: Path, t: pd.Timestamp) -> duckdb.DuckDBPyConnection:
    """Các bảng nguồn "như chụp lại lúc t": bỏ dòng chưa vào hệ thống trước t, xoá giá trị chỉ biết được sau t.

    Dùng để KIỂM TRA rò rỉ: feature dựng từ kết nối này phải giống hệt feature dựng từ dữ liệu đầy đủ.
    """
    src = {name: f"read_parquet('{interim / name}.parquet')" for name in TABLES}
    ts = f"TIMESTAMP '{t:%Y-%m-%d}'"
    views = {
        "customers": f"SELECT * FROM {src['customers']} WHERE signup_date < {ts}",
        "subscriptions": f"SELECT * FROM {src['subscriptions']} WHERE start_date <= {ts}",
        "plans": f"SELECT * FROM {src['plans']}",
        "plan_prices": f"SELECT * FROM {src['plan_prices']} WHERE effective_from <= {ts}",
        "invoices": f"""SELECT * REPLACE (CASE WHEN paid_date < {ts} THEN paid_date END AS paid_date)
                        FROM {src["invoices"]} WHERE issued_date < {ts}""",
        "usage": f"SELECT * FROM {src['usage']} WHERE month < {ts}",
        "tickets": f"""SELECT * REPLACE (CASE WHEN resolved_at < {ts} THEN resolved_at END AS resolved_at,
                                         CASE WHEN resolved_at < {ts} THEN csat END AS csat)
                       FROM {src["tickets"]} WHERE logged_at < {ts}""",
        "cancellations": f"SELECT * FROM {src['cancellations']} WHERE request_date < {ts}",
    }
    con = duckdb.connect()
    con.execute("SET enable_progress_bar = false")
    for name, sql in views.items():
        con.execute(f"CREATE VIEW {name} AS {sql}")
    return con


def build(con: duckdb.DuckDBPyConnection, snapshots: Sequence[pd.Timestamp] = config.SNAPSHOTS) -> pd.DataFrame:
    con.register("snapshots", pd.DataFrame({"t": pd.to_datetime(list(snapshots))}))
    df = con.execute(FEATURE_SQL).df()
    df["t"] = pd.to_datetime(df["t"])
    for col in CATEGORICAL:
        df[col] = df[col].astype("category")
    df[NUMERIC] = df[NUMERIC].astype("float64")  # một kiểu số duy nhất, NaN = thiếu (sklearn và LightGBM đều hiểu)
    df[LABEL] = df[LABEL].astype("int64")
    return df


def build_all(interim: Path = config.INTERIM, out: Path = config.PROCESSED) -> pd.DataFrame:
    from churn_telco import schemas  # kiểm tra schema trước và sau khi dựng (A4 · DATA-05)

    schemas.validate_clean(interim)
    df = schemas.FEATURES.validate(build(connect(interim)), lazy=True)
    schemas.check_snapshots(df)
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "features.parquet", index=False)
    log.info("features.parquet: %d dòng × %d cột, tỷ lệ churn %.2f%%", len(df), df.shape[1], 100 * df[LABEL].mean())
    return df


def load(processed: Path = config.PROCESSED) -> pd.DataFrame:
    """Bảng học + các khối feature bổ sung `features_*.parquet` (A6: marketing), ghép theo khoá (t, customer_id)."""
    df = pd.read_parquet(processed / "features.parquet")
    for extra in sorted(processed.glob("features_*.parquet")):
        df = df.merge(pd.read_parquet(extra), on=KEYS, how="left", validate="one_to_one")
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    build_all()
