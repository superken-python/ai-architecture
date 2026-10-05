# CMB-09 · Data Agent OS — data agent nhiều domain pack trên AgentOS

**Tổ hợp:** CMB-09 · Hỏi số liệu bằng tiếng Việt (text-to-SQL agent) — Nhóm 6 + 7 · **Trạng thái:** thiết kế, chờ review
(chưa có code) · **Người thực hiện:** <tên>

Dự án nghiên cứu: xây một data agent gần giống data agent nội bộ của OpenAI. Người dùng hỏi số liệu bằng tiếng Việt; agent
tự tìm bảng, viết SQL, tự kiểm tra kết quả, trả lời kèm nguồn tham chiếu và học từ góp ý đã được duyệt. Điểm riêng:

- **Nhiều domain pack** (timesheet, finance, …), tất cả kế thừa **pack `core` = kỹ năng chung của data agent**, luôn nạp trước.
- **AgentOS** (Agno) quản lý tập trung agent của **Agno SDK** (runtime chính) và **OpenAI Agents SDK** (runtime phụ, qua adapter).
- Dữ liệu truy vấn qua **MCP DBHub**, nhưng luôn đi qua **Data Gateway** để kiểm quyền và ghi bằng chứng.
- **Tracing bền vững** cho cả hai runtime trong cùng một DB; vòng **review → learning → cập nhật pack**.

![Kiến trúc v1](docs/assets/kien-truc-v1.svg)

## Tài liệu

| # | Tài liệu | Nội dung |
|---|---|---|
| 1 | [Kiến trúc](docs/01-kien-truc.md) | nguyên tắc, thành phần, luồng một câu hỏi, thứ tự nạp kỹ năng, 6 lớp ngữ cảnh, review, tracing, triển khai |
| 2 | [Review diagram v0](docs/02-review-diagram-v0.md) | điểm mạnh, 13 điểm cần bổ sung, thay đổi trong v1 |
| 3 | [Chi tiết kỹ thuật](docs/03-chi-tiet-ky-thuat.md) | API đã kiểm chứng, đặc tả domain pack, gateway, DBHub, hai runtime, tracing, review, eval, API, cấu hình |
| 4 | [ADR-001 · OpenAI Agents SDK](docs/04-adr-openai-agents-sdk.md) | có cần runtime OpenAI không; luồng OpenAI có cần nạp kỹ năng core không |
| 5 | [Checklist triển khai](CHECKLIST.md) | quyết định cần chốt, 9 giai đoạn, tiêu chí hoàn thành |

## 1 · ĐÚNG — framing

| Câu hỏi | Trả lời |
|---|---|
| Quyết định nào sẽ thay đổi? | Quản lý (PMO, tài chính) tự lấy số liệu cho quyết định nhân sự/dự án/chi phí trong vài phút, thay vì chờ analyst viết SQL |
| Ai dùng, thế nào, bao lâu một lần? | PMO, trưởng phòng, kế toán; hằng ngày qua web chat, Slack, API; báo cáo định kỳ chạy theo lịch |
| KPI nghiệp vụ | Tỷ lệ câu hỏi số liệu tự phục vụ được; thời gian từ câu hỏi đến con số; số yêu cầu SQL gửi analyst giảm |
| Metric kỹ thuật | Tỷ lệ con số đúng tuyệt đối trên golden set (so khớp **kết quả**, không so chuỗi SQL); tỷ lệ hỏi lại đúng lúc với câu mơ hồ; 100% chặn đúng yêu cầu ghi dữ liệu/PII; token, chi phí, độ trễ mỗi câu |
| Loại sai nào đắt hơn? | Con số sai mà trông hợp lý (lỗi im lặng) đắt hơn nhiều so với từ chối hoặc hỏi lại → bắt buộc trích nguồn, tự kiểm tra, lint quy tắc nghiệp vụ |
| Cách làm hiện tại | Analyst viết SQL theo yêu cầu; dashboard cố định |
| Có cần AI không? | Câu hỏi lặp lại → workflow báo cáo cố định (không cần agent). Agent chỉ dành cho câu hỏi ad-hoc |
| Ràng buộc | Dữ liệu nội bộ không rời hệ thống (trace không gửi ra ngoài mặc định); quyền theo vai trò; chỉ đọc; ngân sách token |

## Phạm vi

**v1:** pack `core` + `timesheet` + `finance` trên dữ liệu giả lập; mỗi pack một nguồn dữ liệu qua DBHub; Agno runtime và
OpenAI Agents SDK runtime; định tuyến; workflow báo cáo; tracing bền vững; review → learning; eval so sánh hai runtime.

**Sau v1:** câu hỏi ghép nhiều pack; BigQuery (DBHub chưa hỗ trợ); tri thức tổ chức từ Drive/SharePoint; đọc code
dbt/ETL để làm giàu ngữ cảnh; mọi thao tác ghi dữ liệu.

## Kỹ năng sẽ luyện

`DATA-01` SQL phân tích · `LLM-08` text-to-SQL · `LLM-02` structured output · `LLM-04` đánh giá · `LLM-05` tool calling /
agent · `LLM-06` an toàn LLM · `OPS-06` tracing, chi phí · `OPS-08` bảo mật dữ liệu · `EFF-03` tinh gọn ngữ cảnh ·
`EFF-07` kiểm chứng xác định — xem [danh mục kỹ năng](../../docs/02-skill-map/generated/README.md).
