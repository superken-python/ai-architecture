# A4 · Dữ liệu đúng thời điểm và feature

**Tuần 4** · Kỹ năng: [DATA-03](../02-skill-map/generated/mang/data.md#data-03) **Trung cấp**,
[DATA-04](../02-skill-map/generated/mang/data.md#data-04) Cơ bản, [DATA-05](../02-skill-map/generated/mang/data.md#data-05) Cơ bản ·
Lab: [`labs/data-03-trung-cap-ro-ri-du-lieu/`](../../labs/data-03-trung-cap-ro-ri-du-lieu/README.md) ·
Sản phẩm: pipeline feature có kiểm tra pandera + test chứng minh không rò rỉ dữ liệu

Đây là bài quan trọng nhất của Giai đoạn A. Lỗi đắt nhất trong ML dữ liệu bảng không nằm ở model mà ở **bảng học**:
feature vô tình chứa thông tin của tương lai. Model khi đó đạt AUC 0,97 trên giấy, rồi sụp đổ khi chạy thật, vì
tương lai không có sẵn lúc chấm điểm. Ta sẽ dựng bảng học đúng cách, chứng minh nó đúng bằng test, rồi cố tình làm
sai để thấy cái sai trông "đẹp" tới mức nào.

**Sau bài này bạn làm được:**

- Định nghĩa bảng học theo ngày chấm điểm: tổng thể khách, cửa sổ feature, cửa sổ nhãn.
- Viết một câu SQL dựng feature "as-of" từ 8 bảng vận hành: `ASOF JOIN`, cửa sổ thời gian, lọc theo thời điểm dữ liệu
  vào hệ thống.
- Nhận ra bốn loại rò rỉ và bắt chúng bằng: kết quả quá đẹp, AUC từng feature, độ quan trọng bất thường, **test đúng
  thời điểm**.
- Viết hợp đồng dữ liệu bằng pandera để pipeline tự dừng khi dữ liệu sai schema hoặc lệch phân phối.

---

## 1 · Lý thuyết: bảng học theo ngày chấm điểm

### 1.1 Ba khái niệm: ngày chấm điểm, cửa sổ feature, cửa sổ nhãn

Model sẽ chạy **ngày 1 hằng tháng**. Bảng học phải mô phỏng đúng tình huống đó, cho từng tháng trong quá khứ:

```text
                    cửa sổ feature (chỉ dữ liệu ĐÃ VÀO hệ thống trước t)        cửa sổ nhãn
  ──────────[ t−180 ngày ……… t−90 ……… t−30 ……… t )[ t ……………… t+30 ngày )──────────▶ thời gian
                                                ▲
                                     ngày chấm điểm t (ngày 1 hằng tháng)
```

- **Tổng thể tại t**: khách đã vào mạng trước t và **chưa gửi** yêu cầu hủy nào trước t. Khách đã đi thì không cần
  chấm điểm.
- **Feature tại t**: chỉ tính từ những gì hệ thống **đã biết** trước t.
- **Nhãn tại t**: khách gửi yêu cầu hủy (không hoàn tác) trong `[t, t + 30 ngày)`. *Chỉ nhãn* được nhìn vào tương lai.

Một khách có mặt ở nhiều tháng, mỗi tháng một dòng với feature khác nhau. 18 tháng × ~20.000 khách = **359.908 dòng**.

### 1.2 Bốn loại rò rỉ dữ liệu

| Loại | Ví dụ ở Sóng Xanh | Vì sao nguy hiểm |
|---|---|---|
| **Thông tin tương lai** | cột `status` của CRM là trạng thái *ngày export* (05/01/2026); đếm ticket trên *toàn bộ* lịch sử | khi chấm điểm thật, tương lai chưa xảy ra: feature mang giá trị khác hẳn lúc train |
| **Dữ liệu vào hệ thống trễ** | lọc ticket theo `created_at` (khách gọi lúc nào) thay vì `logged_at` (nhân viên nhập lúc nào) | 20,8% ticket vào hệ thống trễ ≥ 1 ngày (bài A2): lúc chấm điểm chúng chưa có |
| **Proxy của nhãn** | ticket "Yêu cầu hủy": 70% khách gọi hỏi thủ tục hủy vài ngày trước khi gửi yêu cầu chính thức | thông tin có thật trước t, nhưng nó *là* bắt đầu của nhãn. Model học "ai hỏi hủy thì hủy", vô ích cho việc giữ chân sớm |
| **Rò rỉ qua cách đánh giá** | chia ngẫu nhiên; tính trung vị/target encoding trên cả bảng trước khi chia | model "nhìn trộm" dữ liệu cùng giai đoạn hoặc chính tập test |

Loại thứ ba cần phân biệt kỹ. Một ticket "Yêu cầu hủy" vào hệ thống trước t là thông tin **có thật** tại t, nên đây
không phải rò rỉ theo thời gian. Nhưng khách đã tự nói muốn hủy thì họ được chuyển sang quy trình giữ chân riêng (quầy
hủy). Mục tiêu của model là tìm khách **trước** lúc đó. Đưa nó vào feature chỉ làm metric đẹp lên mà quyết định
không tốt hơn.

### 1.3 Ba quy tắc chống rò rỉ cho bảng học

1. **Mọi bảng sự kiện lọc theo thời điểm dữ liệu vào hệ thống trước t** (ticket: `logged_at < t`; hoá đơn: phát
   hành trước t, và ngày trả chỉ tính nếu trả trước t).
2. **Giá trị thay đổi theo thời gian lấy theo trạng thái tại t**: kỳ thuê bao, giá cước dùng `ASOF JOIN`. Không bao
   giờ dùng cột "trạng thái hiện tại".
3. **Không dùng proxy của nhãn** (ticket "Yêu cầu hủy").

Mỗi quy tắc có một test. Quan trọng nhất là **test đúng thời điểm** (mục 1.5).

### 1.4 Feature cho dữ liệu hành vi

| Họ feature | Ví dụ | Ý tưởng |
|---|---|---|
| Trạng thái tại t | `contract_months`, `days_to_contract_end`, `plan_code`, `autopay` | khách đang ở "tình huống" nào |
| Thay đổi theo thời gian | `fee_change_90d` (giá hôm nay / giá 90 ngày trước) | thay đổi thường quan trọng hơn mức tuyệt đối |
| Cửa sổ gần đây | `tickets_30d`, `network_tickets_60d`, `billing_tickets_90d` | đếm sự kiện trong 30/60/90 ngày; mỗi cửa sổ trả lời một câu hỏi |
| Tỷ lệ so với chính mình | `usage_ratio` = data tháng trước / trung bình 3 tháng trước đó | so với *thói quen của khách đó*, không so với người khác |
| Độ gần (recency) | `days_since_last_ticket` | sự kiện vừa xảy ra quan trọng hơn sự kiện cũ |
| Mức xấu nhất | `min_csat_90d`, `max_days_late_90d`, `outage_m1` | một trải nghiệm tệ đủ làm khách bỏ đi |
| Thiếu cũng là thông tin | `usage_missing_m1`; `days_to_contract_end` thiếu = không có hợp đồng | đừng vội điền trung vị: giữ NaN cho LightGBM, thêm cờ cho logistic |

### 1.5 Test đúng thời điểm — bằng chứng thay cho lời hứa

Ý tưởng rất đơn giản. Với một ngày t, ta tạo bản sao các bảng nguồn **như chụp lại đúng lúc t**: xoá dòng chưa vào hệ
thống trước t, xoá giá trị chỉ biết được sau t (ngày trả của hoá đơn trả sau t, thời điểm xử lý của ticket xử lý sau
t…). Rồi dựng feature hai lần:

- từ dữ liệu **đầy đủ** (như lúc train);
- từ dữ liệu **chụp tại t** (như lúc chấm điểm thật).

Hai bảng phải **giống hệt nhau**. Feature nào dùng thông tin sau t sẽ cho giá trị khác, và test đỏ. Không cần đoán
feature nào đáng ngờ: test kiểm tra tất cả, cho cả những feature viết sau này.

### 1.6 Hợp đồng dữ liệu — để pipeline tự dừng

Dữ liệu nguồn sẽ thay đổi mà không ai báo: một chi nhánh đổi cách nhập tỉnh, một job export chạy thiếu. Pipeline phải
**dừng với thông báo rõ ràng** thay vì train/chấm điểm trên dữ liệu hỏng. Hai tầng kiểm tra:

- **Schema theo dòng** (pandera): kiểu, khoảng giá trị, tập giá trị cho phép, khoá không trùng.
- **Phân phối theo bảng**: số khách mỗi tháng không lệch quá ±25% so với trung vị, tỷ lệ churn trong khoảng hợp lý.

---

## 2 · Lab A4

### A4.1 `features.py` — một câu SQL cho cả bảng học

**File: `src/churn_telco/features.py` · `đầu file`**

```python
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
```

Docstring ghi lại ba quy tắc ở mục 1.3. Đây là "hợp đồng" của module, và mỗi quy tắc có một test.

**File: `src/churn_telco/features.py` · `log…NUMERIC`**

```python
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
```

Danh sách feature viết **tường minh**: thêm/bớt feature là một dòng diff, review được. `META` (lý do hủy) chỉ dùng để
phân tích lỗi ở bài A6. Nó nằm trong bảng nhưng **không bao giờ** là feature, vì đó là thông tin của tương lai.

Giờ tới phần chính. Đọc câu SQL theo từng CTE:

**File: `src/churn_telco/features.py` · `FEATURE_SQL`**

```python
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
```

| CTE | Làm gì | Chống rò rỉ ở đâu |
|---|---|---|
| `snap` | danh sách ngày chấm điểm (đăng ký từ Python) | — |
| `done` | yêu cầu hủy **hoàn tất** (bỏ "Đã hoàn tác") | khách đổi ý trong 7 ngày không phải churn |
| `pop` | tổng thể: vào mạng trước t, chưa gửi yêu cầu hủy trước t | `NOT EXISTS (... request_date < t)` |
| `sub` | kỳ thuê bao đang hiệu lực tại t | `ASOF LEFT JOIN ... p.t >= s.start_date`: kỳ gần nhất bắt đầu ≤ t |
| `fee` | giá tại t và giá **cùng gói** 90 ngày trước | ASOF JOIN hai lần vào bảng giá theo ngày hiệu lực |
| `use` | data, TV, phút mất mạng tháng m1; trung bình data 3 tháng m2–m4 | chỉ `u.month < t` (tháng đã chốt số liệu) |
| `tix` | ticket theo cửa sổ 30/60/90 ngày, ticket còn mở, CSAT thấp nhất, ngày từ ticket gần nhất | `logged_at < t`; bỏ "Yêu cầu hủy"; "còn mở tại t" = chưa xử lý **hoặc** xử lý sau t |
| `pay` | số kỳ trễ/chưa trả, đang nợ tại t, số ngày trễ tối đa, số lần hoàn tiền | hoá đơn phát hành trước t; trả sau t nghĩa là **tại t vẫn đang nợ** |
| `lab` | nhãn: yêu cầu hủy hoàn tất trong `[t, t + 30 ngày)` | phần duy nhất nhìn vào tương lai, và đúng là phải nhìn |

Một vài chỗ đáng đọc chậm:

- **Mọi CTE đều xuất phát từ `pop`** (`FROM pop p LEFT JOIN ...`, rồi `GROUP BY ALL`). Khách không có ticket nào vẫn
  có dòng với `tickets_30d = 0`. `count(k.ticket_id)` không đếm NULL.
- **`FILTER (WHERE ...)`** tính nhiều cửa sổ trong **một** lần quét: 30, 60, 90 ngày trên cùng một JOIN 180 ngày.
- **`open_tickets`**: `resolved_at IS NULL OR resolved_at >= p.t`. Ticket được xử lý *sau* t thì *tại* t vẫn đang
  mở. Viết `resolved_at IS NULL` thôi thì dùng thông tin tương lai: ticket xử lý ngày t+3 bị coi là "đã xử lý" tại t.
- **`min_csat_90d`** chỉ lấy CSAT của ticket **đã xử lý trước t**, vì khách chấm điểm sau khi ticket được xử lý.
- **`max_days_late_90d`**: `least(coalesce(paid_date, t), t) − due_date`. Chưa trả, hoặc trả sau t, thì tính tới t.
- **`round(avg(...), 4)`**: DuckDB cộng số thực song song, nên thứ tự cộng khác nhau giữa các lần chạy, làm lệch ở
  chữ số thứ 13. Làm tròn để bảng học giống hệt từng bit mỗi lần dựng. Nhờ vậy mã băm dữ liệu ở bài A7 ổn định
  (có test riêng).
- **`days_to_contract_end`** chỉ có giá trị khi có hợp đồng (`CASE WHEN contract_months > 0`), khách không kỳ hạn
  để NULL.

**File: `src/churn_telco/features.py` · `TABLES…connect`**

```python
TABLES = ["customers", "subscriptions", "plans", "plan_prices", "invoices", "usage", "tickets", "cancellations"]


def connect(interim: Path = config.INTERIM) -> duckdb.DuckDBPyConnection:
    """Một kết nối DuckDB trong bộ nhớ; mỗi bảng sạch là một view đọc thẳng file parquet (không nạp hết vào RAM)."""
    con = duckdb.connect()
    con.execute("SET enable_progress_bar = false")
    for name in TABLES:
        con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{interim / name}.parquet')")
    return con
```

`connect` tạo 8 **view** trỏ thẳng vào file parquet. DuckDB chỉ đọc những cột và dòng truy vấn cần, nên không phải
nạp cả 480.000 hoá đơn vào RAM pandas.

**File: `src/churn_telco/features.py` · `connect_as_of`**

```python
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
```

Đây là "cỗ máy thời gian" của mục 1.5: cùng 8 view, nhưng mỗi bảng bị cắt về trạng thái tại t.

- `WHERE logged_at < t`, `WHERE issued_date < t`… bỏ dòng chưa vào hệ thống.
- `SELECT * REPLACE (CASE WHEN paid_date < t THEN paid_date END AS paid_date)`: giữ mọi cột nhưng **xoá** ngày trả
  nếu nó sau t. `REPLACE` là cú pháp DuckDB thay một cột trong `SELECT *`.
- `csat` bị xoá theo `resolved_at`: điểm hài lòng chỉ có sau khi ticket được xử lý.

Hàm này không dùng để train. Nó chỉ dùng để **kiểm tra** (test và lab).

**File: `src/churn_telco/features.py` · `build`**

```python
def build(con: duckdb.DuckDBPyConnection, snapshots: Sequence[pd.Timestamp] = config.SNAPSHOTS) -> pd.DataFrame:
    con.register("snapshots", pd.DataFrame({"t": pd.to_datetime(list(snapshots))}))
    df = con.execute(FEATURE_SQL).df()
    df["t"] = pd.to_datetime(df["t"])
    for col in CATEGORICAL:
        df[col] = df[col].astype("category")
    df[NUMERIC] = df[NUMERIC].astype("float64")  # một kiểu số duy nhất, NaN = thiếu (sklearn và LightGBM đều hiểu)
    df[LABEL] = df[LABEL].astype("int64")
    return df
```

`build` nhận **bất kỳ kết nối nào**: đầy đủ, chụp tại t, hoặc dữ liệu nhỏ trong test. Nhờ vậy cùng một câu SQL phục vụ
cả train, chấm điểm thật (bài A6) lẫn kiểm tra. Sau khi lấy kết quả: categorical thành kiểu `category` (LightGBM tự
xử lý), mọi feature số thành `float64` (NaN = thiếu, sklearn và LightGBM đều hiểu), nhãn thành `int64`.

**File: `src/churn_telco/features.py` · `build_all…__main__`**

```python
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
```

- `build_all` kiểm tra **trước** (bảng sạch) và **sau** (bảng học + phân phối từng tháng), rồi mới ghi file. Hỏng
  thì dừng, file cũ không bị ghi đè bằng dữ liệu xấu. Import `schemas` nằm trong hàm để module không phụ thuộc vòng.
- `load` ghép bảng học với các khối feature bổ sung `features_*.parquet` (bài A6 thêm khối marketing).
  `validate="one_to_one"` làm pandas **báo lỗi** nếu khoá bị trùng ở bất kỳ bên nào, thay vì lặng lẽ nhân bản dòng.
  Đây là tiêu chí "không sinh dòng trùng sau khi ghép" của DATA-02.

### A4.2 `schemas.py` — hợp đồng dữ liệu

**File: `src/churn_telco/schemas.py` · `đầu file…DataQualityError`**

```python
"""Hợp đồng dữ liệu (A4 · DATA-05): pipeline TỰ DỪNG với thông báo rõ ràng khi dữ liệu sai schema hoặc lệch mạnh.

Hai tầng kiểm tra:
- Schema (pandera): kiểu, khoảng giá trị, tập giá trị cho phép, khoá không trùng — kiểm tra từng dòng.
- Phân phối (`check_snapshots`): số khách và tỷ lệ churn từng tháng không được lệch bất thường — kiểm tra cả bảng.

Cột ngày giờ chỉ kiểm tra "là kiểu ngày giờ": pandas 3 giữ đơn vị của nguồn (ms/us/ns), ép một đơn vị là sai vặt.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pandera.pandas as pa

from churn_telco.clean import CANONICAL_PROVINCES, PII_COLUMNS, TICKET_CATEGORIES

PLAN_CODES = ["SX50", "SX150", "SX300", "SX150TV", "SX300TV", "COMBO"]
SEGMENTS = ["Hộ gia đình", "Doanh nghiệp nhỏ"]
CHANNELS = ["Cửa hàng", "Online", "Đại lý", "Không rõ"]
PAYMENTS = ["Tiền mặt tại điểm", "Chuyển khoản", "Ví điện tử", "Tự động trừ thẻ"]


class DataQualityError(ValueError):
    """Dữ liệu đầu vào không đạt — dừng pipeline thay vì train/chấm điểm trên dữ liệu hỏng."""
```

Một lớp lỗi riêng (`DataQualityError`) để code gọi phân biệt được "dữ liệu hỏng" với lỗi lập trình.

**File: `src/churn_telco/schemas.py` · `_datetime…validate_clean`**

```python
def _datetime(nullable: bool = False) -> pa.Column:
    is_dt = pa.Check(pd.api.types.is_datetime64_any_dtype, error="không phải kiểu ngày giờ")
    return pa.Column(checks=is_dt, nullable=nullable)


CUSTOMERS = pa.DataFrameSchema(
    {
        "customer_id": pa.Column(str, unique=True),  # sau khử trùng: mỗi khách một dòng
        "province": pa.Column(str, pa.Check.isin(CANONICAL_PROVINCES)),
        "segment": pa.Column(str, pa.Check.isin(SEGMENTS)),
        "channel": pa.Column(str, pa.Check.isin(CHANNELS)),
        "signup_date": _datetime(),
        "date_of_birth": _datetime(nullable=True),
    },
    checks=[
        pa.Check(lambda df: not set(PII_COLUMNS) & set(df.columns), error="còn cột PII (tên, điện thoại, email)"),
        pa.Check(lambda df: df["date_of_birth"].dropna().gt("1930-01-01").all(), error="còn ngày sinh mặc định 1900"),
    ],
    name="customers",
)
TICKETS = pa.DataFrameSchema(
    {
        "ticket_id": pa.Column(str, unique=True),
        "category": pa.Column(str, pa.Check.isin(TICKET_CATEGORIES)),
        "created_at": _datetime(),
        "logged_at": _datetime(),
        "csat": pa.Column(float, pa.Check.in_range(1, 5), nullable=True),
    },
    checks=pa.Check(lambda df: df["logged_at"] >= df["created_at"], error="ticket vào hệ thống trước khi được tạo"),
    name="tickets",
)
INVOICES = pa.DataFrameSchema(
    {"invoice_id": pa.Column(str, unique=True), "amount": pa.Column(float), "is_adjustment": pa.Column(bool)},
    checks=pa.Check(lambda df: (df["amount"] > 0) | df["is_adjustment"], error="hoá đơn thường có số tiền <= 0"),
    name="invoices",
)
USAGE = pa.DataFrameSchema(
    {"data_gb": pa.Column(float, pa.Check.gt(0)), "outage_minutes": pa.Column(float, pa.Check.ge(0))},
    unique=["customer_id", "month"],  # một khách một dòng mỗi tháng
    name="usage",
)
CLEAN = {"customers": CUSTOMERS, "tickets": TICKETS, "invoices": INVOICES, "usage": USAGE}


def validate_clean(interim: Path) -> None:
    """Kiểm tra các bảng đã làm sạch; gom MỌI lỗi (lazy=True) rồi mới báo, để sửa một lần."""
    for name, schema in CLEAN.items():
        try:
            schema.validate(pd.read_parquet(interim / f"{name}.parquet"), lazy=True)
        except pa.errors.SchemaErrors as err:
            raise DataQualityError(f"Bảng sạch '{name}' không đạt:\n{err.failure_cases.head(20)}") from err
```

- Mỗi `pa.Column` khai báo kiểu, kiểm tra và có được thiếu hay không. Kiểm tra cả bảng (`checks=` của
  `DataFrameSchema`) dùng cho quy tắc nhiều cột: `logged_at >= created_at`, không còn cột PII.
- `lazy=True` gom **mọi** lỗi rồi mới báo, để sửa một lần thay vì sửa xong lỗi này mới thấy lỗi khác.
- `_datetime()` chỉ kiểm tra "là kiểu ngày giờ" chứ không ép đơn vị (pandas 3 giữ `ms`/`us`/`ns` theo nguồn).

**File: `src/churn_telco/schemas.py` · `FEATURES…check_snapshots`**

```python
FEATURES = pa.DataFrameSchema(
    {
        "t": _datetime(),
        "customer_id": pa.Column(str),
        "segment": pa.Column("category", pa.Check.isin(SEGMENTS)),
        "channel": pa.Column("category", pa.Check.isin(CHANNELS)),
        "province": pa.Column("category", pa.Check.isin(CANONICAL_PROVINCES)),
        "plan_code": pa.Column("category", pa.Check.isin(PLAN_CODES)),
        "payment_method": pa.Column("category", pa.Check.isin(PAYMENTS)),
        "tenure_days": pa.Column(float, pa.Check.ge(1)),  # khách vào mạng trước t ít nhất 1 ngày
        "age": pa.Column(float, pa.Check.in_range(16, 100), nullable=True),
        "monthly_fee": pa.Column(float, pa.Check.in_range(100_000, 1_000_000)),
        "fee_change_90d": pa.Column(float, pa.Check.in_range(-0.5, 0.5)),
        "contract_months": pa.Column(float, pa.Check.isin([0, 12, 24])),
        "days_to_contract_end": pa.Column(float, pa.Check.in_range(0, 730), nullable=True),
        "data_gb_m1": pa.Column(float, pa.Check.gt(0), nullable=True),
        "usage_ratio": pa.Column(float, pa.Check.gt(0), nullable=True),
        "outage_m1": pa.Column(float, pa.Check.ge(0), nullable=True),
        "tickets_30d": pa.Column(float, pa.Check.ge(0)),
        "open_tickets": pa.Column(float, pa.Check.ge(0)),
        "min_csat_90d": pa.Column(float, pa.Check.in_range(1, 5), nullable=True),
        "unpaid_at_t": pa.Column(float, pa.Check.ge(0)),
        "max_days_late_90d": pa.Column(float, pa.Check.ge(0), nullable=True),
        "churn_30d": pa.Column(int, pa.Check.isin([0, 1])),
    },
    unique=["t", "customer_id"],  # một khách chỉ có một dòng mỗi ngày chấm điểm — nếu trùng là JOIN sai
    name="features",
)


def check_snapshots(df: pd.DataFrame, max_size_change: float = 0.25, churn_range: tuple = (0.003, 0.15)) -> None:
    """Kiểm tra phân phối theo từng ngày chấm điểm: số khách và tỷ lệ churn nằm trong khoảng hợp lý."""
    per_t = df.groupby("t").agg(n=("customer_id", "size"), churn=("churn_30d", "mean"))
    size_dev = per_t["n"] / per_t["n"].median() - 1
    problems = [
        f"{t:%Y-%m}: {row.n} khách, lệch {dev:+.0%} so với trung vị"
        for (t, row), dev in zip(per_t.iterrows(), size_dev, strict=True)
        if abs(dev) > max_size_change
    ]
    problems += [
        f"{t:%Y-%m}: tỷ lệ churn {row.churn:.2%} ngoài khoảng {churn_range[0]:.1%}–{churn_range[1]:.0%}"
        for t, row in per_t.iterrows()
        if not churn_range[0] <= row.churn <= churn_range[1]
    ]
    if problems:
        raise DataQualityError("Bảng học lệch phân phối bất thường:\n  " + "\n  ".join(problems))
```

- `unique=["t", "customer_id"]`: một khách chỉ có một dòng mỗi ngày chấm điểm. Trùng thì gần như chắc chắn có một JOIN
  sai.
- Khoảng giá trị là **kiến thức nghiệp vụ** viết thành code: giá tăng quá ±50% trong 90 ngày, tuổi ngoài 16–100, hợp
  đồng khác 0/12/24 tháng. Những trường hợp đó phải dừng lại hỏi.
- `check_snapshots` bắt lỗi mà kiểm tra từng dòng không thấy. Nếu một tháng thiếu 2/3 khách (job export chạy dở), từng
  dòng vẫn hợp lệ nhưng cả bảng thì sai.

### A4.3 Dựng bảng học

```bash
make features
```

```text
INFO __main__: features.parquet: 359908 dòng × 36 cột, tỷ lệ churn 2.10%
```

Xem ba tháng gần nhất của khách `KH000113` (khách đứng đầu danh sách gọi tháng 01/2026 ở bài A6):

```text
         t customer_id plan_code  contract_months  days_to_contract_end  tenure_days  data_gb_m1  data_gb_m2_m4  usage_ratio  late_or_unpaid_90d  churn_30d
2025-10-01    KH000113     SX300             12.0                  92.0       1951.0       292.2       221.7667     1.317601                 0.0          0
2025-11-01    KH000113     SX300             12.0                  61.0       1982.0       280.5       246.5667     1.137623                 0.0          0
2025-12-01    KH000113     SX300             12.0                  31.0       2012.0       218.8       271.7000     0.805300                 1.0          0
```

Mỗi tháng `days_to_contract_end` giảm ~30 ngày, `tenure_days` tăng ~30. Tháng 12, lượng data giảm còn 80% mức thường
và có một kỳ trả trễ. Bảng học "kể chuyện" từng khách theo thời gian, đúng như thiết kế.

Tỷ lệ giá trị thiếu cũng là thông tin:

```text
days_to_contract_end      0.607    ← 61% khách không có hợp đồng kỳ hạn
tv_hours_m1               0.613    ← khách không dùng gói TV
min_csat_90d              0.756    ← 3/4 khách không có ticket nào được chấm điểm trong 90 ngày
days_since_last_ticket    0.374    ← không có ticket trong 180 ngày
usage_ratio               0.039    ← khách mới (chưa đủ 4 tháng) hoặc thiếu số đo
```

### A4.4 Test — chứng minh bảng học đúng thời điểm

**File: `tests/test_features.py` · `đầu file…test_point_in_time_catches_created_at_leak`**

```python
"""A4: bảng học đúng thời điểm. Test quan trọng nhất của dự án là `test_point_in_time`: dựng lại feature tại t từ dữ
liệu đã bị CẮT về đúng những gì hệ thống biết tại t — kết quả phải giống hệt bản dựng từ dữ liệu đầy đủ. Feature nào
lén dùng thông tin sau t sẽ cho giá trị khác và test đỏ.
"""

import pandas as pd
import pandera.pandas as pa
import pytest

from churn_telco import features, schemas
from churn_telco.features import KEYS, LABEL, META


def feature_part(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=[LABEL, *META]).set_index(KEYS).sort_index()


@pytest.mark.parametrize("t", ["2024-11-01", "2025-06-01", "2025-12-01"])
def test_point_in_time(small, t):
    t = pd.Timestamp(t)
    full = features.build(features.connect(small.interim), [t])
    as_of = features.build(features.connect_as_of(small.interim, t), [t])
    pd.testing.assert_frame_equal(feature_part(full), feature_part(as_of), check_categorical=False)


def test_point_in_time_catches_created_at_leak(small, monkeypatch):
    """Lọc ticket theo created_at (lúc khách gọi) thay vì logged_at (lúc vào hệ thống) — test phải bắt được."""
    monkeypatch.setattr(features, "FEATURE_SQL", features.FEATURE_SQL.replace("logged_at", "created_at"))
    t = pd.Timestamp("2025-06-01")
    full = features.build(features.connect(small.interim), [t])
    as_of = features.build(features.connect_as_of(small.interim, t), [t])
    with pytest.raises(AssertionError):
        pd.testing.assert_frame_equal(feature_part(full), feature_part(as_of), check_categorical=False)
```

- `test_point_in_time` chạy cho **ba** ngày ở ba giai đoạn khác nhau. `check_categorical=False` vì tập category có thể
  khác nhau (dữ liệu chụp tại t ít giá trị hơn) trong khi giá trị thì giống nhau.
- `test_point_in_time_catches_created_at_leak` là **test của test**. `monkeypatch` thay `logged_at` bằng `created_at`
  trong câu SQL, và test đúng thời điểm **phải đỏ**. Một test chưa từng đỏ thì chưa chứng minh được nó bắt lỗi.

Ba test khác giữ ba quy tắc:

**File: `tests/test_features.py` · `test_label_matches_cancellations…test_cancel_request_tickets_are_not_features`**

```python
def test_label_matches_cancellations(small):
    done = small.clean["cancellations"].query("status == 'Hoàn tất'")[["customer_id", "request_date"]]
    df = small.df[KEYS + [LABEL]].merge(done, on="customer_id", how="left")
    in_window = (df["request_date"] >= df["t"]) & (df["request_date"] < df["t"] + pd.Timedelta(days=30))
    assert (in_window.astype(int) == df[LABEL]).all()


def test_revoked_cancellation_is_not_churn(small):
    revoked = small.clean["cancellations"].query("status == 'Đã hoàn tác'")["customer_id"]
    finished = small.clean["cancellations"].query("status == 'Hoàn tất'")["customer_id"]
    only_revoked = set(revoked) - set(finished)
    assert only_revoked
    assert small.df.loc[small.df["customer_id"].isin(only_revoked), LABEL].sum() == 0


def test_cancel_request_tickets_are_not_features(small):
    """tickets_30d không đếm ticket "Yêu cầu hủy" — nếu đếm, đó là proxy của nhãn."""
    t = pd.Timestamp("2025-06-01")
    tickets = small.clean["tickets"]
    window = tickets[(tickets["logged_at"] < t) & (tickets["logged_at"] >= t - pd.Timedelta(days=30))]
    got = small.df[small.df["t"] == t].set_index("customer_id")["tickets_30d"]
    expected = window[window["category"] != "Yêu cầu hủy"].groupby("customer_id").size()
    pd.testing.assert_series_equal(got, expected.reindex(got.index, fill_value=0).astype(float), check_names=False)
```

Nhãn được kiểm bằng một cách tính **độc lập**: pandas thay vì SQL. Hai cách viết khác nhau cho cùng kết quả thì khó
cùng sai. Còn test kiểm tra hợp đồng dữ liệu thì *cố tình làm hỏng* dữ liệu và đòi pipeline phải dừng:

**File: `tests/test_features.py` · `test_schema_rejects_duplicated_rows…test_validate_clean_rejects_pii`**

```python
def test_schema_rejects_duplicated_rows(small):
    broken = pd.concat([small.df.head(100), small.df.head(1)], ignore_index=True)  # như một JOIN nhân đôi dòng
    with pytest.raises(pa.errors.SchemaErrors):
        schemas.FEATURES.validate(broken, lazy=True)


def test_schema_rejects_out_of_range_values(small):
    broken = small.df.head(100).copy()
    broken.loc[broken.index[0], "fee_change_90d"] = 3.0  # giá tăng 300%: gần như chắc chắn là lỗi dữ liệu
    with pytest.raises(pa.errors.SchemaErrors, match="fee_change_90d"):
        schemas.FEATURES.validate(broken, lazy=True)


def test_snapshot_check_detects_missing_month_of_data(small):
    df = small.df
    last = df["t"].max()
    broken = df[(df["t"] != last) | (df["customer_id"] < "KH001000")]  # tháng cuối mất 2/3 khách
    with pytest.raises(schemas.DataQualityError, match=f"{last:%Y-%m}"):
        schemas.check_snapshots(broken)


def test_validate_clean_rejects_pii(small, tmp_path):
    for name in schemas.CLEAN:
        pd.read_parquet(small.interim / f"{name}.parquet").to_parquet(tmp_path / f"{name}.parquet")
    customers = pd.read_parquet(tmp_path / "customers.parquet").assign(phone="0900000000")
    customers.to_parquet(tmp_path / "customers.parquet")
    with pytest.raises(schemas.DataQualityError, match="PII"):
        schemas.validate_clean(tmp_path)
```

```bash
uv run pytest tests/test_features.py -q
```

```text
..............                                                           [100%]
```

### A4.5 Lab: cố tình gây rò rỉ, rồi bắt nó

**File: `labs/data-03-trung-cap-ro-ri-du-lieu/leakage_lab.py`**

```python
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
```

```bash
cd labs/data-03-trung-cap-ro-ri-du-lieu
uv run --project ../../projects/g1-churn-telco python leakage_lab.py
```

```text
1) Cùng model, chỉ khác feature (đánh giá trên valid):
   as-of đúng                   AUC 0.733 · PR-AUC 0.162
   + ticket toàn lịch sử (a)    AUC 0.876 · PR-AUC 0.314
   + trạng thái CRM (b)         AUC 0.974 · PR-AUC 0.493
   → Churn hành vi khó đoán: AUC 0,97 là dấu hiệu báo động, không phải thành công.

2) AUC của từng feature một mình (valid), 6 cao nhất:
   is_cancelled_crm           0.956  ← nghi rò rỉ
   cancel_tickets_all_time    0.821  ← nghi rò rỉ
   usage_ratio                0.634
   data_gb_m1                 0.599
   network_tickets_60d        0.586
   outage_m1                  0.579

3) Model có cột CRM: is_cancelled_crm chiếm 54% tổng gain, feature thứ hai chỉ 19%

4) Lọc theo created_at: 0.8% dòng có tickets_30d khác; AUC 0.732 (as-of đúng: 0.733)
   Test đúng thời điểm tại 2025-06-01, logged_at (đúng): 0 khách lệch → xanh
   Test đúng thời điểm tại 2025-06-01, created_at (sai): 93 khách lệch → ĐỎ

5) Chia ngẫu nhiên 80/20 trên cả 18 tháng: AUC 0.774 — một con số, không biết nó đúng cho tháng nào
   Backtest gốc 2025-01: học  6 tháng → AUC 3 tháng sau 0.761
   Backtest gốc 2025-04: học  9 tháng → AUC 3 tháng sau 0.777
   Backtest gốc 2025-07: học 12 tháng → AUC 3 tháng sau 0.733
   Backtest gốc 2025-10: học 15 tháng → AUC 3 tháng sau 0.788
   → Hiệu quả dao động theo giai đoạn (khuyến mãi của đối thủ, mùa bão...). Báo cáo dải này, không phải một số.
```

Đọc từng phần:

1. **"Quá đẹp".** Hai câu SQL trông vô hại đẩy AUC từ 0,73 lên 0,88 và 0,97. Câu (a) đếm cả ticket "Yêu cầu hủy" gọi
   *sau* t (70% khách rời có một ticket như vậy). Câu (b) dùng trạng thái *ngày export*. Không feature hành vi nào
   cho AUC 0,97 với churn, nên con số này là dấu hiệu báo động.
2. **AUC từng feature.** Feature hành vi mạnh nhất (`usage_ratio`) một mình chỉ đạt 0,63. Hai feature trên 0,8 là nghi
   phạm số một. Lấy ngưỡng 0,8 làm cảnh báo tự động là đủ thô mà vẫn hữu ích.
3. **Độ quan trọng dồn vào một feature** (54% so với 19%) là dấu hiệu thứ ba.
4. **Lỗi tinh vi: metric không bắt được.** Lọc theo `created_at` chỉ làm 0,8% dòng khác giá trị, AUC gần như y nguyên
   (0,732 so với 0,733). Không nhìn metric nào phát hiện được. Nhưng khi chạy thật, feature sẽ **lệch** so với lúc
   train (train/serve skew). Chỉ **test đúng thời điểm** bắt được: 93 khách lệch tại 01/06/2025.
5. **Backtest cuốn chiếu.** Đứng ở 4 thời điểm, mỗi lần chỉ học quá khứ và chấm 3 tháng sau đó: AUC dao động
   0,73–0,79. Tháng 07–09/2025 khó nhất (bài A6 sẽ tìm ra vì sao). Một con số chia ngẫu nhiên (0,774) che mất dải
   này. Báo cáo cho người dùng phải nói được "khoảng 0,73 tới 0,79 tuỳ giai đoạn".

> **Kết quả thật:** trên dữ liệu này, chia ngẫu nhiên không cho con số lạc quan hơn hẳn chia theo thời gian (bạn có
> thể tự kiểm tra ở bài tập 4). Lý do dùng chia theo thời gian ở đây không phải "ngẫu nhiên luôn lạc quan". Lý do là
> nó trả lời đúng câu hỏi "model chạy tháng sau sẽ ra sao", và cho thấy hiệu quả thay đổi theo giai đoạn.

---

## 3 · Kiểm tra kết quả

- [ ] `make features` chạy qua cả hai lớp kiểm tra và ghi `data/processed/features.parquet` (359.908 dòng).
- [ ] `uv run pytest tests/test_features.py` xanh; `test_point_in_time_catches_created_at_leak` chứng minh test đúng
      thời điểm biết bắt lỗi.
- [ ] Lab: bạn chỉ ra được cột gây AUC 0,97 bằng cả ba cách (quá đẹp, AUC từng feature, độ quan trọng).
- [ ] Bạn giải thích được vì sao lỗi `created_at` không làm đổi metric mà vẫn nguy hiểm (DATA-03 Trung cấp).

## 4 · Lỗi thường gặp

| Triệu chứng | Nguyên nhân | Cách sửa |
|---|---|---|
| AUC offline 0,9+, chạy thật tệ hẳn | feature dùng thông tin tương lai | test đúng thời điểm cho mọi feature |
| Số dòng bảng học tăng sau khi thêm một JOIN | JOIN một-nhiều không gom nhóm | `GROUP BY` về (t, customer_id); schema `unique` |
| "Khách đang có ticket mở" quá ít | `resolved_at IS NULL` bỏ qua ticket xử lý sau t | `resolved_at IS NULL OR resolved_at >= t` |
| Mã băm dữ liệu đổi dù không sửa gì | phép cộng số thực song song cho kết quả khác ở chữ số cuối | làm tròn kết quả `avg` trong SQL |
| Feature "trạng thái hiện tại" rất mạnh | cột snapshot của CRM tại ngày export | không dùng; chỉ dùng bảng có lịch sử theo thời gian |

## 5 · Bài tập

1. **(Cơ bản — DATA-04)** Thêm feature `days_since_plan_change` (số ngày từ lần đổi gói gần nhất). Đặt nó trong câu
   SQL theo đúng ba quy tắc, thêm vào `NUMERIC`, chạy lại test đúng thời điểm.
2. **(Cơ bản)** Thêm vào `FEATURES` một kiểm tra cho `usage_ratio` (> 0 và < 20). Viết test cố tình làm hỏng giá trị
   đó và đòi pipeline dừng.
3. **(Trung cấp — DATA-03)** Viết hàm tự động "báo động rò rỉ": với mọi cột số, tính AUC một mình trên valid; cột nào
   > 0,8 thì dừng pipeline kèm tên cột. Gắn vào `build_all`.
4. **(Trung cấp)** Đo lại "chia ngẫu nhiên vs chia theo thời gian" trên **cùng** giai đoạn 07–09/2025: train bằng 80%
   dòng của mọi tháng, chấm 20% dòng còn lại của 07–09/2025, so với model chỉ học quá khứ. Kết quả có như bạn đoán
   không? Giải thích vì sao.
5. **(Mở rộng)** Cột `status` của bảng yêu cầu hủy cũng "thay đổi theo thời gian": yêu cầu gửi ngày t−2 có thể bị
   hoàn tác ngày t+3. Tổng thể `pop` có đang dùng thông tin tương lai không? Ảnh hưởng lớn tới đâu?

---

**Tiếp theo:** [A5 · LightGBM, mất cân bằng và ngưỡng theo chi phí](a5-lightgbm-nguong-chi-phi.md). Có bảng học đúng
thời điểm rồi, giờ mới tới model mạnh hơn, và từ điểm số đi tới quyết định gọi ai.
