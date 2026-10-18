# STAT-02 · Cơ bản · Khoảng tin cậy bootstrap cho bộ đánh giá đóng băng

**Kỹ năng:** [STAT-02 Đo lường bất định của kết quả đánh giá](../../docs/02-skill-map/generated/mang/stat.md#stat-02) · **Mức:** Cơ bản
(kèm [ML-01](../../docs/02-skill-map/generated/mang/ml.md#ml-01), [BIZ-02](../../docs/02-skill-map/generated/mang/biz.md#biz-02) Cơ bản)
**Thời lượng:** ~3 giờ · **Môi trường:** `cd projects/g1-churn-telco && make setup` · **Chi phí API ước tính:** 0 USD

## Mục tiêu

Sau lab này mọi con số đánh giá bạn báo cáo đều kèm khoảng tin cậy 95%, và bạn chỉ kết luận "A tốt hơn B" khi chênh
lệch cặp có khoảng tin cậy không chứa 0.

## Dữ liệu

Bảng học của dự án (`make features`) và bộ đánh giá đóng băng `eval/manifest.json` (3 tháng 10–12/2025).

## Các bước

Làm theo [Bài A3](../../docs/03-giai-doan-a-nen-tang/a3-baseline-bo-danh-gia.md):

1. Viết `split.py` — chia theo thời gian, đóng băng tập test bằng mã băm.
2. Viết `metrics.py` (AUC, PR-AUC, precision@500 theo tháng, bootstrap theo khách) và `baselines.py`.
3. Viết `evaluate.py`, chạy `make eval`.
4. Chạy lab để hiểu khoảng tin cậy từ bên trong:

   ```bash
   cd labs/stat-02-co-ban-bootstrap
   uv run --project ../../projects/g1-churn-telco python bootstrap_lab.py
   ```

## Kiểm tra kết quả

- [ ] `make eval` in bảng 4 baseline, mỗi ô có KTC 95%, cột cuối là chênh lệch cặp so với logistic.
- [ ] Giải thích được vì sao công thức nhanh ±1,96·√(p(1−p)/n) gần bằng bootstrap ở thí nghiệm 1.
- [ ] Giải thích được vì sao chép tập test 3 lần làm KTC "theo dòng" hẹp đi √3 lần mà không thêm thông tin nào.

## Câu hỏi mở rộng

- Cần bao nhiêu tháng đánh giá để KTC của precision@500 còn ±1 điểm phần trăm?
- Viết kiểm định McNemar cho hai danh sách gọi và so với chênh lệch cặp bootstrap.
