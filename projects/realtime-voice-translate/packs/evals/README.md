# Golden Evaluation Dataset

Bộ mẫu đánh giá chất lượng phiên dịch trực tiếp **Nhật ⇄ Anh ⇄ Việt** trên GPU 8 GB.

## Cấu trúc
- `manifest.jsonl`: Danh sách các câu mẫu vàng, metadata ngôn ngữ và bản dịch chuẩn cho 6 chiều dịch:
  - vi ⇄ ja
  - vi ⇄ en
  - ja ⇄ en
- Các file âm thanh WAV (16 kHz, PCM16 mono) được lưu trữ ngoài git hoặc tải tự động qua script.

## Chỉ tiêu đo lường
- **LID Accuracy:** Tỷ lệ nhận đúng tiếng trong {ja, en, vi}. Mục tiêu: ≥ 98% (câu ≥ 1,5s), ≥ 90% (câu 0,5–1,5s).
- **ASR:** WER (en, vi) và CER (ja).
- **MT:** chrF++ và đánh giá ngữ nghĩa.
- **Latency (p50 / p95):** Đo từ thời điểm kết thúc câu nói đến khi nhận đủ 2 bản dịch.
