<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# Nhóm 2 · Dự báo chuỗi thời gian

> “Tháng sau bán (hoặc cần) bao nhiêu?” — Khối A · Dự đoán

**Ví dụ trong doanh nghiệp:** nhu cầu và tồn kho, doanh thu, dòng tiền, lưu lượng cuộc gọi tổng đài.

| Đầu vào | Kỹ thuật chính | Đầu ra | Quyết định kinh doanh |
|---|---|---|---|
| Doanh số theo ngày/tuần, lịch khuyến mãi, Tết và ngày lễ | ETS/ARIMA, LightGBM toàn cục cho nhiều mã hàng | Dự báo điểm và khoảng dự báo (quantile) | Đặt hàng, phân bổ tồn kho, xếp nhân sự |

## Mức năng lực của nhóm (từ bản đồ bài toán)

| Mức | Nội dung |
|---|---|
| Cơ bản | Baseline seasonal naive, ETS/ARIMA, metric WAPE và MASE. Backtest cuốn chiếu theo thời gian, không xáo trộn dữ liệu. |
| Trung cấp | Một mô hình LightGBM chung cho hàng nghìn mã hàng, dùng đặc trưng lag, rolling, khuyến mãi, Tết và ngày lễ. |
| Nâng cao | Dự báo xác suất (quantile) để ra quyết định tồn kho, dự báo phân cấp (hierarchical reconciliation), mô hình nền tảng như Chronos, TimesFM. Luôn so với baseline. |

- **Metric chính:** WAPE, MASE; pinball loss cho dự báo quantile.
- **Công cụ:** statsforecast, mlforecast, Darts, LightGBM
- **Bẫy thường gặp:** Xáo trộn dữ liệu khi chia train/test; bỏ qua Tết và khuyến mãi; chỉ đưa ra một con số khi quyết định cần khoảng dự báo.
- **Dự án luyện tập:** Dự báo doanh số cửa hàng × mặt hàng trên bộ M5 (Walmart), so LightGBM với seasonal naive bằng backtest cuốn chiếu.

## Kỹ năng cần cho nhóm này

### ● Cốt lõi (16)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI | Nền tảng chung | 1, 3, 4, 5, 6, 7, 8 |
| [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án | Nền tảng chung | 1, 3, 4, 5, 6, 7, 8 |
| [DATA-01](../mang/data.md#data-01) SQL phân tích | Cầu nối liên họ | 1, 3, 4, 6, 7, 8 |
| [DATA-02](../mang/data.md#data-02) Xử lý dữ liệu bảng | Dùng chung trong họ | 1, 3, 4, 8 |
| [DATA-03](../mang/data.md#data-03) Đúng thời điểm và chống rò rỉ dữ liệu | Dùng chung trong họ | 1, 3, 4, 8 |
| [DATA-04](../mang/data.md#data-04) Feature engineering cho bảng và chuỗi thời gian | Dùng chung trong họ | 1, 3, 4, 8 |
| [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả | Nền tảng chung | 1, 3, 4, 5, 6, 7, 8 |
| [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá | Nền tảng chung | 1, 3, 4, 5, 6, 7, 8 |
| [STAT-04](../mang/stat.md#stat-04) Dự báo xác suất và định lượng bất định | Dùng chung trong họ | 8 |
| [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn | Cầu nối liên họ | 1, 3, 4, 6, 8 |
| [ML-02](../mang/ml.md#ml-02) Gradient boosting | Dùng chung trong họ | 1, 3, 4, 8 |
| [ML-06](../mang/ml.md#ml-06) Mô hình chuỗi thời gian | Dùng chung trong họ | 3, 8 |
| [BIZ-01](../mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) | Nền tảng chung | 1, 3, 4, 5, 6, 7, 8 |
| [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) | Nền tảng chung | 1, 3, 4, 5, 6, 7, 8 |
| [BIZ-03](../mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) | Nền tảng chung | 1, 3, 4, 5, 6, 7, 8 |
| [BIZ-05](../mang/biz.md#biz-05) Kiến thức miền nghiệp vụ | Nền tảng chung | 1, 3, 4, 5, 6, 7, 8 |

### ◐ Cần (10)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-03](../mang/py.md#py-03) Kiểm thử và chất lượng code | Nền tảng chung | 1, 3, 4, 5, 6, 7, 8 |
| [DATA-05](../mang/data.md#data-05) Kiểm định chất lượng dữ liệu và nhãn | Nền tảng chung | 1, 3, 4, 5, 6, 7, 8 |
| [DL-01](../mang/dl.md#dl-01) PyTorch nền tảng | Cầu nối liên họ | 3, 4, 5, 6 |
| [OPT-01](../mang/opt.md#opt-01) Quy hoạch tuyến tính và nguyên (LP/MIP) | Dùng chung trong họ | 8 |
| [OPT-03](../mang/opt.md#opt-03) Ra quyết định dưới bất định (dự báo rồi tối ưu) | Dùng chung trong họ | 8 |
| [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model | Nền tảng chung | 1, 3, 4, 5, 6, 7, 8 |
| [OPS-02](../mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập | Nền tảng chung | 1, 3, 4, 5, 6, 7, 8 |
| [OPS-03](../mang/ops.md#ops-03) Pipeline và điều phối tác vụ | Cầu nối liên họ | 1, 3, 4, 6 |
| [OPS-04](../mang/ops.md#ops-04) Giám sát model và drift | Cầu nối liên họ | 1, 3, 4, 5, 6, 8 |
| [BIZ-04](../mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) | Nền tảng chung | 1, 3, 4, 5, 6, 7, 8 |

### ○ Ít (8)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-04](../mang/py.md#py-04) Gọi API và I/O đồng thời bền vững | Cầu nối liên họ | 3, 5, 6, 7 |
| [STAT-03](../mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test | Cầu nối liên họ | 1, 4, 6, 8 |
| [ML-05](../mang/ml.md#ml-05) Học không giám sát và phát hiện bất thường | Dùng chung trong họ | 3, 4 |
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
9. [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả — ● Cốt lõi
10. [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá — ● Cốt lõi
11. [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn — ● Cốt lõi
12. [STAT-04](../mang/stat.md#stat-04) Dự báo xác suất và định lượng bất định — ● Cốt lõi
13. [ML-02](../mang/ml.md#ml-02) Gradient boosting — ● Cốt lõi
14. [ML-06](../mang/ml.md#ml-06) Mô hình chuỗi thời gian — ● Cốt lõi
15. [DL-01](../mang/dl.md#dl-01) PyTorch nền tảng — ◐ Cần
16. [OPT-01](../mang/opt.md#opt-01) Quy hoạch tuyến tính và nguyên (LP/MIP) — ◐ Cần
17. [OPT-03](../mang/opt.md#opt-03) Ra quyết định dưới bất định (dự báo rồi tối ưu) — ◐ Cần
18. [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model — ◐ Cần
19. [OPS-02](../mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập — ◐ Cần
20. [OPS-03](../mang/ops.md#ops-03) Pipeline và điều phối tác vụ — ◐ Cần
21. [OPS-04](../mang/ops.md#ops-04) Giám sát model và drift — ◐ Cần
22. [BIZ-01](../mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) — ● Cốt lõi
23. [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) — ● Cốt lõi
24. [BIZ-03](../mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) — ● Cốt lõi
25. [BIZ-04](../mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) — ◐ Cần
26. [BIZ-05](../mang/biz.md#biz-05) Kiến thức miền nghiệp vụ — ● Cốt lõi

## Tổ hợp có nhóm này

- [CMB-02 · Dự báo rồi tối ưu (tồn kho, xếp ca)](../to-hop-ky-nang.md#cmb-02) — Dự báo nhu cầu dạng quantile (Nhóm 2) → tối ưu đặt hàng / xếp ca dưới ràng buộc (Nhóm 8)
- [CMB-07 · Tổng đài thông minh](../to-hop-ky-nang.md#cmb-07) — Ghi âm → ASR → phân loại/tóm tắt (Nhóm 6) → chuyển ticket (Nhóm 7); lưu lượng lịch sử → dự báo cuộc gọi (Nhóm 2) → xếp ca (Nhóm 8)
