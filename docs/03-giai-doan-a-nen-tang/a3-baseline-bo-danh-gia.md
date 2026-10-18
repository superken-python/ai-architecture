# A3 · Baseline và bộ đánh giá cố định

**Tuần 3** · Kỹ năng: [ML-01](../02-skill-map/generated/mang/ml.md#ml-01) Cơ bản,
[BIZ-02](../02-skill-map/generated/mang/biz.md#biz-02) Cơ bản, [STAT-02](../02-skill-map/generated/mang/stat.md#stat-02) Cơ bản ·
Lab: [`labs/stat-02-co-ban-bootstrap/`](../../labs/stat-02-co-ban-bootstrap/README.md) ·
Sản phẩm: `make eval` in metric của các baseline kèm khoảng tin cậy bootstrap

Thứ tự đúng của một dự án ML là: **đóng băng bộ đánh giá → đo cách làm hiện tại → thử baseline rẻ nhất → mới tới model
"xịn"**. Làm ngược lại, bạn sẽ chọn model trên chính tập dùng để báo cáo, so với một baseline yếu tự đặt ra, và báo
cáo một con số không có sai số. Đó là ba cách phổ biến nhất để tự lừa mình.

**Sau bài này bạn làm được:**

- Chia dữ liệu theo thời gian thành train / valid / test, và đóng băng tập test bằng manifest có mã băm.
- Chọn metric đúng cho bài toán xếp hạng có năng lực giới hạn: AUC, PR-AUC, precision@k và recall@k theo tháng.
- Dựng bậc thang baseline: ngẫu nhiên → luật nghiệp vụ → luật phân tích → logistic regression trong một `Pipeline`.
- Tính khoảng tin cậy bootstrap theo khách và so hai model bằng chênh lệch cặp.

---

## 1 · Lý thuyết: ba tập dữ liệu và việc của từng tập

### 1.1 Mỗi tập một việc — không dùng lẫn

| Tập | Tháng (ngày chấm điểm) | Dùng để | Không được dùng để |
|---|---|---|---|
| **train** | 07/2024 → 06/2025 | học tham số của model | đánh giá |
| **valid** | 07/2025 → 09/2025 | chọn số vòng (early stopping), hiệu chỉnh xác suất, chọn ngưỡng, phân tích lỗi | báo cáo con số cuối |
| **test — đóng băng** | 10/2025 → 12/2025 | so các phương án **đã chốt** và báo cáo | chọn tham số, "soi lỗi", thử ý tưởng |

Tập test giống đề thi cuối kỳ. Nếu xem đề rồi sửa bài, điểm số không còn nói lên năng lực thật. Mỗi lần bạn nhìn kết
quả trên test rồi đổi gì đó, tập test "rò" một chút vào model. Sau vài chục lần, con số báo cáo lạc quan hơn thực tế
(lab ở mục A3.6 đo hiệu ứng này).

### 1.2 Chia theo thời gian, không chia ngẫu nhiên

Model sẽ chạy ngày 1 hằng tháng, dùng dữ liệu *quá khứ* để đoán *tháng tới*. Đánh giá cũng phải mô phỏng đúng như vậy:
học các tháng trước, chấm các tháng sau.

```text
ngày chấm điểm t:  2024-07 ......... 2025-06 | 2025-07 .. 2025-09 | 2025-10 .. 2025-12 | 2026-01
                   ├──────── train ────────┤ ├───── valid ──────┤ ├── test (đóng băng) ─┤   chấm thật
nhãn của t:        [t, t+30 ngày) — nhãn của t = 2025-06-01 kết thúc trước 2025-07-01: không chồng lên valid
```

Chia ngẫu nhiên thì các tháng bị trộn: model học tháng 9 rồi được chấm tháng 8. Hơn nữa, **hiệu quả của model dao
động theo giai đoạn** (đợt khuyến mãi của đối thủ, mùa bão). Một con số chia ngẫu nhiên che mất sự dao động đó. Bài A4
đo điều này bằng backtest cuốn chiếu.

### 1.3 Đóng băng = ghi lại chính xác tập test là gì

"Tập test = 3 tháng cuối" chưa đủ chặt. Nếu tuần sau ai đó sửa cách tính nhãn hoặc cách lọc khách, "3 tháng cuối" đã
là một tập khác, và mọi so sánh với kết quả cũ trở nên vô nghĩa. Vì vậy ta ghi một **manifest** và commit nó:

```json
{
  "rule": "t > 2025-09-01 (3 tháng cuối có nhãn)",
  "snapshots": ["2025-10-01", "2025-11-01", "2025-12-01"],
  "rows": 60912,
  "customers": 21246,
  "positives": 1386,
  "sha256": "5e768609de8badd13cffc938b3eb12cb0eda2adcb9b9f898b74b39af17b4f85f"
}
```

`sha256` là mã băm của toàn bộ (ngày, mã khách, nhãn) đã sắp xếp. Đổi **một** nhãn thì mã băm đổi hoàn toàn. Mọi lần
đánh giá đều tính lại mã băm và so với manifest; lệch thì dừng. Đóng băng làm **trước khi** nhìn kết quả của bất kỳ
model nào.

---

## 2 · Lý thuyết: baseline

### 2.1 Bậc thang baseline

| Bậc | Baseline | Trả lời câu hỏi |
|---|---|---|
| 0 | **Ngẫu nhiên** | Sàn: precision@500 ≈ tỷ lệ nền. Thấp hơn mức này là code có lỗi |
| 1 | **Luật CSKH hiện tại** — sắp hết hợp đồng, báo lỗi mạng, không kỳ hạn, trả trễ | Model có hơn *cách đang làm* không? Đây là con số nghiệp vụ quan tâm |
| 2 | **Luật của người phân tích** — dùng ít đi nhiều nhất xếp trước (nhận xét 4 ở bài A2) | Một luật một dòng, rút ra từ EDA, đã đủ chưa? |
| 3 | **Logistic regression** dùng mọi feature | Một model tuyến tính đơn giản đạt tới đâu? Đây là **tham chiếu** cho model phức tạp |

Mỗi bậc rẻ hơn bậc sau. Model phức tạp (LightGBM ở bài A5) chỉ đáng dùng nếu nó vượt bậc 3 một cách **có ý nghĩa
thống kê**. Nếu chênh lệch nằm trong sai số, logistic regression thắng vì dễ hiểu, dễ vận hành.

### 2.2 `Pipeline` — tiền xử lý cũng là một phần của model

Logistic regression cần dữ liệu số, không thiếu, cùng thang đo. Ta cần ba bước:

- biến phân loại (tỉnh, gói…) → **one-hot**;
- giá trị thiếu → **điền trung vị**, kèm cột cờ "đã thiếu" (`add_indicator=True`), vì thiếu cũng là thông tin. Ví dụ
  khách không có hợp đồng thì `days_to_contract_end` thiếu;
- **chuẩn hoá** về trung bình 0, độ lệch 1.

Tham số của các bước này (trung vị, trung bình, danh sách category) phải học **chỉ từ train**. Nếu tính trung vị trên
cả bảng rồi mới chia, thông tin của tập test đã lọt vào train: đó là một dạng rò rỉ. Gói mọi bước vào một
`Pipeline`, thì `fit(train)` học tất cả trên train, và `predict(test)` chỉ *áp dụng*. Bài này có test kiểm tra đúng
điều đó.

---

## 3 · Lý thuyết: metric khi năng lực có hạn

### 3.1 Bốn metric và ý nghĩa của chúng

- **AUC**: chọn ngẫu nhiên một khách rời và một khách ở lại, xác suất model xếp khách rời *cao hơn*. Ngẫu nhiên = 0,5.
  AUC đo **cả** bảng xếp hạng, kể cả phần cuối danh sách mà ta không bao giờ gọi tới.
- **PR-AUC (average precision)**: trung bình precision tại mỗi vị trí có một khách rời. Ngẫu nhiên = **tỷ lệ nền**
  (~0,02), không phải 0,5. PR-AUC nhạy với phần đầu danh sách, phù hợp sự kiện hiếm hơn AUC.
- **precision@500**: trong 500 khách điểm cao nhất của tháng, tỷ lệ thật sự rời. Đây là metric chính, gắn trực tiếp với
  tiền (bài A1).
- **recall@500**: trong tất cả khách rời của tháng, tỷ lệ nằm trong top 500. Mỗi tháng có khoảng 470 khách rời,
  nên một model hoàn hảo đạt recall@500 = 1 với precision@500 ≈ 0,94. Thực tế còn rất xa mức đó.

Precision và recall@k tính **từng tháng rồi lấy trung bình**, vì danh sách gọi được lập từng tháng.

### 3.2 Ví dụ tính tay

10 khách đã xếp theo điểm giảm dần; khách rời (1) ở vị trí 1, 3, 8:

| Vị trí | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Nhãn | **1** | 0 | **1** | 0 | 0 | 0 | 0 | **1** | 0 | 0 |

- **precision@3** = 2/3, **recall@3** = 2/3.
- **AUC**: có 3 × 7 = 21 cặp (rời, ở lại). Khách vị trí 1 đứng trên cả 7 khách ở lại; vị trí 3 đứng trên 6 (thua vị
  trí 2); vị trí 8 đứng trên 2 (vị trí 9, 10). AUC = (7 + 6 + 2)/21 = **0,714**.
- **Average precision** = trung bình precision tại vị trí của từng khách rời = (1/1 + 2/3 + 3/8)/3 = **0,681**.

`sklearn.metrics.roc_auc_score` và `average_precision_score` cho đúng 0,714 và 0,681. Module `metrics.py` bên dưới
cũng phải cho đúng các số đó (có test).

---

## 4 · Lý thuyết: một con số đánh giá luôn đi kèm sai số

### 4.1 Khoảng tin cậy cho một tỷ lệ

precision@500 trên 3 tháng là một tỷ lệ trên n = 1.500 lần gọi. Với p = 0,255, sai số chuẩn ≈ √(p(1−p)/n) = 0,0113.
Khoảng tin cậy 95% ≈ p ± 1,96 × 0,0113 = **0,255 ± 0,022**. Hai model chênh nhau 0,01 trên tập này là chưa nói được gì.

### 4.2 Bootstrap — khi không có công thức

AUC, PR-AUC, precision@k theo tháng không có công thức sai số gọn. **Bootstrap** ước lượng sai số bằng mô phỏng:

1. Rút lại tập đánh giá **có hoàn lại**, cùng kích thước: có dòng được rút 2–3 lần, có dòng không được rút.
2. Tính metric trên mẫu vừa rút.
3. Lặp 1.000 lần. Khoảng giữa phân vị 2,5% và 97,5% của 1.000 giá trị là khoảng tin cậy 95%.

**Rút theo đơn vị độc lập.** Một khách có tới 3 dòng (3 tháng) trong tập test, và các dòng của cùng một khách không độc
lập với nhau. Ta rút **khách**, không rút dòng: khách được rút 2 lần thì mọi dòng của khách đó có trọng số 2. Lab
(mục A3.6) cho thấy rút sai đơn vị làm khoảng tin cậy hẹp giả tạo.

### 4.3 So hai model: chênh lệch cặp

Hai khoảng tin cậy chồng nhau **không** có nghĩa là hai model như nhau. Hai model được chấm trên **cùng** các khách,
nên phần dao động do "khách nào lọt vào mẫu" là chung. Cách đúng: ở mỗi vòng bootstrap, tính metric của **cả hai**
model trên cùng mẫu, lấy hiệu số; khoảng tin cậy của 1.000 hiệu số là KTC của chênh lệch. KTC không chứa 0 thì chênh
lệch có ý nghĩa.

### 4.4 Lời nguyền người thắng

Thử 100 phương án rồi giữ cái tốt nhất trên tập đánh giá: con số của "người thắng" bị thổi phồng, vì nó thắng một phần
nhờ may. Phòng tránh bằng ba việc: chốt **một** metric chính từ trước (precision@500); thử ý tưởng trên **valid**;
và chỉ mang **vài** phương án đã chốt sang tập đóng băng.

---

## 5 · Lab A3

### A3.0 Chuẩn bị: bảng học

Đánh giá cần một **bảng học**: mỗi dòng là (ngày chấm điểm t, khách), gồm feature tính từ dữ liệu trước t và nhãn
`churn_30d` (khách gửi yêu cầu hủy trong 30 ngày kể từ t). Dựng bảng này *đúng thời điểm* là toàn bộ nội dung của bài
A4. Ở bài này, hãy chép
[`features.py`](../../projects/g1-churn-telco/src/churn_telco/features.py) và
[`schemas.py`](../../projects/g1-churn-telco/src/churn_telco/schemas.py) từ repo và dùng chúng như một hộp đen, giống
`simulate.py` ở bài A2.

```bash
make features
```

```text
INFO __main__: features.parquet: 359908 dòng × 36 cột, tỷ lệ churn 2.10%
```

Hai thứ bạn cần biết về bảng này lúc này: khoá là (`t`, `customer_id`), nhãn là `churn_30d`. Danh sách feature nằm
trong `features.CATEGORICAL` và `features.NUMERIC`.

### A3.1 `split.py` — chia theo thời gian và đóng băng

**File: `src/churn_telco/split.py` · `đầu file`**

```python
"""Chia theo thời gian và đóng băng bộ đánh giá (A3 · BIZ-02, ML-01).

- train ≤ 2025-06 (học) · valid 2025-07..09 (early stopping, hiệu chỉnh, chọn ngưỡng) · test 2025-10..12 (đóng băng).
- Chia theo THỜI GIAN chứ không ngẫu nhiên: model sẽ chấm điểm tháng sau bằng dữ liệu tháng trước, nên đánh giá cũng
  phải "học quá khứ, đoán tương lai".
- "Đóng băng" = ghi manifest (danh sách tháng, số dòng, số ca churn, mã băm của khoá + nhãn) vào eval/manifest.json và
  commit. Lần đánh giá nào cũng kiểm tra lại mã băm: ai sửa pipeline làm đổi tập test thì `make eval` báo lỗi ngay.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from churn_telco import config
from churn_telco.features import KEYS, LABEL
```

**File: `src/churn_telco/split.py` · `MANIFEST…split`**

```python
MANIFEST = config.EVAL_DIR / "manifest.json"


def split(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    t = df["t"]
    return {
        "train": df[t <= config.TRAIN_END],
        "valid": df[(t > config.TRAIN_END) & (t <= config.VALID_END)],
        "test": df[t > config.VALID_END],
    }
```

`split` chỉ so sánh ngày, nhờ vậy ngắn và không thể sai. Ba điều kiện phủ kín mọi dòng và không chồng nhau. Test
`test_time_split_has_no_overlap` khẳng định đúng điều đó.

**File: `src/churn_telco/split.py` · `fingerprint…describe`**

```python
def fingerprint(df: pd.DataFrame) -> str:
    """Mã băm SHA-256 của (t, customer_id, nhãn) đã sắp xếp — đổi một dòng hay một nhãn là đổi mã."""
    rows = df[[*KEYS, LABEL]].sort_values(KEYS)
    payload = rows.assign(t=rows["t"].dt.strftime("%Y-%m-%d")).to_csv(index=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def describe(test: pd.DataFrame) -> dict:
    return {
        "rule": f"t > {config.VALID_END:%Y-%m-%d} (3 tháng cuối có nhãn)",
        "snapshots": sorted(test["t"].dt.strftime("%Y-%m-%d").unique().tolist()),
        "rows": len(test),
        "customers": int(test["customer_id"].nunique()),
        "positives": int(test[LABEL].sum()),
        "sha256": fingerprint(test),
    }
```

`fingerprint` chỉ băm **khoá + nhãn**, không băm feature. Ở bài A4 bạn sửa feature mà bộ đánh giá vẫn giữ nguyên.
Nhưng sửa cách chọn khách hay cách tính nhãn thì mã băm đổi. Sắp xếp theo khoá trước khi băm để thứ tự dòng không ảnh
hưởng. Ngày được đổi thành chuỗi `%Y-%m-%d` để mã băm không phụ thuộc đơn vị thời gian của pandas.

**File: `src/churn_telco/split.py` · `freeze…frozen_test`**

```python
def freeze(df: pd.DataFrame, path: Path = MANIFEST, force: bool = False) -> dict:
    """Ghi manifest của tập test. Đã có thì KHÔNG ghi đè (trừ khi force=True — tức là bạn cố ý đổi bộ đánh giá)."""
    if path.exists() and not force:
        raise FileExistsError(f"{path} đã có — bộ đánh giá đã đóng băng; dùng force=True nếu thật sự muốn đổi")
    manifest = describe(split(df)["test"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def frozen_test(df: pd.DataFrame, path: Path = MANIFEST) -> pd.DataFrame:
    """Tập test đã kiểm tra khớp manifest — mọi con số báo cáo đều đi qua hàm này."""
    test = split(df)["test"]
    expected = json.loads(path.read_text(encoding="utf-8"))
    actual = describe(test)
    if actual["sha256"] != expected["sha256"]:
        diff = {k: (expected[k], actual[k]) for k in ("rows", "customers", "positives") if expected[k] != actual[k]}
        raise ValueError(
            f"Tập test không khớp {path.name} (manifest, hiện tại): {diff or 'cùng số dòng, khác nội dung'}"
        )
    return test
```

- `freeze` **từ chối ghi đè** manifest có sẵn. Muốn đổi bộ đánh giá phải cố ý truyền `force=True`, và khi đó mọi kết
  quả cũ hết so sánh được. Đó là một quyết định cần ghi vào lịch sử dự án.
- `frozen_test` là **cổng duy nhất** để lấy tập test. Nó tính lại mô tả, so mã băm, và nếu lệch thì báo đúng chỗ lệch
  (số dòng, số khách, số ca churn) để biết ai đã đổi gì.

### A3.2 `metrics.py` — metric xếp hạng và bootstrap nhanh

**File: `src/churn_telco/metrics.py` · `đầu file`**

```python
"""Metric xếp hạng khi năng lực xử lý có hạn + khoảng tin cậy bootstrap theo khách (A3 · STAT-02, A5 · ML-03).

- AUC: xác suất một khách churn được xếp trên một khách không churn — đo cả bảng xếp hạng.
- PR-AUC (average precision): tập trung vào phần đầu bảng, nhạy với dữ liệu mất cân bằng hơn AUC.
- precision@k / recall@k: mỗi tháng CSKH gọi được k = 500 khách — trong 500 người đó bao nhiêu người thật sự sắp rời
  (precision), và bắt được bao nhiêu phần trong số người sắp rời (recall). Tính TỪNG THÁNG rồi lấy trung bình.

Bootstrap theo cụm: một khách xuất hiện ở nhiều tháng trong tập test nên các dòng không độc lập. Mỗi vòng bootstrap
rút lại KHÁCH (có hoàn lại); khách được rút n lần thì mọi dòng của khách đó có trọng số n. Thứ tự xếp hạng của mỗi
model chỉ tính một lần, mỗi vòng chỉ đổi trọng số — nên 1.000 vòng chạy trong vài giây.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from churn_telco import config
from churn_telco.features import LABEL
```

**File: `src/churn_telco/metrics.py` · `METRICS…rank`**

```python
METRICS = ["auc", "pr_auc", "p@k", "r@k", "f1@k"]


@dataclass(frozen=True)
class Ranked:
    """Một model trên một tập đánh giá: xếp hạng tính một lần, dùng lại cho mọi vòng bootstrap."""

    y: np.ndarray  # nhãn theo thứ tự dòng gốc
    order: np.ndarray  # chỉ số dòng theo điểm giảm dần (cả tập)
    last: np.ndarray  # vị trí cuối của mỗi nhóm điểm bằng nhau trong `order` — điểm hoà là một ngưỡng
    by_t: tuple[np.ndarray, ...]  # từng tháng: chỉ số dòng theo điểm giảm dần


def rank(score: np.ndarray, y: np.ndarray, t: np.ndarray) -> Ranked:
    score, y, t = np.asarray(score, float), np.asarray(y, int), np.asarray(t)
    order = np.argsort(-score, kind="stable")
    s = score[order]
    last = np.flatnonzero(np.r_[s[1:] != s[:-1], True])
    by_t = tuple(np.flatnonzero(t == m)[np.argsort(-score[t == m], kind="stable")] for m in np.unique(t))
    return Ranked(y, order, last, by_t)
```

Ý tưởng để bootstrap nhanh: **thứ tự xếp hạng không đổi** giữa các vòng, chỉ có *trọng số* của từng dòng đổi (khách
được rút 0, 1, 2… lần). Vì vậy ta sắp xếp **một lần** trong `rank`:

- `order`: chỉ số dòng theo điểm giảm dần.
- `last`: vị trí cuối của mỗi nhóm **điểm bằng nhau**. Các dòng điểm hoà phải được xét cùng lúc như một ngưỡng, nếu
  không AUC phụ thuộc thứ tự ngẫu nhiên của chúng. Luật CSKH cho rất nhiều khách cùng điểm, nên đây không phải chi
  tiết thừa.
- `by_t`: thứ tự riêng trong từng tháng, cho precision@k theo tháng.

**File: `src/churn_telco/metrics.py` · `evaluate`**

```python
def evaluate(r: Ranked, w: np.ndarray | None = None, k: int = config.CALL_CAPACITY) -> dict[str, float]:
    """Mọi metric của một model với trọng số dòng w (mặc định 1 = không bootstrap)."""
    w = np.ones(len(r.y)) if w is None else np.asarray(w, float)
    ys, ws = r.y[r.order], w[r.order]
    tps = np.cumsum(ws * ys)[r.last]  # số ca churn được bắt khi hạ ngưỡng xuống từng mức điểm
    fps = np.cumsum(ws * (1 - ys))[r.last]
    tpr, fpr = np.r_[0, tps] / tps[-1], np.r_[0, fps] / fps[-1]
    precision = np.divide(tps, tps + fps, out=np.ones_like(tps), where=(tps + fps) > 0)
    per_month = []
    for idx in r.by_t:
        yt, wt = r.y[idx], w[idx]
        take = np.clip(k - (np.cumsum(wt) - wt), 0, wt)  # phần trọng số của mỗi dòng lọt vào top-k
        hit = (take * yt).sum()
        p, rc = hit / take.sum(), hit / max((wt * yt).sum(), 1e-12)
        per_month.append((p, rc, 2 * p * rc / (p + rc) if p + rc else 0.0))
    p_k, r_k, f1_k = np.mean(per_month, axis=0)
    return {
        "auc": float(np.trapezoid(tpr, fpr)),
        "pr_auc": float(np.sum(np.diff(tpr) * precision)),
        "p@k": float(p_k),
        "r@k": float(r_k),
        "f1@k": float(f1_k),
    }
```

Đọc theo khối:

- `tps`, `fps`: cộng dồn trọng số khách rời / khách ở lại khi hạ ngưỡng xuống từng mức điểm. Từ đó suy ra `tpr`
  (recall) và `fpr`. **AUC** là diện tích dưới đường (fpr, tpr), tính bằng `np.trapezoid`.
- **PR-AUC** = Σ (tăng recall) × precision tại ngưỡng đó. Đây đúng là định nghĩa của `average_precision_score`.
- **precision@k với trọng số**: `take` là phần trọng số của mỗi dòng lọt vào top-k. Một khách trọng số 2 chiếm 2 chỗ.
  Dòng nằm vắt qua ranh giới k chỉ được tính phần nằm trong.
- Không có trọng số (`w=None`) thì mọi dòng nặng 1, cho đúng metric thường.

**File: `src/churn_telco/metrics.py` · `bootstrap`**

```python
def bootstrap(
    scores: dict[str, np.ndarray],
    frame: pd.DataFrame,
    n_boot: int = 1000,
    k: int = config.CALL_CAPACITY,
    reference: str | None = None,
    cluster: str | None = "customer_id",
    seed: int = config.SEED,
) -> pd.DataFrame:
    """Khoảng tin cậy 95% cho mọi metric của mọi model, cộng chênh lệch CẶP so với model `reference`.

    Chênh lệch cặp: hai model được đo trên CÙNG một mẫu bootstrap ở mỗi vòng, nên phần dao động do mẫu triệt tiêu —
    khoảng tin cậy của chênh lệch hẹp hơn nhiều so với việc so hai khoảng tin cậy riêng lẻ.
    """
    y, t = frame[LABEL].to_numpy(), frame["t"].to_numpy()
    ranked = {name: rank(s, y, t) for name, s in scores.items()}
    codes = pd.factorize(frame[cluster])[0] if cluster else np.arange(len(frame))
    n = codes.max() + 1
    rng = np.random.default_rng(seed)
    draws: dict[str, list[dict]] = {name: [] for name in ranked}
    for _ in range(n_boot):
        w = np.bincount(rng.integers(0, n, n), minlength=n)[codes]
        for name, r in ranked.items():
            draws[name].append(evaluate(r, w, k))
    point = {name: evaluate(r, k=k) for name, r in ranked.items()}
    boot = {name: pd.DataFrame(d) for name, d in draws.items()}
    rows = []
    for name in ranked:
        for m in METRICS:
            row = {"model": name, "metric": m, "value": point[name][m]}
            row |= {"lo": boot[name][m].quantile(0.025), "hi": boot[name][m].quantile(0.975)}
            if reference and name != reference:
                delta = boot[name][m] - boot[reference][m]
                row |= {"delta": point[name][m] - point[reference][m], "p_better": float((delta > 0).mean())}
                row |= {"delta_lo": delta.quantile(0.025), "delta_hi": delta.quantile(0.975)}
            rows.append(row)
    return pd.DataFrame(rows)
```

- `codes`: mỗi khách một số nguyên. `np.bincount(rng.integers(0, n, n))` đếm mỗi khách được rút bao nhiêu lần, rồi
  `[codes]` trải số lần đó ra mọi dòng của khách. Đây là **bootstrap theo cụm**. `cluster=None` thì mỗi dòng là một
  cụm (bootstrap theo dòng, chỉ để so sánh trong lab).
- Mọi model dùng **cùng** `w` trong một vòng, nên `delta` là chênh lệch **cặp** (mục 4.3). `p_better` là tỷ lệ vòng mà
  model tốt hơn tham chiếu.
- `seed` cố định: chạy lại ra đúng khoảng tin cậy cũ.

**File: `src/churn_telco/metrics.py` · `table`**

```python
def table(results: pd.DataFrame, k: int = config.CALL_CAPACITY) -> str:
    """Bảng markdown: mỗi model một dòng, mỗi ô "giá trị [KTC 95%]"; cột cuối là chênh lệch P@k so với tham chiếu."""
    names = {"auc": "AUC", "pr_auc": "PR-AUC", "p@k": f"P@{k}", "r@k": f"R@{k}", "f1@k": f"F1@{k}"}
    lines = ["| Model | " + " | ".join(names.values()) + f" | Δ P@{k} so với tham chiếu |", "|---" * 7 + "|"]
    for model, g in results.groupby("model", sort=False):
        g = g.set_index("metric")
        cells = [f"{g.at[m, 'value']:.3f} [{g.at[m, 'lo']:.3f}–{g.at[m, 'hi']:.3f}]" for m in METRICS]
        if "delta" in g and pd.notna(g.at["p@k", "delta"]):
            d = g.loc["p@k"]
            cells.append(f"{d.delta:+.3f} [{d.delta_lo:+.3f}…{d.delta_hi:+.3f}]")
        else:
            cells.append("—")
        lines.append(f"| {model} | " + " | ".join(cells) + " |")
    return "\n".join(lines)
```

### A3.3 `baselines.py` — bậc thang baseline

**File: `src/churn_telco/baselines.py`**

```python
"""Baseline (A3 · BIZ-02, ML-01): con số phải vượt TRƯỚC khi nói tới model "xịn".

Bốn mức, từ rẻ tới đắt:
1. Ngẫu nhiên — sàn: precision@500 ≈ tỷ lệ churn nền. Thấp hơn mức này là có lỗi.
2. Luật CSKH hiện tại — cách đang làm: gọi khách sắp hết hợp đồng, rồi khách hay báo lỗi mạng (framing A1).
3. Luật giảm sử dụng — luật của người phân tích sau EDA (A2): khách dùng ít đi nhiều nhất xếp trước.
4. Logistic regression trong một Pipeline — model tuyến tính đơn giản nhất dùng mọi feature.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from churn_telco import config
from churn_telco.features import CATEGORICAL, LABEL, NUMERIC


def _jitter(df: pd.DataFrame, seed: int = config.SEED) -> np.ndarray:
    """Nhiễu rất nhỏ để phá hoà điểm một cách ngẫu nhiên (luật cho rất nhiều khách cùng điểm)."""
    return np.random.default_rng(seed).random(len(df)) * 1e-6


def random_scores(df: pd.DataFrame) -> np.ndarray:
    return _jitter(df)


def rule_cskh(df: pd.DataFrame) -> np.ndarray:
    points = (
        4 * (df["days_to_contract_end"] <= 30)  # sắp hết hợp đồng: đội gia hạn vẫn gọi nhóm này
        + 2 * (df["network_tickets_60d"] >= 1)  # vừa phàn nàn về mạng
        + 1 * (df["contract_months"] == 0)  # không kỳ hạn: rời lúc nào cũng được
        + 1 * (df["late_or_unpaid_90d"] >= 1)  # trả cước trễ
    )
    return points.to_numpy(float) + _jitter(df)


def rule_usage_drop(df: pd.DataFrame) -> np.ndarray:
    ratio = df["usage_ratio"].fillna(1.0).to_numpy()  # data tháng trước / trung bình 3 tháng trước đó
    return -ratio + _jitter(df)  # dùng ít đi nhiều nhất thì xếp trước


def make_logistic(numeric: list[str] = NUMERIC, categorical: list[str] = CATEGORICAL) -> Pipeline:
    """Mọi bước tiền xử lý nằm TRONG Pipeline: imputer/scaler chỉ học từ tập train khi gọi fit — không rò rỉ."""
    pre = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
            ("num", make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler()), numeric),
        ]
    )
    return Pipeline([("pre", pre), ("model", LogisticRegression(C=0.5, max_iter=2000))])


def fit_logistic(train: pd.DataFrame) -> Pipeline:
    return make_logistic().fit(train[CATEGORICAL + NUMERIC], train[LABEL])


RULES = {"Ngẫu nhiên": random_scores, "Luật CSKH hiện tại": rule_cskh, "Luật giảm sử dụng": rule_usage_drop}
```

- `_jitter`: luật cho hàng nghìn khách cùng điểm. Nhiễu cỡ 1e-6 (nhỏ hơn mọi khoảng cách điểm thật) phá hoà một cách
  ngẫu nhiên nhưng **cố định theo seed**, nên top-500 của luật là xác định, không phụ thuộc thứ tự dòng.
- `rule_cskh` viết **cách làm hiện tại** thành code (bài A1, mục 1.4). Hệ số 4/2/1/1 là thứ tự ưu tiên CSKH đang dùng,
  không phải tham số học từ dữ liệu.
- `make_logistic` gói one-hot, điền thiếu + cờ thiếu, chuẩn hoá và logistic regression vào **một** `Pipeline`.
  `handle_unknown="ignore"`: gặp giá trị category lạ lúc chấm điểm (một tỉnh mới) thì bỏ qua thay vì lỗi. `C=0.5` là
  mức điều chuẩn vừa phải.

### A3.4 `evaluate.py` — harness một lệnh

**File: `src/churn_telco/evaluate.py`**

```python
"""Harness đánh giá một lệnh (A3 · BIZ-02): `make eval` = mọi baseline + mọi model đã train, trên CÙNG bộ đánh giá đóng
băng, kèm khoảng tin cậy bootstrap và chênh lệch cặp so với baseline tham chiếu.

    uv run python -m churn_telco.evaluate                  # tập test đóng băng → reports/eval.md + reports/eval.json
    uv run python -m churn_telco.evaluate --split valid    # tập valid (dùng khi phát triển)
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from churn_telco import baselines, config, features, metrics, split

log = logging.getLogger(__name__)
REFERENCE = "Logistic"  # baseline tham chiếu: model phải vượt nó mới đáng thêm độ phức tạp

Scorer = Callable[[pd.DataFrame], np.ndarray]


def candidates(train: pd.DataFrame, models_dir: Path = config.MODELS) -> dict[str, Scorer]:
    """Baseline (học lại mỗi lần chạy, vài giây) + mọi model đã lưu trong models/*/bundle.json."""
    logistic = baselines.fit_logistic(train)
    scorers: dict[str, Scorer] = dict(baselines.RULES)
    scorers[REFERENCE] = lambda df: logistic.predict_proba(df[logistic.feature_names_in_])[:, 1]
    bundles = sorted(models_dir.glob("*/bundle.json"))
    if bundles:  # model LightGBM có từ A5; trước đó harness chỉ chấm baseline
        from churn_telco import train as training

        for path in bundles:
            bundle = training.load(path.parent)
            scorers[bundle.meta["name"]] = bundle.score
    return scorers


def run(
    which: str = "test",
    n_boot: int = 1000,
    processed: Path = config.PROCESSED,
    manifest: Path = split.MANIFEST,
    models_dir: Path = config.MODELS,
) -> pd.DataFrame:
    df = features.load(processed)
    if not manifest.exists():  # lần chạy đầu tiên: đóng băng trước khi nhìn bất kỳ kết quả nào
        log.warning("Chưa có %s — đóng băng tập test ngay bây giờ: %s", manifest, split.freeze(df, manifest))
    parts = split.split(df)
    frame = split.frozen_test(df, manifest) if which == "test" else parts[which]
    scores = {name: score(frame) for name, score in candidates(parts["train"], models_dir).items()}
    return metrics.bootstrap(scores, frame, n_boot=n_boot, reference=REFERENCE)


def save(results: pd.DataFrame, which: str, out: Path = config.REPORTS) -> str:
    out.mkdir(parents=True, exist_ok=True)
    text = f"Tập: **{which}** · KTC 95% bootstrap theo khách · tham chiếu: {REFERENCE}\n\n{metrics.table(results)}\n"
    (out / f"eval_{which}.md").write_text(text, encoding="utf-8")
    (out / f"eval_{which}.json").write_text(results.to_json(orient="records", force_ascii=False, indent=1), "utf-8")
    return text


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--split", choices=["valid", "test"], default="test")
    parser.add_argument("--n-boot", type=int, default=1000)
    args = parser.parse_args(argv)
    print(save(run(args.split, args.n_boot), args.split))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
```

- `candidates` trả về **từ điển tên → hàm chấm điểm**. Baseline học lại mỗi lần (vài giây); model đã train được nạp
  từ `models/*/bundle.json`. Hôm nay thư mục `models/` còn trống nên harness chỉ chấm baseline. Từ bài A5, model mới
  tự xuất hiện trong bảng mà không phải sửa file này. Import `train` nằm trong `if bundles:` để file chạy được trước
  khi `train.py` tồn tại.
- `run`: lần đầu chạy, chưa có manifest thì **đóng băng ngay** (trước khi tính bất kỳ metric nào). Từ lần sau, mọi
  đánh giá trên test đều đi qua `split.frozen_test`.
- `save` ghi `reports/eval_test.md` (cho người đọc) và `.json` (cho báo cáo A8 đọc lại).

```bash
make eval
```

```text
WARNING __main__: Chưa có .../eval/manifest.json — đóng băng tập test ngay bây giờ: {'rule': ..., 'rows': 60912, ...}
Tập: **test** · KTC 95% bootstrap theo khách · tham chiếu: Logistic

| Model | AUC | PR-AUC | P@500 | R@500 | F1@500 | Δ P@500 so với tham chiếu |
|---|---|---|---|---|---|---|
| Ngẫu nhiên | 0.493 [0.478–0.509] | 0.022 [0.021–0.024] | 0.021 [0.014–0.028] | 0.022 [0.015–0.031] | 0.022 [0.014–0.029] | -0.234 [-0.259…-0.211] |
| Luật CSKH hiện tại | 0.668 [0.654–0.683] | 0.052 [0.047–0.060] | 0.075 [0.062–0.088] | 0.081 [0.067–0.095] | 0.078 [0.064–0.091] | -0.180 [-0.204…-0.156] |
| Luật giảm sử dụng | 0.683 [0.666–0.700] | 0.108 [0.096–0.124] | 0.217 [0.193–0.236] | 0.236 [0.211–0.254] | 0.226 [0.202–0.244] | -0.037 [-0.061…-0.021] |
| Logistic | 0.763 [0.749–0.778] | 0.190 [0.169–0.215] | 0.255 [0.231–0.278] | 0.276 [0.255–0.299] | 0.265 [0.244–0.287] | — |
```

Đọc bảng:

- **Ngẫu nhiên**: AUC ≈ 0,5, P@500 ≈ 0,021 ≈ tỷ lệ nền 2,28%. Sàn đúng như lý thuyết, nghĩa là code đo không lỗi.
- **Luật CSKH hiện tại**: P@500 = 7,5%, tức 37 người trúng mỗi tháng. Bài A1 đã tính hoà vốn ở ~5,4%, nên cách làm
  hiện tại chỉ vừa có lãi.
- **Một luật một dòng** (dùng ít đi) đạt 21,7%, gấp gần 3 lần cách làm hiện tại. Đây là sức mạnh của EDA tốt.
- **Logistic** đạt 25,5%, hơn luật dùng ít đi **3,7 điểm** với KTC chênh lệch cặp [2,1; 6,1] không chứa 0: có ý
  nghĩa. Logistic thành **tham chiếu** cho LightGBM ở bài A5.

Commit `eval/manifest.json` ngay sau lần chạy đầu tiên.

### A3.5 Test: metric của ta phải khớp sklearn

**File: `tests/test_eval.py` · `test_metrics_match_sklearn…test_metrics_handle_ties_and_weights_like_sklearn`**

```python
def test_metrics_match_sklearn(scored):
    test, score = scored
    m = metrics.evaluate(metrics.rank(score, test[LABEL], test["t"]))
    assert m["auc"] == pytest.approx(roc_auc_score(test[LABEL], score))
    assert m["pr_auc"] == pytest.approx(average_precision_score(test[LABEL], score))


def test_metrics_handle_ties_and_weights_like_sklearn(scored):
    test, _ = scored
    ties = (test["contract_months"] == 0).to_numpy(float)  # chỉ 2 mức điểm: rất nhiều điểm hoà
    w = np.random.default_rng(1).integers(0, 3, len(test))
    m = metrics.evaluate(metrics.rank(ties, test[LABEL], test["t"]), w)
    assert m["auc"] == pytest.approx(roc_auc_score(test[LABEL], ties, sample_weight=w))
    assert m["pr_auc"] == pytest.approx(average_precision_score(test[LABEL], ties, sample_weight=w))
```

Tự viết metric thì phải chứng minh nó đúng bằng một nguồn đáng tin: so với sklearn, kể cả khi **điểm hoà** (luật hai
mức điểm) và khi **có trọng số** (bootstrap). Hai test khác bảo vệ bộ đánh giá:

**File: `tests/test_eval.py` · `test_frozen_test_detects_any_change…test_freeze_refuses_to_overwrite`**

```python
def test_frozen_test_detects_any_change(small):
    manifest = small.root / "eval" / "manifest.json"
    assert len(split.frozen_test(small.df, manifest)) == json.loads(manifest.read_text())["rows"]
    tampered = small.df.copy()
    row = tampered.index[tampered["t"] == tampered["t"].max()][0]
    tampered.loc[row, LABEL] = 1 - tampered.loc[row, LABEL]  # đổi đúng MỘT nhãn
    with pytest.raises(ValueError, match="không khớp"):
        split.frozen_test(tampered, manifest)


def test_freeze_refuses_to_overwrite(small):
    with pytest.raises(FileExistsError):
        split.freeze(small.df, small.root / "eval" / "manifest.json")
```

Đổi **đúng một** nhãn thì `frozen_test` phải từ chối. Test viết đúng kịch bản mà ta muốn chặn.

### A3.6 Lab: khoảng tin cậy từ bên trong

**File: `labs/stat-02-co-ban-bootstrap/bootstrap_lab.py`**

```python
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
```

```bash
cd labs/stat-02-co-ban-bootstrap
uv run --project ../../projects/g1-churn-telco python bootstrap_lab.py
```

```text
1) P@500 logistic = 0.255; công thức nhanh: ±0.022 → [0.233, 0.277]
   bootstrap theo khách (1.000 lần): [0.231, 0.278]

2) Chỉ 1 tháng: [0.224, 0.306] — rộng gấp 1.76 lần khi dùng 3 tháng (√3 ≈ 1,73)

3) Tập gốc:              AUC ±0.0148
   Chép 3 lần, rút theo khách: AUC ±0.0148  ← đúng: không đổi
   Chép 3 lần, rút theo dòng:  AUC ±0.0086  ← hẹp giả tạo

4) Logistic 0.255 [0.231–0.278] vs luật giảm sử dụng 0.217 [0.193–0.236]
   chênh lệch cặp: +0.037 [+0.021…+0.061], P(logistic tốt hơn) = 1.000

5) Tỷ lệ churn nền 0.023; 100 model ngẫu nhiên có P@500 từ 0.013 tới 0.033
   Chọn cái tốt nhất → báo cáo 0.033, cao hơn nền 46% — toàn là may rủi.
   → Chốt trước MỘT metric chính và vài phương án; tập đóng băng không phải chỗ thử hàng chục ý tưởng.
```

1. Công thức nhanh ±0,022 gần như trùng bootstrap. Với một tỷ lệ, bạn ước lượng được sai số **trong đầu** trước khi
   chạy bất cứ gì.
2. Chỉ dùng 1 tháng thì khoảng tin cậy rộng gần đúng √3 lần. Muốn hẹp đi một nửa thì cần gấp 4 lần dữ liệu.
3. Chép tập test 3 lần không thêm chút thông tin nào. Rút theo khách thì KTC giữ nguyên (đúng); rút theo dòng thì KTC
   hẹp đi √3 lần như thể có thêm dữ liệu (sai). Trên tập test gốc, mỗi khách rời chỉ xuất hiện một lần nên hai cách
   cho kết quả gần nhau. Với bài toán nhãn lặp lại theo khách (trả trễ nhiều tháng) thì sai lệch là thật.
4. Hai KTC [0,231–0,278] và [0,193–0,236] **chồng nhau**, nhưng KTC chênh lệch cặp [+0,021; +0,061] **không chứa 0**.
   Logistic tốt hơn thật. So hai KTC riêng lẻ sẽ cho kết luận sai.
5. Model **ngẫu nhiên** "giỏi" nhất trong 100 cái trông hơn mức nền 46%. Đó là lý do tập đóng băng không được dùng để
   chọn giữa nhiều phương án.

---

## 6 · Kiểm tra kết quả

- [ ] `make eval` chạy từ đầu, in bảng 4 baseline có KTC 95%, ghi `reports/eval_test.md` và `eval/manifest.json`.
- [ ] `eval/manifest.json` đã commit. Chạy lại `make eval` không đổi một chữ số nào (seed cố định).
- [ ] `uv run pytest tests/test_eval.py` xanh: metric khớp sklearn, đổi một nhãn bị phát hiện, imputer học trên train.
- [ ] Bạn giải thích được cho đồng nghiệp: vì sao 2 KTC chồng nhau mà vẫn kết luận được "logistic tốt hơn" (STAT-02).

## 7 · Lỗi thường gặp

| Triệu chứng | Nguyên nhân | Cách sửa |
|---|---|---|
| Kết quả test "đẹp hơn" valid rất nhiều | đã chọn tham số/ngưỡng trên test | mọi lựa chọn làm trên valid; test chỉ báo cáo |
| KTC hẹp bất thường | bootstrap theo dòng khi dòng không độc lập | bootstrap theo khách (`cluster="customer_id"`) |
| Kết luận "A tốt hơn B" vì A cao hơn 0,005 | không có sai số | báo KTC chênh lệch cặp, chỉ kết luận khi không chứa 0 |
| Logistic báo lỗi giá trị thiếu hoặc tỉnh lạ | tiền xử lý ngoài Pipeline / thiếu `handle_unknown` | gói mọi bước vào `Pipeline` |
| `make eval` báo tập test không khớp manifest | ai đó đổi cách chọn khách hoặc tính nhãn | xem chỗ lệch trong thông báo; nếu cố ý thì `freeze(force=True)` và ghi lại lý do |

## 8 · Bài tập

1. **(Cơ bản)** Thêm baseline "khách không kỳ hạn có ticket mạng trong 60 ngày" vào `RULES`. Nó đứng ở đâu trong bậc
   thang?
2. **(Cơ bản)** Dùng công thức ở mục 4.1: cần bao nhiêu tháng đánh giá để KTC của precision@500 còn ±1 điểm phần trăm?
   Kiểm tra lại bằng bootstrap.
3. **(Trung cấp — STAT-02)** Viết kiểm định McNemar cho hai danh sách gọi (cùng 1.500 lượt gọi) và so kết luận với
   chênh lệch cặp bootstrap.
4. **(Trung cấp — ML-01)** Thêm `--split valid` vào lần chạy và so thứ hạng các baseline giữa valid và test. Thứ hạng
   có đổi không? Điều đó nói gì về việc chọn model trên valid?

---

**Tiếp theo:** [A4 · Dữ liệu đúng thời điểm và feature](a4-feature-as-of-ro-ri.md). Ta mở hộp đen `features.py`: dựng
bảng học sao cho mọi feature chỉ dùng dữ liệu có trước ngày chấm điểm, rồi cố tình làm sai để thấy hậu quả.
