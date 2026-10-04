<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# Nhóm 4 · Gợi ý và xếp hạng

> “Nên hiển thị gì cho người này?” — Khối A · Dự đoán

**Ví dụ trong doanh nghiệp:** gợi ý sản phẩm, bán chéo bảo hiểm, xếp hạng kết quả tìm kiếm.

| Đầu vào | Kỹ thuật chính | Đầu ra | Quyết định kinh doanh |
|---|---|---|---|
| Lịch sử xem và mua, thông tin sản phẩm và người dùng | Retrieval (CF, two-tower) rồi ranking (learning-to-rank) | Danh sách top-K riêng cho từng người | Hiển thị trên app/web, kiểm chứng bằng A/B test |

## Mức năng lực của nhóm (từ bản đồ bài toán)

| Mức | Nội dung |
|---|---|
| Cơ bản | Baseline "phổ biến nhất" hoặc "hay mua cùng", collaborative filtering, metric Recall@K và NDCG. |
| Trung cấp | Kiến trúc 2 tầng retrieval + ranking, learning-to-rank, xử lý cold-start cho người dùng và sản phẩm mới. |
| Nâng cao | Mô hình theo chuỗi hành vi (sequential), A/B test đo doanh thu thật, cân bằng nhiều mục tiêu như doanh thu và độ đa dạng. |

- **Metric chính:** Recall@K, NDCG, MAP (offline); CTR, tỷ lệ chuyển đổi, doanh thu mỗi phiên (online).
- **Công cụ:** implicit (ALS), LightFM, LightGBM (LambdaRank), Faiss
- **Bẫy thường gặp:** Offline tốt nhưng online không tăng; vòng lặp chỉ gợi ý thứ đã phổ biến; quên người dùng và sản phẩm mới.
- **Dự án luyện tập:** Gợi ý phim trên MovieLens, so baseline phổ biến với ALS theo Recall@10 và NDCG@10.

## Kỹ năng cần cho nhóm này

### ● Cốt lõi (15)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI | Nền tảng chung | 1, 2, 3, 5, 6, 7, 8 |
| [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án | Nền tảng chung | 1, 2, 3, 5, 6, 7, 8 |
| [DATA-01](../mang/data.md#data-01) SQL phân tích | Cầu nối liên họ | 1, 2, 3, 6, 7, 8 |
| [DATA-02](../mang/data.md#data-02) Xử lý dữ liệu bảng | Dùng chung trong họ | 1, 2, 3, 8 |
| [DATA-03](../mang/data.md#data-03) Đúng thời điểm và chống rò rỉ dữ liệu | Dùng chung trong họ | 1, 2, 3, 8 |
| [DATA-04](../mang/data.md#data-04) Feature engineering cho bảng và chuỗi thời gian | Dùng chung trong họ | 1, 2, 3, 8 |
| [STAT-03](../mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test | Cầu nối liên họ | 1, 6, 8 |
| [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn | Cầu nối liên họ | 1, 2, 3, 6, 8 |
| [ML-02](../mang/ml.md#ml-02) Gradient boosting | Dùng chung trong họ | 1, 2, 3, 8 |
| [ML-07](../mang/ml.md#ml-07) Truy xuất và xếp hạng hai tầng (retrieve → rerank) | Cầu nối liên họ | 5, 6, 7 |
| [ML-08](../mang/ml.md#ml-08) Hệ gợi ý chuyên biệt | Chuyên biệt | — |
| [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model | Nền tảng chung | 1, 2, 3, 5, 6, 7, 8 |
| [OPS-04](../mang/ops.md#ops-04) Giám sát model và drift | Cầu nối liên họ | 1, 2, 3, 5, 6, 8 |
| [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) | Nền tảng chung | 1, 2, 3, 5, 6, 7, 8 |
| [BIZ-03](../mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) | Nền tảng chung | 1, 2, 3, 5, 6, 7, 8 |

### ◐ Cần (16)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-03](../mang/py.md#py-03) Kiểm thử và chất lượng code | Nền tảng chung | 1, 2, 3, 5, 6, 7, 8 |
| [DATA-05](../mang/data.md#data-05) Kiểm định chất lượng dữ liệu và nhãn | Nền tảng chung | 1, 2, 3, 5, 6, 7, 8 |
| [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả | Nền tảng chung | 1, 2, 3, 5, 6, 7, 8 |
| [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá | Nền tảng chung | 1, 2, 3, 5, 6, 7, 8 |
| [STAT-06](../mang/stat.md#stat-06) Suy luận nhân quả và uplift | Dùng chung trong họ | 8 |
| [ML-05](../mang/ml.md#ml-05) Học không giám sát và phát hiện bất thường | Dùng chung trong họ | 3 |
| [DL-01](../mang/dl.md#dl-01) PyTorch nền tảng | Cầu nối liên họ | 2, 3, 5, 6 |
| [DL-03](../mang/dl.md#dl-03) Embedding và học biểu diễn | Cầu nối liên họ | 3, 5, 6 |
| [OPT-04](../mang/opt.md#opt-04) Bandit và học tăng cường cơ bản | Dùng chung trong họ | 8 |
| [OPS-02](../mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập | Nền tảng chung | 1, 2, 3, 5, 6, 7, 8 |
| [OPS-03](../mang/ops.md#ops-03) Pipeline và điều phối tác vụ | Cầu nối liên họ | 1, 2, 3, 6 |
| [OPS-05](../mang/ops.md#ops-05) Tối ưu suy luận và serving model | Cầu nối liên họ | 3, 5, 6 |
| [OPS-07](../mang/ops.md#ops-07) Real-time và streaming | Dùng chung trong họ | 3 |
| [BIZ-01](../mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) | Nền tảng chung | 1, 2, 3, 5, 6, 7, 8 |
| [BIZ-04](../mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) | Nền tảng chung | 1, 2, 3, 5, 6, 7, 8 |
| [BIZ-05](../mang/biz.md#biz-05) Kiến thức miền nghiệp vụ | Nền tảng chung | 1, 2, 3, 5, 6, 7, 8 |

### ○ Ít (11)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-04](../mang/py.md#py-04) Gọi API và I/O đồng thời bền vững | Cầu nối liên họ | 3, 5, 6, 7 |
| [DATA-07](../mang/data.md#data-07) Dữ liệu đồ thị | Chuyên biệt | 3 |
| [STAT-05](../mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc | Cầu nối liên họ | 1, 3, 5, 6, 7, 8 |
| [ML-03](../mang/ml.md#ml-03) Dữ liệu mất cân bằng và sự kiện hiếm | Cầu nối liên họ | 1, 3, 5 |
| [ML-04](../mang/ml.md#ml-04) Giải thích mô hình | Cầu nối liên họ | 1, 3, 5, 8 |
| [DL-02](../mang/dl.md#dl-02) Transfer learning và fine-tune mô hình pretrained | Dùng chung trong họ | 5, 6 |
| [LLM-01](../mang/llm.md#llm-01) Gọi LLM API và prompt engineering | Dùng chung trong họ | 5, 6, 7 |
| [OPS-08](../mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ | Cầu nối liên họ | 1, 3, 5, 6, 7 |
| [BIZ-06](../mang/biz.md#biz-06) Đọc và tái hiện paper | Bổ trợ | — |
| [EFF-06](../mang/eff.md#eff-06) Xử lý theo lô và bất đồng bộ | Dùng chung trong họ | 5, 6 |
| [EFF-08](../mang/eff.md#eff-08) Tiết kiệm token khi dùng AI hỗ trợ lập trình | Bổ trợ | — |

## Lộ trình học cho nhóm này

Thứ tự đã tôn trọng tiên quyết. Kỹ năng đánh dấu *(tiên quyết)* không trực tiếp thuộc nhóm nhưng cần để học các kỹ năng phía sau. Gợi ý: đạt **Cơ bản** cho cả danh sách trước, rồi mới lên **Trung cấp** ở các kỹ năng Cốt lõi.

1. [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI — ● Cốt lõi
2. [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án — ● Cốt lõi
3. [PY-03](../mang/py.md#py-03) Kiểm thử và chất lượng code — ◐ Cần
4. [DATA-01](../mang/data.md#data-01) SQL phân tích — ● Cốt lõi
5. [DATA-02](../mang/data.md#data-02) Xử lý dữ liệu bảng — ● Cốt lõi
6. [DATA-03](../mang/data.md#data-03) Đúng thời điểm và chống rò rỉ dữ liệu — ● Cốt lõi
7. [DATA-04](../mang/data.md#data-04) Feature engineering cho bảng và chuỗi thời gian — ● Cốt lõi
8. [DATA-05](../mang/data.md#data-05) Kiểm định chất lượng dữ liệu và nhãn — ◐ Cần
9. [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả — ◐ Cần
10. [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá — ◐ Cần
11. [STAT-03](../mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test — ● Cốt lõi
12. [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn — ● Cốt lõi
13. [ML-02](../mang/ml.md#ml-02) Gradient boosting — ● Cốt lõi
14. [STAT-06](../mang/stat.md#stat-06) Suy luận nhân quả và uplift — ◐ Cần
15. [ML-05](../mang/ml.md#ml-05) Học không giám sát và phát hiện bất thường — ◐ Cần
16. [DL-01](../mang/dl.md#dl-01) PyTorch nền tảng — ◐ Cần
17. [DL-03](../mang/dl.md#dl-03) Embedding và học biểu diễn — ◐ Cần
18. [ML-07](../mang/ml.md#ml-07) Truy xuất và xếp hạng hai tầng (retrieve → rerank) — ● Cốt lõi
19. [ML-08](../mang/ml.md#ml-08) Hệ gợi ý chuyên biệt — ● Cốt lõi
20. [OPT-04](../mang/opt.md#opt-04) Bandit và học tăng cường cơ bản — ◐ Cần
21. [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model — ● Cốt lõi
22. [OPS-02](../mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập — ◐ Cần
23. [OPS-03](../mang/ops.md#ops-03) Pipeline và điều phối tác vụ — ◐ Cần
24. [OPS-04](../mang/ops.md#ops-04) Giám sát model và drift — ● Cốt lõi
25. [OPS-05](../mang/ops.md#ops-05) Tối ưu suy luận và serving model — ◐ Cần
26. [OPS-07](../mang/ops.md#ops-07) Real-time và streaming — ◐ Cần
27. [BIZ-01](../mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) — ◐ Cần
28. [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) — ● Cốt lõi
29. [BIZ-03](../mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) — ● Cốt lõi
30. [BIZ-04](../mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) — ◐ Cần
31. [BIZ-05](../mang/biz.md#biz-05) Kiến thức miền nghiệp vụ — ◐ Cần

## Tổ hợp có nhóm này

- [CMB-05 · Gợi ý và kiểm chứng bằng thí nghiệm](../to-hop-ky-nang.md#cmb-05) — Sinh danh sách gợi ý (Nhóm 4) → đo tác động thật bằng A/B test hoặc bandit (Nhóm 8)
