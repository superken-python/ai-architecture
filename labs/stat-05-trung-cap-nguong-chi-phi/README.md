# STAT-05 · Trung cấp · LightGBM, hiệu chỉnh xác suất và ngưỡng theo chi phí

**Kỹ năng:** [STAT-05 Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc](../../docs/02-skill-map/generated/mang/stat.md#stat-05) · **Mức:** Trung cấp
(kèm [ML-02](../../docs/02-skill-map/generated/mang/ml.md#ml-02), [ML-03](../../docs/02-skill-map/generated/mang/ml.md#ml-03) Trung cấp)
**Thời lượng:** ~4 giờ · **Môi trường:** `cd projects/g1-churn-telco && make setup` · **Chi phí API ước tính:** 0 USD

## Mục tiêu

Sau lab này bạn train LightGBM có early stopping, đánh giá đúng cho sự kiện hiếm (PR-AUC, precision@k), kiểm tra
xác suất có đáng tin không, và chọn ngưỡng gọi theo giá trị kỳ vọng và năng lực 500 cuộc/tháng.

## Dữ liệu

Bảng học + model `models/lgbm-v1/` (`make features train`).

## Các bước

Làm theo [Bài A5](../../docs/03-giai-doan-a-nen-tang/a5-lightgbm-nguong-chi-phi.md):

1. Viết `train.py` (bundle = `model.txt` + `bundle.json`) và `decision.py` (Platt, EV, danh sách gọi, đường lợi nhuận).
2. `make train eval` — LightGBM vào bảng so sánh, có KTC và chênh lệch cặp với logistic.
3. Chạy lab:

   ```bash
   cd labs/stat-05-trung-cap-nguong-chi-phi
   uv run --project ../../projects/g1-churn-telco python threshold_lab.py    # biểu đồ trong out/
   ```

## Kiểm tra kết quả

- [ ] LightGBM hơn logistic có ý nghĩa thống kê trên tập đóng băng (KTC chênh lệch cặp của P@500 không chứa 0).
- [ ] Bảng độ tin cậy 10 nhóm: dự đoán ≈ thực tế; bạn giải thích được vì sao class weight phá hỏng nó.
- [ ] Đường coverage–precision–lợi nhuận + một con số khuyến nghị số cuộc gọi mỗi tháng.

## Câu hỏi mở rộng

- Chọn có hiệu chỉnh hay không bằng cross-validation NGAY TRÊN tập valid, thay vì nhìn tập đóng băng.
- Tuning có ngân sách bằng Optuna (50 lần thử) trên valid: P@500 trên tập đóng băng có tăng ngoài biên sai số không?
