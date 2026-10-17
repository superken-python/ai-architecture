# Luật dữ liệu khách hàng

- Mã khách hàng có dạng `KH-` + 4 chữ số. Không tự tạo mã mới.
- `credit_limit` và `debt` là số nguyên VND, không dấu phân cách (300000000, không phải 300.000.000).
- `status` chỉ nhận: Đang giao, Hoàn tất, Tạm dừng.
- Giảm `credit_limit` quá 50% trong một lần: hỏi người dùng xác nhận trước khi gọi tool ghi.
- Khi trả lời về tiền, ghi rõ đơn vị (triệu VND).
