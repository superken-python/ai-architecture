"""A7: API — health/version không cần khoá, chấm điểm cần khoá, đầu vào sai bị từ chối rõ ràng."""

import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from churn_telco import api, score, split

KEY = "khoa-test"


@pytest.fixture(scope="module")
def client(small):
    outputs = small.root / "outputs"
    outputs.mkdir(exist_ok=True)
    return TestClient(api.create_app(small.root / "models" / "lgbm-v2", outputs, api_key=KEY))


@pytest.fixture(scope="module")
def payload(small):
    rows = split.split(small.df)["test"].head(5)
    cols = ["customer_id", *small.bundle.features]
    return rows, json.loads(rows[cols].to_json(orient="records"))


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


@pytest.mark.parametrize(
    ("change", "field"),
    [({"province": "Sài Gòn"}, "province"), ({"tenure_days": "nhiều"}, "tenure_days")],
)
def test_invalid_input_is_rejected(client, payload, change, field):
    _, records = payload
    bad = {**records[0], **change}
    r = client.post("/score", json={"customers": [bad]}, headers={"X-API-Key": KEY})
    assert r.status_code == 422 and field in json.dumps(r.json())


def test_missing_required_feature_is_rejected(client, payload):
    _, records = payload
    bad = {k: v for k, v in records[0].items() if k != "contract_months"}
    assert client.post("/score", json={"customers": [bad]}, headers={"X-API-Key": KEY}).status_code == 422


def test_batch_size_limit(client, payload):
    _, records = payload
    r = client.post("/score", json={"customers": records * 201}, headers={"X-API-Key": KEY})  # 1.005 khách
    assert r.status_code == 422


def test_top_reads_latest_call_list(client, small):
    assert client.get("/top", headers={"X-API-Key": KEY}).status_code == 404  # chưa chạy job chấm điểm
    import pandas as pd

    df = score.build_features(pd.Timestamp("2026-01-01"), small.interim, small.promos)
    score.call_list(small.bundle, df).to_parquet(small.root / "outputs" / "call_list_2026-01-01.parquet")
    r = client.get("/top?k=3", headers={"X-API-Key": KEY})
    assert r.status_code == 200 and len(r.json()["rows"]) == 3
    assert client.get("/top?k=501", headers={"X-API-Key": KEY}).status_code == 422


def test_demo_page(client):
    r = client.get("/")
    assert r.status_code == 200 and "X-API-Key" in r.text
