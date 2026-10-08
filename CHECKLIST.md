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
- [ ] **P1** Thêm mẫu issue GitHub: "Lab mới", "Dự án mới", "Tự đánh giá tuần", "Đề xuất sửa catalog".
- [ ] **P2** Tạo GitHub Project (bảng Kanban) liên kết với checklist này.
- [x] **P2** Xuất bản đồ kỹ năng thành trang HTML để chia sẻ cho người không dùng GitHub → trang web lộ trình (`web/`).
- [ ] **P0** Bật GitHub Pages: Settings → Pages → Source: **GitHub Actions** (xem `web/README.md`), rồi kiểm tra trang
      trên điện thoại và máy tính.
- [ ] **P1** Review nội dung lộ trình theo bước (`catalog/roadmap.yaml`): việc cần làm, sản phẩm nộp, mức mục tiêu của
      từng tuần; nội dung giai đoạn D (đề xuất mới) và 5 hướng chuyên sâu.
- [ ] **P2** Gắn tên miền riêng hoặc thêm trang vào menu nội bộ của công ty (nếu cần).

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

- [ ] **P1** Tuần 1–2: `py-02` cấu trúc dự án & uv · `data-01` SQL as-of với DuckDB · `stat-01` vì sao accuracy đánh lừa
- [ ] **P1** Tuần 3: `ml-01` baseline + bộ đánh giá cố định · `stat-02` khoảng tin cậy cho metric
- [ ] **P1** Tuần 4: `data-03` phát hiện leakage (cố tình tạo leakage rồi bắt nó)
- [ ] **P1** Tuần 5–6: `ml-02` LightGBM · `stat-05` chọn ngưỡng theo chi phí & đường coverage–accuracy · `ml-04` SHAP
- [ ] **P1** Tuần 7: `ops-01` FastAPI + Docker cho model
- [ ] **P2** Tuần 9–10: `llm-02` structured output + validate · `eff-01` đo token & chi phí trên tiếng Việt
- [ ] **P2** Tuần 11: `ml-07` BM25 vs embedding vs hybrid trên văn bản tiếng Việt
- [ ] **P2** Tuần 13–14: `llm-04` golden set + LLM-as-judge · `eff-02` prompt caching · `eff-07` lớp kiểm chứng
- [ ] **P2** Lab "thanh ngang chữ T" cho G2, G3, G4, G5, G7, G8 (baseline tối thiểu mỗi nhóm)

## Giai đoạn 4 · Dự án luyện tập

- [ ] **P1** `projects/g1-churn-telco/` — mốc cuối tháng 2: top 500 khách + lý do SHAP, chạy qua API.
- [ ] **P2** `projects/g6-rag-handbook/` — mốc cuối tháng 4: RAG tiếng Việt + golden set ~100 câu + bảng
      chất lượng–chi phí–độ trễ.
- [ ] **P2** `projects/cmb-08-ticket-cascade/` — chứng minh tiết kiệm token mà độ chính xác không giảm.
- [ ] **P1** `projects/cmb-09-data-agent-os/` — chủ dự án review thiết kế v2 (kiến trúc POC, tái sử dụng skill Data plugin,
      ADR-001), trả lời mục P0 rồi làm POC theo [checklist riêng của dự án](projects/cmb-09-data-agent-os/CHECKLIST.md).
- [ ] **P2** Dự án của hướng chuyên sâu đã chọn — mốc cuối tháng 6.

## Giai đoạn 5 · Production (dự kiến)

- [ ] **P2** Mẫu dịch vụ: FastAPI + Docker + health check + version model + tracing.
- [ ] **P2** Mẫu giám sát: drift (Evidently) cho model bảng; dashboard chi phí cho hệ LLM.
- [ ] **P2** Quy trình đánh giá trước khi triển khai: offline → shadow → A/B, tiêu chí go/no-go.
- [ ] **P2** Checklist bảo mật & tuân thủ dữ liệu cá nhân (làm cùng pháp chế).

## Duy trì định kỳ

- [ ] Mỗi tuần: cập nhật [bảng tự đánh giá](docs/02-skill-map/generated/tu-danh-gia.md) cá nhân + 1 paper (`BIZ-06`).
- [ ] Mỗi quý: rà lại catalog (công cụ lỗi thời, kỹ năng mới), nâng phiên bản thư viện (`uv lock --upgrade`),
      kiểm tra lại số liệu giá/caching trong `docs/02-skill-map/03-tiet-kiem-token-chinh-xac.md`.
- [ ] Khi bản đồ bài toán có phiên bản mới (v2): cập nhật `catalog/problems.yaml` → `make catalog` → xử lý cảnh báo
      thiếu độ phủ.
