# DATA-03 · Trung cấp · Feature as-of và bắt rò rỉ dữ liệu

**Kỹ năng:** [DATA-03 Đúng thời điểm và chống rò rỉ dữ liệu](../../docs/02-skill-map/generated/mang/data.md#data-03) · **Mức:** Trung cấp
(kèm [DATA-04](../../docs/02-skill-map/generated/mang/data.md#data-04), [DATA-05](../../docs/02-skill-map/generated/mang/data.md#data-05) Cơ bản)
**Thời lượng:** ~4 giờ · **Môi trường:** `cd projects/g1-churn-telco && make setup` · **Chi phí API ước tính:** 0 USD

## Mục tiêu

Sau lab này bạn dựng được bảng học "as-of" từ 8 bảng vận hành bằng một câu SQL, chứng minh nó không rò rỉ bằng test
đúng thời điểm, và nhận ra rò rỉ qua kết quả "quá đẹp", AUC từng feature, độ quan trọng bất thường.

## Dữ liệu

`data/interim/` của dự án (`make clean-data`).

## Các bước

Làm theo [Bài A4](../../docs/03-giai-doan-a-nen-tang/a4-feature-as-of-ro-ri.md):

1. Viết `features.py` (SQL as-of: ASOF JOIN, FILTER theo cửa sổ, lọc theo `logged_at`) và `schemas.py` (pandera).
2. Chạy `make features`, rồi `uv run pytest tests/test_features.py` — test đúng thời điểm phải xanh.
3. Cố tình gây rò rỉ và bắt nó:

   ```bash
   cd labs/data-03-trung-cap-ro-ri-du-lieu
   uv run --project ../../projects/g1-churn-telco python leakage_lab.py
   ```

## Kiểm tra kết quả

- [ ] AUC valid của bản rò rỉ (≈ 0,97) cao bất thường so với bản as-of (≈ 0,73) và bạn chỉ ra được cột gây ra nó.
- [ ] Test đúng thời điểm xanh với `logged_at`, đỏ với `created_at` — dù AUC hai bản gần như bằng nhau.
- [ ] Pipeline tự dừng với thông báo rõ ràng khi bảng học có dòng trùng hoặc tháng thiếu khách (test schema).

## Câu hỏi mở rộng

- Cột `status` của khách lúc chấm điểm thật tháng 01/2026 có giá trị gì? Vì sao nó "đẹp" khi train?
- Thêm feature `days_since_plan_change` (đổi gói gần nhất) theo đúng ba quy tắc as-of, kèm test.
