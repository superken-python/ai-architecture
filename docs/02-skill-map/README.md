# 02 · Bản đồ kỹ năng lập trình AI (giai đoạn 2)

Giai đoạn 1 trả lời *"thị trường có những bài toán AI nào?"* ([bản đồ bài toán](../01-problem-map/README.md)).
Giai đoạn 2 trả lời *"cần những kỹ năng lập trình nào, từ cơ bản đến nâng cao, để làm được tất cả bài toán đó —
kỹ năng nào dùng chung, kỹ năng nào riêng, ghép với nhau thế nào, và làm sao tiết kiệm token mà vẫn chính xác?"*

## Đọc theo thứ tự

| # | Tài liệu | Trả lời câu hỏi |
|---|---|---|
| 1 | [Kiến trúc kỹ năng](01-kien-truc-ky-nang.md) | Kỹ năng được tổ chức thế nào: 10 mảng × 5 tầng × 3 mức; thế nào là "đạt" |
| 2 | [Ma trận kỹ năng × nhóm](generated/ma-tran-ky-nang.md) *(sinh tự động)* | Kỹ năng nào dùng cho nhóm nào, chia sẻ bao nhiêu |
| 3 | [Kỹ năng kết hợp](02-ky-nang-ket-hop.md) | Ghép nhiều nhóm thành một hệ thế nào cho đúng |
| 4 | [Tiết kiệm token, chính xác tuyệt đối](03-tiet-kiem-token-chinh-xac.md) | Giảm chi phí LLM mà không đánh đổi độ chính xác |
| 5 | [Lộ trình học](04-lo-trinh-hoc.md) | Học gì trước, theo 6 tháng và theo hướng chuyên sâu |
| 6 | [Bảng tự đánh giá](generated/tu-danh-gia.md) *(sinh tự động)* | Mình đang ở mức nào |

Tra cứu: [thẻ kỹ năng theo mảng và lộ trình theo nhóm](generated/README.md) · [thứ tự học & đòn bẩy](generated/thu-tu-hoc.md) · [tổ hợp](generated/to-hop-ky-nang.md).

## Kết luận chính

**1. Học kỹ năng, không học "bài toán" — 89% kỹ năng dùng cho từ 2 nhóm trở lên.**
Danh mục (phiên bản hiện tại) có 65 kỹ năng: 13 *nền tảng chung* (cả 8 nhóm), 14 *cầu nối liên họ*, 31 *dùng chung trong họ*,
chỉ 5 *chuyên biệt* (đồ thị, hệ gợi ý, thị giác máy tính, giọng nói, định tuyến/lập lịch) và 2 *bổ trợ*.
Tầng được **tính tự động** từ mức sử dụng, không gán tay.

**2. Tám nhóm tách thành hai "họ".** Đếm số kỹ năng Cốt lõi/Cần chung giữa từng cặp nhóm
([ma trận chia sẻ](generated/ma-tran-ky-nang.md#chia-se)) cho thấy hai cụm rõ rệt:

- *Họ dữ liệu có cấu trúc & quyết định* — Nhóm 1, 2, 3, 4, 8.
- *Họ dữ liệu phi cấu trúc & GenAI* — Nhóm 5, 6, 7.
- Ngoài 13 kỹ năng nền tảng chung, hai nhóm **cùng họ** chia sẻ thêm trung bình 10–20 kỹ năng; hai nhóm
  **khác họ** chỉ chia sẻ thêm khoảng 5. Muốn chuyển họ, đi qua **14 kỹ năng cầu nối** như ML-07 (truy xuất
  & xếp hạng), STAT-05 (calibration & dự đoán có chọn lọc), DL-03 (embedding), OPS-04 (giám sát).

**3. Kỹ năng đòn bẩy cao nhất là phương pháp, không phải thuật toán.** Top đầu
[bảng đòn bẩy](generated/thu-tu-hoc.md) là Python, Git, *baseline + bộ đánh giá cố định* (BIZ-02),
*phân tích lỗi* (BIZ-03), *đo bất định của kết quả* (STAT-02), *framing* (BIZ-01) và *đóng gói model* (OPS-01).
Đây là hiện thực hóa quy trình ĐÚNG → NHANH → CHÍNH XÁC → THUYẾT PHỤC của giai đoạn 1.

**4. Những điều chỉnh so với ma trận giai đoạn 1** (chi tiết: [đối chiếu](generated/ma-tran-ky-nang.md#doi-chieu-giai-doan-1)):

- **RAG và hệ gợi ý dùng chung một kiến trúc** retrieve → rerank (ML-07). Giai đoạn 1 xếp *ML cổ điển* là
  "Ít" cho Nhóm 6, nhưng tầng truy xuất của RAG chính là truy hồi thông tin cổ điển (BM25, Recall@K, NDCG).
- **Thống kê là Cốt lõi cho LLM.** Golden set 100 câu đạt 90% có sai số khoảng ±6 điểm phần trăm — không đo
  bất định (STAT-02) thì không biết prompt mới tốt hơn thật hay chỉ do may.
- **Structured output là Cốt lõi cho Document AI** (Nhóm 5), không chỉ cho chatbot.
- **Calibration & dự đoán có chọn lọc (STAT-05) là cầu nối của độ chính xác:** cùng một kỹ thuật "tự động
  ca chắc chắn, chuyển người ca nghi ngờ" dùng cho chấm điểm tín dụng, cảnh báo gian lận, OCR và LLM.
- **Bổ sung hai mảng mới:** *Lập trình nền tảng* (PY) và *Tiết kiệm token & độ tin cậy* (EFF, 8 kỹ năng).

**5. "Chính xác tuyệt đối" là thuộc tính của hệ thống, không phải của model.** Không model nào đúng 100%.
Cách đạt được: mọi đầu ra tự động đi qua lớp kiểm chứng xác định (EFF-07), phần nghi ngờ chuyển sang đường
đắt hơn hoặc cho người (STAT-05), và **mọi tối ưu token chỉ được giữ khi eval không giảm** (LLM-04, STAT-02).
Xem [03-tiet-kiem-token-chinh-xac.md](03-tiet-kiem-token-chinh-xac.md).

## Nguồn dữ liệu & cách cập nhật

Mọi bảng trong `generated/` được sinh từ ba file YAML — **nguồn dữ liệu duy nhất**:

```
catalog/
├── problems.yaml       # 8 nhóm bài toán, 2 họ, ma trận giai đoạn 1
├── skills.yaml         # 10 mảng, 65 kỹ năng (mức, nhóm dùng, tiên quyết, công cụ, tiêu chí đạt)
└── combinations.yaml   # 9 tổ hợp dự án ghép nhiều nhóm
```

Sửa YAML → `make catalog` (sinh lại tài liệu) → `make check`. Bộ kiểm tra tự động chặn: id trùng, tiên quyết
không tồn tại hoặc vòng lặp, mức không hợp lệ, và **thiếu độ phủ** (một ô Cốt lõi của ma trận giai đoạn 1 không
có kỹ năng Cốt lõi nào). Hướng dẫn thêm kỹ năng/nhóm mới: [CONTRIBUTING.md](../../CONTRIBUTING.md).
