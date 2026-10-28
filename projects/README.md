# projects/ — dự án luyện tập theo nhóm bài toán (giai đoạn 4)

Mỗi nhóm bài toán có một dự án luyện tập (từ [bản đồ bài toán](../docs/01-problem-map/README.md)); mỗi tổ hợp có
thể có một dự án tích hợp. Dự án đi trọn quy trình ĐÚNG → NHANH → CHÍNH XÁC → THUYẾT PHỤC và là bằng chứng để tự
đánh giá mức **Trung cấp** của nhóm.

## Dự án luyện tập — mỗi nhóm bài toán một dự án

Mỗi dự án là một bài toán doanh nghiệp thu nhỏ: biết rõ **làm ra cái gì cho ai**, **thế nào là đạt** (đo bằng con số),
và **dùng dữ liệu nào**. Câu chuyện đầy đủ, bộ dữ liệu có gì, vì sao chọn và cách tải: [Dữ liệu luyện tập](../docs/00-setup/05-du-lieu-luyen-tap.md).

| Thư mục | Nhóm | Dự án làm gì | Mục tiêu đạt được | Dữ liệu · lĩnh vực |
|---|---|---|---|---|
| [`g1-churn-telco/`](g1-churn-telco/README.md) | 1 · Bảng | Danh sách 500 khách nên gọi giữ chân mỗi tháng cho CSKH nhà mạng, mỗi khách kèm 3 lý do và việc nên làm; API trong Docker, báo cáo 1 trang. **Hoàn thành** — real case của [Giai đoạn A](../docs/03-giai-doan-a-nen-tang/README.md) | **Đã đạt:** 140 thay vì 37 người sắp rời được gọi trúng mỗi tháng, lợi nhuận thêm 44,5 triệu đ/tháng (KTC 95%: 39,0…49,6) | Nhà mạng Sóng Xanh mô phỏng (20.000 khách, 8 bảng) + Telco Customer Churn · viễn thông — [chi tiết](../docs/00-setup/05-du-lieu-luyen-tap.md#g1) |
| `g2-forecast-m5/` *(dự kiến)* | 2 · Chuỗi thời gian | Dự báo số bán 28 ngày tới cho từng mặt hàng ở từng cửa hàng của chuỗi siêu thị, để đặt hàng không thiếu không thừa | Sai số (WAPE) thấp hơn ít nhất 10% so với cách "lấy lại số tuần trước", giữ qua ≥ 3 lần backtest | M5 – Walmart: 3.049 mặt hàng × 10 cửa hàng, hơn 5 năm bán hàng · bán lẻ — [chi tiết](../docs/00-setup/05-du-lieu-luyen-tap.md#g2) |
| `g3-fraud-creditcard/` *(dự kiến)* | 3 · Bất thường | Chấm điểm rủi ro từng giao dịch thẻ, cảnh báo vừa sức đội điều tra mỗi ngày | Cùng số cảnh báo mỗi ngày, bắt được nhiều gian lận hơn rõ rệt luật đơn giản; báo cáo số tiền chặn được | Credit Card Fraud Detection: 284.807 giao dịch, 492 gian lận · ngân hàng — [chi tiết](../docs/00-setup/05-du-lieu-luyen-tap.md#g3) |
| `g4-recsys-movielens/` *(dự kiến)* | 4 · Gợi ý | Gợi ý 10 phim riêng cho từng người dùng, so với gợi ý "10 phim phổ biến nhất" cho tất cả | Recall@10 và NDCG@10 cao hơn baseline phổ biến có ý nghĩa thống kê; có cách gợi ý cho người dùng mới | MovieLens: 100.836 lượt chấm điểm, 9.742 phim · giải trí — [chi tiết](../docs/00-setup/05-du-lieu-luyen-tap.md#g4) |
| `g5-invoice-extraction/` *(dự kiến)* | 5 · Ảnh và tài liệu | Lấy ngày, tổng tiền, mã số thuế từ ảnh hoá đơn; so OCR + luật với model đọc ảnh; ca không chắc chuyển người | Mỗi trường đúng ≥ 95% trên phần tự xử lý; bảng so sánh độ chính xác – chi phí – thời gian | Hoá đơn tự chụp + MC-OCR 2021 (2.436 hoá đơn tiếng Việt) · kế toán — [chi tiết](../docs/00-setup/05-du-lieu-luyen-tap.md#g5) |
| `g6-rag-handbook/` *(dự kiến)* | 6 · LLM và RAG | Trợ lý hỏi đáp trên quy định, luôn trích điều luật làm căn cứ, không bịa | Golden set ~100 câu: tìm đúng căn cứ ≥ 90%, trả lời đúng ≥ 85%, 100% có trích dẫn | Bộ luật Lao động 2019 (17 chương, 220 điều) · pháp luật, nhân sự — [chi tiết](../docs/00-setup/05-du-lieu-luyen-tap.md#g6) |
| `g7-quote-agent/` *(dự kiến)* | 7 · Agent | Agent đọc email hỏi giá → tra bảng giá → soạn báo giá → chờ người duyệt rồi mới gửi | Đúng mặt hàng và số lượng ≥ 90% email; 100% giá lấy từ bảng giá; không gửi khi chưa duyệt | Tự tạo: 30–50 email + bảng giá CSV + đáp án · bán hàng B2B — [chi tiết](../docs/00-setup/05-du-lieu-luyen-tap.md#g7) |
| `g8-vrp-delivery/` *(dự kiến)* | 8 · Tối ưu và nhân quả | Xếp tuyến giao hàng 1 kho × 20 điểm bằng OR-Tools; đo tác động thật của email khuyến mãi để chọn khách nên gửi | Quãng đường ngắn hơn ≥ 15%, 100% đúng tải trọng và khung giờ; chọn khách để gửi mà lãi hơn gửi tất cả | Toạ độ tự sinh + Hillstrom (64.000 khách) · logistics, marketing — [chi tiết](../docs/00-setup/05-du-lieu-luyen-tap.md#g8) |
| [`g9-video-chu-cai/`](g9-video-chu-cai/README.md) | 9 · Tạo nội dung | Video 3 phút dạy 29 chữ cái tiếng Việt trên nền nhạc: bảng học ở giữa, hai nhân vật cử động (tách nền từ video Gemini) đứng hai góc; dựng bằng code (kịch bản YAML → giọng đọc → nhạc → hình → ffmpeg), máy nghe lại lời đọc bằng ASR. **Đã dựng**, có [hướng dẫn tự làm bằng Claude Code](g9-video-chu-cai/docs/huong-dan-claude-code.md) | **Đã đạt:** 28/29 câu chữ cái được máy nghe đúng cả âm lẫn từ ví dụ, kể cả khi có nhạc; dựng lại ~3 phút, không tốn phí API. Còn: thu âm chữ P, giáo viên duyệt | Kịch bản + video nhân vật tự tạo (Gemini), Noto Emoji, giọng Piper vi_VN (VAIS-1000, CC BY 4.0) · giáo dục — [chi tiết](../docs/00-setup/05-du-lieu-luyen-tap.md#g9) |

Chi tiết từng nhóm (metric, bẫy, kỹ năng cần): xem trang nhóm trong [bản đồ kỹ năng](../docs/02-skill-map/generated/README.md).

## Dự án tổ hợp và dự án khác

| Thư mục | Nhóm / tổ hợp | Dự án | Dữ liệu |
|---|---|---|---|
| `cmb-08-ticket-cascade/` *(dự kiến)* | Tổ hợp CMB-08 | Phân loại ticket hỗ trợ theo bậc: model nhỏ xử lý ca dễ → LLM xử lý ca khó → người xử lý ca không chắc. **Mục tiêu:** độ chính xác ngang việc gửi mọi ticket cho LLM nhưng chi phí thấp hơn nhiều, trình bày bằng bảng chất lượng – chi phí | Tự tạo hoặc bộ ticket công khai |
| [`cmb-09-data-agent-os/`](cmb-09-data-agent-os/README.md) | Tổ hợp CMB-09 | Data agent nhiều domain pack trên AgentOS, dùng lại skill của Data plugin, dữ liệu qua MCP DBHub — **thiết kế POC** | Giả lập (timesheet, finance) |
| [`cmb-10-excel-agent-addin/`](cmb-10-excel-agent-addin/README.md) | Tổ hợp CMB-10 | Khung chat AI trong Excel (Office add-in) nối với agent của hệ thống: tìm theo cột, chèn dòng có xem trước và hoàn tác, 41 tính năng mở rộng — **nghiên cứu khả thi + POC 0.2** (AgentOS + AG-UI + agent Agno, gpt-5-mini; web POC + Office add-in) | Workbook mẫu tự tạo / ẩn danh |
| [`realtime-voice-translate/`](realtime-voice-translate/README.md) | 6 · Giọng nói | Dịch hội thoại trực tiếp Nhật ⇄ Anh ⇄ Việt trên web điện thoại, model chạy tại chỗ trên GPU 8 GB — **kế hoạch triển khai** | Tự thu (golden set) + FLEURS |
| [`gpt-excel-agent-chatbot/`](gpt-excel-agent-chatbot/README.md) | **7 · Agent** chính; 6 · LLM hỗ trợ | Chatbot trong Excel Office nối agent nội bộ, tìm theo cột và thêm bản ghi — **nghiên cứu khả thi, chưa code** | Workbook giả lập dự kiến; chưa tạo dữ liệu |
| [`gemini-excel-ai-agent/`](gemini-excel-ai-agent/README.md) | Tổ hợp CMB-10 / 7 · Agent | Plugin AI Chatbot nhúng Excel Office, kết nối AI Agent nội bộ thao tác bảng tính hai chiều — **nghiên cứu khả thi & thiết kế kiến trúc** | Tự sinh & Dữ liệu doanh nghiệp mẫu |
| [`security_scan/`](security_scan/README.md) | Ngoài các nhóm AI | Knowledge base IPA + NVD (export tổng hợp, template CSV) để Semgrep, ZAP, Trivy tra cứu qua CWE/CVE; quy trình cập nhật liên tục; runbook tiếng Anh để tự dựng lại — **nghiên cứu + thiết kế dữ liệu** | CWE 4.14, NVD (mirror fkie-cad), JVN iPedia (fixture), output mẫu của các công cụ |

## Cấu trúc một dự án

```
projects/<thư-mục>/
├── README.md            # framing 1 trang + kết quả — theo mẫu templates/project/README.md
├── src/<tên_gói>/       # code dùng lại, có test
├── notebooks/           # khám phá, phân tích lỗi
├── eval/                # golden set (nếu công khai) + script đánh giá — `make eval` của dự án
├── tests/
└── Makefile             # setup / eval / serve của riêng dự án (gọi uv run ...)
```

Quy tắc:

- **Viết framing trước khi viết code** (phần đầu README theo mẫu): quyết định thay đổi, KPI, loại sai đắt hơn,
  baseline hiện tại.
- **Đóng băng bộ đánh giá trước model đầu tiên.** Mọi thí nghiệm báo cáo trên cùng bộ đánh giá, kèm khoảng tin cậy.
- Code dùng chung giữa nhiều dự án (đọc dữ liệu, harness đánh giá, client LLM có đo chi phí...) đưa lên
  `src/aiarch/` để các dự án khác dùng lại — đây là cách "kỹ năng dùng chung" trở thành "code dùng chung".

## Bắt đầu một dự án

```bash
mkdir -p projects/g1-churn-telco/{src,notebooks,eval,tests}
cp templates/project/README.md projects/g1-churn-telco/README.md
```
