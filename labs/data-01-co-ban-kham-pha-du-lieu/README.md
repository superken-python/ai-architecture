# DATA-01 · Cơ bản · Khám phá dữ liệu nguồn bằng DuckDB và pandas

**Kỹ năng:** [DATA-01 SQL phân tích](../../docs/02-skill-map/generated/mang/data.md#data-01) · **Mức:** Cơ bản
(kèm [DATA-02](../../docs/02-skill-map/generated/mang/data.md#data-02), [STAT-01](../../docs/02-skill-map/generated/mang/stat.md#stat-01) Cơ bản)
**Thời lượng:** ~3 giờ · **Môi trường:** `cd projects/g1-churn-telco && make setup` · **Chi phí API ước tính:** 0 USD

## Mục tiêu

Sau lab này bạn truy vấn được dữ liệu vận hành nhiều bảng bằng SQL (JOIN, GROUP BY, FILTER, ASOF JOIN), mô tả phân
phối bằng trung vị/phân vị, và viết được 5 nhận xét có số liệu làm đầu vào cho feature ở bài A4.

## Dữ liệu

Hệ nguồn mô phỏng của nhà mạng Sóng Xanh (CRM, billing, helpdesk, đo mạng): `make data clean-data` trong dự án sinh
`data/raw/` (bản thô, có lỗi thật) và `data/interim/` (bản sạch). Không có dữ liệu cá nhân thật.

## Các bước

Làm theo [Bài A2](../../docs/03-giai-doan-a-nen-tang/a2-sql-pandas-thong-ke.md):

1. Đếm lỗi trong bảng thô bằng SQL: dòng trùng, tỉnh viết 43 kiểu, ngày sinh mặc định, ticket vào hệ thống trễ.
2. Viết `clean.py` (làm sạch có quy tắc, bỏ PII ngay bước đầu), chạy `make clean-data`.
3. Chạy `eda.py` — bảng khách-tháng, tỷ lệ rời theo tháng, theo hợp đồng (ASOF JOIN), theo tỉnh × quý, dấu hiệu dùng
   ít đi, phân phối lệch:

   ```bash
   cd labs/data-01-co-ban-kham-pha-du-lieu
   uv run --project ../../projects/g1-churn-telco python eda.py      # biểu đồ trong out/
   ```

## Kiểm tra kết quả

- [ ] Tỷ lệ churn nền tính ra ≈ 2,0%/tháng và bạn giải thích được vì sao accuracy 98% là vô dụng.
- [ ] `unknown_values()` trả về rỗng: mọi tên tỉnh và loại ticket đã chuẩn hoá (có test).
- [ ] 5 nhận xét, mỗi câu có một con số tính từ dữ liệu (không gõ tay), kèm 2 biểu đồ trong `out/`.

## Câu hỏi mở rộng

- Đỉnh churn quý 4 ở miền Trung và quý 3/2025 ở HCM, Bình Dương: hỏi ai trong công ty để biết chuyện gì đã xảy ra?
- Viết lại truy vấn "theo hợp đồng" bằng pandas `merge_asof` và so thời gian chạy với DuckDB.
- Làm lại EDA trên bộ [Telco Customer Churn của IBM](https://github.com/IBM/telco-customer-churn-on-icp4d) — bộ đó
  thiếu thông tin gì để làm feature as-of?
