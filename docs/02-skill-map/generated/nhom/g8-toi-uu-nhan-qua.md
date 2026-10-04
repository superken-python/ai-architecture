<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# Nhóm 8 · Tối ưu hóa và suy luận nhân quả

> “Nên làm gì là tốt nhất?” — Khối D · Quyết định

**Ví dụ trong doanh nghiệp:** tuyến giao hàng, xếp ca, định giá khuyến mãi, phân bổ ngân sách marketing.

| Đầu vào | Kỹ thuật chính | Đầu ra | Quyết định kinh doanh |
|---|---|---|---|
| Dự báo, ràng buộc (xe, ca, ngân sách), dữ liệu thí nghiệm | LP/MIP, uplift modeling, suy luận nhân quả | Phương án tối ưu, ước lượng tác động thật | Lộ trình xe, lịch ca, chọn khách cần tác động |

## Mức năng lực của nhóm (từ bản đồ bài toán)

| Mức | Nội dung |
|---|---|
| Cơ bản | A/B test đúng cách (cỡ mẫu, ý nghĩa thống kê), quy hoạch tuyến tính với OR-Tools. |
| Trung cấp | Quy hoạch nguyên (MIP) cho xếp lịch và định tuyến xe (VRP). Kết hợp "dự báo rồi tối ưu", dùng uplift modeling để chọn đúng khách cần tác động. |
| Nâng cao | Causal inference (DoWhy, EconML, difference-in-differences), multi-armed bandit. |

- **Metric chính:** Chi phí hoặc lợi nhuận so với cách làm hiện tại; mức tăng (uplift) có ý nghĩa thống kê; mức vi phạm ràng buộc.
- **Công cụ:** OR-Tools, PuLP, Pyomo, DoWhy, EconML, CausalML
- **Bẫy thường gặp:** Nhầm tương quan với nhân quả; tối ưu trên dự báo một điểm mà bỏ qua bất định; dừng A/B test sớm khi thấy kết quả đẹp.
- **Dự án luyện tập:** Tối ưu tuyến giao hàng cho 1 kho và 20 điểm giao bằng OR-Tools, so tổng quãng đường với tuyến hiện tại.
- **Nguyên tắc:** Dự đoán chưa tạo ra tiền, quyết định mới tạo ra tiền — nhóm này là cầu nối từ model đến lợi nhuận.

## Kỹ năng cần cho nhóm này

### ● Cốt lõi (14)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7 |
| [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7 |
| [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7 |
| [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7 |
| [STAT-03](../mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test | Cầu nối liên họ | 1, 4, 6 |
| [STAT-04](../mang/stat.md#stat-04) Dự báo xác suất và định lượng bất định | Dùng chung trong họ | 2 |
| [STAT-06](../mang/stat.md#stat-06) Suy luận nhân quả và uplift | Dùng chung trong họ | 4 |
| [OPT-01](../mang/opt.md#opt-01) Quy hoạch tuyến tính và nguyên (LP/MIP) | Dùng chung trong họ | 2 |
| [OPT-02](../mang/opt.md#opt-02) Tối ưu tổ hợp — định tuyến và lập lịch | Chuyên biệt | — |
| [OPT-03](../mang/opt.md#opt-03) Ra quyết định dưới bất định (dự báo rồi tối ưu) | Dùng chung trong họ | 2 |
| [BIZ-01](../mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7 |
| [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7 |
| [BIZ-03](../mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7 |
| [BIZ-05](../mang/biz.md#biz-05) Kiến thức miền nghiệp vụ | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7 |

### ◐ Cần (16)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-03](../mang/py.md#py-03) Kiểm thử và chất lượng code | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7 |
| [DATA-01](../mang/data.md#data-01) SQL phân tích | Cầu nối liên họ | 1, 2, 3, 4, 6, 7 |
| [DATA-02](../mang/data.md#data-02) Xử lý dữ liệu bảng | Dùng chung trong họ | 1, 2, 3, 4 |
| [DATA-03](../mang/data.md#data-03) Đúng thời điểm và chống rò rỉ dữ liệu | Dùng chung trong họ | 1, 2, 3, 4 |
| [DATA-04](../mang/data.md#data-04) Feature engineering cho bảng và chuỗi thời gian | Dùng chung trong họ | 1, 2, 3, 4 |
| [DATA-05](../mang/data.md#data-05) Kiểm định chất lượng dữ liệu và nhãn | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7 |
| [STAT-05](../mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc | Cầu nối liên họ | 1, 3, 5, 6, 7 |
| [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn | Cầu nối liên họ | 1, 2, 3, 4, 6 |
| [ML-02](../mang/ml.md#ml-02) Gradient boosting | Dùng chung trong họ | 1, 2, 3, 4 |
| [ML-04](../mang/ml.md#ml-04) Giải thích mô hình | Cầu nối liên họ | 1, 3, 5 |
| [ML-06](../mang/ml.md#ml-06) Mô hình chuỗi thời gian | Dùng chung trong họ | 2, 3 |
| [OPT-04](../mang/opt.md#opt-04) Bandit và học tăng cường cơ bản | Dùng chung trong họ | 4 |
| [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7 |
| [OPS-02](../mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7 |
| [OPS-04](../mang/ops.md#ops-04) Giám sát model và drift | Cầu nối liên họ | 1, 2, 3, 4, 5, 6 |
| [BIZ-04](../mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7 |

### ○ Ít (8)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-04](../mang/py.md#py-04) Gọi API và I/O đồng thời bền vững | Cầu nối liên họ | 3, 5, 6, 7 |
| [DATA-07](../mang/data.md#data-07) Dữ liệu đồ thị | Chuyên biệt | 3 |
| [DL-01](../mang/dl.md#dl-01) PyTorch nền tảng | Cầu nối liên họ | 2, 3, 4, 5, 6 |
| [LLM-01](../mang/llm.md#llm-01) Gọi LLM API và prompt engineering | Dùng chung trong họ | 5, 6, 7 |
| [OPS-03](../mang/ops.md#ops-03) Pipeline và điều phối tác vụ | Cầu nối liên họ | 1, 2, 3, 4, 6 |
| [OPS-08](../mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ | Cầu nối liên họ | 1, 3, 5, 6, 7 |
| [BIZ-06](../mang/biz.md#biz-06) Đọc và tái hiện paper | Bổ trợ | — |
| [EFF-08](../mang/eff.md#eff-08) Tiết kiệm token khi dùng AI hỗ trợ lập trình | Bổ trợ | — |

## Lộ trình học cho nhóm này

Thứ tự đã tôn trọng tiên quyết. Kỹ năng đánh dấu *(tiên quyết)* không trực tiếp thuộc nhóm nhưng cần để học các kỹ năng phía sau. Gợi ý: đạt **Cơ bản** cho cả danh sách trước, rồi mới lên **Trung cấp** ở các kỹ năng Cốt lõi.

1. [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI — ● Cốt lõi
2. [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án — ● Cốt lõi
3. [PY-03](../mang/py.md#py-03) Kiểm thử và chất lượng code — ◐ Cần
4. [DATA-01](../mang/data.md#data-01) SQL phân tích — ◐ Cần
5. [DATA-02](../mang/data.md#data-02) Xử lý dữ liệu bảng — ◐ Cần
6. [DATA-03](../mang/data.md#data-03) Đúng thời điểm và chống rò rỉ dữ liệu — ◐ Cần
7. [DATA-04](../mang/data.md#data-04) Feature engineering cho bảng và chuỗi thời gian — ◐ Cần
8. [DATA-05](../mang/data.md#data-05) Kiểm định chất lượng dữ liệu và nhãn — ◐ Cần
9. [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả — ● Cốt lõi
10. [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá — ● Cốt lõi
11. [STAT-03](../mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test — ● Cốt lõi
12. [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn — ◐ Cần
13. [STAT-04](../mang/stat.md#stat-04) Dự báo xác suất và định lượng bất định — ● Cốt lõi
14. [STAT-05](../mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc — ◐ Cần
15. [ML-02](../mang/ml.md#ml-02) Gradient boosting — ◐ Cần
16. [STAT-06](../mang/stat.md#stat-06) Suy luận nhân quả và uplift — ● Cốt lõi
17. [ML-04](../mang/ml.md#ml-04) Giải thích mô hình — ◐ Cần
18. [ML-06](../mang/ml.md#ml-06) Mô hình chuỗi thời gian — ◐ Cần
19. [OPT-01](../mang/opt.md#opt-01) Quy hoạch tuyến tính và nguyên (LP/MIP) — ● Cốt lõi
20. [OPT-02](../mang/opt.md#opt-02) Tối ưu tổ hợp — định tuyến và lập lịch — ● Cốt lõi
21. [OPT-03](../mang/opt.md#opt-03) Ra quyết định dưới bất định (dự báo rồi tối ưu) — ● Cốt lõi
22. [OPT-04](../mang/opt.md#opt-04) Bandit và học tăng cường cơ bản — ◐ Cần
23. [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model — ◐ Cần
24. [OPS-02](../mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập — ◐ Cần
25. [OPS-04](../mang/ops.md#ops-04) Giám sát model và drift — ◐ Cần
26. [BIZ-01](../mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) — ● Cốt lõi
27. [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) — ● Cốt lõi
28. [BIZ-03](../mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) — ● Cốt lõi
29. [BIZ-04](../mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) — ◐ Cần
30. [BIZ-05](../mang/biz.md#biz-05) Kiến thức miền nghiệp vụ — ● Cốt lõi

## Tổ hợp có nhóm này

- [CMB-02 · Dự báo rồi tối ưu (tồn kho, xếp ca)](../to-hop-ky-nang.md#cmb-02) — Dự báo nhu cầu dạng quantile (Nhóm 2) → tối ưu đặt hàng / xếp ca dưới ràng buộc (Nhóm 8)
- [CMB-05 · Gợi ý và kiểm chứng bằng thí nghiệm](../to-hop-ky-nang.md#cmb-05) — Sinh danh sách gợi ý (Nhóm 4) → đo tác động thật bằng A/B test hoặc bandit (Nhóm 8)
- [CMB-06 · Dự đoán rồi can thiệp (churn + uplift)](../to-hop-ky-nang.md#cmb-06) — Dự đoán khả năng rời bỏ (Nhóm 1) → chọn khách mà can thiệp thật sự thay đổi kết quả (Nhóm 8, uplift)
- [CMB-07 · Tổng đài thông minh](../to-hop-ky-nang.md#cmb-07) — Ghi âm → ASR → phân loại/tóm tắt (Nhóm 6) → chuyển ticket (Nhóm 7); lưu lượng lịch sử → dự báo cuộc gọi (Nhóm 2) → xếp ca (Nhóm 8)
