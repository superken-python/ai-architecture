# 02 · Tái sử dụng skill của Data plugin khi khởi tạo agent

Câu hỏi: skill của **Data plugin** (plugin "Data" của Anthropic trong Claude/Cowork) có dùng lại được cho agent object của
dự án này không, và dùng thế nào?

**Kết luận ngắn:** dùng lại được. 6/10 skill dùng được ngay (chỉ là hướng dẫn, chạy bằng SQL qua DBHub), 3 skill cần thêm tool
ghi file hoặc chạy Python nên để sau POC, 1 skill (`data-context-extractor`) dùng **offline** để sinh skill của từng domain
pack. Cần một điều chỉnh nhỏ khi nạp: `LocalSkills(..., validate=False)`.

## 1. Nguồn đã kiểm tra

| Mục | Giá trị |
|---|---|
| Repo | `anthropics/knowledge-work-plugins`, thư mục `data` (plugin `data`, `plugin.json` version 1.1.0) |
| Commit | `8444efc` (2026-10-01) |
| Giấy phép | Apache-2.0 → được sao chép vào repo, phải giữ `LICENSE` và ghi nguồn |
| Cách kiểm tra | đọc từng `SKILL.md`; chạy `agno.skills.validate_skill_directory` (agno 3.1.1); nạp bằng `Skills(loaders=[LocalSkills(..., validate=False)])` |

**Lưu ý về phiên bản:** ảnh chụp màn hình của chủ dự án cho thấy plugin Data đã cài có **20 skill** với tên khác
(Analyze Data Quality, Build Dashboard, Build Report, Convert To Doc, Convert To Slides, Create Data Context, Design KPIs,
Gather Business Context, Index, …). Bản này **không có** trong repo công khai và không đọc được từ môi trường làm tài liệu.
Đánh giá dưới đây dựa trên bản công khai 1.1.0; mục 5 ánh xạ tạm theo tên và mô tả. Cần file thật của bản 20 skill
(xuất thư mục plugin hoặc file zip) để kiểm tra lại.

## 2. Đánh giá từng skill (bản 1.1.0)

| Skill | Kích thước | Làm gì | Cần môi trường gì | Quyết định |
|---|---|---|---|---|
| `analyze` | 4,4 KB | workflow trả lời câu hỏi số liệu: hiểu câu hỏi → lấy dữ liệu → phân tích → kiểm tra → trình bày | chỉ tool SQL | **POC — dùng lại** (skill vào chính) |
| `write-query` | 4,8 KB | viết SQL tối ưu theo dialect | chỉ hướng dẫn | **POC — dùng lại** |
| `sql-queries` | 11,1 KB | best practice SQL nhiều dialect (có PostgreSQL), CTE, window function | chỉ hướng dẫn | **POC — dùng lại** |
| `explore-data` | 11,5 KB | profiling bảng: null, phân phối, trùng lặp, vấn đề chất lượng | chỉ tool SQL | **POC — dùng lại** (≈ "Analyze Data Quality") |
| `validate-data` | 14,9 KB | QA trước khi chia sẻ: join explosion, average of averages, kỳ chưa đủ, sanity check | chỉ hướng dẫn (ví dụ Python không bắt buộc) | **POC — dùng lại** |
| `statistical-analysis` | 10,4 KB | thống kê mô tả, xu hướng, outlier, kiểm định | ví dụ dùng Python; phần lớn tính được bằng SQL | **POC — dùng lại**, dặn tính bằng SQL |
| `build-dashboard` | 26,0 KB | dashboard HTML tự chứa (Chart.js, bộ lọc, KPI card) | phải **ghi file HTML** | **Sau POC** — thêm tool ghi file vào thư mục `outputs/` |
| `create-viz` | 5,2 KB | biểu đồ bằng Python | phải **chạy Python** | **Sau POC** — cần sandbox |
| `data-visualization` | 11,1 KB | chọn loại biểu đồ, code matplotlib/plotly | phải **chạy Python** | **Sau POC** — cần sandbox |
| `data-context-extractor` | 7,2 KB + 4 references + 1 script | phỏng vấn analyst, khám phá schema → **sinh skill dữ liệu riêng của công ty** | Claude/Claude Code có kết nối CSDL, ghi file | **Offline** — công cụ tạo domain pack, không nạp vào agent |

Ước lượng token (≈ 4 ký tự/token): 6 skill POC tổng ≈ 57 KB ≈ 14k token **nếu tải hết**; nhưng prompt ban đầu chỉ chứa tên + mô
tả và phần hướng dẫn cố định của Agno (≈ 1k token), nội dung chỉ tải khi agent gọi `get_skill_instructions` — một câu hỏi thường cần 2–3 skill (≈ 4–7k token).
Cần đo thật ở POC-1.

## 3. Các điểm không tương thích đã phát hiện và cách xử lý

| # | Phát hiện (đã kiểm chứng) | Ảnh hưởng | Xử lý trong POC |
|---|---|---|---|
| 1 | Frontmatter có `argument-hint` (6 skill) và `user-invocable` (3 skill) — trường riêng của Claude | validator của Agno báo lỗi 9/10 skill; `LocalSkills` mặc định `validate=True` sẽ dừng khởi động | `LocalSkills(path, validate=False)` — đã thử: nạp đủ 10 skill. Sau POC: script đồng bộ bỏ 2 trường này để bật lại validate |
| 2 | `analyze` gọi tên `sql-queries`, `data-visualization`; `write-query` gọi `sql-queries` | thiếu skill được nhắc tới thì agent tìm không thấy | nạp các skill liên quan cùng nhau; instructions ghi rõ "chưa có công cụ vẽ biểu đồ — bỏ bước trực quan hóa, trình bày bảng" |
| 3 | 6 skill có link `../../CONNECTORS.md`; `data-context-extractor` dùng placeholder `~~data warehouse` | link hỏng nếu sao chép lệch cấu trúc (test link của repo sẽ báo lỗi); agent không biết "data warehouse" là gì | sao chép **giữ nguyên cấu trúc** vào `vendor/data-plugin/` (gồm `CONNECTORS.md`, `LICENSE`); instructions: "data warehouse = tool `execute_sql_<source>` / `search_objects_<source>` của DBHub, dialect PostgreSQL" |
| 4 | Viết theo kiểu slash command (`/analyze <question>`), có nhánh "chưa kết nối warehouse → nhờ người dùng dán dữ liệu" | không gây lỗi; nhánh dán dữ liệu không áp dụng | instructions nói rõ DBHub luôn có sẵn |
| 5 | Nội dung tiếng Anh, ví dụ tiền tệ `$` | câu trả lời có thể lẫn tiếng Anh / định dạng số Mỹ | instructions: trả lời tiếng Việt; định dạng số theo skill của domain (VND, triệu đồng) |
| 6 | Không có skill nào biết nghiệp vụ của công ty | agent không biết bộ lọc chuẩn, định nghĩa metric | đó chính là việc của **skill domain** (mục 4) |

## 4. Domain pack = skill do `data-context-extractor` sinh ra

`data-context-extractor` sinh một skill dạng `[company]-data-analyst/` gồm `SKILL.md` (dialect SQL, phân biệt thực thể, thuật
ngữ, **bộ lọc chuẩn**, **metric chính**, độ trễ dữ liệu) và `references/` (`entities.md`, `metrics.md`, `tables/<domain>.md`).
Các mục đó trùng với "Business rules" và "Data dictionary" của domain pack trong diagram v0, nên v2 dùng luôn định dạng này
thay vì tự đặt ra định dạng YAML riêng.

Quy trình tạo một domain pack (làm một lần, rồi cập nhật bằng iteration mode):

1. Mở Claude Code (hoặc Claude/Cowork) có cài Data plugin và kết nối DBHub làm MCP server.
2. Gọi bootstrap mode: "Create a data context skill for our timesheet database" → trả lời các câu hỏi về thực thể, metric,
   bộ lọc chuẩn, lỗi hay gặp.
3. Đổi tên skill sinh ra thành `timesheet-data-analyst`, đặt vào `packs/timesheet/skills/`, viết `pack.yaml`.
4. Review qua PR như code. Skill sinh ra chỉ có `name` + `description` trong frontmatter nên **qua được** validator của Agno.

Kết quả là mỗi agent object có hai lớp skill: **① skill chung của Data plugin** (cách phân tích) và **② skill domain** (dữ
liệu của công ty nghĩa là gì). Thứ tự nạp ①→② giữ nguyên trong danh mục skill; trùng tên thì ② thắng — dùng khi một domain
muốn thay hẳn một skill chung (ví dụ một `analyze` riêng cho tài chính).

## 5. Ánh xạ tạm sang bản 20 skill trong ảnh chụp

Chỉ dựa trên tên và mô tả hiển thị; cần file thật để xác nhận.

| Skill trong ảnh | Mô tả hiển thị | Gần với (bản 1.1.0) | Dự kiến |
|---|---|---|---|
| Index | Answer data questions and route analytics work | `analyze` | POC — skill vào chính |
| Analyze Data Quality | Assess tables and datasets before analysis or publication | `explore-data` + `validate-data` | POC |
| Build Dashboard | Create source-backed dashboards… | `build-dashboard` | sau POC — cần tool ghi file |
| Build Report | Turn reviewed evidence into polished analytical reports | chế độ "formal report" của `analyze` + mẫu tài liệu trong `validate-data` | sau POC — kèm report template của domain |
| Create Data Context | Customize analysis, reporting, and dashboard context | `data-context-extractor` | offline — sinh skill domain |
| Gather Business Context | Collect product and business context before analysis | phần câu hỏi của `data-context-extractor` | offline |
| Design KPIs | Define KPIs, driver metrics, guardrails, and scorecards | (không có) | offline — bổ sung mục metric của skill domain |
| Convert To Doc / Convert To Slides | tạo DOCX/Google Doc/slide từ "Data app" | (không có; phụ thuộc "Data app" của Claude) | không dùng — gắn với ứng dụng Claude |

## 6. Cách đưa vào repo (khi bắt đầu POC)

- Sao chép nguyên thư mục `data/` của plugin (chỉ các skill chọn dùng + `CONNECTORS.md` + `LICENSE`) vào
  `vendor/data-plugin/`, thêm `vendor/data-plugin/NOTICE.md` ghi repo, commit `8444efc`, ngày sao chép, các thay đổi (nếu có).
- Không sửa nội dung skill trong POC; mọi điều chỉnh đặt trong instructions của agent → nâng cấp chỉ là sao chép lại và xem diff.
- Thư mục `vendor/` cần được loại khỏi `ruff` nếu sau này có script Python trong skill.
