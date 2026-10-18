# OPS-01 · Cơ bản · API chấm điểm FastAPI + Docker, MLflow và bảo mật dữ liệu

**Kỹ năng:** [OPS-01 Đóng gói và phục vụ model](../../docs/02-skill-map/generated/mang/ops.md#ops-01) · **Mức:** Cơ bản
(kèm [OPS-02](../../docs/02-skill-map/generated/mang/ops.md#ops-02), [OPS-08](../../docs/02-skill-map/generated/mang/ops.md#ops-08) Cơ bản)
**Thời lượng:** ~4 giờ · **Môi trường:** `cd projects/g1-churn-telco && make setup` + Docker · **Chi phí API ước tính:** 0 USD

## Mục tiêu

Sau lab này `docker compose up` cho ra API chấm điểm có health check, version model, khoá API; mọi lần train nằm
trong MLflow; và bạn có một lệnh rà soát repo không chứa secret hay dữ liệu khách trước khi push.

## Dữ liệu

Model `models/lgbm-v2/` và danh sách gọi `data/outputs/` (`make train-v2 score`).

## Các bước

Làm theo [Bài A7](../../docs/03-giai-doan-a-nen-tang/a7-api-docker-mlflow-bao-mat.md):

1. Viết `api.py`, chạy `make serve`, mở http://127.0.0.1:8000/docs.
2. Gọi API như một hệ thống khác:

   ```bash
   cd labs/ops-01-co-ban-dong-goi-api
   uv run --project ../../projects/g1-churn-telco python call_api.py --url http://127.0.0.1:8000
   ```

3. `Dockerfile` + `docker-compose.yml`, chạy `make docker-up`, kiểm tra `docker compose ps` báo `(healthy)`.
4. `tracking.py`, chạy `make track mlflow-ui`.
5. Rà soát bảo mật: `uv run --project ../../projects/g1-churn-telco python security_check.py`.

## Kiểm tra kết quả

- [ ] `/health` 200; `/version` cho biết model, phiên bản, mã băm dữ liệu; `/score` không khoá → 401, dữ liệu sai → 422.
- [ ] Container chạy bằng user thường, hệ thống file chỉ đọc, không chứa shap/mlflow/pytest.
- [ ] MLflow có 2 run (v1, v2) với tham số, metric, mã băm dữ liệu, commit; tải được `model.txt` về.
- [ ] `security_check.py` in "✔ Sạch".

## Câu hỏi mở rộng

- Tái tạo đúng metric valid của run v1 từ MLflow trong 10 phút (dữ liệu nào, commit nào, lệnh nào?).
- Đo độ trễ khi 10 client gọi đồng thời; p95 có còn dưới 200 ms không?
