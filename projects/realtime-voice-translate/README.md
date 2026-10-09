# Realtime Voice Translate — dịch hội thoại trực tiếp Nhật ⇄ Anh ⇄ Việt

**Nhóm bài toán:** Nhóm 6 · đầu vào giọng nói · **Người thực hiện:** <tên> · **Trạng thái:** framing — thiết kế, chờ
review (chưa có code)

Web app cho điện thoại: hai người ngồi đối diện, màn hình chia đôi, nửa trên xoay 180°. Một người nói → hệ thống tự nhận
ra câu đó là tiếng **Nhật, Anh hay Việt** → ghi lại câu nói → dịch ngay sang **hai tiếng còn lại** và hiện ở nửa của người
nghe. Model chạy tại chỗ trên **một GPU tối đa 8 GB VRAM**. Docker gồm **phần AI** và **phần FE**, build và chạy ngay
trên máy GPU, dùng trong **mạng nội bộ** qua HTTPS (tạm chưa mở ra Internet).

## Tài liệu

| # | Tài liệu | Nội dung |
|---|---|---|
| 1 | [Kế hoạch triển khai chi tiết](docs/01-ke-hoach-trien-khai.md) | yêu cầu, SLO, kiến trúc, chọn model cho GPU 8 GB, pipeline realtime, UI điện thoại, cấu trúc thư mục theo best practice, Docker + HTTPS nội bộ, triển khai trên máy GPU, kiểm thử/eval, kế hoạch P0–P6, rủi ro, ADR, câu hỏi mở |

Nền tảng cấu trúc: [best practice dự án Python AI](../python-ai-project-structure-best-practices.md).

## Lựa chọn chính (P0 đo rồi mới chốt)

| Tầng | Mặc định | Ứng viên thay thế |
|---|---|---|
| Tách câu | Silero VAD (CPU) | — |
| Nhận dạng + phân biệt ngôn ngữ | Whisper `large-v3-turbo` qua faster-whisper, `int8_float16` (~1,5 GB) | Qwen3-ASR-0.6B · Whisper `large-v3` |
| Dịch | Hy-MT2-1.8B qua llama.cpp, `Q8_0` (~2–2,5 GB) | Hy-MT2-7B · TranslateGemma-4B · Qwen3-4B-Instruct |
| Giao thức | WebSocket + PCM16 16 kHz | WebRTC khi thêm đọc to bản dịch |
| Triển khai | Docker Compose ngay trên máy GPU: `ai` + `mt` (phần AI), `web` (phần FE, HTTPS nội bộ); `make deploy` | ngrok/tunnel khi cần truy cập từ xa |

## 1 · ĐÚNG — framing

| Câu hỏi | Trả lời |
|---|---|
| Quyết định nào sẽ thay đổi nhờ model? | Hai người không chung ngôn ngữ (Việt/Nhật/Anh) nói chuyện trực tiếp mà không cần phiên dịch viên |
| Ai dùng kết quả, dùng thế nào, bao lâu một lần? | Nhân viên và đối tác trong các buổi gặp trực tiếp (họp, tiếp khách, nhà máy); mở web trên điện thoại đặt giữa bàn; mỗi buổi 15–60 phút |
| KPI nghiệp vụ | Hội thoại trôi chảy: người nghe đọc được bản dịch khoảng 1–1,5 s sau khi người nói ngừng; ít phải nói lại vì dịch sai |
| Metric kỹ thuật tương ứng | Độ trễ "ngừng nói → đủ 2 bản dịch" (p50/p95); LID accuracy 3 tiếng; WER/CER; chrF++/COMET + người chấm; VRAM đỉnh |
| Loại sai nào đắt hơn? | Bản dịch sai mà đọc vẫn trôi chảy (sai nghĩa, sai số, sai tên) ≫ dịch chậm hoặc báo "chưa chắc". Nhận sai ngôn ngữ cho ra bản dịch vô nghĩa — dễ thấy, sửa bằng một chạm |
| Cách làm hiện tại (baseline nghiệp vụ) | Phiên dịch viên; hoặc app dịch cloud trên điện thoại (dữ liệu ra ngoài, phụ thuộc mạng) |
| Có cần AI không, hay luật if-else là đủ? | Cần AI cho nhận dạng giọng nói và dịch; phần chốt ngôn ngữ cuối cùng, hiển thị và giới hạn tài nguyên dùng luật xác định |
| Ràng buộc | 1 GPU ≤ 8 GB tại chỗ; model chạy localhost; chỉ dùng trong mạng nội bộ (HTTPS bằng CA nội bộ); server không lưu hội thoại |

## 2 · NHANH — baseline và bộ đánh giá

- Bộ đánh giá: `golden-v0` — FLEURS ja/en/vi (câu song song) + hội thoại tự thu trên điện thoại + đoạn nhiễu để đo ảo
  giác; đóng băng ở P0 (chi tiết ở mục 11.2 của kế hoạch).
- Baseline: Whisper `large-v3-turbo` + Hy-MT2-1.8B → kết quả: <điền sau P0>
- Lệnh tái tạo: `make eval`

## 3 · CHÍNH XÁC — các vòng cải tiến

| Vòng | Nhóm lỗi lớn nhất | Thay đổi | Metric trước → sau (± KTC) | Độ trễ/VRAM trước → sau |
|---|---|---|---|---|
| 1 | | | | |

## 4 · THUYẾT PHỤC — kết quả

- So với baseline: <điền sau P5>
- Demo: `make up` → điện thoại cùng Wi-Fi (đã cài CA nội bộ) mở `https://<IP máy GPU>:8443`
- Giới hạn và rủi ro: xem mục 14 của kế hoạch

## Kỹ năng sẽ luyện

`DL-06` ASR (streaming độ trễ thấp) · `LLM-07` tự host LLM · `LLM-04` đánh giá · `OPS-01` đóng gói và phục vụ model ·
`OPS-05` tối ưu suy luận · `OPS-07` real-time và streaming · `OPS-08` bảo mật dữ liệu · `PY-04` I/O đồng thời ·
`STAT-02` bất định của kết quả đánh giá · `EFF-07` kiểm chứng xác định — xem
[danh mục kỹ năng](../../docs/02-skill-map/generated/README.md).
