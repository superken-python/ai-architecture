# GPT Excel Agent Chatbot — trợ lý thao tác Excel qua AI Agent nội bộ

**Nhóm chính:** G7 · AI Agent và tự động hóa quy trình. **Nhóm hỗ trợ:** G6 · Ngôn ngữ, LLM và RAG.
**Trạng thái:** nghiên cứu khả thi, chỉ tài liệu Markdown, chưa có code hay POC.
**Ngày nghiên cứu:** 2026-10-13.

Chatbot nằm trong khung bên cạnh của Excel Office, kết nối AI Agent của doanh nghiệp để tìm dữ liệu theo cột,
lấy bản ghi từ hệ thống và thêm một dòng đầy đủ vào workbook đang mở. Tên `gpt-` là prefix dự án theo yêu cầu,
không ràng buộc nhà cung cấp model.

**Kết luận:** khả thi về nền tảng. Đề xuất **Excel Task Pane Add-in + Office.js + API adapter tới agent hiện có**.
Microsoft cung cấp task pane và API đọc/ghi workbook; độ ổn định trên file, máy và hệ thống thực tế vẫn cần POC.
Nguồn: [Excel add-ins overview](https://learn.microsoft.com/en-us/office/dev/add-ins/excel/excel-add-ins-overview).

## Tài liệu

| Tài liệu | Nội dung |
|---|---|
| [01 · Mô tả bài toán](docs/01-mo-ta-bai-toan.md) | Nhu cầu, ví dụ, phân loại trong 8 nhóm, phạm vi và chức năng mở rộng |
| [02 · Solution approach](docs/02-solution-approach.md) | So sánh phương án, kiến trúc, kết nối agent, search/insert, quyền và triển khai |
| [03 · Đánh giá khả thi](docs/03-danh-gia-kha-thi.md) | Giới hạn, kế hoạch kiểm chứng, tiêu chí go/no-go, ước lượng và nguồn Microsoft |

## Framing trước khi triển khai

| Câu hỏi | Định hướng |
|---|---|
| Ai sử dụng? | Nhân viên vận hành, kinh doanh, kế toán, analyst đang nhập và đối soát dữ liệu bằng Excel |
| Thay đổi công việc gì? | Từ lọc/tìm rồi copy-paste thủ công sang yêu cầu bằng ngôn ngữ tự nhiên, xem trước và áp dụng |
| Baseline nghiệp vụ | Excel Filter/Find, công thức tra cứu và copy-paste; đo thời gian trên cùng bộ tác vụ |
| Có cần AI không? | AI giúp hiểu câu hỏi và điều phối; tìm khớp mã, kiểm kiểu và ghi ô phải dùng logic xác định |
| KPI | Thời gian hoàn thành, tỷ lệ đúng bản ghi/đúng cột, số lỗi nhập liệu, chi phí mỗi tác vụ |
| Sai nào đắt hơn? | Ghi nhầm workbook, sai dữ liệu hoặc thêm trùng đắt hơn việc yêu cầu người dùng làm rõ |
| MVP đề xuất | Một workbook, một Excel Table đã chọn, tìm theo cột và thêm một bản ghi có preview |
| Chưa kết luận được | Excel build thực tế, chính sách tenant, giao thức/auth của agent, chất lượng dữ liệu và hiệu năng |

Đây là **use case mới của G7**, chưa cần thêm G9. Xem [bản đồ bài toán](../../docs/01-problem-map/README.md)
và [danh sách dự án](../README.md). Kế hoạch POC trong tài liệu là bước tương lai; lần nghiên cứu này không tạo
manifest, ứng dụng, workbook mẫu hay cấu hình triển khai.
