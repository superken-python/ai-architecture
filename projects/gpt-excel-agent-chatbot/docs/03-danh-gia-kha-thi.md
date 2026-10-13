# 03 · Đánh giá khả thi, kế hoạch kiểm chứng và nguồn tham khảo

**Ngày tra cứu:** 2026-10-13. **Kết luận:** đủ cơ sở để đề xuất POC, chưa đủ bằng chứng xác nhận production.
Các mốc và metric dưới đây là đề xuất đánh giá, không phải kết quả đã chạy.

## 1. Mức khả thi theo yêu cầu

| Yêu cầu | Đánh giá | Cơ sở / điều kiện |
|---|---|---|
| Chatbot nằm trong Excel Office | Khả thi cao | Task pane của Office Add-ins [S1] |
| Nối agent của doanh nghiệp | Khả thi về kiến trúc | Web UI + API adapter; cần xác minh auth, session và resume tool của hệ thống thật |
| Tìm dữ liệu theo cột | Khả thi cao trên bảng có cấu trúc | API đọc cột + logic so sánh; hiệu năng phải đo [S2][S7] |
| Thêm một bản ghi đầy đủ | Khả thi cao có điều kiện | Table rows API; phải kiểm schema, formula, duplicate và readback [S2] |
| Chèn cả hàng worksheet | Có API, phạm vi khó hơn | Entire-row range + insert; ảnh hưởng bố cục rộng [S5][S6] |
| Mở rộng update/filter/report | Khả thi theo từng tool | Đánh giá riêng API, quyền và tiêu chí đúng |
| Chạy trên mọi bản Excel | Chưa thể cam kết | Kiểm requirement set và build, không chỉ hệ điều hành [S15] |
| Ghi nền khi đóng Excel | Ngoài kiến trúc MVP | Xem luồng Graph riêng, đặc biệt quyền delegated [S9][S10] |
| Nhiều người ghi, luôn đúng một lần | Chưa thể cam kết | Coauthoring có xung đột; Excel không phải DB transaction [S11] |

Điểm khó chính là **định nghĩa và kiểm chứng thao tác ghi đúng**. Giao diện chat hoặc khả năng model hiểu câu hỏi
không đủ để kết luận hệ thống đã ghi đúng workbook, đúng cột, đúng kiểu và không trùng.

## 2. Ràng buộc cần kiểm chứng

### Host và API

Office Add-ins có hướng hỗ trợ Windows, Mac và web [S1], nhưng từng API có requirement set riêng [S15].
Kiểm tra runtime bằng `Office.context.requirements.isSetSupported`, khai báo mức tối thiểu theo API dùng thật;
tính năng không đủ API phải bị vô hiệu hóa với lý do rõ ràng. Không lấy tính năng preview làm nền cho MVP.

| Môi trường mục tiêu | Cách kiểm chứng ở POC tương lai |
|---|---|
| Excel Microsoft 365 Windows | Một build cụ thể trên kênh cập nhật của công ty; workbook `.xlsx` cục bộ và cloud |
| Excel Microsoft 365 macOS | Test riêng task pane, auth, công thức và read/write; không suy ra từ Windows |
| Excel on the web | File thử trên nền tảng doanh nghiệp được hỗ trợ; test network, payload và auth |
| Excel perpetual/cũ, iPad/mobile | Ngoài MVP; chỉ công bố khi có nhu cầu và ma trận API được kiểm tra |

### Kích thước và hiệu năng

Microsoft nêu giới hạn request/response 5 MB trên Excel web và tối đa 5 triệu ô cho thao tác get range trên
các nền tảng [S7]. Đây là giới hạn kỹ thuật, không phải kích thước nên đưa vào prompt. Đọc theo vùng/cột,
chia lô, gom lệnh và giảm số lần sync; không quét toàn sheet cho mỗi câu hỏi.

Đề xuất đo bảng 1.000, 10.000 và 50.000 dòng × khoảng 20 cột, bao gồm text dài và cột công thức. Tăng kích
thước theo kết quả đo, không cam kết 50.000 dòng nhanh trên mọi máy. Kết quả phân trang phải thể hiện tổng phạm
vi đã tìm, số kết quả bị giới hạn và trường hợp chưa quét xong.

### Workbook và quyền ghi

Protected sheet, chế độ chỉ đọc, header không rõ, merged cell và bảng có bố cục phức tạp cần đường xử lý riêng.
MVP dừng có giải thích khi ngoài phạm vi. Với shared workbook, event và cache cần xử lý thay đổi từ coauthor [S11].
Preview không phải khóa dữ liệu; phải có kiểm tra lại và xử lý trạng thái chưa xác định.

## 3. POC đề xuất cho giai đoạn sau

Chưa thực hiện các bước sau trong đợt này; không có source code, manifest hoặc workbook thử được tạo.

| Mốc | Nội dung | Điều kiện qua mốc |
|---|---|---|
| P0 · Chốt môi trường | Excel build/OS, tenant, auth, API agent, workbook/schema mẫu, quyền dữ liệu | Có ma trận hỗ trợ và contract thống nhất |
| P1 · Cầu nối không dùng AI | Task pane đọc context, search cột, thêm dòng bằng lệnh định sẵn | Chứng minh Office.js và readback hoạt động trên host mục tiêu |
| P2 · Nối agent | Chat → structured tool → executor → tool result → agent tiếp tục | Agent chọn đúng tool; yêu cầu mơ hồ được làm rõ |
| P3 · Ghi có kiểm soát | Preview, precondition, duplicate, timeout, reconnect, journal | Không ghi nhầm hoặc tự thêm lại khi chưa rõ kết quả |
| P4 · Pilot nghiệp vụ | Người dùng thật trên bản sao file, so với baseline, đo tải và chi phí | Đạt tiêu chí đã chốt; có danh sách giới hạn được chấp nhận |

**Ước lượng nội bộ, chưa cam kết:** P0–P1 khoảng 3–5 ngày công; P2–P3 khoảng 5–10 ngày công; P4 khoảng
5–10 ngày công. Tổng 13–25 ngày công cho phạm vi hẹp, nếu agent API/auth đã sẵn và có quyền thử add-in.
Chờ admin, sửa backend chưa có tool calling hoặc làm sạch workbook nằm ngoài ước lượng. Không có cơ sở báo
giá chính xác khi chưa xác minh các điều kiện này.

Chi phí vận hành gồm frontend/API hosting, token hoặc model nội bộ, log/storage và hỗ trợ Excel clients.
Đo chi phí trên tác vụ hoàn tất, gồm retry và câu hỏi làm rõ; chưa chốt nhà cung cấp hay đơn giá model.

## 4. Bộ tình huống đánh giá trước khi viết model logic

Đề xuất đóng băng 60 tình huống: 20 search, 20 insert, 20 lỗi/biên. Dùng file giả lập, đáp án và trạng thái
workbook mong đợi được người nghiệp vụ xác nhận. Kiểm kết quả ô/khóa thực tế, không chỉ chấm lời trả lời.

| Nhóm kiểm chứng | Ca quan trọng |
|---|---|
| Search | Không khớp, một/nhiều kết quả, AND, hoa/thường, Unicode, mã có số 0 đầu, hàng bị ẩn |
| Mapping | Đổi thứ tự/tên cột, thiếu field bắt buộc, ngày/tiền theo locale, cột công thức |
| Insert | Table rỗng, cuối bảng, total row, dữ liệu ngay dưới bảng, trùng khóa, cùng SKU khác đơn |
| Đúng target | Chuyển sheet, mở hai workbook trùng tên, đổi schema sau preview |
| Reliability | Timeout trước/sau ghi, mất ACK, double-click, reconnect, lỗi giữa nhiều bước |
| Giới hạn quyền | File chỉ đọc, sheet protected, tool ngoài allowlist, cell chứa chỉ thị giả, text giống công thức |
| Mở rộng pilot | Coauthor sửa đồng thời; phát hiện xung đột hoặc loại khỏi phạm vi hỗ trợ |

**Ngưỡng đề xuất cho go/no-go:**

- Tác vụ hợp lệ trong bộ eval hoàn thành đúng ít nhất 95%; trường hợp không chắc phải dừng/làm rõ.
- Mọi thao tác ghi được chấp nhận phải đúng target/schema/giá trị khi readback; không có ca ghi sai, ghi ngoài
  phạm vi hay thêm trùng do phát lại cùng command trong bộ kiểm chứng. Một lỗi nghiêm trọng là no-go.
- 100% ca lỗi/ngoài phạm vi trả trạng thái trung thực; không báo “đã ghi” khi chỉ có đề xuất hoặc ACK chưa rõ.
- Mục tiêu ban đầu: search xác định p95 ≤ 2 giây trên bảng 10.000 dòng × 20 cột; end-to-end p95 ≤ 15 giây,
  không tính thời gian người dùng duyệt. Điều chỉnh sau P1 theo máy/model thực tế.
- Pilot hướng tới giảm ít nhất 30% thời gian so với Filter/Find + copy-paste trên cùng tác vụ, không tăng lỗi.

Các ngưỡng này do dự án đề xuất, không phải SLA Microsoft. Bộ 60 ca chỉ là cổng vào pilot, không chứng minh
an toàn tuyệt đối hay tính ổn định production.

## 5. Những thông tin còn thiếu

1. Công ty dùng Excel Windows/Mac/web và build/kênh cập nhật nào? Chính sách có cho cài add-in riêng không?
2. Workbook ở máy cá nhân, thư mục mạng hay OneDrive/SharePoint? Có đồng biên tập và protected sheet không?
3. Bản đầu chỉ thêm record trong Table hay cần cả chèn hàng worksheet giữa báo cáo?
4. Agent hiện tại cung cấp API/auth/tool calling thế nào; có thể tạm dừng và tiếp tục sau client tool result không?
5. Dữ liệu lấy từ Excel hay hệ thống khác; khóa nào xác định dòng duy nhất và cột nào chứa công thức?
6. Cột nào được phép gửi tới backend/model; ai dùng plugin và cần lưu audit bao lâu?

Các câu hỏi này không ngăn việc nghiên cứu hiện tại; cần chốt trước triển khai. Khuyến nghị tiến hành POC theo
phạm vi một Table/một writer, sau đó quyết định mở rộng dựa trên dữ liệu kiểm chứng.

## 6. Nguồn chính thức đã đối chiếu

Nguồn Microsoft dưới đây xác nhận năng lực nền tảng và các giới hạn được nêu. Kiến trúc adapter, tool contract,
MVP, ước lượng và tiêu chí đánh giá là **đề xuất của dự án**, không phải đảm bảo từ Microsoft. Tài liệu nền tảng
có thể thay đổi; cần kiểm tra lại ở P0 theo build và tenant thực tế.

| Mã | Tài liệu | Nội dung dùng để đối chiếu |
|---|---|---|
| S1 | [Excel add-ins overview](https://learn.microsoft.com/en-us/office/dev/add-ins/excel/excel-add-ins-overview) | Task pane, workbook APIs, nền tảng và phân biệt COM/VSTO |
| S2 | [Create, read, and manage Excel tables](https://learn.microsoft.com/en-us/office/dev/add-ins/excel/excel-add-ins-tables) | Đọc cột/table, thêm hàng, filter/sort |
| S3 | [Understand the Office JavaScript API](https://learn.microsoft.com/en-us/office/dev/add-ins/develop/understand-the-javascript-api-for-office) | Mô hình API và tương tác với Office host |
| S4 | [Office Add-ins manifest](https://learn.microsoft.com/en-us/office/dev/add-ins/develop/add-in-manifests) | Add-in only XML và unified manifest |
| S5 | [Insert ranges using the Excel JavaScript API](https://learn.microsoft.com/en-us/office/dev/add-ins/excel/excel-add-ins-ranges-insert) | Insert range và dịch ô |
| S6 | [Excel.Range — ExcelApi 1.1](https://learn.microsoft.com/en-us/javascript/api/excel/excel.range?view=excel-js-1.1) | `getEntireRow` và API range |
| S7 | [Excel JavaScript API performance optimization](https://learn.microsoft.com/en-us/office/dev/add-ins/excel/performance) | Payload, cell limits, batch và hiệu năng |
| S8 | [Differences between Office Scripts and Office Add-ins](https://learn.microsoft.com/en-us/office/dev/scripts/resources/add-ins-differences) | UI/auth của add-in và script automation |
| S9 | [Working with Excel in Microsoft Graph](https://learn.microsoft.com/en-us/graph/api/resources/excel?view=graph-rest-1.0) | Vị trí lưu file và định dạng được hỗ trợ |
| S10 | [Create TableRow — Microsoft Graph](https://learn.microsoft.com/en-us/graph/api/table-post-rows?view=graph-rest-1.0) | Quyền delegated; application permission không được hỗ trợ |
| S11 | [Coauthoring in Excel add-ins](https://learn.microsoft.com/en-us/office/dev/add-ins/excel/co-authoring-in-excel-add-ins) | Cache, event và xung đột thêm dòng |
| S12 | [Deploy and publish Office Add-ins](https://learn.microsoft.com/en-us/office/dev/add-ins/publish/publish) | Phân phối nội bộ và Marketplace |
| S13 | [API support for content and task pane add-ins](https://learn.microsoft.com/en-us/office/dev/add-ins/develop/support-for-task-pane-and-content-add-ins) | Quyền `ReadWriteDocument` trong manifest |
| S14 | [SSO with nested app authentication](https://learn.microsoft.com/en-us/office/dev/add-ins/quickstarts/sso-quickstart) | Hướng tích hợp SSO cần kiểm tra theo host |
| S15 | [Specify Office hosts and API requirements](https://learn.microsoft.com/en-us/office/dev/add-ins/develop/specify-office-hosts-and-api-requirements) | Requirement sets và tương thích Office |
