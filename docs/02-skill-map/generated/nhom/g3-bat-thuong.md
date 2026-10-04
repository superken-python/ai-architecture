<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# Nhóm 3 · Phát hiện bất thường

> “Giao dịch hay máy móc này có gì lạ?” — Khối A · Dự đoán

**Ví dụ trong doanh nghiệp:** gian lận thẻ và ví điện tử, bảo trì dự đoán, giám sát hệ thống IT.

| Đầu vào | Kỹ thuật chính | Đầu ra | Quyết định kinh doanh |
|---|---|---|---|
| Luồng giao dịch, log hệ thống, dữ liệu cảm biến | Luật nghiệp vụ + Isolation Forest, autoencoder | Điểm bất thường, danh sách cảnh báo xếp hạng | Chặn giao dịch, cử người kiểm tra, bảo trì sớm |

## Mức năng lực của nhóm (từ bản đồ bài toán)

| Mức | Nội dung |
|---|---|
| Cơ bản | z-score, IQR, luật nghiệp vụ, Isolation Forest. |
| Trung cấp | Kết hợp luật với ML. Đánh giá bằng precision@k, với k là số cảnh báo đội vận hành xử lý được mỗi ngày. |
| Nâng cao | Autoencoder, phát hiện gian lận trên đồ thị (mạng lưới tài khoản liên kết), xử lý real-time, học từ phản hồi của người điều tra. |

- **Metric chính:** precision@k, recall, PR-AUC, tỷ lệ cảnh báo giả.
- **Công cụ:** scikit-learn, PyOD, NetworkX, Kafka (luồng real-time)
- **Bẫy thường gặp:** Quá nhiều cảnh báo giả khiến đội vận hành bỏ qua cảnh báo; dùng accuracy khi bất thường chiếm dưới 1% dữ liệu.
- **Dự án luyện tập:** Phát hiện gian lận trên bộ Credit Card Fraud Detection, chọn ngưỡng theo số cảnh báo xử lý được mỗi ngày.

## Kỹ năng cần cho nhóm này

### ● Cốt lõi (18)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI | Nền tảng chung | 1, 2, 4, 5, 6, 7, 8 |
| [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án | Nền tảng chung | 1, 2, 4, 5, 6, 7, 8 |
| [DATA-01](../mang/data.md#data-01) SQL phân tích | Cầu nối liên họ | 1, 2, 4, 6, 7, 8 |
| [DATA-02](../mang/data.md#data-02) Xử lý dữ liệu bảng | Dùng chung trong họ | 1, 2, 4, 8 |
| [DATA-03](../mang/data.md#data-03) Đúng thời điểm và chống rò rỉ dữ liệu | Dùng chung trong họ | 1, 2, 4, 8 |
| [DATA-04](../mang/data.md#data-04) Feature engineering cho bảng và chuỗi thời gian | Dùng chung trong họ | 1, 2, 4, 8 |
| [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả | Nền tảng chung | 1, 2, 4, 5, 6, 7, 8 |
| [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá | Nền tảng chung | 1, 2, 4, 5, 6, 7, 8 |
| [STAT-05](../mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc | Cầu nối liên họ | 1, 5, 6, 7, 8 |
| [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn | Cầu nối liên họ | 1, 2, 4, 6, 8 |
| [ML-03](../mang/ml.md#ml-03) Dữ liệu mất cân bằng và sự kiện hiếm | Cầu nối liên họ | 1, 5 |
| [ML-05](../mang/ml.md#ml-05) Học không giám sát và phát hiện bất thường | Dùng chung trong họ | 4 |
| [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model | Nền tảng chung | 1, 2, 4, 5, 6, 7, 8 |
| [OPS-04](../mang/ops.md#ops-04) Giám sát model và drift | Cầu nối liên họ | 1, 2, 4, 5, 6, 8 |
| [BIZ-01](../mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) | Nền tảng chung | 1, 2, 4, 5, 6, 7, 8 |
| [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) | Nền tảng chung | 1, 2, 4, 5, 6, 7, 8 |
| [BIZ-03](../mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) | Nền tảng chung | 1, 2, 4, 5, 6, 7, 8 |
| [BIZ-05](../mang/biz.md#biz-05) Kiến thức miền nghiệp vụ | Nền tảng chung | 1, 2, 4, 5, 6, 7, 8 |

### ◐ Cần (15)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-03](../mang/py.md#py-03) Kiểm thử và chất lượng code | Nền tảng chung | 1, 2, 4, 5, 6, 7, 8 |
| [PY-04](../mang/py.md#py-04) Gọi API và I/O đồng thời bền vững | Cầu nối liên họ | 5, 6, 7 |
| [DATA-05](../mang/data.md#data-05) Kiểm định chất lượng dữ liệu và nhãn | Nền tảng chung | 1, 2, 4, 5, 6, 7, 8 |
| [DATA-07](../mang/data.md#data-07) Dữ liệu đồ thị | Chuyên biệt | — |
| [ML-02](../mang/ml.md#ml-02) Gradient boosting | Dùng chung trong họ | 1, 2, 4, 8 |
| [ML-04](../mang/ml.md#ml-04) Giải thích mô hình | Cầu nối liên họ | 1, 5, 8 |
| [ML-06](../mang/ml.md#ml-06) Mô hình chuỗi thời gian | Dùng chung trong họ | 2, 8 |
| [DL-01](../mang/dl.md#dl-01) PyTorch nền tảng | Cầu nối liên họ | 2, 4, 5, 6 |
| [DL-03](../mang/dl.md#dl-03) Embedding và học biểu diễn | Cầu nối liên họ | 4, 5, 6 |
| [OPS-02](../mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập | Nền tảng chung | 1, 2, 4, 5, 6, 7, 8 |
| [OPS-03](../mang/ops.md#ops-03) Pipeline và điều phối tác vụ | Cầu nối liên họ | 1, 2, 4, 6 |
| [OPS-05](../mang/ops.md#ops-05) Tối ưu suy luận và serving model | Cầu nối liên họ | 4, 5, 6 |
| [OPS-07](../mang/ops.md#ops-07) Real-time và streaming | Dùng chung trong họ | 4 |
| [OPS-08](../mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ | Cầu nối liên họ | 1, 5, 6, 7 |
| [BIZ-04](../mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) | Nền tảng chung | 1, 2, 4, 5, 6, 7, 8 |

### ○ Ít (7)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [STAT-03](../mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test | Cầu nối liên họ | 1, 4, 6, 8 |
| [STAT-04](../mang/stat.md#stat-04) Dự báo xác suất và định lượng bất định | Dùng chung trong họ | 2, 8 |
| [DL-02](../mang/dl.md#dl-02) Transfer learning và fine-tune mô hình pretrained | Dùng chung trong họ | 5, 6 |
| [LLM-01](../mang/llm.md#llm-01) Gọi LLM API và prompt engineering | Dùng chung trong họ | 5, 6, 7 |
| [BIZ-06](../mang/biz.md#biz-06) Đọc và tái hiện paper | Bổ trợ | — |
| [EFF-06](../mang/eff.md#eff-06) Xử lý theo lô và bất đồng bộ | Dùng chung trong họ | 5, 6 |
| [EFF-08](../mang/eff.md#eff-08) Tiết kiệm token khi dùng AI hỗ trợ lập trình | Bổ trợ | — |

## Lộ trình học cho nhóm này

Thứ tự đã tôn trọng tiên quyết. Kỹ năng đánh dấu *(tiên quyết)* không trực tiếp thuộc nhóm nhưng cần để học các kỹ năng phía sau. Gợi ý: đạt **Cơ bản** cho cả danh sách trước, rồi mới lên **Trung cấp** ở các kỹ năng Cốt lõi.

1. [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI — ● Cốt lõi
2. [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án — ● Cốt lõi
3. [PY-03](../mang/py.md#py-03) Kiểm thử và chất lượng code — ◐ Cần
4. [PY-04](../mang/py.md#py-04) Gọi API và I/O đồng thời bền vững — ◐ Cần
5. [DATA-01](../mang/data.md#data-01) SQL phân tích — ● Cốt lõi
6. [DATA-02](../mang/data.md#data-02) Xử lý dữ liệu bảng — ● Cốt lõi
7. [DATA-03](../mang/data.md#data-03) Đúng thời điểm và chống rò rỉ dữ liệu — ● Cốt lõi
8. [DATA-04](../mang/data.md#data-04) Feature engineering cho bảng và chuỗi thời gian — ● Cốt lõi
9. [DATA-05](../mang/data.md#data-05) Kiểm định chất lượng dữ liệu và nhãn — ◐ Cần
10. [DATA-07](../mang/data.md#data-07) Dữ liệu đồ thị — ◐ Cần
11. [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả — ● Cốt lõi
12. [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá — ● Cốt lõi
13. [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn — ● Cốt lõi
14. [STAT-05](../mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc — ● Cốt lõi
15. [ML-02](../mang/ml.md#ml-02) Gradient boosting — ◐ Cần
16. [ML-03](../mang/ml.md#ml-03) Dữ liệu mất cân bằng và sự kiện hiếm — ● Cốt lõi
17. [ML-04](../mang/ml.md#ml-04) Giải thích mô hình — ◐ Cần
18. [ML-05](../mang/ml.md#ml-05) Học không giám sát và phát hiện bất thường — ● Cốt lõi
19. [ML-06](../mang/ml.md#ml-06) Mô hình chuỗi thời gian — ◐ Cần
20. [DL-01](../mang/dl.md#dl-01) PyTorch nền tảng — ◐ Cần
21. [DL-03](../mang/dl.md#dl-03) Embedding và học biểu diễn — ◐ Cần
22. [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model — ● Cốt lõi
23. [OPS-02](../mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập — ◐ Cần
24. [OPS-03](../mang/ops.md#ops-03) Pipeline và điều phối tác vụ — ◐ Cần
25. [OPS-04](../mang/ops.md#ops-04) Giám sát model và drift — ● Cốt lõi
26. [OPS-05](../mang/ops.md#ops-05) Tối ưu suy luận và serving model — ◐ Cần
27. [OPS-07](../mang/ops.md#ops-07) Real-time và streaming — ◐ Cần
28. [OPS-08](../mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ — ◐ Cần
29. [BIZ-01](../mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) — ● Cốt lõi
30. [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) — ● Cốt lõi
31. [BIZ-03](../mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) — ● Cốt lõi
32. [BIZ-04](../mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) — ◐ Cần
33. [BIZ-05](../mang/biz.md#biz-05) Kiến thức miền nghiệp vụ — ● Cốt lõi

## Tổ hợp có nhóm này

- [CMB-04 · Phát hiện rồi giải thích (cảnh báo gian lận cho điều tra viên)](../to-hop-ky-nang.md#cmb-04) — Chấm điểm bất thường (Nhóm 3) → LLM tóm tắt bằng chứng cho từng cảnh báo (Nhóm 6) → hàng đợi xử lý + ghi nhận phản hồi (Nhóm 7)
