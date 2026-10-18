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
