# 01 · Mô tả bài toán và phân loại doanh nghiệp

**Ngày:** 2026-10-13 · **Trạng thái:** nghiên cứu, chưa triển khai.

## 1. Nhu cầu và đầu ra

Người dùng làm việc ngay trong Excel Office, mở một chatbot ở task pane và yêu cầu AI Agent của hệ thống
thực hiện thao tác trên workbook. Đầu ra cần có là dữ liệu được tìm đúng hoặc thay đổi đúng trên Excel,
kèm kết quả có thể kiểm tra; câu trả lời bằng văn bản chỉ là một phần giao diện.

| Yêu cầu | Hành vi mong muốn |
|---|---|
| Gắn chatbot vào Excel | Nút mở task pane, lịch sử chat, hiển thị workbook/sheet/table đang thao tác |
| Tích hợp agent nội bộ | Đăng nhập hệ thống, gửi yêu cầu và ngữ cảnh cần thiết, nhận câu trả lời hoặc yêu cầu gọi tool |
| Search theo column | Chọn đúng bảng/cột, tìm chính xác hoặc theo điều kiện, trả cả bản ghi và vị trí |
| Insert nguyên một row | Ánh xạ theo tên cột, kiểm dữ liệu, xem trước, thêm dòng và đọc lại để xác nhận |
| Mở rộng tương tác | Bổ sung tool đọc/ghi và workflow nghiệp vụ theo từng giai đoạn |

## 2. Thuộc nhóm nào trong 8 nhóm hiện có?

[Bản đồ hiện tại](../../../docs/01-problem-map/README.md) phân loại theo **đầu ra nghiệp vụ**.
Đối chiếu [catalog gốc](../../../catalog/problems.yaml):

| Nhóm | Vai trò với dự án |
|---|---|
| **G7 · AI Agent và tự động hóa quy trình** | **Nhóm chính:** nhận yêu cầu → gọi công cụ → tìm dữ liệu → kiểm tra → thao tác Excel → báo kết quả |
| **G6 · Ngôn ngữ, LLM và RAG** | Hỗ trợ hiểu yêu cầu, tên cột, thuật ngữ và giải thích; RAG chỉ cần khi tra tài liệu/quy tắc nội bộ |
| G1 · Dự đoán dữ liệu bảng | Chỉ thêm khi dự đoán/chấm điểm; file dạng bảng không tự làm dự án thuộc G1 |
| G2 / G3 / G4 | Chỉ tham gia nếu bổ sung dự báo, phát hiện bất thường hoặc gợi ý/xếp hạng |
| G5 · Thị giác và Document AI | Có thể tham gia luồng đọc hóa đơn/PDF rồi đề xuất dòng Excel |
| G8 · Tối ưu và nhân quả | Chỉ tham gia nếu có tối ưu kế hoạch dưới ràng buộc hoặc phân tích tác động |

**Quyết định:** bổ sung use case “trợ lý thao tác Excel” trong tài liệu và danh sách dự án của G7, giữ nguyên
8 nhóm. Không tạo G9 chỉ vì có giao diện plugin mới; không cần tạo một tổ hợp catalog mới cho bản nghiên cứu.

## 3. Các tình huống cụ thể

### UC-01 · Tìm dữ liệu trong workbook

> Trong bảng Orders, tìm tất cả dòng có CustomerCode bằng KH001 và Status bằng Pending.

Add-in lấy schema của bảng đã chọn. Agent đề xuất điều kiện có cấu trúc; executor đọc cột cần thiết và so sánh
bằng logic xác định. Trả số kết quả, dữ liệu và vị trí có thể bấm để chọn trong Excel. Nếu có nhiều bảng
Orders hoặc tên cột không rõ, yêu cầu chọn lại trước khi thực hiện.

Phải phân biệt “không có kết quả” với “mới tìm trong một phần dữ liệu”. Mặc định tìm toàn bộ phần dữ liệu
của Table đã chọn, kể cả các hàng đang bị filter ẩn; nếu chỉ tìm hàng hiển thị thì thể hiện rõ phạm vi đó.

### UC-02 · Lấy dữ liệu từ hệ thống rồi thêm dòng

> Tra sản phẩm SKU-001 trong hệ thống và thêm vào bảng OrderLines: số lượng 20, đơn giá theo bảng giá hiện hành.

1. Agent dùng tool nghiệp vụ của hệ thống để lấy sản phẩm và giá trong quyền của người đang đăng nhập.
2. Ánh xạ dữ liệu vào schema OrderLines; hiển thị nguồn, thời điểm tra cứu, đơn vị và tiền tệ.
3. Kiểm tra cột bắt buộc, mã đơn hàng, mã dòng duy nhất và quy tắc trùng. SKU có thể lặp hợp lệ trong nhiều đơn,
   nên không dùng SKU làm khóa duy nhất nếu nghiệp vụ không quy định.
4. Hiển thị dòng dự kiến, bảng đích và vị trí thêm; người dùng áp dụng.
5. Đọc lại schema/khóa, thực thi và kiểm chứng dòng đã thêm. Chỉ báo thành công khi có kết quả thực thi.

Ghi Excel không tự đồng nghĩa tạo đơn hàng trong ERP. Nếu cần ghi ngược ERP, đó là workflow riêng có quyền,
kiểm tra và kết quả từng hệ thống; không giả định hai thao tác là một giao dịch nguyên tử.

### UC-03 · Hai nghĩa của “insert nguyên một row”

| Cách hiểu | Tác động | Phạm vi đề xuất |
|---|---|---|
| **Một bản ghi trong Excel Table** | Thêm đầy đủ các trường của bảng, tôn trọng cột công thức | MVP: thêm cuối bảng; chèn tại vị trí xác định ở bước sau |
| **Một hàng vật lý của worksheet** | Dịch hàng trên toàn sheet, có thể ảnh hưởng bảng nằm bên cạnh và công thức | Mở rộng: preview riêng, chỉ bật khi thật sự cần |

“Đầy đủ” nghĩa là mọi cột được xử lý theo schema: giá trị người dùng nhập, dữ liệu từ hệ thống, giá trị mặc định,
công thức hoặc ô trống được phép. Agent không tự bịa trường thiếu. Workbook chỉ có range thường cần chọn rõ
vùng và header; chuyển thành Table là một thay đổi cần preview, không tự chuyển âm thầm.

## 4. Khả năng mở rộng

| Khả năng | Ví dụ | Ưu tiên / điều kiện |
|---|---|---|
| Đọc vùng chọn, sheet, table | “Giải thích các cột trong bảng này” | MVP: metadata; dữ liệu theo phạm vi |
| Tìm theo nhiều cột | Mã chính xác, contains, khoảng ngày/số, AND/OR | MVP bắt đầu với equals; tăng toán tử có kiểm chứng |
| Cập nhật theo khóa | Đổi trạng thái một OrderLineId | Sau MVP; hiển thị giá trị trước/sau |
| Thêm nhiều dòng | Nhập danh sách sản phẩm từ hệ thống | Sau MVP; chia lô, báo kết quả từng dòng |
| Lọc, sắp xếp, định dạng | Tô màu bản ghi thiếu mã, sắp ngày giao | Kiểm tra ảnh hưởng thứ tự và phạm vi |
| Kiểm chất lượng dữ liệu | Trùng khóa, sai kiểu, thiếu dữ liệu | Luật xác định trước; AI giải thích lỗi |
| Tổng hợp, công thức, biểu đồ | Tổng doanh thu theo khách, tạo biểu đồ | Tool/API riêng; tính số bằng Excel hoặc backend |
| Đối soát Excel với ERP/CRM | Tìm chênh lệch giá và mã chưa tồn tại | Cần định danh, nguồn dữ liệu và quyền rõ ràng |
| Điền Excel từ tài liệu | Đọc hóa đơn thành các dòng có nguồn tham chiếu | G5 + G6 + G7; kiểm chứng trích xuất |
| Dự báo / tối ưu | Dự báo bán hàng, lập kế hoạch nhập | Dự án con G2/G8; phải có model và eval riêng |
| Xóa, hoàn tác, ghi ngược hệ thống | Xóa dòng trùng, khôi phục dữ liệu | Thiết kế riêng; không nằm trong MVP |

Các mục sau MVP là khả năng thiết kế, chưa phải tính năng đã có. API hỗ trợ đến đâu còn phụ thuộc Excel host,
requirement set và cấu trúc file; xem [solution approach](02-solution-approach.md).

## 5. Phạm vi nghiên cứu và giả định ban đầu

- Ưu tiên Excel Microsoft 365 trên Windows; kiểm chứng thêm macOS và web trước khi công bố hỗ trợ.
- Dùng `.xlsx`, workbook đang mở, bảng có header rõ và một người thực thi lệnh ghi trong MVP.
- Agent hiện có có thể tích hợp qua API/adapter, nhưng chưa xác minh endpoint, auth hay tool protocol thực tế.
- Không mặc định dùng Microsoft Copilot hoặc chuyển agent sang một framework mới.
- Chưa hỗ trợ Excel cũ `.xls`, mọi cấu trúc merged cell, chạy nền khi đóng Excel hoặc ghi đồng thời nhiều người.

## 6. Giá trị cần đo

Đo cùng một bộ tác vụ trước/sau: thời gian thao tác, tỷ lệ chọn đúng bảng/cột, đúng bản ghi, đúng giá trị sau ghi,
số lần làm rõ, lỗi trùng và chi phí agent. Trước mắt chưa có số đo chứng minh tiết kiệm; tiêu chí kiểm chứng được
đề xuất trong [đánh giá khả thi](03-danh-gia-kha-thi.md).
