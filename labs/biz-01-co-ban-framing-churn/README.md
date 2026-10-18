# BIZ-01 · Cơ bản · Quy bài toán churn ra tiền trước khi có model

**Kỹ năng:** [BIZ-01 Framing bài toán và quy đổi giá trị](../../docs/02-skill-map/generated/mang/biz.md#biz-01) · **Mức:** Cơ bản
(kèm [PY-01](../../docs/02-skill-map/generated/mang/py.md#py-01), [PY-02](../../docs/02-skill-map/generated/mang/py.md#py-02) Cơ bản)
**Thời lượng:** ~2 giờ · **Môi trường:** `cd projects/g1-churn-telco && make setup` · **Chi phí API ước tính:** 0 USD

## Mục tiêu

Sau lab này bạn viết lại được mục tiêu mơ hồ "giảm churn" thành một bài toán đo được — *precision@500 mỗi tháng cho
đội CSKH* — và biết con số đó phải đạt bao nhiêu thì dự án mới đáng làm.

## Dữ liệu

Chưa cần dữ liệu: chỉ dùng giả định nghiệp vụ trong
[`config.py`](../../projects/g1-churn-telco/src/churn_telco/config.py) (chi phí gọi, tỷ lệ giữ chân, ưu đãi, biên
lợi nhuận, năng lực 500 cuộc/tháng).

## Các bước

Làm theo [Bài A1](../../docs/03-giai-doan-a-nen-tang/a1-python-git-framing.md):

1. Dựng dự án bằng `uv` theo cấu trúc `src/ tests/`, commit đầu tiên với `.gitignore` chặn dữ liệu và `.env`.
2. Viết `config.py` — một chỗ duy nhất cho đường dẫn, mốc thời gian, giả định nghiệp vụ.
3. Chạy `value_calc.py` để quy giả định ra tiền:

   ```bash
   cd labs/biz-01-co-ban-framing-churn
   uv run --project ../../projects/g1-churn-telco python value_calc.py
   uv run --project ../../projects/g1-churn-telco python value_calc.py --save-rate 0.15
   ```

4. Viết phần **1 · ĐÚNG — framing** trong README của dự án (quyết định, KPI, chi phí từng loại sai, cách làm hiện tại).

## Kiểm tra kết quả

- [ ] `make setup` trên một máy sạch cho ra đúng môi trường (`uv.lock` đã commit).
- [ ] `git status` sạch, không có `data/`, `models/`, `.env` trong danh sách theo dõi.
- [ ] Framing có đủ: quyết định thay đổi, KPI nghiệp vụ, metric kỹ thuật (precision@500/tháng), chi phí gọi nhầm và
      bỏ sót, cách làm hiện tại, ngưỡng hoà vốn (≈ 5,4% với giả định gốc).

## Câu hỏi mở rộng

- Với tỷ lệ giữ chân 15%, precision@500 tối thiểu là bao nhiêu? Kết luận "có nên làm" có đổi không?
- Gọi nhầm một khách không định rời có tốn gì ngoài 25.000 đ? (gợi ý: khách bị làm phiền, ưu đãi bị "xin" không cần)
- Khi nào chỉ cần luật if-else là đủ? Viết luật CSKH hiện tại thành code — đó sẽ là baseline ở bài A3.
