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
