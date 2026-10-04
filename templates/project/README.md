# <Tên dự án>

**Nhóm bài toán:** <Nhóm X · tên> (hoặc tổ hợp CMB-xx) · **Người thực hiện:** <tên> · **Trạng thái:** framing | baseline | cải tiến | hoàn thành

## 1 · ĐÚNG — framing (viết trước khi code)

| Câu hỏi | Trả lời |
|---|---|
| Quyết định nào sẽ thay đổi nhờ model? | |
| Ai dùng kết quả, dùng thế nào, bao lâu một lần? | |
| KPI nghiệp vụ | |
| Metric kỹ thuật tương ứng (ví dụ precision@500/tuần) | |
| Loại sai nào đắt hơn? Ước tính chi phí mỗi loại | |
| Cách làm hiện tại (baseline nghiệp vụ) | |
| Có cần AI không, hay luật if-else là đủ? | |
| Ràng buộc: dữ liệu, quyền riêng tư, độ trễ, chi phí | |

## 2 · NHANH — baseline và bộ đánh giá

- Bộ đánh giá: <nguồn, kích thước, cách tách (theo thời gian?), phiên bản>
- Baseline: <luật / LightGBM mặc định / LLM + prompt> → kết quả: <metric ± khoảng tin cậy>, chi phí, độ trễ
- Lệnh tái tạo: `make eval`

## 3 · CHÍNH XÁC — các vòng cải tiến

| Vòng | Nhóm lỗi lớn nhất | Thay đổi | Metric trước → sau (± KTC) | Chi phí/tác vụ trước → sau |
|---|---|---|---|---|
| 1 | | | | |

## 4 · THUYẾT PHỤC — kết quả

- So với baseline: <...>
- Quy ra tiền/giờ công: <...>
- Demo: <link/lệnh chạy>
- Giới hạn và rủi ro: <...>

## Kỹ năng đã luyện

<Liệt kê ID kỹ năng và mức đạt được, để cập nhật bảng tự đánh giá.>
