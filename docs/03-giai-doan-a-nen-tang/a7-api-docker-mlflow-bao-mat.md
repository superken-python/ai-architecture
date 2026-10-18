# A7 · Đóng gói, theo dõi thực nghiệm và bảo mật dữ liệu

**Tuần 7** · Kỹ năng: [OPS-01](../02-skill-map/generated/mang/ops.md#ops-01) Cơ bản,
[OPS-02](../02-skill-map/generated/mang/ops.md#ops-02) Cơ bản, [OPS-08](../02-skill-map/generated/mang/ops.md#ops-08) Cơ bản ·
Lab: [`labs/ops-01-co-ban-dong-goi-api/`](../../labs/ops-01-co-ban-dong-goi-api/README.md) ·
Sản phẩm: `docker compose up` ra API chấm điểm; MLflow có lịch sử thí nghiệm; repo không chứa secret/dữ liệu thật

Model chỉ có giá trị khi hệ thống khác dùng được nó. Bài này đưa model ra khỏi máy bạn theo ba hướng. **Phục vụ**: một
API có kiểm tra đầu vào, khoá truy cập, health check và version, chạy trong container. **Ghi lại**: mỗi lần train là
một bản ghi tái lập được trong MLflow. **Bảo vệ**: không secret, không dữ liệu khách nào lọt vào Git hay ra ngoài hệ
thống.

**Sau bài này bạn làm được:**

- Viết API FastAPI: schema đầu vào sinh từ model, khoá API so sánh thời gian hằng số, lỗi rõ ràng (401/404/422).
- Đóng gói bằng Docker: cài từ lockfile, lớp cache hợp lý, chạy bằng user thường, hệ thống file chỉ đọc, health check.
- Ghi mỗi lần train vào MLflow: tham số, metric, phiên bản dữ liệu, commit, artifact model.
- Rà soát repo và dữ liệu: secret, lịch sử Git, PII; phân loại dữ liệu nào được phép đi đâu.

---

## 1 · Lý thuyết: phục vụ model

### 1.1 Theo lô hay theo yêu cầu?

| | Theo lô (batch) | Theo yêu cầu (online API) |
|---|---|---|
| Ở dự án | `make score` ngày 1 hằng tháng → danh sách 500 khách | `POST /score` khi nhân viên mở hồ sơ khách trong CRM |
| Khi nào dùng | quyết định theo chu kỳ, cho nhiều khách cùng lúc | quyết định tại chỗ, cho từng khách |
| Độ trễ cần | phút–giờ | dưới vài trăm ms |
| Feature lấy từ đâu | dựng tại chỗ bằng SQL của bảng học | bên gọi gửi kèm (hoặc lấy từ feature store) |

Bài toán gọi giữ chân **chủ yếu là theo lô**. API phục vụ hai việc: tra cứu danh sách gọi mới nhất (`/top`), và chấm
điểm khi hệ thống khác gửi feature (`/score`).

### 1.2 Hợp đồng của một API model

- **Đầu vào có schema**: thiếu trường, sai kiểu, tỉnh lạ thì từ chối với lỗi **422** chỉ rõ trường nào. Không đoán,
  không lặng lẽ điền giá trị.
- **Biết đang chạy model nào**: `/version` trả tên, phiên bản, ngày train, mã băm dữ liệu, commit. Khi kết quả lạ, câu
  hỏi đầu tiên luôn là "model nào?".
- **Health check**: `/health` để Docker/load balancer biết tiến trình còn sống.
- **Truy cập có kiểm soát**: endpoint trả dữ liệu khách cần khoá. Thiếu hoặc sai khoá thì **401**.
- **Hỏng sớm**: thiếu khoá cấu hình hoặc thiếu model thì **không khởi động**, thay vì chạy rồi lỗi ở request đầu tiên.

### 1.3 Docker: đóng gói môi trường cùng code

Image là "máy tính đóng hộp": hệ điều hành, Python, thư viện đúng phiên bản và code. Năm thực hành dùng trong dự án:

1. **Cài từ lockfile** (`uv sync --locked`): image build hôm nay và sau 6 tháng giống nhau.
2. **Thứ tự lớp**: chép `pyproject.toml` + `uv.lock` và cài thư viện **trước**, chép code **sau**. Sửa code thì Docker
   dùng lại lớp thư viện đã cache, build lại mất vài giây thay vì vài phút.
3. **Chỉ cài cái cần để phục vụ**: không shap, mlflow, pytest. Image nhỏ hơn, ít thư viện thì ít lỗ hổng.
4. **Không chạy bằng root**, hệ thống file **chỉ đọc**: lỡ có lỗ hổng, kẻ tấn công cũng không có quyền root và không
   ghi được gì.
5. **Secret không nằm trong image**: khoá API đi vào lúc chạy qua biến môi trường (`.env`). Model cũng gắn vào lúc
   chạy (volume chỉ đọc), nên đổi model không phải build lại image.

---

## 2 · Lý thuyết: theo dõi thực nghiệm và tái lập

Sáu tháng sau, ai đó hỏi: *"Model đang chạy được train thế nào, trên dữ liệu nào, metric bao nhiêu?"* Muốn trả lời
được, **mỗi lần train** phải ghi lại:

| Ghi gì | Ở dự án |
|---|---|
| Code | commit git (`git_commit`) |
| Dữ liệu | mã băm SHA-256 của file feature (`features_sha256`) — vì vậy bảng học phải giống từng bit mỗi lần dựng (bài A4) |
| Tham số | toàn bộ `PARAMS`, tập feature, số cây |
| Môi trường | phiên bản Python, LightGBM, pandas (+ `uv.lock` trong commit) |
| Kết quả | metric valid; báo cáo đánh giá trên tập đóng băng |
| Artifact | `model.txt` + `bundle.json`, tải về là phục vụ được |

Ở dự án này, `train.py` **đã** ghi tất cả vào `bundle.json` (bài A5). MLflow chỉ là nơi gom mọi bundle lại, có giao
diện để so sánh và tìm kiếm. Tách như vậy thì code train không phụ thuộc MLflow, và đổi sang công cụ khác chỉ phải sửa
một file.

---

## 3 · Lý thuyết: bảo mật dữ liệu

### 3.1 Ba loại thứ không bao giờ được lọt ra

- **Secret**: khoá API, mật khẩu, token. Nằm trong biến môi trường hoặc kho secret; trong repo chỉ có `.env.example`.
- **Dữ liệu cá nhân (PII)**: tên, số điện thoại, email, số giấy tờ. Ở dự án, PII bị **bỏ ngay ở bước làm sạch** (bài
  A2). Từ đó trở đi, file trung gian, model, log, danh sách gọi đều không chứa PII. Đó là nguyên tắc **tối thiểu hoá
  dữ liệu**.
- **Dữ liệu khách nói chung**, kể cả đã bỏ PII: vẫn không vào Git, không gửi ra API bên ngoài (ví dụ một LLM trên
  cloud) nếu chưa được duyệt.

### 3.2 Lịch sử Git không quên

`git rm` một file `.env` ở commit sau **không** xoá nó khỏi lịch sử. Ai clone repo cũng lấy lại được. Lỡ commit secret
thì việc đầu tiên là **đổi secret** (coi như đã lộ), sau đó mới dọn lịch sử. Phòng hơn chữa: `.gitignore` từ commit
đầu, cộng một kiểm tra tự động trước khi push (lab ở mục A7.5).

### 3.3 Phân loại dữ liệu — viết ra, đừng để trong đầu

Một bảng ngắn, ai cũng hiểu, trả lời "dữ liệu này được phép đi đâu". Lab in bảng này ra cùng kết quả rà soát.

---

## 4 · Lab A7

### A7.1 `api.py` — từng phần

**File: `src/churn_telco/api.py` · `đầu file…OPTIONAL`**

```python
"""API chấm điểm churn (A7 · OPS-01, OPS-08): FastAPI, có health check, version model, khoá API, kiểm tra đầu vào.

- GET  /health   — sống/chết (không cần khoá; dùng cho Docker HEALTHCHECK và load balancer)
- GET  /version  — model nào đang chạy: tên, phiên bản, ngày train, mã băm dữ liệu, commit (không cần khoá)
- POST /score    — chấm điểm tối đa 1.000 khách gửi kèm feature → xác suất, giá trị kỳ vọng, 3 lý do (cần khoá)
- GET  /top      — danh sách gọi của tháng gần nhất do job chấm điểm hằng tháng tạo ra (cần khoá)
- GET  /         — trang demo cho CSKH: nhập khoá, xem danh sách gọi kèm lý do

Cấu hình qua biến môi trường (file .env khi chạy docker compose — .env KHÔNG commit, chỉ commit .env.example):
CHURN_API_KEY (bắt buộc), CHURN_MODEL_DIR, CHURN_OUTPUTS. Log chỉ ghi số lượng và thời gian, không ghi feature.

    uv run uvicorn churn_telco.api:create_app --factory --port 8000
"""

# Không dùng `from __future__ import annotations` ở file này: FastAPI phải đọc được kiểu ScoreRequest được tạo động
# bên trong create_app; chú thích kiểu dạng chuỗi thì FastAPI không tìm thấy nó.
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Annotated, Literal

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, create_model

from churn_telco import config, decision, explain, schemas, train
from churn_telco.clean import CANONICAL_PROVINCES

log = logging.getLogger("churn_telco.api")
DEMO_PAGE = Path(__file__).with_name("demo.html")

CATEGORY_VALUES = {
    "segment": schemas.SEGMENTS,
    "channel": schemas.CHANNELS,
    "province": CANONICAL_PROVINCES,
    "plan_code": schemas.PLAN_CODES,
    "payment_method": schemas.PAYMENTS,
}
# Feature được phép thiếu (NaN) — đúng như trong bảng học: khách không có hợp đồng, chưa từng có ticket, thiếu số đo...
OPTIONAL = {
    "age",
    "days_to_contract_end",
    "data_gb_m1",
    "data_gb_m2_m4",
    "usage_ratio",
    "tv_hours_m1",
    "outage_m1",
    "outage_avg_3m",
    "min_csat_90d",
    "days_since_last_ticket",
    "max_days_late_90d",
}
```

- Docstring liệt kê mọi endpoint, cái nào cần khoá, cấu hình qua biến nào. Người vận hành chỉ cần đọc đoạn này.
- Không dùng `from __future__ import annotations` ở file này. Kiểu `ScoreRequest` được **tạo động** bên trong
  `create_app`; nếu chú thích kiểu là chuỗi, FastAPI không tìm được nó và hiểu nhầm tham số. Comment ở đầu file ghi lại
  lý do để người sau không "sửa cho đồng bộ".
- `CATEGORY_VALUES` tái dùng danh sách giá trị chuẩn của `clean.py` và `schemas.py`: một nguồn sự thật cho cả làm
  sạch, kiểm tra dữ liệu và API.
- `OPTIONAL`: feature được phép thiếu, khớp với những cột được thiếu trong bảng học.

**File: `src/churn_telco/api.py` · `request_model…Score`**

```python
def request_model(features: list[str]) -> type[BaseModel]:
    """Schema đầu vào sinh từ danh sách feature CỦA MODEL ĐANG CHẠY — đổi model là API tự đổi theo, không sửa tay."""
    fields: dict = {"customer_id": (str, Field(min_length=1, max_length=20))}
    for col in features:
        if col in CATEGORY_VALUES:
            fields[col] = (Literal[tuple(CATEGORY_VALUES[col])], ...)
        else:
            fields[col] = (float | None, None) if col in OPTIONAL else (float, ...)
    customer = create_model("Customer", **fields)
    return create_model("ScoreRequest", customers=(list[customer], Field(min_length=1, max_length=1000)))


class Reason(BaseModel):
    text: str
    action: str
    shap: float


class Score(BaseModel):
    customer_id: str
    probability: float = Field(description="Xác suất rời mạng trong 30 ngày (đã hiệu chỉnh)")
    expected_value: float = Field(description="Giá trị kỳ vọng (VND) của một cuộc gọi giữ chân")
    should_call: bool = Field(description="EV > 0 — chưa xét năng lực gọi 500 khách/tháng")
    reasons: list[Reason]
```

`request_model` sinh schema pydantic **từ danh sách feature của model đang chạy**. Category thành `Literal[...]` (tỉnh
lạ bị từ chối); feature số thành `float` (bắt buộc) hoặc `float | None` (được thiếu). Model v2 cần
`competitor_promo_30d` nên API v2 tự đòi trường đó. Đổi model là API đổi theo, không phải sửa tay hai nơi.
`max_length=1000` giới hạn kích thước request, để một lời gọi không làm treo dịch vụ.

**File: `src/churn_telco/api.py` · `create_app`**

```python
def create_app(model_dir: Path | None = None, outputs: Path | None = None, api_key: str | None = None) -> FastAPI:
    model_dir = model_dir or Path(os.getenv("CHURN_MODEL_DIR", config.MODELS / "lgbm-v2"))
    outputs = outputs or Path(os.getenv("CHURN_OUTPUTS", config.DATA / "outputs"))
    api_key = api_key or os.getenv("CHURN_API_KEY")
    if not api_key:  # an toàn mặc định: thiếu khoá thì không chạy, thay vì chạy mà không có khoá
        raise RuntimeError("Thiếu CHURN_API_KEY — tạo .env từ .env.example rồi đặt một khoá ngẫu nhiên")
    bundle = train.load(model_dir)  # thiếu model thì dừng ngay lúc khởi động, không đợi request đầu tiên mới lỗi
    ScoreRequest = request_model(bundle.features)  # noqa: N806 — một class, đặt tên như class
    numeric = [c for c in bundle.features if c not in CATEGORY_VALUES]
    app = FastAPI(title="Churn Sóng Xanh", version=bundle.meta.get("version", bundle.meta["feature_set"]))

    def require_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
        if x_api_key is None or not secrets.compare_digest(x_api_key, api_key):  # so sánh thời gian hằng số
            raise HTTPException(status_code=401, detail="Sai hoặc thiếu X-API-Key")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/version")
    def version() -> dict:
        meta = bundle.meta
        keys = ["name", "version", "feature_set", "best_iteration", "trained_at", "git_commit", "valid"]
        return {k: meta.get(k) for k in keys} | {"features_sha256": meta["data"].get("features_sha256")}

    @app.post("/score", dependencies=[Depends(require_key)])
    def score(req: ScoreRequest) -> list[Score]:  # type: ignore[valid-type]
        start = time.perf_counter()
        df = pd.DataFrame([c.model_dump() for c in req.customers])
        for col, values in CATEGORY_VALUES.items():  # kiểu category như lúc train (LightGBM tự khớp mã category)
            df[col] = pd.Categorical(df[col], categories=sorted(values))
        df[numeric] = df[numeric].astype(float)
        p = bundle.proba(df)
        ev = decision.expected_value(p, decision.customer_value(df))
        why = explain.reasons(bundle, df)
        out = []
        for i, row in df.iterrows():
            reasons = [
                Reason(text=why.at[i, f"reason_{j}"], action=why.at[i, f"action_{j}"], shap=why.at[i, f"shap_{j}"])
                for j in (1, 2, 3)
                if f"reason_{j}" in why and pd.notna(why.at[i, f"reason_{j}"])
            ]
            out.append(
                Score(
                    customer_id=row.customer_id,
                    probability=p[i],
                    expected_value=ev[i],
                    should_call=ev[i] > 0,
                    reasons=reasons,
                )
            )
        log.info("score: %d khách trong %.0f ms", len(df), 1000 * (time.perf_counter() - start))
        return out

    @app.get("/top", dependencies=[Depends(require_key)])
    def top(k: Annotated[int, Query(ge=1, le=config.CALL_CAPACITY)] = 50) -> dict:
        files = sorted(outputs.glob("call_list_*.parquet"))
        if not files:
            raise HTTPException(status_code=404, detail="Chưa có danh sách gọi — chạy `make score` trước")
        calls = pd.read_parquet(files[-1]).head(k)
        calls["t"] = calls["t"].dt.strftime("%Y-%m-%d")
        return {"file": files[-1].name, "rows": calls.round(4).to_dict(orient="records")}

    @app.get("/", response_class=HTMLResponse)
    def demo() -> str:
        return DEMO_PAGE.read_text(encoding="utf-8")  # trang tĩnh; dữ liệu lấy qua /top bằng khoá người dùng nhập

    return app
```

- **Factory** `create_app(...)` thay cho biến `app` toàn cục: test tạo app với model và khoá riêng, production đọc biến
  môi trường. uvicorn gọi factory bằng cờ `--factory`.
- **Hỏng sớm**: thiếu `CHURN_API_KEY` hoặc thiếu model thì dừng ngay khi khởi động.
- **`require_key`** là một *dependency* của FastAPI, gắn vào endpoint bằng `dependencies=[Depends(require_key)]`.
  `secrets.compare_digest` so sánh trong thời gian hằng số, để kẻ tấn công không đoán được khoá qua thời gian phản hồi.
- **`/score`**: chuyển request thành DataFrame **cùng kiểu dữ liệu như lúc train** (category, float), rồi gọi đúng các
  hàm đã dùng khi chấm điểm theo lô (`bundle.proba`, `decision.expected_value`, `explain.reasons`). Một test kiểm tra
  API cho đúng xác suất của chấm điểm theo lô.
- **Log** chỉ ghi số khách và thời gian xử lý, **không** ghi feature: log thường được gửi tới nhiều hệ thống khác, nên
  không được thành đường rò dữ liệu khách.
- **`/top`** đọc danh sách gọi mới nhất mà `make score` đã tạo; chưa có thì trả 404 kèm hướng dẫn. `k` bị giới hạn
  1–500 bằng `Query(ge=1, le=...)`.
- **`/`** trả trang demo tĩnh. Trang này không chứa dữ liệu; nó gọi `/top` bằng khoá người dùng nhập.

**File: `src/churn_telco/demo.html`**

```html
<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Danh sách gọi giữ chân</title>
<style>
  body { font: 15px system-ui, sans-serif; margin: 24px; max-width: 1100px }
  table { border-collapse: collapse; width: 100% }
  td, th { border-bottom: 1px solid #ddd; padding: 6px; text-align: left; vertical-align: top }
  small { color: #666 }
</style></head>
<body><h1>Danh sách gọi giữ chân khách hàng</h1>
<p><small id="ver"></small></p>
<form id="f"><input id="key" type="password" placeholder="X-API-Key" required> <button>Xem 50 khách đầu</button></form>
<p id="msg"></p><table id="tbl"></table>
<script>
fetch('/version').then(r => r.json()).then(v => {
  document.getElementById('ver').textContent = `Model ${v.name} · phiên bản ${v.version} · train ${v.trained_at}`;
});
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
document.getElementById('f').onsubmit = async (e) => {
  e.preventDefault();
  const r = await fetch('/top?k=50', {headers: {'X-API-Key': document.getElementById('key').value}});
  const msg = document.getElementById('msg'), tbl = document.getElementById('tbl');
  if (!r.ok) { msg.textContent = (await r.json()).detail; tbl.innerHTML = ''; return; }
  const data = await r.json();
  msg.textContent = `${data.file} — xếp theo giá trị kỳ vọng của cuộc gọi`;
  const reasons = x => [1, 2, 3].filter(i => x['reason_' + i])
    .map(i => `${esc(x['reason_' + i])}<br><small>→ ${esc(x['action_' + i])}</small>`).join('<br>');
  tbl.innerHTML = '<tr><th>#</th><th>Khách</th><th>Xác suất</th><th>EV (đ)</th><th>Lý do → việc nên làm</th></tr>' +
    data.rows.map(x => `<tr><td>${x.rank}</td>
      <td>${esc(x.customer_id)}<br><small>${esc(x.province)} · ${esc(x.plan_code)}</small></td>
      <td>${(100 * x.p).toFixed(0)}%</td><td>${Math.round(x.ev).toLocaleString('vi-VN')}</td>
      <td>${reasons(x)}</td></tr>`).join('');
};
</script></body></html>
```

Hàm `esc` thoát ký tự HTML trước khi chèn dữ liệu vào trang, để tránh chèn mã (XSS) từ dữ liệu.

Chạy API trên máy:

```bash
make setup      # tạo .env từ .env.example nếu chưa có — đổi CHURN_API_KEY thành một khoá ngẫu nhiên
make serve
```

```text
INFO:     Started server process [12229]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Thiếu khoá thì không khởi động:

```text
RuntimeError: Thiếu CHURN_API_KEY — tạo .env từ .env.example rồi đặt một khoá ngẫu nhiên
```

Mở http://127.0.0.1:8000/docs: FastAPI sinh tài liệu tương tác từ schema, gồm cả các giá trị tỉnh hợp lệ.

### A7.2 Gọi API như một hệ thống khác

**File: `labs/ops-01-co-ban-dong-goi-api/call_api.py`**

```python
"""Lab A7 · OPS-01: gọi API chấm điểm như một hệ thống khác sẽ gọi — đúng, sai, và nhanh tới đâu.

Chạy API trước (một trong hai cách), rồi chạy file này ở terminal khác:
    cd projects/g1-churn-telco && make serve          # hoặc: make docker-up
    cd labs/ops-01-co-ban-dong-goi-api
    uv run --project ../../projects/g1-churn-telco python call_api.py --url http://127.0.0.1:8000

Khoá API đọc từ biến môi trường CHURN_API_KEY, nếu không có thì từ file projects/g1-churn-telco/.env.
"""

import argparse
import json
import os
import statistics
import time

import httpx
from churn_telco import config, features, split


def api_key() -> str:
    if key := os.getenv("CHURN_API_KEY"):
        return key
    for line in (config.ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("CHURN_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("Không tìm thấy CHURN_API_KEY (biến môi trường hoặc .env của dự án)")


def records(n: int, feature_names: list[str]) -> list[dict]:
    """n khách của tháng mới nhất trong bảng học, đúng định dạng JSON mà API nhận."""
    df = features.load()
    latest = split.split(df)["test"].query("t == t.max()").head(n)
    return json.loads(latest[["customer_id", *feature_names]].to_json(orient="records"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--n-latency", type=int, default=50, help="số request để đo độ trễ")
    args = parser.parse_args()
    client = httpx.Client(base_url=args.url, timeout=10, trust_env=False)  # gọi thẳng, không qua proxy hệ thống
    auth = {"X-API-Key": api_key()}

    # 1. Sống chưa, model nào đang chạy? — hai endpoint không cần khoá
    print("1) /health:", client.get("/health").json())
    version = client.get("/version").json()
    print(f"   /version: {version['name']} · phiên bản {version['version']} · train {version['trained_at']}")
    feature_names = client.get("/openapi.json").json()["components"]["schemas"]["Customer"]["properties"]
    feature_names = [f for f in feature_names if f != "customer_id"]

    # 2. Chấm điểm 3 khách
    batch = records(3, feature_names)
    for item in client.post("/score", json={"customers": batch}, headers=auth).json():
        reasons = "; ".join(r["text"] for r in item["reasons"]) or "—"
        print(f"2) {item['customer_id']}: p={item['probability']:.1%} EV={item['expected_value']:,.0f} đ · {reasons}")

    # 3. Sai thì phải sai RÕ RÀNG: thiếu khoá → 401, dữ liệu sai → 422 kèm chỗ sai
    print("3) Không có khoá:", client.post("/score", json={"customers": batch}).status_code)
    bad = client.post("/score", json={"customers": [{**batch[0], "province": "Sài Gòn"}]}, headers=auth)
    detail = bad.json()["detail"][0]
    print(f"   Tỉnh không hợp lệ: {bad.status_code} · {detail['loc']} · {detail['msg'][:60]}…")

    # 4. Độ trễ: từng khách một (như màn hình CRM gọi) và theo lô 500 khách (như job hằng tháng)
    one = records(1, feature_names)
    latencies = []
    for _ in range(args.n_latency):
        start = time.perf_counter()
        client.post("/score", json={"customers": one}, headers=auth).raise_for_status()
        latencies.append(1000 * (time.perf_counter() - start))
    p95 = statistics.quantiles(latencies, n=20)[-1]
    print(f"4) {args.n_latency} request × 1 khách: trung vị {statistics.median(latencies):.0f} ms · p95 {p95:.0f} ms")
    big = records(500, feature_names)
    start = time.perf_counter()
    client.post("/score", json={"customers": big}, headers=auth).raise_for_status()
    print(f"   1 request × 500 khách: {1000 * (time.perf_counter() - start):.0f} ms")

    # 5. Danh sách gọi tháng mới nhất (job `make score` tạo ra)
    top = client.get("/top", params={"k": 3}, headers=auth)
    if top.status_code == 200:
        for row in top.json()["rows"]:
            print(f"5) #{row['rank']} {row['customer_id']} p={row['p']:.0%} · {row['reason_1']}")
    else:
        print("5) /top:", top.status_code, top.json()["detail"])


if __name__ == "__main__":
    main()
```

- Danh sách feature lấy từ chính `/openapi.json` của API: client tự biết API đang đòi trường gì.
- `trust_env=False`: gọi thẳng localhost, không đi qua proxy hệ thống (máy công ty thường có proxy).
- Đo độ trễ bằng nhiều request rồi báo **trung vị và p95**, không báo trung bình: vài request chậm bất thường làm lệch
  trung bình.

```bash
cd labs/ops-01-co-ban-dong-goi-api
uv run --project ../../projects/g1-churn-telco python call_api.py --url http://127.0.0.1:8000
```

```text
1) /health: {'status': 'ok'}
   /version: LightGBM v2 · phiên bản v2-488c967b · train 2026-10-18T11:19:39+00:00
2) KH000001: p=1.0% EV=-20,305 đ · Không có hợp đồng kỳ hạn — có thể rời mạng bất cứ lúc nào; Gói SX300, cước 320.000 đ/tháng
2) KH000005: p=10.5% EV=46,842 đ · Chất lượng mạng: mất mạng 2029 phút tháng trước, 5 lần báo lỗi mạng trong 60 ngày; Không có hợp đồng kỳ hạn — có thể rời mạng bất cứ lúc nào; Tháng trước dùng 336 GB, bằng 75% mức trung bình 3 tháng trước đó
2) KH000006: p=1.2% EV=-19,510 đ · Không có hợp đồng kỳ hạn — có thể rời mạng bất cứ lúc nào
3) Không có khoá: 401
   Tỉnh không hợp lệ: 422 · ['body', 'customers', 0, 'province'] · Input should be 'TP. Hồ Chí Minh', 'Hà Nội', 'Đà Nẵng', 'Hải…
4) 50 request × 1 khách: trung vị 38 ms · p95 62 ms
   1 request × 500 khách: 739 ms
5) #1 KH000113 p=94% · Hợp đồng 12 tháng hết hạn hôm nay
5) #2 KH024223 p=45% · Tháng trước dùng 134 GB, bằng 47% mức trung bình 3 tháng trước đó
5) #3 KH017489 p=71% · Hợp đồng 24 tháng hết hạn hôm nay
```

Độ trễ phụ thuộc máy; trên laptop của bạn số có thể khác. Chấm 500 khách trong **một** request (0,7 giây) nhanh hơn
nhiều so với 500 request riêng lẻ (500 × 38 ms ≈ 19 giây): gửi theo lô khi có thể.

Test API dùng `TestClient` (không cần chạy server), mỗi test một hành vi của hợp đồng ở mục 1.2:

**File: `tests/test_api.py` · `test_requires_api_key_to_start…test_score_matches_batch_scoring`**

```python
def test_requires_api_key_to_start(small, monkeypatch):
    monkeypatch.delenv("CHURN_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="CHURN_API_KEY"):
        api.create_app(small.root / "models" / "lgbm-v2")


def test_health_and_version_are_public(client, small):
    assert client.get("/health").json() == {"status": "ok"}
    version = client.get("/version").json()
    assert version["name"] == "LightGBM v2" and version["best_iteration"] == small.bundle.meta["best_iteration"]


def test_score_needs_the_key(client, payload):
    _, records = payload
    assert client.post("/score", json={"customers": records}).status_code == 401
    assert client.post("/score", json={"customers": records}, headers={"X-API-Key": "sai"}).status_code == 401


def test_score_matches_batch_scoring(client, payload, small):
    rows, records = payload
    out = client.post("/score", json={"customers": records}, headers={"X-API-Key": KEY}).json()
    np.testing.assert_allclose([o["probability"] for o in out], small.bundle.proba(rows), rtol=1e-9)
    assert all(len(o["reasons"]) <= 3 for o in out)
```

### A7.3 Docker

**File: `Dockerfile`**

```dockerfile
# API chấm điểm churn (A7 · OPS-01). Image chỉ chứa code + thư viện lõi; model và danh sách gọi gắn vào lúc chạy
# (docker-compose.yml), nên đổi model không phải build lại image.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

# libgomp1: LightGBM cần OpenMP. uv cài bằng pip để không phụ thuộc registry nào khác ngoài PyPI.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.11.32

WORKDIR /app

# 1) Thư viện trước, đúng phiên bản trong uv.lock, chỉ nhóm lõi (không shap/mlflow/pytest).
#    Lớp này được cache: sửa code rồi build lại không phải cài lại thư viện.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-default-groups --no-install-project

# 2) Rồi mới tới code.
COPY src ./src
RUN uv sync --locked --no-default-groups

# Không chạy bằng root: lỡ có lỗ hổng thì kẻ tấn công cũng không có quyền root trong container.
RUN useradd --create-home --uid 10001 app
USER app
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["uvicorn", "churn_telco.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

**File: `.dockerignore`**

```gitignore
# Chỉ gửi vào Docker build những gì image cần: code + lockfile. Không dữ liệu, không model, không secret.
.venv/
data/
models/
mlruns/
reports/
eval/
tests/
.env
**/__pycache__/
.pytest_cache/
.ruff_cache/
```

**File: `docker-compose.yml`**

```yaml
# A7 · `docker compose up --build -d` → API tại http://127.0.0.1:8000 (tài liệu tương tác: /docs, trang demo: /)
# Cần trước: `make train-v2 score` (model trong models/, danh sách gọi trong data/outputs/) và file .env có CHURN_API_KEY.
services:
  api:
    build: .
    image: churn-telco-api:0.1.0
    ports:
      - "127.0.0.1:8000:8000" # chỉ mở trên máy mình; mở ra mạng thì đặt sau reverse proxy có HTTPS
    env_file: .env # CHURN_API_KEY — secret nằm ngoài image và ngoài Git
    environment:
      CHURN_MODEL_DIR: /app/models/lgbm-v2
      CHURN_OUTPUTS: /app/outputs
    volumes:
      - ./models:/app/models:ro # chỉ đọc: container không sửa được model
      - ./data/outputs:/app/outputs:ro
    read_only: true # hệ thống file của container chỉ đọc
    tmpfs:
      - /tmp
    restart: unless-stopped
```

- `.dockerignore` giữ dữ liệu, model, `.env`, `.venv` **ngoài** ngữ cảnh build. Thiếu file này, `docker build` gửi cả
  gigabyte dữ liệu khách vào image.
- `uv sync --locked --no-default-groups --no-install-project` cài thư viện lõi trước khi có code. Lần `uv sync` thứ hai
  chỉ cài package dự án.
- `libgomp1`: LightGBM cần thư viện OpenMP của hệ thống. Thiếu nó, `import lightgbm` lỗi ngay khi khởi động.
- `HEALTHCHECK` gọi `/health` bằng Python có sẵn trong image (không cần cài `curl`).
- `ports: "127.0.0.1:8000:8000"`: chỉ mở cổng trên chính máy bạn. Muốn mở ra mạng thì đặt sau reverse proxy có HTTPS.

```bash
make docker-up
docker compose ps
```

```text
NAME                   IMAGE                   COMMAND                  SERVICE   CREATED         STATUS                   PORTS
g1-churn-telco-api-1   churn-telco-api:0.1.0   "uvicorn churn_telco…"   api       8 seconds ago   Up 6 seconds (healthy)   127.0.0.1:8000->8000/tcp
```

Kiểm tra các lớp bảo vệ bên trong container:

```bash
docker compose exec api sh -c 'id; touch /app/x; python -c "import shap"'
```

```text
uid=10001(app) gid=10001(app) groups=10001(app)
touch: cannot touch '/app/x': Read-only file system
ModuleNotFoundError: No module named 'shap'
```

Container chạy bằng user thường, không ghi được file, không có thư viện phân tích. Image nặng khoảng 410 MB (nén). Gọi
`call_api.py` vào container cho kết quả giống hệt mục A7.2. Dừng bằng `make docker-down`.

### A7.4 MLflow

**File: `src/churn_telco/tracking.py`**

```python
"""Ghi mỗi lần train vào MLflow (A7 · OPS-02): tham số, metric, phiên bản dữ liệu, commit và chính model.

Training (A5) đã ghi mọi thứ vào models/<tên>/bundle.json; module này chỉ "gửi" bundle đó lên MLflow, nên tracking
không làm rối code train và thay MLflow bằng công cụ khác chỉ phải sửa một file. Kho MLflow cục bộ: mlruns/ (SQLite +
thư mục artifact), xem bằng `make mlflow-ui`.

    uv run python -m churn_telco.tracking models/lgbm-v1 models/lgbm-v2
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")  # tắt dòng gợi ý in ra mỗi lần import mlflow

import mlflow  # noqa: E402

from churn_telco import config  # noqa: E402

MLRUNS = Path(os.getenv("CHURN_MLRUNS", config.ROOT / "mlruns"))
EXPERIMENT = "churn-30d"


def setup(store: Path = MLRUNS) -> str:
    store.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{store / 'mlflow.db'}")
    if mlflow.get_experiment_by_name(EXPERIMENT) is None:
        mlflow.create_experiment(EXPERIMENT, artifact_location=(store / "artifacts").as_uri())
    mlflow.set_experiment(EXPERIMENT)
    return mlflow.get_tracking_uri()


def log_bundle(path: Path, store: Path = MLRUNS, eval_report: Path | None = None) -> str:
    """Một run MLflow cho một bundle; trả về run_id."""
    setup(store)
    meta = json.loads((path / "bundle.json").read_text(encoding="utf-8"))
    with mlflow.start_run(run_name=meta["name"]) as run:
        mlflow.log_params({f"lgb.{k}": v for k, v in meta["params"].items()})
        mlflow.log_params({"feature_set": meta["feature_set"], "n_features": len(meta["features"])})
        mlflow.log_params(
            {"best_iteration": meta["best_iteration"], "train_period": "..".join(meta["data"]["train_period"])}
        )
        mlflow.log_metrics(
            {f"valid_{k.replace('@k', f'_at_{config.CALL_CAPACITY}')}": v for k, v in meta["valid"].items()}
        )
        mlflow.set_tags(
            {
                "data.features_sha256": meta["data"].get("features_sha256", "chưa ghi"),
                "git_commit": meta.get("git_commit") or "không có",
                "model_version": meta.get("version", meta["feature_set"]),
            }
        )
        mlflow.log_artifacts(str(path), artifact_path="bundle")  # model.txt + bundle.json: tải về là phục vụ được
        if eval_report and eval_report.exists():
            mlflow.log_artifact(str(eval_report))
        return run.info.run_id


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ghi bundle model vào MLflow")
    parser.add_argument("bundles", type=Path, nargs="+")
    args = parser.parse_args(argv)
    report = config.REPORTS / "eval_test.md"
    for path in args.bundles:
        print(f"{path.name}: run {log_bundle(path, eval_report=report)} → {mlflow.get_tracking_uri()}")


if __name__ == "__main__":
    main()
```

- `MLFLOW_DISABLE_AGENT_HINT` được đặt **trước** `import mlflow` (vì vậy mới có `# noqa: E402`), để tắt dòng gợi ý
  mlflow in ra mỗi lần import.
- Kho MLflow cục bộ: SQLite (`mlruns/mlflow.db`) cho metadata, thư mục `mlruns/artifacts/` cho file. Cùng một code chạy
  được với MLflow server của công ty: chỉ cần đổi `tracking_uri`.
- `log_bundle` đọc `bundle.json` và ghi: tham số (`lgb.*`, tập feature, số cây, giai đoạn train), metric valid,
  **tag** mã băm dữ liệu + commit + phiên bản model, và **artifact** là cả thư mục bundle cùng báo cáo đánh giá.

```bash
make track
```

```text
lgbm-v1: run ce8684d9927240deb428222859f8ee06 → sqlite:////…/projects/g1-churn-telco/mlruns/mlflow.db
lgbm-v2: run fa2f87ebe6154ee79f3399da26ba3d35 → sqlite:////…/projects/g1-churn-telco/mlruns/mlflow.db
```

`make mlflow-ui` mở giao diện ở http://127.0.0.1:5000: chọn hai run v1 và v2, bấm *Compare* để xem tham số và metric
cạnh nhau. Tab *Artifacts* tải được `model.txt`. Để **tái tạo** metric của một run cũ (OPS-02 "Đạt khi"): lấy tag
`git_commit`, checkout commit đó, chạy `make data features`, kiểm tra mã băm file feature trùng tag
`data.features_sha256`, rồi `make train`. Dữ liệu và code giống từng bit nên metric giống từng chữ số.

### A7.5 Rà soát bảo mật trước khi push

**File: `labs/ops-01-co-ban-dong-goi-api/security_check.py`**

```python
"""Lab A7 · OPS-08: rà soát trước khi push — repo không chứa secret, không chứa dữ liệu khách, output không lộ PII.

Bốn kiểm tra, mỗi cái in ✔ hoặc ✘; có ✘ thì thoát mã 1 (gắn được vào pre-commit hoặc CI):
1. File đang được Git theo dõi không chứa chuỗi giống khoá bí mật và không có file .env thật.
2. Lịch sử Git chưa từng chứa .env hay dữ liệu thô của dự án (xoá ở commit sau vẫn còn trong lịch sử!).
3. Thư mục dữ liệu, model, mlruns của dự án nằm trong .gitignore.
4. Bảng trung gian và danh sách gọi không có cột/giá trị PII (tên, số điện thoại, email).
Cuối cùng in bảng phân loại dữ liệu: cột nào được phép rời khỏi hệ thống, tới đâu.

    cd labs/ops-01-co-ban-dong-goi-api
    uv run --project ../../projects/g1-churn-telco python security_check.py
"""

import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
from churn_telco import config
from churn_telco.clean import PII_COLUMNS

REPO = config.ROOT.parents[1]
PROJECT = config.ROOT.relative_to(REPO).as_posix()
SECRET_PATTERNS = {
    "khoá riêng (private key)": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "OpenAI/Anthropic key": re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
}
PHONE = re.compile(r"(?<![\d.])0[35789]\d{8}(?!\d)")  # 10 số bắt đầu 03/05/07/08/09, không phải phần thập phân
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
problems: list[str] = []


def git(*args: str) -> list[str]:
    out = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


def check(ok: bool, message: str) -> None:
    print(f"   {'✔' if ok else '✘'} {message}")
    if not ok:
        problems.append(message)


# 1. File đang theo dõi
print("1) File Git đang theo dõi:")
tracked = git("ls-files")
env_files = [f for f in tracked if Path(f).name.startswith(".env") and not f.endswith(".env.example")]
check(not env_files, f"không có file .env thật ({env_files or 'không có'})")
hits = []
for name in tracked:
    path = REPO / name
    if path.suffix in {".png", ".jpg", ".parquet", ".lock", ".ico", ".pdf"} or not path.is_file():
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    hits += [f"{name}: {kind}" for kind, pattern in SECRET_PATTERNS.items() if pattern.search(text)]
check(not hits, f"không có chuỗi giống khoá bí mật trong {len(tracked)} file ({hits[:3] or 'sạch'})")

# 2. Lịch sử Git
print("2) Lịch sử Git (mọi commit, mọi nhánh):")
ever = set(git("log", "--all", "--name-only", "--format="))
bad = sorted(f for f in ever if (Path(f).name == ".env") or f.startswith(f"{PROJECT}/data/"))
check(not bad, f"chưa từng commit .env hay {PROJECT}/data/ ({bad[:3] or 'sạch'})")

# 3. .gitignore
print("3) .gitignore:")
for folder in ("data/raw/customers.csv", "models/lgbm-v2/model.txt", "mlruns/mlflow.db", ".env"):
    ignored = subprocess.run(["git", "check-ignore", "-q", f"{PROJECT}/{folder}"], cwd=REPO).returncode == 0
    check(ignored, f"{PROJECT}/{folder} bị Git bỏ qua")

# 4. PII trong dữ liệu đã xử lý và output
print("4) PII trong dữ liệu sau bước làm sạch:")
for path in sorted(config.INTERIM.glob("*.parquet")) + sorted(config.PROCESSED.glob("*.parquet")):
    columns = set(pd.read_parquet(path).columns)
    check(not columns & set(PII_COLUMNS), f"{path.relative_to(config.DATA)}: không có cột {PII_COLUMNS}")
for path in sorted((config.DATA / "outputs").glob("*.csv")):
    text = path.read_text(encoding="utf-8-sig")
    check(
        not (PHONE.search(text) or EMAIL.search(text)), f"{path.relative_to(config.DATA)}: không có số điện thoại/email"
    )

print("\nPhân loại dữ liệu — được phép đi đâu:")
print("   | Dữ liệu                         | Ví dụ                     | Được phép                              |")
print("   |---------------------------------|---------------------------|----------------------------------------|")
print("   | Định danh cá nhân (PII)         | tên, SĐT, email           | chỉ trong CRM, không vào pipeline ML   |")
print("   | Mã khách (bí danh)              | KH000113                  | nội bộ: pipeline, API, danh sách gọi   |")
print("   | Hành vi theo khách              | data dùng, ticket, cước   | nội bộ; KHÔNG gửi API bên ngoài (LLM)  |")
print("   | Số tổng hợp ≥ 50 khách mỗi ô    | tỷ lệ churn theo tỉnh     | báo cáo, slide, gửi đối tác            |")
print("   | Secret                          | CHURN_API_KEY             | chỉ biến môi trường / .env cục bộ      |")
if problems:
    print(f"\n✘ {len(problems)} vấn đề — sửa trước khi push")
    sys.exit(1)
print("\n✔ Sạch — có thể push")
```

- Rà **mọi file Git đang theo dõi** tìm chuỗi giống khoá bí mật (khoá riêng, khoá OpenAI/Anthropic, AWS, GitHub).
- Rà **cả lịch sử** (`git log --all --name-only`) tìm `.env` hay dữ liệu của dự án từng bị commit.
- Kiểm tra `.gitignore` bằng `git check-ignore` cho từng loại file nhạy cảm.
- Kiểm tra dữ liệu sau làm sạch không còn cột PII, và danh sách gọi không chứa số điện thoại/email. Regex số điện thoại
  có `(?<![\d.])`: không bắt nhầm phần thập phân của xác suất, vì `0.0912345678` trông giống một số điện thoại.
- Có vấn đề thì thoát mã 1: gắn được vào pre-commit hoặc CI.

```bash
uv run --project ../../projects/g1-churn-telco python security_check.py
```

```text
1) File Git đang theo dõi:
   ✔ không có file .env thật (không có)
   ✔ không có chuỗi giống khoá bí mật trong 503 file (sạch)
2) Lịch sử Git (mọi commit, mọi nhánh):
   ✔ chưa từng commit .env hay projects/g1-churn-telco/data/ (sạch)
3) .gitignore:
   ✔ projects/g1-churn-telco/data/raw/customers.csv bị Git bỏ qua
   ✔ projects/g1-churn-telco/models/lgbm-v2/model.txt bị Git bỏ qua
   ✔ projects/g1-churn-telco/mlruns/mlflow.db bị Git bỏ qua
   ✔ projects/g1-churn-telco/.env bị Git bỏ qua
4) PII trong dữ liệu sau bước làm sạch:
   ✔ interim/customers.parquet: không có cột ['full_name', 'phone', 'email']
   ...
   ✔ outputs/call_list_2026-01-01.csv: không có số điện thoại/email

Phân loại dữ liệu — được phép đi đâu:
   | Dữ liệu                         | Ví dụ                     | Được phép                              |
   |---------------------------------|---------------------------|----------------------------------------|
   | Định danh cá nhân (PII)         | tên, SĐT, email           | chỉ trong CRM, không vào pipeline ML   |
   | Mã khách (bí danh)              | KH000113                  | nội bộ: pipeline, API, danh sách gọi   |
   | Hành vi theo khách              | data dùng, ticket, cước   | nội bộ; KHÔNG gửi API bên ngoài (LLM)  |
   | Số tổng hợp ≥ 50 khách mỗi ô    | tỷ lệ churn theo tỉnh     | báo cáo, slide, gửi đối tác            |
   | Secret                          | CHURN_API_KEY             | chỉ biến môi trường / .env cục bộ      |

✔ Sạch — có thể push
```

Ở lần chạy đầu tiên, kiểm tra cuối từng **đỏ**: regex số điện thoại bắt nhầm xác suất `0.0912345678` trong file CSV.
Kiểm tra bảo mật cũng cần được kiểm tra, và một báo động giả là lý do để sửa regex, không phải lý do để tắt kiểm tra.

---

## 5 · Kiểm tra kết quả

- [ ] `make docker-up` → `docker compose ps` báo `(healthy)`; `/version` cho biết model, phiên bản, mã băm dữ liệu
      (OPS-01 "Đạt khi").
- [ ] `/score` không khoá → 401, tỉnh lạ → 422, thiếu trường bắt buộc → 422, quá 1.000 khách → 422 (có test).
- [ ] MLflow có run v1 và v2 với tham số, metric, tag mã băm dữ liệu và commit; tải được `model.txt` (OPS-02).
- [ ] `security_check.py` in "✔ Sạch"; bạn có bảng phân loại dữ liệu nào được gửi đi đâu (OPS-08 "Đạt khi").

## 6 · Lỗi thường gặp

| Triệu chứng | Nguyên nhân | Cách sửa |
|---|---|---|
| FastAPI coi body là query param, trả 422 khó hiểu | `from __future__ import annotations` + kiểu tạo động | bỏ import đó ở file có kiểu tạo động |
| Container khởi động rồi chết: `libgomp.so.1` | thiếu OpenMP trong image slim | `apt-get install libgomp1` |
| Build Docker rất chậm mỗi lần sửa code | chép code trước khi cài thư viện | cài từ lockfile trước, chép `src/` sau |
| Image chứa dữ liệu hoặc `.env` | thiếu `.dockerignore` | `.dockerignore` loại `data/`, `models/`, `.env`, `.venv/` |
| Không biết model nào đang chạy | không có `/version`, bundle không ghi phiên bản | `/version` + `bundle.json` + MLflow |
| Lộ khoá trong lịch sử Git | commit `.env` rồi mới xoá | đổi khoá ngay; `.gitignore` từ commit đầu; `security_check.py` trước khi push |

## 7 · Bài tập

1. **(Cơ bản — OPS-01)** Thêm endpoint `GET /customers/{customer_id}` trả dòng của khách đó trong danh sách gọi mới
   nhất (404 nếu không có). Viết test.
2. **(Cơ bản — OPS-08)** Thêm vào `security_check.py` kiểm tra: không file nào trong `reports/` chứa mã khách
   (`KH\d{6}`). Báo cáo chỉ nên có số tổng hợp.
3. **(Trung cấp — OPS-01)** Đo độ trễ khi 10 client gọi đồng thời (`concurrent.futures`). p95 còn dưới 200 ms không?
   Nếu không, thử chạy uvicorn với `--workers 2`.
4. **(Trung cấp — OPS-02)** Làm đúng quy trình tái tạo ở mục A7.4 cho run v1 trong 10 phút, kể cả khi đã chạy
   `make clean`. Ghi lại các bước vào README dự án.
5. **(Mở rộng)** Image hiện gắn model qua volume. Viết `Dockerfile.model` **chép model vào image** và gắn nhãn phiên
   bản (`LABEL model_version=...`). So ưu nhược điểm hai cách cho việc rollback.

---

**Tiếp theo:** [A8 · Trình bày kết quả — mốc giai đoạn A](a8-trinh-bay-ket-qua.md). Quy tất cả ra một trang mà trưởng
phòng CSKH đọc trong 10 phút và quyết định được.
