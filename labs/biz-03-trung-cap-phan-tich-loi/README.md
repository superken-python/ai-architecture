# BIZ-03 · Trung cấp · Phân tích lỗi, lý do SHAP và kiểm thử pipeline

**Kỹ năng:** [BIZ-03 Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm](../../docs/02-skill-map/generated/mang/biz.md#biz-03) · **Mức:** Trung cấp
(kèm [ML-04](../../docs/02-skill-map/generated/mang/ml.md#ml-04), [PY-03](../../docs/02-skill-map/generated/mang/py.md#py-03) Trung cấp)
**Thời lượng:** ~4 giờ · **Môi trường:** `cd projects/g1-churn-telco && make setup` · **Chi phí API ước tính:** 0 USD

## Mục tiêu

Sau lab này bạn đọc và nhóm được 100 ca sai theo nguyên nhân, sửa nhóm lớn nhất bằng dữ liệu mới, lập bảng
"nhóm lỗi – số ca – đã sửa – metric trước/sau", và sinh 3 lý do dễ hiểu cho từng khách trong danh sách gọi.

## Dữ liệu

Bảng học, model v1 và v2 (`make train train-v2`), lịch khuyến mãi của đối thủ (`data/marketing/`).

## Các bước

Làm theo [Bài A6](../../docs/03-giai-doan-a-nen-tang/a6-phan-tich-loi-shap-test.md):

1. Chạy lab phân tích lỗi trên tập valid:

   ```bash
   cd labs/biz-03-trung-cap-phan-tich-loi
   uv run --project ../../projects/g1-churn-telco python error_analysis.py   # beeswarm trong out/
   ```

2. Viết `marketing.py`, `make train-v2`, so v1 → v2.
3. Viết `explain.py` (SHAP → nhóm lý do → câu tiếng Việt), `score.py`, chạy `make score`.
4. Viết test cho pipeline (`tests/`), chạy `make test`.

## Kiểm tra kết quả

- [ ] Bảng nhóm lỗi với số ca thật từ 100 ca bỏ sót, và metric valid v1 → v2.
- [ ] `data/outputs/call_list_2026-01-01.csv`: 500 khách, mỗi khách tối đa 3 lý do + việc nên làm, không có PII.
- [ ] `make test` xanh; test so SHAP của LightGBM với thư viện shap khớp tới 1e-8.

## Câu hỏi mở rộng

- "Dùng ít đi" là triệu chứng hay nguyên nhân? Tách lý do thành "dấu hiệu" và "nguyên nhân có thể" cho CSKH.
- Nhóm "chuyển nhà" không sửa được bằng feature: đề xuất cách khác (dịch vụ chuyển địa điểm?) và ước lượng giá trị.
