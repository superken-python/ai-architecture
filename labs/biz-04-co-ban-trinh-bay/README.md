# BIZ-04 · Cơ bản · Báo cáo 1 trang, phân tích độ nhạy và demo

**Kỹ năng:** [BIZ-04 Trình bày, demo và thuyết phục](../../docs/02-skill-map/generated/mang/biz.md#biz-04) · **Mức:** Cơ bản
(kèm [PY-02](../../docs/02-skill-map/generated/mang/py.md#py-02) Trung cấp)
**Thời lượng:** ~3 giờ · **Môi trường:** `cd projects/g1-churn-telco && make setup` · **Chi phí API ước tính:** 0 USD

## Mục tiêu

Sau lab này bạn trình bày được kết quả cho người ngoài ngành trong 10 phút: so với cách làm hiện tại, quy ra khách giữ
được và tiền, kèm khoảng tin cậy, độ nhạy theo giả định, giới hạn và đề nghị bước tiếp theo.

## Dữ liệu

Toàn bộ sản phẩm của các bài trước (`make all`).

## Các bước

Làm theo [Bài A8](../../docs/03-giai-doan-a-nen-tang/a8-trinh-bay-ket-qua.md):

1. `make report` → `reports/README.md` (báo cáo 1 trang) + 2 biểu đồ.
2. Phân tích độ nhạy và khung câu chuyện 3 phút:

   ```bash
   cd labs/biz-04-co-ban-trinh-bay
   uv run --project ../../projects/g1-churn-telco python sensitivity.py     # tornado trong out/
   ```

3. Demo: `make docker-up`, mở http://127.0.0.1:8000, nhập khoá, xem danh sách gọi kèm lý do.
4. Đưa dự án lên quy trình nhóm: nhánh + pull request, CI chạy `make check`, `make all` tái lập từ đầu.

## Kiểm tra kết quả

- [ ] Báo cáo 1 trang: bảng so với cách làm hiện tại có KTC, lợi nhuận tăng thêm, độ nhạy, giới hạn và rủi ro.
- [ ] Biểu đồ tornado chỉ ra giả định cần đo lại trước khi nhân rộng.
- [ ] Một người không làm ML đọc báo cáo 10 phút và nói lại được: nên làm gì tiếp và vì sao.

## Câu hỏi mở rộng

- Thiết kế thử nghiệm có nhóm đối chứng 2 tháng: cần bao nhiêu khách để đo được tỷ lệ giữ chân ±5 điểm?
- Làm demo Streamlit/Gradio một màn hình cho CSKH (danh sách + lý do + ô ghi kết quả cuộc gọi).
