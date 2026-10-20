# Lịch sử công việc

Ghi lại **những gì đã làm**, mới nhất ở trên. Việc **sắp làm** nằm trong [CHECKLIST.md](CHECKLIST.md).

Quy ước khi thêm một mục:

- Tiêu đề: `## YYYY-MM-DD · <tên công việc>` (kèm link PR nếu có).
- Ghi: **Đã làm** (kết quả cụ thể), **Quyết định** (đã chọn gì, vì sao), **Còn mở** (chuyển sang CHECKLIST).
- Khi một mục trong CHECKLIST hoàn thành: đánh dấu `[x]` ở CHECKLIST và thêm một dòng tóm tắt vào đây.

---

## 2026-10-20 · Lab 01: tạo project từ thư mục trống với `.venv`, PyCharm, khối lệnh dán được vào zsh

**Đã làm**

- `docs/self-practices/guide_01_agno.md` mục 3.1 viết lại thành hai cách. **Cách A**: đã có project của Lab 00, chỉ
  `uv add -r requirements.txt`. **Cách B**: thư mục trống → `uv init --bare --no-workspace --python 3.12` →
  `uv python pin 3.12` → `uv venv` → `uv add -r requirements.txt` → chép 6 file nền của Lab 00 (bản đã sửa cho mcp 2.x)
  → kiểm tra. Có bảng giải thích từng lệnh, một khối macOS/Linux và một khối PowerShell để chép một lần, mục **Mở
  project trong PyCharm** (tự nhận `.venv`, chọn interpreter bằng tay, bảng phím tắt macOS/Windows). Hết lỗi
  `error: No pyproject.toml found…` khi chạy `uv add` ở thư mục trống.
- Bảng lỗi mục 8.1 thêm 4 dòng: thiếu `pyproject.toml`, `uv add` sửa nhầm `pyproject.toml` của project cha,
  `zsh: command not found: #`, PyCharm gạch đỏ import.
- `labs/llm-05-trung-cap-agno-agentos/README.md`: phần Cài đặt dùng hàm `lab01() { uv run --no-project … "$@"; }` thay
  cho biến `$AGNO` (zsh không tách biến thành nhiều từ nên `$AGNO python …` báo `command not found`); chú thích chuyển
  sang bảng; thêm link tới Cách B.

**Quyết định**

- Khối lệnh để dán không có chú thích `#`: zsh mặc định của macOS coi `#` là tên lệnh khi dán vào Terminal, dòng
  `REPO=…  # ghi chú` để `REPO` rỗng và các lệnh `cp` sau đó hỏng. Đặt `setopt interactivecomments` ở dòng đầu khối dán
  không cứu được vì zsh đọc cả khối dán rồi mới chạy (đã thử bằng pty + bracketed paste). Mỗi bước in tên bằng
  `echo '== N) …'`.
- `uv init --bare --no-workspace`: chỉ tạo `pyproject.toml`, không gộp vào project uv cha nếu người học lỡ đặt thư mục
  bên trong repo.
- Kiểm chứng (uv 0.11): khối lệnh lấy nguyên văn từ tài liệu chạy trên thư mục trống bằng bash và bằng zsh 5.9 (dán qua
  pty), 74 test của project tham chiếu qua trong môi trường tạo ra; `.venv` có sẵn từ `python -m venv` (3.11, 3.13)
  được `uv add` tạo lại bằng 3.12. Khối Cài đặt của README chạy qua 117 test (74 + 43 doc-sync) bằng cả hai shell.

**Còn mở**

- Chạy thử khối PowerShell trên Windows và các bước chọn interpreter trên PyCharm bản mới (CHECKLIST).

## 2026-10-19 · Dự án luyện tập và dữ liệu: mô tả, mục tiêu, bộ dữ liệu cho người mới

**Đã làm**

- Viết lại `docs/00-setup/05-du-lieu-luyen-tap.md` cho người chưa rành AI: bảng đọc nhanh 8 dự án (doanh nghiệp hỏi gì →
  dự án → dữ liệu và lĩnh vực → đích đến), vài khái niệm cần biết, rồi mỗi nhóm một mục (anchor `#g1`…`#g8`) gồm câu
  chuyện doanh nghiệp, dự án làm gì, **mục tiêu đạt được** đo bằng con số, và **dữ liệu**: lĩnh vực, bên trong có gì (số
  dòng, cột, khoảng thời gian), dùng để làm gì, vì sao chọn, hạn chế, giấy phép, cách tải. Số liệu các bộ dữ liệu đã đối
  chiếu nguồn: Telco 7.043 khách (26,5% rời mạng), M5 3.049 mặt hàng × 10 cửa hàng × 1.941 ngày, Credit Card Fraud
  284.807 giao dịch / 492 gian lận, MovieLens latest-small 100.836 lượt chấm điểm, MC-OCR 2.436 hoá đơn, SROIE ~1.000
  hoá đơn, Bộ luật Lao động 2019 17 chương 220 điều, Hillstrom 64.000 khách.
- `catalog/problems.yaml`: mỗi nhóm có `practice_project` viết lại bằng lời thường + `practice_target` (mục tiêu đạt
  được) + `practice_data` (dữ liệu, lĩnh vực); `make catalog` báo lỗi nếu thiếu. Trang nhóm sinh tự động và trang nhóm
  trên web hiện đủ ba ý kèm link tới mục chi tiết của nhóm trong tài liệu dữ liệu luyện tập.
- `projects/README.md`: bảng dự án luyện tập có cột "Dự án làm gì", "Mục tiêu đạt được", "Dữ liệu · lĩnh vực" (G1 ghi
  kết quả đã đạt); bảng riêng cho dự án tổ hợp và dự án khác. Tài liệu dữ liệu luyện tập có thẻ trong trang Tài liệu.

**Quyết định**

- Mục tiêu viết thành ngưỡng đo được (ví dụ "sai số thấp hơn ít nhất 10% so với seasonal naive", "đúng ≥ 95% trên phần
  tự xử lý") để người học biết khi nào là xong; con số cụ thể là đề xuất, chỉnh khi bắt đầu từng dự án.

## 2026-10-18 · Trang web: liên kết học xuyên suốt + đọc tài liệu ngay trên trang (định dạng như GitHub)

**Đã làm**

- **Liên kết chéo** lộ trình ↔ kỹ năng ↔ nhóm bài toán ↔ tài liệu, tính từ `catalog/docs.yaml` (mới — thay danh sách
  tài liệu viết cứng trong `site.py`; mỗi tài liệu khai báo `kind`, `step`, `skills`, `groups`, `combos`, `domains`,
  `pages`; `make catalog` kiểm tra file và id):
  - Bước lộ trình: thanh **Học ngay** (bài học + lab của bước) và nhãn "Có bài học + lab"; bước chưa có bài học gợi ý
    tài liệu theo kỹ năng của bước (vd. B7 → radar agent, lab harness, tự học Agno...). Giai đoạn: hướng dẫn, dự án,
    link setup.
  - Kỹ năng: thẻ **Học kỹ năng này** (bài học/lab/tài liệu theo mức, bước, nút học ngay, dự án áp dụng, đọc thêm theo
    mảng); dòng kỹ năng ở lộ trình nhóm và hướng chuyên sâu có nút **Học ngay** tới bài phù hợp mức.
  - Nhóm: **Học và thực hành nhóm này** (giai đoạn dùng nhóm làm dự án, dự án, tài liệu, lab); tổ hợp: dự án.
  - Tổng quan: thẻ **Tiếp tục học** — bước kế tiếp chưa xong + bài học, lab. Trang Tài liệu: thẻ có chip bước, kỹ năng,
    nhóm, tổ hợp, mảng, trang. Mỗi trang có dòng "Đọc thêm" từ `pages`.
- **Khung xem tài liệu toàn màn hình** (`#/doc/<đường dẫn>`), thay mọi link sang GitHub:
  - `src/aiarch/docview.py` render lúc build bằng markdown-it-py + mdit-py-plugins (GFM: bảng, task list, alert, autolink,
    footnote, `$…$`/`$$…$$`) + Pygments (bảng màu "prettylights" của GitHub); anchor tiêu đề theo đúng thuật toán của
    GitHub; thẻ HTML nguy hiểm bị vô hiệu như GFM. Gom 123 file `.md` + 51 file code được nhắc tới (xem có số dòng,
    `#L10-L20`) + ảnh, đi theo liên kết và cây thư mục; chỉ lấy file Git đang theo dõi.
  - Viết lại liên kết: tài liệu/code trong repo → mở trong khung xem; thẻ kỹ năng/nhóm/lộ trình/tổ hợp/ma trận sinh tự
    động → trang tương tác; ảnh → bản sao; permalink theo commit và file nhị phân → GitHub. Kiểm tra tự động: ~2.200
    link tới tài liệu, ~1.700 link tới trang tương tác, 0 link hỏng.
  - Trình duyệt: mermaid 11.17.2 và KaTeX 0.16.47 tự chứa trong `web/assets/vendor/` (ghim phiên bản, kiểm mã băm sha512,
    `make site-vendor`), chỉ tải khi tài liệu cần; vẽ lại sơ đồ khi đổi sáng/tối; mục lục bám theo vị trí đọc; nút sao
    chép code; đầu trang ghi bài thuộc bước/kỹ năng nào, học cùng lab nào; cuối trang đánh dấu kỹ năng đã đạt, bài
    trước/tiếp, cùng thư mục; nút Đóng/Esc/Back quay về đúng trang và vị trí cuộn.
- Kiểm thử: `tests/test_docview.py` (GFM, anchor GitHub, viết lại liên kết, mọi link của tài liệu thật, chỉ xuất file
  được theo dõi), `tests/test_site.py` (docs.yaml, mọi bước giai đoạn A có bài học + lab); `tests/test_docs_links.py`
  dùng chung thuật toán anchor. `make site-test` mở **mọi** tài liệu trên desktop + điện thoại (sơ đồ, công thức vẽ
  được, không tràn ngang) và các luồng mở/đóng/Esc/chuyển tài liệu/sang trang kỹ năng.
- Sửa sơ đồ sequence trong `projects/gpt-excel-agent-chatbot/docs/02-solution-approach.md`: dấu `;` trong lời nhắn là
  ký tự xuống dòng của mermaid nên sơ đồ hỏng (cả trên GitHub).

**Quyết định**

- **Render lúc build bằng Python, không render trên trình duyệt**: kiểm thử được từng liên kết, cùng thuật toán anchor
  với test tài liệu, trang nhẹ (chỉ tải đúng file cần đọc). Chỉ mermaid và KaTeX chạy trên trình duyệt (không có bản
  Python tương đương).
- **Tự chứa mermaid/KaTeX thay vì CDN** (~4 MB, `-diff` trong `.gitattributes`): sơ đồ và công thức luôn hiện, kiểm thử
  không cần mạng.
- Link tới tài liệu **sinh tự động** (thẻ kỹ năng, trang nhóm, lộ trình) mở **trang tương tác** tương ứng vì ở đó có
  tiến độ và nút học ngay; các trang `.md` khác của thư mục `generated/` vẫn xem được trong khung xem.

**Còn mở**

- Bật GitHub Pages (CHECKLIST P0). Repo private + Pages công khai thì nội dung tài liệu cũng công khai.
- Khi viết bài học giai đoạn B: khai báo trong `catalog/docs.yaml` với `step: B…` để các trang tự nối.

## 2026-10-18 · Giai đoạn A · Nền tảng: 8 bài học + 8 lab + real case churn xây từ đầu

**Đã làm**

- `docs/03-giai-doan-a-nen-tang/`: trang tổng quan + 8 bài A1–A8 theo lộ trình tuần 1–8. Mỗi bài có lý thuyết vừa đủ
  (ví dụ tính tay có đáp số), lab làm tới đâu giải thích tới đó, output chạy thật, kiểm tra kết quả theo "Đạt khi" của
  thẻ kỹ năng, lỗi thường gặp, bài tập. Ảnh kết quả trong `img/`.
- `projects/g1-churn-telco/` — real case **nhà mạng Sóng Xanh** (dữ liệu mô phỏng, cố định theo seed): 8 bảng vận
  hành có lỗi thật (trùng dòng, tỉnh 43 cách viết, NFD, ticket vào hệ thống trễ, trạng thái CRM tại ngày export) →
  làm sạch bỏ PII → bảng học as-of bằng một câu SQL DuckDB (359.908 dòng) + pandera → chia theo thời gian, bộ đánh giá
  đóng băng bằng mã băm (`eval/manifest.json`) → baseline + LightGBM, bootstrap theo khách → hiệu chỉnh, giá trị kỳ vọng,
  danh sách gọi theo năng lực → phân tích lỗi, feature marketing (v2) → 3 lý do SHAP tiếng Việt → API FastAPI (khoá,
  `/health`, `/version`, demo) + Docker (user thường, chỉ đọc) + MLflow → báo cáo 1 trang (`reports/README.md`).
  `make all` tái lập toàn bộ trong ~1 phút 20 giây.
- Kết quả trên 3 tháng đóng băng: LightGBM hơn logistic +0,032 precision@500 (KTC +0,017…+0,043); so với danh sách
  CSKH hiện tại: 140 thay vì 37 người gọi trúng/tháng, +44,5 triệu đ/tháng (KTC 39,0…49,6).
- 8 lab trong `labs/` (biz-01, data-01, stat-02, data-03, stat-05, biz-03, ops-01, biz-04), chạy bằng môi trường của
  dự án. 157 test của dự án: pipeline trên nhà mạng 3.000 khách, test đúng thời điểm (và test chứng minh nó bắt được
  lỗi lọc theo `created_at`), API, các lệnh `make` đầu–cuối, mọi lab (kể cả gọi API qua uvicorn thật), và đồng bộ
  bài học–code (`scripts/sync_doc.py`: khối code trích cả file hoặc từng hàm; test đòi mọi phần của mọi module có
  mặt trong bài).
- CI thêm job `churn-telco`: lint, test, rồi `make data features eval` dựng lại dữ liệu đầy đủ và kiểm tra khớp
  manifest đóng băng. Trang web thêm nhóm "Giai đoạn A · Nền tảng"; cập nhật `labs/README.md`, `projects/README.md`,
  README gốc, lộ trình.

**Quyết định**

- **Dữ liệu mô phỏng thay cho bộ Telco công khai**: bộ công khai là một bảng phẳng không có thời gian, không học được
  as-of và rò rỉ dữ liệu. Bộ Telco giữ lại làm bài tập chuyển giao (A2). Cơ chế churn chỉ mở ra ở A6 để đối chiếu với
  điều model học được.
- **Bài A3 dùng `features.py` như hộp đen** (A4 mới mổ xẻ): đánh giá cần bảng học nhưng lộ trình đặt baseline trước
  feature; giữ đúng thứ tự lộ trình, nói rõ trong bài.
- **Kết quả không như dự đoán thì ghi đúng như đo được**: chia ngẫu nhiên không lạc quan hơn chia theo thời gian trên
  dữ liệu này (lab A4 chuyển sang backtest cuốn chiếu); hiệu chỉnh Platt không cải thiện ECE của LightGBM trên tập
  đóng băng (A5 nói rõ, giữ Platt cho đồng bộ, bài tập chọn bằng valid); feature marketing tăng AUC và độ hiệu chỉnh
  ở HCM/BD nhưng precision@500 gần như không đổi (A6 rút ra kết luận nghiệp vụ: ưu đãi theo vùng).
- **Không pickle**: model lưu `model.txt` (LightGBM) + `bundle.json`; SHAP dùng `pred_contrib` của LightGBM (khớp thư
  viện shap tới 1e-8) nên image Docker không cần shap/mlflow (nhóm phụ thuộc `research`).
- **Bảng học giống từng bit giữa các lần dựng** (làm tròn `avg` trong SQL, `ORDER BY` cho khối marketing) để mã băm
  "phiên bản dữ liệu" ổn định cho MLflow và CI.
- Dockerfile cài `libgomp1` bằng apt và uv bằng pip (chạy được mọi nơi có PyPI); đã build và chạy thử container
  (healthy, uid 10001, hệ thống file chỉ đọc). Proxy của môi trường làm việc chặn kho apt Debian nên lần thử dùng một
  bản Dockerfile riêng cho sandbox, không đưa vào repo.

**Còn mở** (đã chuyển sang CHECKLIST)

- Chủ dự án học thử A1 → A8 và gửi feedback; bản notebook cho lab A2, A6 nếu cần; làm lại dự án trên dữ liệu thật đã
  ẩn danh (nếu được phép).

## 2026-10-18 · Lab 01 Agno chi tiết: 16 phần + project tham chiếu; bổ sung Agno → LangChain

**Đã làm**

- `docs/self-practices/guide_01_agno.md` viết lại thành bài chính của Lab 01: lộ trình 16 phần, Bước 0 nâng MCP lên
  2.x, `.env` cho OpenAI / model local / model giả, baseline `agno_cli.py` (giữ nguyên, đã chạy lại), bản đồ tính năng
  Agno, lỗi thường gặp. Năm bài con trong `docs/self-practices/agno/`: 01a (agent, tool, output có schema,
  streaming), 01b (session, memory, knowledge), 01c (HITL, hook, guardrail, model dự phòng), 01d (MCP client, team,
  workflow), 01e (AgentOS, AG-UI, A2A, MCP server, eval). Mỗi phần: cơ chế đo trên Agno 3.1.3, code hoàn chỉnh, giải
  thích, lệnh chạy, checkpoint, bài tập.
- `labs/llm-05-trung-cap-agno-agentos/`: project tham chiếu (16 module `agno_lab/pNN_*.py`, `mock_llm.py` giả API
  OpenAI cho chat/stream/embeddings, test chạy server thật bằng tiến trình riêng). 117 test: 74 hành vi + 43 đồng bộ
  tài liệu–code (`sync_doc.py`). Đã cài sạch từ `requirements.txt` và chạy lại.
- `docs/agent-radar/02-harness-agno-sang-langchain.md` thêm mục 6: output có schema, `session_state`, guardrail và
  model dự phòng, RAG, MCP client (`langchain-mcp-adapters`), team, workflow `StateGraph`, nhiều tool client cùng lượt.
  Lab LangChain thêm 7 module, 23 test hành vi; tổng 72 test.
- Lab 00 thêm một ghi chú trỏ sang Bước 0 (mcp 2.x); trang web thêm thẻ lab Agno.

**Quyết định**

- Lab 01 dùng **mcp 2.x**: `agno[mcp]` 3.1.3 cần `mcp>=2.1` (với mcp 1.30, `from agno.tools.mcp import MCPTools` lỗi
  `MCPError`). Sửa tối thiểu code Lab 00: `MCPServer` + `ToolError` + `--http` ở server, một dòng `is_error` ở client;
  các file Lab 00 khác giữ nguyên văn (`ruff.toml` của lab bỏ qua hai cảnh báo lint thay vì sửa code người học).
- Lab LangChain giữ **mcp 1.x**: `langchain-mcp-adapters` 0.3.2 cần `mcp<2`. Hai lab vì vậy dùng hai môi trường riêng.
- Học offline bằng model giả có kênh theo system prompt: test tất định cho team, memory, tóm tắt session; ghi rõ mock
  chỉ chứng minh code nối đúng, không chứng minh chất lượng model.

**Còn mở** (đã chuyển sang CHECKLIST)

- Chạy lại 16 phần với model thật; nối Claude Code vào MCP server của AgentOS và JWT (chưa kiểm chứng); đặt harness
  vào một node của workflow LangChain.

## 2026-10-17 · Trang web: menu "Tài liệu" gom mọi tài liệu theo chủ đề

**Đã làm**

- Menu mới **Tài liệu** (`#/tai-lieu`, nhảy thẳng tới nhóm bằng `#/tai-lieu/<nhóm>`): 21 tài liệu chia 4 nhóm — Nền tảng
  lộ trình, AI Agent (Nhóm 7), Lab và dự án, Theo dõi công việc; mỗi thẻ có mô tả một dòng, nhãn (Tài liệu sống, Có code
  chạy được, Tự học, ...) và đường dẫn trong repo, mở bản Markdown trên GitHub.
- Nhóm AI Agent đưa lên web các tài liệu trước đây chưa có: so sánh cơ chế agent, harness Agno → LangChain, lab LLM-05,
  bảng so sánh framework, 4 bài tự học `docs/self-practices`.
- Trang Tổng quan: thẻ tài liệu rút gọn thành lối tắt tới 4 nhóm. Menu cuộn ngang trên mobile tự kéo mục đang mở vào
  tầm nhìn.
- Danh sách tài liệu nằm một chỗ: `DOC_SECTIONS` trong `src/aiarch/site.py`. Test mới: mọi đường dẫn phải tồn tại, mỗi
  tài liệu thuộc đúng một nhóm và có mô tả. Smoke test thêm 2 route.

## 2026-10-17 · Harness agent: Agno → LangChain, cải tiến theo Claude Code + lab LLM-05 đầu tiên

**Đã làm**

- `docs/agent-radar/02-harness-agno-sang-langchain.md`: một run của Agno 3.1.3 đi qua những bước nào (có dẫn mã
  nguồn), 6 hành vi đã đo bằng thí nghiệm, bảng 5 run; ánh xạ sang LangChain 1.4.6 / LangGraph 1.2.16; toàn bộ code
  từng mảnh; 8 lớp cải tiến theo Claude Code và bộ đo vàng.
- `labs/llm-05-trung-cap-harness-langchain/`: lab đầu tiên của repo. Package `harness/` (model kịch bản + model thật,
  tool server + tool client qua `interrupt()`, instructions động, cửa sổ N run, memory theo user, giới hạn, người
  duyệt; `improved.py`: file luật, đọc trước khi ghi có dấu vân tay, kiểm chứng sau khi ghi, `<system-reminder>`,
  quyền theo vai trò, subagent, todo, tóm tắt/xoá kết quả tool cũ), `demo.py`, `eval_golden.py`.
- 39 test (24 hành vi + 15 đồng bộ tài liệu–code), chạy bằng `uv run --no-project --with ...` — không thêm gói vào
  lockfile chung.

**Quyết định**

- Code trong tài liệu sinh nguyên văn từ file của lab; `test_doc_sync.py` đỏ khi hai bên lệch.
- Sửa có chủ ý so với Agno: thiếu `user_id` thì không đọc/ghi memory (Agno dùng `"default"` chung); trần số bước
  dừng hẳn (`exit_behavior="end"`) và có thêm trần số lượt model.
- **Ưu tiên:** tập trung agent harness và workflow agent trước; AG-UI và API để sau (khớp
  `docs/self-practices` mục 10). Tài liệu 02 có phần Tóm tắt và bảng thứ tự học harness → workflow → AG-UI.

**Còn mở** (chuyển sang CHECKLIST)

- Chạy `eval_golden.py` với model thật; workflow agent bằng `StateGraph` (tiếp theo); test resume nhiều interrupt
  cùng lúc; endpoint AG-UI (để sau).

## 2026-10-14 · Radar agent — so sánh cơ chế agent của 4 framework

- `docs/agent-radar/01-co-che-agent.md`: vòng lặp tool, dừng và kết quả có cấu trúc, điểm can thiệp (hook, middleware,
  guardrail), tạm dừng/chạy tiếp, nhiều agent, bộ nhớ — Agno 3.1.3, OpenAI Agents SDK 0.23.1, LangGraph 1.2.15 +
  LangChain 1.4.5, Pydantic AI 2.56.0; đối chiếu trên mã nguồn từng gói.

## 2026-10-14 · Radar agent cho Nhóm 7 — tài liệu sống, cập nhật hằng tháng

**Đã làm**

- `docs/agent-radar/README.md`: kết luận theo nhu cầu, 8 tiêu chí (điều hướng, duyệt người, chạy bền, OTel, MCP, A2A,
  AG-UI, eval), xu hướng 2026 kèm bằng chứng, kiến trúc tham chiếu cho agent Nhóm 7, cách tự đo bằng golden set, quy
  trình cập nhật và quy tắc vòng radar.
- `catalog/agent_landscape.yaml`: 19 framework + 18 công cụ hỗ trợ (giao thức, quan sát, eval, chạy bền, bộ nhớ, sandbox),
  mỗi mục có vòng Adopt/Trial/Assess/Hold, mức kiểm chứng (source/docs/secondary), ngày review.
- `src/aiarch/landscape.py` + `make landscape-refresh` / `make landscape`: kéo số liệu PyPI/npm (+ GitHub khi có token)
  vào `catalog/agent_landscape.snapshot.json`, sinh `docs/agent-radar/generated/bang-so-sanh.md`, gắn cờ gói lâu không
  phát hành, lên major sau lần review, repo archive, mục quá hạn review. Test `tests/test_landscape.py`.
- Workflow `.github/workflows/agent-landscape.yml`: ngày 1 hằng tháng kéo số liệu và mở PR nếu có thay đổi.

**Quyết định**

- Adopt: Agno/AgentOS (đang dùng ở CMB-10, CMB-09). Trial: LangGraph, Pydantic AI, DSPy. Hold: AutoGen/Semantic Kernel
  (đã vào Microsoft Agent Framework), smolagents cho production, OpenAI Agents SDK khi cần AG-UI.
- Lớp chung: MCP cho tool, AG-UI cho giao diện, OTel → Langfuse cho trace, golden set riêng cho eval.

**Còn mở**

- Nhiều mục ở mức `secondary` — cần đọc tài liệu/mã nguồn trước khi dựa vào; chưa có số sao GitHub (môi trường làm bản
  này không gọi được GitHub API — workflow hằng tháng sẽ bổ sung).
- Cần bật quyền "Allow GitHub Actions to create and approve pull requests" để workflow mở PR.

## 2026-10-13 · CMB-10 — POC 0.2: quay lại agent Agno, công cụ Excel chạy ở add-in, Office add-in cho Excel thật ([#6](https://github.com/superken-python/ai-architecture/pull/6))

**Đã làm**

- Bỏ OpenAI Agents SDK và adapter tự viết; agent là một `Agent` Agno phục vụ qua interface AGUI của AgentOS, model
  `OpenAIResponses(gpt-5-mini, reasoning low, store=false)`.
- Công cụ Excel do giao diện khai báo qua AG-UI (`excel_get_context`, `excel_find_rows`, `excel_read_rows`,
  `excel_set_values`, `excel_append_rows`): run tạm dừng → giao diện chạy công cụ (tool ghi có xem trước + xác nhận,
  đọc lại sheet trước khi ghi) → gửi kết quả → run chạy tiếp.
- Một khung chat, hai host: web POC (bảng mô phỏng, file trên server) và **task pane Office add-in** (Office.js, Excel
  Table, giữ số 0 đầu, chèn file xuất vào workbook) + `addin/manifest.xml`, icon, `make addin-certs`, `make dev-https`,
  `make addin-manifest`.
- Chế độ offline và test dùng OpenAI Responses API giả lập trong tiến trình (luật cố định / kịch bản) — cùng đường code
  Agno như khi có key; từ chối `function_call_output` không khớp lời gọi hàm như OpenAI.
- Lệnh `/search`, `/datasets`, `/help` chuyển sang `POST /api/v1/commands` (không gọi model); `/search` mới dùng cột đang
  chọn, agent tự chọn cột khi tìm.
- 47 test unit + integration (tạm dừng/tiếp tục qua AgentOS thật, gpt-5-mini giả lập gọi song song tool server + tool
  Excel) + 2 test e2e (web POC; task pane với Office.js giả lập). Viết lại tài liệu 06, thêm ADR-09.

**Quyết định**

- ADR-09 (theo yêu cầu chủ dự án): quay lại agent Agno vì add-in cần frontend tools; thay ADR-08. Một Agent, không Team:
  đọc mã nguồn Agno 3.1.3 thấy thành viên Team nhận `dependencies` nhưng không nhận công cụ của client.

**Còn mở**

- Chưa chạy với gpt-5-mini thật và chưa chạy trên Excel thật (môi trường làm POC chặn `api.openai.com`, không có Excel).

## 2026-10-13 · CMB-10 — POC 0.1: AgentOS + AG-UI + OpenAI Agents SDK, chat → file Excel, /search → ghi vào cột ([#6](https://github.com/superken-python/ai-architecture/pull/6))

**Đã làm**

- `projects/cmb-10-excel-agent-addin/`: POC Python theo
  [best practice cấu trúc dự án](projects/python-ai-project-structure-best-practices.md) (`src/` layout, tầng API/service/
  schema/agent, prompt YAML tách khỏi code, uv + Makefile).
- Agent viết bằng **OpenAI Agents SDK** 0.23.1: `Điều phối` (triage) handoff sang `Excel Report Agent` (`export_excel`) và
  `Data Search Agent` (`search_data`); model mặc định `gpt-5-mini`; chưa có key thì chạy model offline (luật cố định).
- **AgentOS** (Agno 3.1.3) chỉ làm runtime: adapter tự viết `OpenAIAgentsAdapter` đổi sự kiện stream của SDK sang sự kiện
  AgentOS → AG-UI; session lưu SQLite.
- API dữ liệu giả lập (`/datasets`, `/search`, `/export` → `.xlsx`); workbook service lưu theo phiên bản, xem trước, ghi cột
  / thêm dòng có kiểm chứng (kiểu, phạm vi, trùng mã, `expected_version`), hoàn tác.
- Giao diện web (JS thuần, client AG-UI): khung chat + thẻ file → bấm xem dữ liệu; `/search` (theo cột chọn trên bảng hoặc
  `Cột: từ khóa`) → tích kết quả → **Ghi vào cột** / **Thêm thành dòng mới** → xác nhận.
- 38 test unit + integration (AG-UI qua AgentOS thật, `ScriptedModel` mô phỏng gpt-5-mini gọi tool) + 1 test e2e Chromium;
  hướng dẫn: `docs/06-poc-huong-dan-su-dung.md`.

**Quyết định**

- ADR-08 (chủ dự án chọn): agent và tool viết bằng OpenAI Agents SDK, không viết agent bằng Agno; thay ADR-06. Ghi dữ liệu
  theo mẫu *agent đề xuất → người dùng xác nhận trên giao diện → API ghi xác định*, không cần frontend tools.

**Còn mở**

- Chưa chạy với gpt-5-mini thật (chưa có key; môi trường làm POC chặn `api.openai.com`).
- Adapter chưa hỗ trợ frontend tools (tạm dừng/tiếp tục) — chỉ cần khi agent phải tự đọc sheet giữa run.

## 2026-10-13 · CMB-10 — ADR-07 chọn runtime agent cho Excel add-in ([#6](https://github.com/superken-python/ai-architecture/pull/6))

**Đã làm**

- So sánh AgentOS/Agno với Pydantic AI, Microsoft Agent Framework, LangGraph, Mastra, Google ADK, OpenAI Agents SDK và nền
  tảng low-code theo 6 tiêu chí, đọc mã nguồn phần AG-UI của từng framework và giấy phép trong metadata gói →
  `projects/cmb-10-excel-agent-addin/docs/05-adr-runtime-agent.md`.

**Quyết định** (đề xuất, chờ duyệt)

- Giữ AgentOS/Agno (Apache-2.0): duy nhất có sẵn frontend tools + tạm dừng/tiếp tục lưu ở server, xác thực, session, trace,
  MCP, skill, và dùng chung runtime với CMB-09. AG-UI là giao kèo để backend thay được.
- Dự phòng theo thứ tự: Pydantic AI → Microsoft Agent Framework → LangGraph (server `langgraph-api` là Elastic-2.0).

**Còn mở**

- Control plane của AgentOS (os.agno.com) trả phí khi nối AgentOS chạy thật — add-in không cần, nhưng CMB-09 cần tính nếu
  dùng AgentOS UI ở production.

## 2026-10-13 · Bài toán mới CMB-10 — trợ lý AI trong Excel nối với agent của hệ thống (chỉ tài liệu, [#6](https://github.com/superken-python/ai-architecture/pull/6))

**Đã làm**

- Phân loại: Nhóm 7 + Nhóm 6 → thêm tổ hợp **CMB-10** vào `catalog/combinations.yaml` (11 kỹ năng, 3 kỹ năng keo, 5 bẫy,
  metric end-to-end); thêm ví dụ vào Nhóm 7 (`problems.yaml`) và CMB-10 vào hướng "LLM ứng dụng & Agent"
  (`roadmap.yaml`); `make catalog` sinh lại 5 trang; số tổ hợp 9 → 10 trong README; thêm ví dụ phân rã vào bản đồ bài toán.
- `projects/cmb-10-excel-agent-addin/`: README (framing theo mẫu + kết luận nhanh) và 4 tài liệu nghiên cứu — mô tả bài
  toán và phân loại; giải pháp và kiến trúc (4 phương án, kết nối AG-UI, bộ công cụ Excel, bảo mật, triển khai, ADR);
  41 tính năng mở rộng; đánh giá khả thi (14 bằng chứng có nguồn, 12 rủi ro, ước lượng công sức, kế hoạch POC + go/no-go).
- Kiểm chứng: requirement set Excel (mới nhất ExcelApi 1.21) và API tìm/chèn/gộp hoàn tác trong `@types/office-js`
  1.0.611; mã nguồn `agno` 3.1.1 và 3.1.3 (AG-UI frontend tools + tạm dừng/tiếp tục run, REST, MCP, JWT); phiên bản npm
  của AG-UI client, CopilotKit, MSAL.js; tài liệu Claude for Excel và Microsoft Graph Excel API.

**Quyết định** (đề xuất, chờ duyệt)

- Không thêm nhóm thứ 9: "plugin trong Excel" là kênh giao diện, bài toán là tổ hợp G7 + G6.
- Phương án A (tự xây add-in React + Office.js, nối AgentOS qua AG-UI, cổng ghi đặt ở add-in) làm hướng chính; phương án B
  (Claude for Excel/Copilot + agent hệ thống qua MCP) chỉ chạy thử song song nếu công ty đã có license.
- "Code tìm và tính, LLM chọn tham số"; mọi lệnh ghi qua kiểm chứng + xem trước + xác nhận + một bước hoàn tác.

**Còn mở**

- 9 câu hỏi mở (agent hệ thống nào, phiên bản Excel, tenant/admin, license, chính sách dữ liệu, hệ thống nghiệp vụ,
  workbook mẫu, mạng, nhân lực) → [CHECKLIST.md](CHECKLIST.md).
- `learn.microsoft.com` bị chặn trong môi trường nghiên cứu nên đã đọc bản Markdown gốc trên GitHub của Microsoft; chưa
  chạy thử trên Excel thật.

## 2026-10-09 · Kế hoạch dự án Realtime Voice Translate (chỉ tài liệu)

**Đã làm**

- `projects/realtime-voice-translate/`: README (framing theo mẫu dự án) và
  [kế hoạch triển khai chi tiết](projects/realtime-voice-translate/docs/01-ke-hoach-trien-khai.md) cho web điện thoại dịch
  hội thoại trực tiếp Nhật ⇄ Anh ⇄ Việt: SLO, kiến trúc, chọn model cho GPU 8 GB, pipeline realtime, UI chia đôi, cấu trúc
  thư mục theo best practice, Docker hai phần + HTTPS nội bộ, triển khai trên máy GPU, eval, kế hoạch P0–P6, rủi ro, ADR.

**Quyết định** (đề xuất, chờ P0 đo)

- Cascade Silero VAD → Whisper `large-v3-turbo` (LID giới hạn ja/en/vi + prior theo nửa màn hình) → Hy-MT2-1.8B qua
  llama.cpp; ước tính 4,5–5 GB VRAM.
- WebSocket thay vì WebRTC cho MVP: chưa phát âm thanh (TTS) nên chưa cần WebRTC.
- Chỉ triển khai trên máy GPU (chủ dự án chốt): `make deploy` build image tại chỗ theo commit → chạy → smoke → tự
  rollback khi lỗi; không dùng GitHub Actions để deploy.
- Tạm bỏ ngrok (chủ dự án chốt): chỉ dùng trong mạng nội bộ; nginx phục vụ HTTPS bằng chứng chỉ mkcert vì điện thoại cần
  HTTPS để dùng micro; giao diện, REST và WebSocket cùng một origin.

**Còn mở**

- Yêu cầu số 7 còn trống; GPU cụ thể; có tên miền riêng để làm HTTPS nội bộ không; có bật CI kiểm thử riêng không
  → [CHECKLIST.md](CHECKLIST.md).

## 2026-10-08 · Trang web lộ trình cho GitHub Pages

**Đã làm**

- `catalog/roadmap.yaml`: chuyển lộ trình theo tuần từ Markdown sang dữ liệu — 4 giai đoạn (A Nền tảng, B GenAI,
  C Chuyên sâu, **D Nâng cao · Production** mới), 25 bước (việc cần làm, sản phẩm nộp, kỹ năng + mức mục tiêu),
  5 hướng chuyên sâu, thanh ngang chữ T, thói quen xuyên suốt. Thêm câu hỏi nhận diện bài toán vào `problems.yaml`.
- Bộ kiểm tra lộ trình: kỹ năng tiên quyết phải xuất hiện ở bước trước, mức mục tiêu không giảm, lộ trình phủ đủ
  65/65 kỹ năng, chặn trường lạ (lỗi YAML do dấu phẩy chưa đặt trong ngoặc kép — đã gặp và sửa trong lúc làm).
- Sinh `docs/02-skill-map/generated/lo-trinh.md`; thẻ kỹ năng có thêm dòng "Trong lộ trình"; `04-lo-trinh-hoc.md` rút
  gọn còn nguyên tắc + liên kết.
- `web/` + `src/aiarch/site.py`: trang một trang (HTML/CSS/JS thuần) gồm Tổng quan, Lộ trình, Nhóm bài toán (quiz 30 giây,
  lộ trình 3 chặng mỗi nhóm), Kỹ năng (tìm không dấu, lọc), Ma trận + bản đồ nhiệt, Tổ hợp, Tiến độ (lưu trình duyệt,
  xuất/nhập JSON); sáng/tối; vừa màn hình điện thoại.
- `.github/workflows/pages.yml` triển khai lên Pages khi `main` đổi; CI thêm job kiểm thử trang bằng Chromium thật
  (`scripts/smoke_site.py`, 23 trang × 2 cỡ màn hình); `make site`, `make site-serve`, `make site-test`.

**Quyết định**

- Không dùng framework/bundler: trang tĩnh thuần, dữ liệu nhúng vào `index.html` nên mở file trực tiếp cũng chạy.
- Tiến độ chỉ lưu trong trình duyệt người xem (không backend); chuyển máy bằng file JSON.
- Giai đoạn D là đề xuất thêm để có mức Nâng cao (lộ trình gốc dừng ở tháng 6) — cần chủ dự án duyệt.

**Còn mở**

- Bật Pages trong Settings (Source: GitHub Actions) — chỉ chủ repo làm được.
- Review nội dung từng bước trong `catalog/roadmap.yaml`.

## 2026-10-05 · CMB-09 Data Agent OS — thiết kế v2 cho POC tối giản ([#4](https://github.com/superken-python/ai-architecture/pull/4))

**Đã làm**

- Vẽ lại kiến trúc v2 (`docs/assets/kien-truc-v2.svg`) và thêm sequence diagram cho **khởi tạo agent object**, **một lần chạy**,
  biến thể OpenAI Agents SDK.
- Đánh giá tái sử dụng 10 skill của Data plugin (`anthropics/knowledge-work-plugins`, thư mục `data`, commit `8444efc`,
  Apache-2.0): chạy validator của Agno (9/10 lỗi vì `argument-hint`/`user-invocable`), nạp được cả 10 bằng `validate=False`.
- Viết lại chi tiết kỹ thuật thành tài liệu POC, ADR-001 v2, checklist POC (P0 → POC-1/2/3). Xóa tài liệu chỉ dùng cho v1.

**Quyết định (đề xuất, chờ duyệt)**

- Bỏ khỏi POC: review/learning, auth/RBAC, Data Gateway, router, workflow báo cáo. Platform DB là PostgreSQL.
- Không còn pack `core` tự viết: skill chung lấy từ Data plugin (6 skill chỉ-hướng-dẫn), nạp **trước** skill domain.
- Domain pack = `pack.yaml` + một skill sinh bằng `data-context-extractor` + `evals.yaml`.
- POC-1/2 chỉ dùng Agno; OpenAI Agents SDK là POC-3 tùy chọn (một agent, skill qua tool `load_skill`, không sandbox).

**Còn mở**

- Bản Data plugin 20 skill mà chủ dự án đang cài không có trong repo công khai — cần file thật để kiểm tra lại (P0-02).

## 2026-10-05 · Thiết kế dự án nghiên cứu CMB-09 Data Agent OS ([#3](https://github.com/superken-python/ai-architecture/pull/3), đã merge)

**Đã làm**

- Tạo `projects/cmb-09-data-agent-os/` (chỉ tài liệu thiết kế, chưa có code): kiến trúc v1 (sơ đồ SVG + các luồng Mermaid),
  review diagram v0 (13 điểm cần bổ sung), chi tiết kỹ thuật, ADR-001 về OpenAI Agents SDK, checklist triển khai 9 giai đoạn.
- Kiểm chứng API trên đúng phiên bản: `agno` 3.1.1 (AgentOS, `BaseExternalAgent`, Skills, tracing), `openai-agents` 0.23.1
  (`TracingProcessor`, skills chỉ qua sandbox, `ScriptedModel`), DBHub 1.4.0 + `mcp` 2.3.0 (chạy thử 2 nguồn SQLite), `sqlglot` 30.

**Quyết định (đề xuất, chờ duyệt)**

- Agno là runtime chính; OpenAI Agents SDK là runtime phụ qua adapter tự viết; trong luồng OpenAI, agent chuyên trách nạp skill
  core trước, agent điều phối thì không; không dùng SandboxAgent mặc định.
- Pack `core` (kỹ năng chung của data agent) luôn nạp trước mọi domain pack; skill an toàn bị khóa.
- Agent không gọi DBHub trực tiếp mà qua Data Gateway (kiểm quyền theo người dùng, chặn PII, ghi evidence).
- Trace của cả hai runtime lưu chung bảng `traces`/`spans` của AgentOS; mặc định không gửi trace lên OpenAI.

**Còn mở**

- Chủ dự án trả lời mục P0 trong `projects/cmb-09-data-agent-os/CHECKLIST.md` trước khi bắt đầu P1.

## 2026-10-04 · Thêm CHECKLIST và HISTORY

**Đã làm**

- Tạo `CHECKLIST.md` (việc sắp làm, chia theo giai đoạn, kèm các câu hỏi cần chủ dự án quyết định) và file
  lịch sử này.

**Còn mở**

- Chủ dự án review `CHECKLIST.md`: sửa thứ tự ưu tiên, trả lời mục "Cần quyết định".

## 2026-10-04 · Giai đoạn 2 — bản đồ kỹ năng + setup + cấu trúc dự án ([#1](https://github.com/superken-python/ai-architecture/pull/1), đã merge)

**Đã làm**

- `docs/00-setup/`: 6 tài liệu chuẩn bị môi trường (công cụ, uv và nhóm phụ thuộc, API key và quy tắc dữ liệu,
  GPU, dữ liệu luyện tập, xử lý sự cố) và `make doctor`.
- `docs/01-problem-map/`: bản Markdown của tài liệu giai đoạn 1, kèm file `.docx` gốc.
- `catalog/`: 8 nhóm, 2 họ bài toán, 65 kỹ năng trong 10 mảng (mỗi kỹ năng 3 mức), 9 tổ hợp.
- `src/aiarch/catalog.py`: kiểm tra catalog (gồm kiểm tra độ phủ so với ma trận giai đoạn 1) và sinh tài liệu
  `docs/02-skill-map/generated/`.
- `docs/02-skill-map/`: kiến trúc kỹ năng, kỹ năng kết hợp, tiết kiệm token mà vẫn chính xác, lộ trình 6 tháng.
- Hạ tầng: `pyproject.toml` + `uv.lock`, Makefile, pre-commit, CI, mẫu PR, mẫu kỹ năng/lab/dự án, test (52).

**Quyết định**

- YAML trong `catalog/` là nguồn dữ liệu duy nhất; tài liệu dạng bảng đều sinh tự động.
- Tầng kỹ năng (nền tảng / cầu nối / trong họ / chuyên biệt / bổ trợ) tính tự động từ mức sử dụng, không gán tay.
- Thêm 2 mảng so với giai đoạn 1: PY (lập trình nền tảng) và EFF (tiết kiệm token & độ tin cậy).
- Tài liệu trung lập nhà cung cấp LLM; số liệu giá/caching chỉ dùng làm ví dụ và ghi rõ thời điểm.

**Kết quả kiểm chứng**

- `make check` xanh; cả 10 nhóm phụ thuộc cài và import được trên Linux.
- Chưa kiểm chứng: setup trên Windows/macOS, Colab/Kaggle, lệnh tải dữ liệu Kaggle.

## 2026-10-04 · Giai đoạn 1 — bản đồ bài toán AI doanh nghiệp (v1)

**Đã làm**

- Tài liệu `ban-do-bai-toan-ai-doanh-nghiep_v1_20261004.docx`: 8 nhóm bài toán trong 4 khối, cây nhận diện
  30 giây, ma trận 8 mảng kỹ năng × 8 nhóm, chi tiết từng nhóm, quy trình ĐÚNG → NHANH → CHÍNH XÁC → THUYẾT PHỤC,
  lộ trình 6 tháng và bảng tự đánh giá.
