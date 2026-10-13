# 03 · Tính năng mở rộng

| Thuộc tính | Chi tiết |
|---|---|
| Phiên bản | 0.1 — bản nháp chờ review |
| Ngày lập | 2026-10-13 |
| Phạm vi | Yêu cầu số 4: các tính năng khác mà chatbot/agent có thể tương tác với Excel, ngoài "tìm theo cột rồi chèn dòng" |
| Đọc trước | [02 · Giải pháp và kiến trúc](02-giai-phap-kien-truc.md) — bộ công cụ lõi ở [02 §5](02-giai-phap-kien-truc.md#5-bộ-công-cụ-excel) |

**41 tính năng trong 7 nhóm.** Mỗi tính năng ghi: ví dụ câu lệnh, công cụ/API chính (kèm ExcelApi requirement set tối
thiểu, tra trong `@types/office-js` 1.0.611), mức rủi ro và giai đoạn đề xuất.

**Mức rủi ro** — quyết định cách agent được phép làm:

| Mức | Ý nghĩa | Cách làm bắt buộc |
|---|---|---|
| **R0 · Đọc** | chỉ đọc workbook hoặc hệ thống | không cần xác nhận; chỉ gửi phần cần thiết cho LLM |
| **R1 · Hiển thị** | chọn ô, lọc, tô sáng — đổi cách hiển thị hoặc định dạng, không đổi giá trị | không cần xác nhận; hoàn tác được |
| **R2 · Ghi dữ liệu** | đổi giá trị, công thức hoặc cấu trúc trong workbook | kiểm chứng + xem trước + xác nhận + một bước hoàn tác |
| **R3 · Ghi ra hệ thống** | đổi dữ liệu ngoài Excel (ERP, CRM…) — Ctrl+Z không hoàn tác được | duyệt hai bước, nhật ký, quyền theo người dùng; chỉ sau pilot |

**Giai đoạn:** **POC** (2–3 tuần đầu) · **MVP** (pilot nội bộ) · **Sau** (khi pilot chứng minh được giá trị).

## A · Hiểu workbook

| # | Tính năng | Ví dụ câu lệnh | Công cụ / API chính | Rủi ro | Giai đoạn |
|---|---|---|---|---|---|
| A1 | Tóm tắt workbook, sheet, bảng | "File này có những gì? Bảng nào chứa đơn hàng?" | `excel_get_context`, `excel_describe_table` | R0 | POC |
| A2 | Giải thích công thức, truy vết lỗi | "Ô H15 tính thế nào? Vì sao ra #DIV/0!?" | `Range.formulas` (1.1), `getDirectPrecedents` (1.12), `getPrecedents` (1.14) | R0 | MVP |
| A3 | Hồ sơ cột và chất lượng dữ liệu | "Cột SĐT có bao nhiêu ô trống, trùng, sai định dạng?" | `valueTypes` (1.1), `getSpecialCellsOrNullObject` (1.9), `getMergedAreasOrNullObject` (1.13) + luật định dạng Việt Nam (`DATA-05`, `DATA-06`) | R0 | MVP |
| A4 | Hỏi đáp số liệu trên bảng | "Tổng doanh thu tháng 9 theo chi nhánh?" | `excel_aggregate` — code tính, trả lời kèm vùng ô đã dùng | R0 | POC |

## B · Tìm và lọc

| # | Tính năng | Ví dụ câu lệnh | Công cụ / API chính | Rủi ro | Giai đoạn |
|---|---|---|---|---|---|
| B1 | **Tìm theo điều kiện trên nhiều cột** (yêu cầu 3) | "Đơn của KH-0123 trong tháng 9 có SL > 20" | `excel_find_rows`; `findAllOrNullObject` (1.9) khi tìm toàn sheet | R0 | POC |
| B2 | Tìm gần đúng tiếng Việt | "Khách tên Nguyen Van An ở Đà Nẵng" | chuẩn hóa NFC, bỏ dấu, so khớp gần đúng kèm độ tin cậy | R0 | MVP |
| B3 | Lọc để người dùng tự xem | "Chỉ hiện đơn chưa giao của chi nhánh Hà Nội" | `TableColumn.filter` (1.2), `AutoFilter` (1.9) | R1 | MVP |
| B4 | Đi tới, tô sáng kết quả | "Cho tôi xem dòng đó" | `Range.select` (1.1), `format.fill` (1.1) | R1 | POC |
| B5 | Tìm dòng trùng | "Có khách nào bị nhập trùng không?" | so khớp trong code; **không** dùng `removeDuplicates` (1.9) vì lệnh này xóa dữ liệu | R0 | MVP |
| B6 | So khớp hai bảng (thay VLOOKUP) | "Dòng nào có ở sheet Thu mà không có ở sheet Đơn hàng?" | đọc hai bảng theo trang, ghép trong code | R0 | Sau |

## C · Ghi và chỉnh sửa

Mọi tính năng mức R2 đi qua lớp kiểm chứng và thẻ xem trước ở [02 §5.4](02-giai-phap-kien-truc.md#54-lớp-kiểm-chứng-trước-khi-ghi).

| # | Tính năng | Ví dụ câu lệnh | Công cụ / API chính | Rủi ro | Giai đoạn |
|---|---|---|---|---|---|
| C1 | **Chèn một hoặc nhiều dòng** (yêu cầu 3) | "Thêm đơn mới cho KH-0123: SL 50, đơn giá như lần trước" | `excel_insert_rows` → `TableRowCollection.add` (1.4; `alwaysInsert` 1.15) | R2 | POC |
| C2 | Cập nhật theo khóa | "Đơn DH-889 chuyển trạng thái Đã giao" | `excel_find_rows` + `excel_update_cells` | R2 | MVP |
| C3 | Thêm hoặc cập nhật hàng loạt | "Cập nhật giá theo bảng giá mới, mã chưa có thì thêm" | so khớp theo khóa trong code → một thẻ xem trước tổng hợp (n thêm, m sửa) | R2 | MVP |
| C4 | Điền cột bằng LLM | "Phân loại cột Ghi chú thành Khiếu nại / Hỏi giá / Khác" | xử lý theo lô, luật → model nhỏ → LLM (cascade, `EFF-04`, `EFF-06`); ghi kèm cột độ tin cậy; chỉ điền ô trống; chạy thử 20 dòng trước | R2 | Sau |
| C5 | Viết công thức thay vì giá trị tĩnh | "Thêm cột Thành tiền = SL × Đơn giá" | `Range.formulas` (1.1); cột tính toán của Excel Table tự điền xuống | R2 | MVP |
| C6 | Tạo sheet hoặc bảng kết quả | "Đưa kết quả này ra sheet mới" | `excel_write_table` → `worksheets.add` (1.1), `tables.add` (1.3) | R2 | MVP |
| C7 | Định dạng có điều kiện | "Tô đỏ đơn quá hạn 30 ngày" | `conditionalFormats.add` (1.6) | R2 | Sau |
| C8 | Dropdown theo danh mục của hệ thống | "Cột Trạng thái chỉ cho chọn theo danh mục trong ERP" | `Range.dataValidation` (1.8) + danh mục lấy từ backend | R2 | Sau |
| C9 | Ghi chú nguồn gốc số liệu | tự động khi ghi dữ liệu lấy từ hệ thống | `comments.add` (1.10) hoặc `notes.add` (1.18) | R2 | MVP |

## D · Kết nối hệ thống doanh nghiệp (qua agent)

| # | Tính năng | Ví dụ câu lệnh | Công cụ / API chính | Rủi ro | Giai đoạn |
|---|---|---|---|---|---|
| D1 | Tra dữ liệu gốc để điền (khách, sản phẩm, giá) | "Lấy địa chỉ, MST của KH-0456 từ CRM, thêm vào bảng" | `lookup_<entity>` (backend, chỉ đọc) + C1 | R0 → R2 | POC (một nguồn) |
| D2 | Hỏi số liệu bằng tiếng Việt, đưa kết quả vào sheet | "Giờ công theo dự án tháng 9" | domain agent của CMB-09 (text-to-SQL) + C6 + C9 (ghi kèm câu SQL đã chạy) | R0 → R2 | MVP |
| D3 | Làm mới dữ liệu đã kéo | bấm "Làm mới" trên bảng đã tạo ở D2 | lưu định nghĩa truy vấn trong workbook: `Workbook.settings` (1.4) hoặc `customXmlParts` (1.5) | R2 | Sau |
| D4 | Đối chiếu sheet với hệ thống | "Mã SP nào ở cột B không có trong ERP? Tô vàng dòng sai" | đọc cột theo lô → tra backend theo lô → B4 + bảng tóm tắt | R0 → R1 | MVP |
| D5 | Gửi dòng đã chọn vào hệ thống | "Tạo đơn bán hàng trong ERP từ 5 dòng đang chọn" | `create_<entity>` (backend) với `requires_confirmation`, nhật ký, quyền theo người dùng | **R3** | Sau pilot |
| D6 | Hỏi đáp quy định, chính sách nội bộ có trích dẫn | "Chiết khấu tối đa cho đại lý cấp 2 là bao nhiêu?" | RAG (tổ hợp [CMB-03](../../../docs/02-skill-map/generated/to-hop-ky-nang.md#cmb-03)) | R0 | Sau |

## E · Phân tích và báo cáo

| # | Tính năng | Ví dụ câu lệnh | Công cụ / API chính | Rủi ro | Giai đoạn |
|---|---|---|---|---|---|
| E1 | Tạo biểu đồ | "Vẽ doanh thu theo tháng của 3 chi nhánh" | `charts.add` (1.1) — dữ liệu nguồn phải là vùng ô thật, không phải số LLM tự tạo | R2 | MVP |
| E2 | Tạo PivotTable | "Pivot doanh thu theo vùng và nhóm hàng" | `pivotTables.add` (1.8) | R2 | Sau |
| E3 | Tóm tắt cho quản lý kèm trích dẫn ô | "Viết 5 ý chính về kết quả tháng 9" | A4 + văn bản có trích dẫn địa chỉ ô; số liệu chỉ lấy từ kết quả tính | R0 | Sau |
| E4 | Cảnh báo số liệu bất thường | "Có đơn nào giá lệch bất thường so với bảng giá không?" | z-score/IQR tính bằng code (bản nhẹ của Nhóm 3) → B4 | R0 → R1 | Sau |

## F · Tự động hóa và năng suất

| # | Tính năng | Ví dụ | Công cụ / API chính | Rủi ro | Giai đoạn |
|---|---|---|---|---|---|
| F1 | Hàm tùy biến gọi agent | `=AGENT.LOOKUP("KH-0123"; "hạn mức")` | custom functions (CustomFunctionsRuntime 1.1+, không có trên iPad; nên dùng shared runtime). Rủi ro "bão tính lại" → cache theo tham số, giới hạn tần suất, MVP chỉ cho hàm tra cứu xác định. Microsoft 365 Copilot đã có sẵn hàm `=COPILOT()` | R0 | Sau |
| F2 | Lệnh soạn sẵn gọi bằng `/` | `/doi-soat-cong-no`, `/chuan-hoa-danh-sach-kh` | skill trên AgentOS + mẫu câu lệnh; mỗi lệnh có golden set riêng | theo lệnh | MVP |
| F3 | Nút trên ribbon | "Kiểm tra bảng", "Tra khách hàng" | add-in commands khai báo trong manifest, mở khung chat với lệnh soạn sẵn | theo lệnh | Sau |
| F4 | Tác vụ định kỳ không cần mở Excel | mỗi tối thêm doanh số ngày vào file chung trên SharePoint | Microsoft Graph (phương án C, [02 §6.2](02-giai-phap-kien-truc.md#62-c--không-add-in-agent-ghi-file-qua-microsoft-graph)) | R2 | Sau |
| F5 | Mở rộng sang Outlook, Word | "Soạn email gửi khách danh sách đơn chưa thanh toán" | add-in Outlook/Word dùng chung backend AgentOS và giao kèo AG-UI, chỉ thêm bộ công cụ riêng của ứng dụng | theo ứng dụng | Sau |
| F6 | Gợi ý khi dữ liệu thay đổi | dán 300 dòng mới → gợi ý "kiểm tra trùng và định dạng?" | `Table.onChanged`, `Worksheet.onChanged` (1.7); chỉ gợi ý, không tự gọi LLM mỗi lần sửa ô | R0 | Sau |

## G · Quản trị và an toàn

Không phải "tính năng thêm" mà là nền bắt buộc — làm từ POC và hoàn thiện ở MVP.

| # | Tính năng | Mô tả | Giai đoạn |
|---|---|---|---|
| G1 | Xem trước, xác nhận, hoàn tác | thẻ xem trước cho mọi thao tác R2; một lần ghi = một bước Ctrl+Z (ExcelApi 1.20); nút *Hoàn tác* trong chat dựa trên nhật ký riêng cho bản Excel cũ | POC |
| G2 | Nhật ký thao tác ghi | ai, lúc nào, file nào, vùng nào, giá trị cũ → mới, `run_id` | MVP |
| G3 | Chế độ chỉ đọc theo chính sách | theo nhóm người dùng hoặc theo nhãn của file: ẩn mọi công cụ R2/R3 | MVP |
| G4 | Ngân sách token | giới hạn theo người dùng mỗi ngày, cảnh báo khi gần chạm | MVP |
| G5 | Phản hồi để cải tiến | 👍/👎 và "báo sai" ngay trong chat → ca sai vào golden set (`LLM-04`, `BIZ-03`) | MVP |
| G6 | Cấu hình theo phòng ban | mỗi phòng ban bật skill domain và công cụ backend riêng | Sau |

## Thứ tự đề xuất

| Giai đoạn | Tính năng | Mục tiêu |
|---|---|---|
| **POC** | A1, A4, B1, B4, C1, D1, G1 | chứng minh luồng "tìm theo cột → chèn dòng" và một lần gọi agent hệ thống chạy end-to-end, an toàn |
| **MVP** | A2, A3, B2, B3, B5, C2, C3, C5, C6, C9, D2, D4, E1, F2, G2–G5 | đủ dùng hằng ngày cho nhóm pilot 5–10 người |
| **Sau** | B6, C4, C7, C8, D3, D5, D6, E2–E4, F1, F3–F6, G6 | mở rộng khi pilot có số liệu về thời gian tiết kiệm và tỷ lệ đúng |

## Không nên làm, hoặc để rất muộn

- **Xóa sheet, xóa dữ liệu hàng loạt, bảo vệ/bỏ bảo vệ sheet, lưu/đóng workbook** — rủi ro cao, nhiều lệnh trong số này
  xóa luôn ngăn xếp hoàn tác của Excel.
- **Macro/VBA** — add-in Office.js không chạy VBA; sinh macro cho người dùng tự chạy là rủi ro bảo mật.
- **Gửi cả workbook cho LLM** "để nó tự hiểu" — tốn token, vượt giới hạn, lộ dữ liệu; luôn dùng công cụ tìm/đọc có giới hạn.
- **Ghi vào hệ thống không qua duyệt** (D5 không có bước người duyệt).
- **Dự báo, tối ưu ngay trong add-in** — thuộc Nhóm 2 và Nhóm 8; nếu cần, gọi model ở backend như một công cụ và chỉ đưa
  kết quả vào Excel.
