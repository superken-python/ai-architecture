# Checklist — việc sắp làm

Đây là bản **đề xuất** để chủ dự án review: sửa, xóa, thêm, đổi thứ tự thoải mái. Việc đã xong được đánh dấu
`[x]` và ghi tóm tắt vào [HISTORY.md](HISTORY.md).

Ký hiệu ưu tiên: **P0** làm ngay · **P1** làm trong giai đoạn hiện tại · **P2** khi có thời gian.
Mã trong ngoặc (`ML-07`, `G6`, `CMB-08`) tham chiếu [danh mục kỹ năng](docs/02-skill-map/generated/README.md).

## ❓ Cần chủ dự án quyết định (ảnh hưởng thứ tự mọi việc bên dưới)

- [ ] **Hướng chuyên sâu ưu tiên** cho công ty (chọn 1–2): Rủi ro & tín dụng (G1+G3) · Dự báo & vận hành (G2+G8) ·
      Cá nhân hóa (G4+G8) · Document AI (G5+G6) · LLM ứng dụng & Agent (G6+G7).
- [ ] **Nhà cung cấp LLM chính** để viết ví dụ code cho lab (tài liệu vẫn giữ trung lập).
- [ ] **Dữ liệu nội bộ** nào được phép dùng cho dự án chuyên sâu, ở dạng nào (ẩn danh hóa?), ai phê duyệt.
- [ ] **Ngân sách** API/GPU mỗi tháng cho việc học (để đặt `LLM_DAILY_BUDGET_USD` và giới hạn trên tài khoản).
- [ ] **Người review** kỹ thuật và nghiệp vụ cho PR.
- [ ] Ngày bắt đầu lộ trình 6 tháng (để gắn mốc tuần vào lịch).

## Giai đoạn 2.5 · Rà soát và hoàn thiện nền móng

- [ ] **P0** Review nội dung catalog: mức Cốt lõi/Cần của từng kỹ năng cho từng nhóm, thêm/bớt kỹ năng
      (`catalog/skills.yaml`).
- [ ] **P0** Bật bảo vệ nhánh `main` trên GitHub: bắt buộc qua PR, CI phải xanh.
- [ ] **P1** Thử setup trên Windows (WSL2) và macOS theo `docs/00-setup/`, sửa các bước sai.
- [ ] **P1** Thử tải dữ liệu Kaggle và MovieLens theo `05-du-lieu-luyen-tap.md`.
- [x] **P1** Mô tả rõ dự án luyện tập của 8 nhóm (làm gì, mục tiêu đạt được) và từng bộ dữ liệu (lĩnh vực, có gì, dùng để
      làm gì) → `docs/00-setup/05-du-lieu-luyen-tap.md`, `catalog/problems.yaml`, `projects/README.md`.
- [ ] **P1** Review các ngưỡng mục tiêu đề xuất của 7 dự án chưa làm (G2–G8) trước khi bắt đầu từng dự án.
- [ ] **P1** Thêm mẫu issue GitHub: "Lab mới", "Dự án mới", "Tự đánh giá tuần", "Đề xuất sửa catalog".
- [ ] **P2** Tạo GitHub Project (bảng Kanban) liên kết với checklist này.
- [x] **P2** Xuất bản đồ kỹ năng thành trang HTML để chia sẻ cho người không dùng GitHub → trang web lộ trình (`web/`).
- [ ] **P0** Bật GitHub Pages: Settings → Pages → Source: **GitHub Actions** (xem `web/README.md`), rồi kiểm tra trang
      trên điện thoại và máy tính.
- [ ] **P1** Review nội dung lộ trình theo bước (`catalog/roadmap.yaml`): việc cần làm, sản phẩm nộp, mức mục tiêu của
      từng tuần; nội dung giai đoạn D (đề xuất mới) và 5 hướng chuyên sâu.
- [ ] **P2** Gắn tên miền riêng hoặc thêm trang vào menu nội bộ của công ty (nếu cần).
- [x] **P1** Trang web: liên kết xuyên suốt lộ trình ↔ kỹ năng ↔ nhóm ↔ tài liệu, đọc tài liệu ngay trên trang (định
      dạng như GitHub) → `catalog/docs.yaml` + `src/aiarch/docview.py`.
- [ ] **P1** Mỗi khi thêm bài học/lab/dự án mới: khai báo trong `catalog/docs.yaml` (`step` hoặc `skills`, `groups`)
      để bước, kỹ năng, nhóm trên web tự có nút "Học ngay".

## Giai đoạn 3 · Thư viện dùng chung `src/aiarch/` (làm song song với lab)

Kỹ năng dùng chung → code dùng chung. Làm trước các lab cần đến.

- [ ] **P1** `aiarch.eval`: metric phổ biến (AUC, PR-AUC, precision@k, WAPE/MASE, Recall@K/NDCG) +
      khoảng tin cậy bootstrap + so sánh cặp hai hệ (`STAT-02`, `BIZ-02`).
- [ ] **P1** `aiarch.llm`: client LLM bọc mỏng, ghi token/chi phí/độ trễ mỗi lần gọi, dừng khi vượt ngân sách,
      retry có backoff, cache theo hash (`EFF-01`, `EFF-02`, `PY-04`).
- [ ] **P1** `aiarch.vi`: tiện ích tiếng Việt — chuẩn hóa NFC, tách từ cho BM25, regex CCCD/số điện thoại/tiền
      (`DATA-06`).
- [ ] **P2** `aiarch.data`: hàm tải và cache các bộ dữ liệu luyện tập vào `data/raw/`.

## Giai đoạn 3 · Labs (theo lộ trình tuần, giai đoạn A trước)

Mỗi lab: `labs/<id>-<mức>-<tên>/` theo `templates/lab/README.md`.

- [x] **P1** Giai đoạn A (tuần 1–8): 8 lab `biz-01`, `data-01`, `stat-02`, `data-03`, `stat-05`, `biz-03`, `ops-01`,
      `biz-04` + 8 bài học [docs/03-giai-doan-a-nen-tang/](docs/03-giai-doan-a-nen-tang/README.md) trên real case churn
- [ ] **P1** Chủ dự án học thử Giai đoạn A theo bài A1 → A8 (xây lại từ đầu trong repo riêng) và gửi feedback: bài
      nào thiếu giải thích, bước nào kẹt, bài tập nào quá dễ/khó
- [ ] **P2** Giai đoạn A: bản notebook (`.ipynb`) cho lab A2, A6 nếu người học thích Jupyter hơn script `# %%`
- [ ] **P2** Tuần 9–10: `llm-02` structured output + validate · `eff-01` đo token & chi phí trên tiếng Việt
- [ ] **P2** Tuần 11: `ml-07` BM25 vs embedding vs hybrid trên văn bản tiếng Việt
- [ ] **P2** Tuần 13–14: `llm-04` golden set + LLM-as-judge · `eff-02` prompt caching · `eff-07` lớp kiểm chứng
- [ ] **P2** Lab "thanh ngang chữ T" cho G2, G3, G4, G5, G7, G8 (baseline tối thiểu mỗi nhóm)
- [x] **G7** `llm-05` harness agent bằng LangChain tương đương Agno + cải tiến theo Claude Code
      ([lab](labs/llm-05-trung-cap-harness-langchain/README.md), [tài liệu](docs/agent-radar/02-harness-agno-sang-langchain.md))
- [ ] **P2** `llm-05`: chạy `eval_golden.py` với model thật (gpt-5-mini và một model local), ghi điểm + token + chi phí
- [x] **P1** Workflow agent bằng LangGraph `StateGraph` (song song, vòng sửa có giới hạn, rẽ nhánh, `interrupt()` duyệt,
      lưu bền) — [mục 6.7](docs/agent-radar/02-harness-agno-sang-langchain.md#67-workflow), cùng cấu trúc Phần 11 Lab 01
- [ ] **P2** `llm-05`: đặt harness của mục 4 vào một node của workflow mục 6.7 (bước cần tự chọn tool), giữ người duyệt
      ở node `review`; nối với [Lab 03 LangGraph](docs/self-practices/guide_03_langgraph.md)
- [x] **P2** `llm-05`: test resume khi nhiều tool client dừng cùng lúc (`resume_all`, mục 6.8)
- [x] **G7** Lab 01 Agno chi tiết: baseline + 16 phần có code, cơ chế đã đo và checkpoint
      ([tài liệu](docs/self-practices/guide_01_agno.md), [project tham chiếu](labs/llm-05-trung-cap-agno-agentos/README.md))
- [ ] **P2** Lab 01: chạy lại 16 phần với model thật (gpt-5-mini và một model local), ghi chỗ hành vi khác `mock_llm`
- [ ] **P3** Lab 01: kiểm chứng nối Claude Code vào MCP server của AgentOS (`claude mcp add`, Phần 15) và JWT của AgentOS
- [x] **P1** Lab 01: tạo project từ thư mục trống (`uv init` → `.venv` → `uv add` → PyCharm), khối lệnh dán được vào zsh
      của macOS ([Cách B, mục 3.1](docs/self-practices/guide_01_agno.md#cách-b--bắt-đầu-từ-thư-mục-trống))
- [ ] **P3** Lab 01: chạy thử khối PowerShell của Cách B trên Windows và các bước chọn interpreter trên PyCharm bản mới;
      sửa tên menu nếu khác
- [ ] **P3 · để sau** `llm-05`: endpoint AG-UI cho harness LangChain (thay AgentOS cho CMB-10) — hoãn theo quyết định
      2026-10-17: tập trung harness và workflow agent trước

## Giai đoạn 4 · Dự án luyện tập

- [x] **G9** Thêm Nhóm 9 · Tạo nội dung đa phương tiện (khối E · Sáng tạo, kỹ năng PY-05, DL-07, hướng chuyên sâu
      "Nội dung đa phương tiện") và [video dạy chữ cái](projects/g9-video-chu-cai/README.md) dựng bằng code (cách A),
      có video trên trang Nhóm 9 và [hướng dẫn tự làm bằng Claude Code](projects/g9-video-chu-cai/docs/huong-dan-claude-code.md).
- [ ] **P0** `projects/g9-video-chu-cai/` — thu âm câu chữ P (`giong-thu-am/chu-20.wav`): giọng Piper vais1000 không đọc
      được âm "pờ" (máy nghe thành "thờ"). Rồi `make video && make qa`.
- [ ] **P0** `projects/g9-video-chu-cai/` — giáo viên xem và nghe duyệt cả video theo
      [danh sách kiểm tra](projects/g9-video-chu-cai/docs/huong-dan-claude-code.md#7--người-duyệt-kiểm-tra-trước-khi-dùng-với-bé)
      (cách đọc âm, dấu thanh, hình hợp lứa tuổi) trước khi dùng với bé.
- [ ] **P1** `projects/g9-video-chu-cai/` — chủ dự án chọn bài tiếp theo cho lớp 3 (vd. vần, từ chỉ sự vật – hoạt động –
      đặc điểm); mở rộng kịch bản cho thẻ nhiều chữ (vần "ang", "anh") thay vì một chữ cái.
- [ ] **P2** `projects/g9-video-chu-cai/` — thử cách B cho cảnh mở đầu/kết (công cụ tạo video có ảnh tham chiếu nhân
      vật), giữ phần dạy chữ bằng code; so chi phí và độ nhất quán nhân vật.

- [x] **G7 + G6** Nghiên cứu [GPT Excel Agent Chatbot](projects/gpt-excel-agent-chatbot/README.md): mô tả bài toán,
      solution approach, khả thi và nguồn Microsoft; chỉ Markdown, chưa code.
- [ ] **P1** Trước khi triển khai Excel chatbot: chốt Excel build/tenant, workbook/schema và API/auth của agent;
      xem [kế hoạch POC đề xuất](projects/gpt-excel-agent-chatbot/docs/03-danh-gia-kha-thi.md).
- [x] **P1** `projects/g1-churn-telco/` — mốc Giai đoạn A: top 500 khách + lý do SHAP, chạy qua API Docker, bộ đánh giá
      đóng băng, báo cáo 1 trang (real case của 8 bài học).
- [ ] **P2** `projects/g1-churn-telco/` — làm lại trên dữ liệu thật của công ty (nếu được phép, đã ẩn danh): thay
      `simulate.py` + `clean.py`, giữ nguyên bảng học, bộ đánh giá, harness, API.
- [ ] **P2** `projects/g6-rag-handbook/` — mốc cuối tháng 4: RAG tiếng Việt + golden set ~100 câu + bảng
      chất lượng–chi phí–độ trễ.
- [ ] **P2** `projects/cmb-08-ticket-cascade/` — chứng minh tiết kiệm token mà độ chính xác không giảm.
- [ ] **P1** `projects/cmb-09-data-agent-os/` — chủ dự án review thiết kế v2 (kiến trúc POC, tái sử dụng skill Data plugin,
      ADR-001), trả lời mục P0 rồi làm POC theo [checklist riêng của dự án](projects/cmb-09-data-agent-os/CHECKLIST.md).
- [ ] **P1** `projects/realtime-voice-translate/` — chủ dự án review
      [kế hoạch triển khai](projects/realtime-voice-translate/docs/01-ke-hoach-trien-khai.md), trả lời câu hỏi mở (mục 16,
      gồm yêu cầu số 7 còn trống), rồi làm P0: thu golden set + benchmark model trên máy GPU 8 GB.
- [ ] **P1** `projects/cmb-10-excel-agent-addin/` — chủ dự án review
      [nghiên cứu khả thi](projects/cmb-10-excel-agent-addin/README.md) (phân loại CMB-10, 4 phương án, kiến trúc AG-UI,
      41 tính năng), trả lời 9 câu hỏi mở rồi làm P0 → POC theo
      [kế hoạch POC](projects/cmb-10-excel-agent-addin/docs/04-danh-gia-kha-thi.md#6-kế-hoạch-poc).
- [ ] **P1** `projects/cmb-10-excel-agent-addin/` — điền `OPENAI_API_KEY` vào `.env`, chạy POC 0.2 với `gpt-5-mini`
      (các câu ở [hướng dẫn §7](projects/cmb-10-excel-agent-addin/docs/06-poc-huong-dan-su-dung.md#7-sử-dụng)); ghi lại
      độ trễ, số token, câu nào agent hiểu sai hoặc gọi sai công cụ Excel.
- [ ] **P1** `projects/cmb-10-excel-agent-addin/` — nạp add-in vào **Excel thật** (web + Windows/Mac) theo
      [addin/README.md](projects/cmb-10-excel-agent-addin/addin/README.md), chạy lại kịch bản của `tests/e2e/test_taskpane.py`
      bằng tay, ghi khác biệt so với Office.js giả lập.
- [ ] **P1** `projects/cmb-10-excel-agent-addin/` — chủ dự án review POC 0.2 và
      [ADR-09](projects/cmb-10-excel-agent-addin/docs/05-adr-runtime-agent.md#bổ-sung--adr-09--quay-lại-agent-agno-một-agent-công-cụ-excel-chạy-ở-add-in)
      (một agent Agno, không agent điều hướng vì thành viên Team không nhận công cụ Excel); quyết định bước tiếp:
      đăng nhập (NAA), nối API dữ liệu thật, golden set.
- [ ] **P2** Dự án của hướng chuyên sâu đã chọn — mốc cuối tháng 6.

## Giai đoạn 5 · Production (dự kiến)

- [ ] **P2** Mẫu dịch vụ: FastAPI + Docker + health check + version model + tracing.
- [ ] **P2** Mẫu giám sát: drift (Evidently) cho model bảng; dashboard chi phí cho hệ LLM.
- [ ] **P2** Quy trình đánh giá trước khi triển khai: offline → shadow → A/B, tiêu chí go/no-go.
- [ ] **P2** Checklist bảo mật & tuân thủ dữ liệu cá nhân (làm cùng pháp chế).

## Duy trì định kỳ

- [ ] **P1** Bật Settings → Actions → General → "Allow GitHub Actions to create and approve pull requests" để workflow
      [radar agent](docs/agent-radar/README.md) mở PR số liệu hằng tháng; chạy thử bằng "Run workflow".
- [ ] Mỗi tháng: duyệt PR số liệu radar agent — xem cột **Cờ** trong
      [bảng so sánh](docs/agent-radar/generated/bang-so-sanh.md), sửa `catalog/agent_landscape.yaml`, `make landscape`.
- [ ] Mỗi quý: review toàn bộ radar agent, nâng các mục `secondary` lên `docs`/`source`, tìm framework mới.

- [ ] Mỗi tuần: cập nhật [bảng tự đánh giá](docs/02-skill-map/generated/tu-danh-gia.md) cá nhân + 1 paper (`BIZ-06`).
- [ ] Mỗi quý: rà lại catalog (công cụ lỗi thời, kỹ năng mới), nâng phiên bản thư viện (`uv lock --upgrade`),
      kiểm tra lại số liệu giá/caching trong `docs/02-skill-map/03-tiet-kiem-token-chinh-xac.md`.
- [ ] Khi bản đồ bài toán có phiên bản mới (v2): cập nhật `catalog/problems.yaml` → `make catalog` → xử lý cảnh báo
      thiếu độ phủ.
