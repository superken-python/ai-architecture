<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# Nhóm 1 · Dự đoán trên dữ liệu bảng

> “Khách này có rời bỏ, vỡ nợ hay mua hàng không?” — Khối A · Dự đoán

**Ví dụ trong doanh nghiệp:** churn, chấm điểm tín dụng, lead scoring, định giá.

| Đầu vào | Kỹ thuật chính | Đầu ra | Quyết định kinh doanh |
|---|---|---|---|
| Hồ sơ khách hàng, lịch sử giao dịch (dạng bảng) | Gradient boosting: LightGBM, XGBoost, CatBoost | Xác suất rời bỏ hoặc vỡ nợ, giá trị dự đoán | Chọn khách cần chăm sóc, duyệt hoặc từ chối khoản vay |

## Mức năng lực của nhóm (từ bản đồ bài toán)

| Mức | Nội dung |
|---|---|
| Cơ bản | pandas, SQL, scikit-learn. Chọn đúng metric (AUC, F1 cho phân loại; MAE cho hồi quy), vì accuracy rất dễ đánh lừa khi dữ liệu lệch. |
| Trung cấp | XGBoost/LightGBM/CatBoost, feature engineering, xử lý mất cân bằng, phát hiện data leakage, chia train/test theo thời gian. |
| Nâng cao | Hiệu chỉnh xác suất (calibration), giải thích bằng SHAP, chọn ngưỡng theo chi phí của từng loại sai, giám sát drift. Thử TabPFN khi dữ liệu ít. |

- **Metric chính:** AUC, F1, precision@k (phân loại); MAE, RMSE (hồi quy).
- **Công cụ:** pandas, scikit-learn, LightGBM, XGBoost, CatBoost, SHAP
- **Bẫy thường gặp:** Dùng thông tin "tương lai" làm feature (leakage); chia ngẫu nhiên khi dữ liệu có yếu tố thời gian; tối ưu accuracy trên dữ liệu lệch.
- **Dự án luyện tập:** Dự đoán churn trên bộ Telco Customer Churn, xuất danh sách top 500 khách cho CSKH kèm lý do từ SHAP.

## Kỹ năng cần cho nhóm này

### ● Cốt lõi (17)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI | Nền tảng chung | 2, 3, 4, 5, 6, 7, 8 |
| [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án | Nền tảng chung | 2, 3, 4, 5, 6, 7, 8 |
| [DATA-01](../mang/data.md#data-01) SQL phân tích | Cầu nối liên họ | 2, 3, 4, 6, 7, 8 |
| [DATA-02](../mang/data.md#data-02) Xử lý dữ liệu bảng | Dùng chung trong họ | 2, 3, 4, 8 |
| [DATA-03](../mang/data.md#data-03) Đúng thời điểm và chống rò rỉ dữ liệu | Dùng chung trong họ | 2, 3, 4, 8 |
| [DATA-04](../mang/data.md#data-04) Feature engineering cho bảng và chuỗi thời gian | Dùng chung trong họ | 2, 3, 4, 8 |
| [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả | Nền tảng chung | 2, 3, 4, 5, 6, 7, 8 |
| [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá | Nền tảng chung | 2, 3, 4, 5, 6, 7, 8 |
| [STAT-05](../mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc | Cầu nối liên họ | 3, 5, 6, 7, 8 |
| [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn | Cầu nối liên họ | 2, 3, 4, 6, 8 |
| [ML-02](../mang/ml.md#ml-02) Gradient boosting | Dùng chung trong họ | 2, 3, 4, 8 |
| [ML-03](../mang/ml.md#ml-03) Dữ liệu mất cân bằng và sự kiện hiếm | Cầu nối liên họ | 3, 5 |
| [ML-04](../mang/ml.md#ml-04) Giải thích mô hình | Cầu nối liên họ | 3, 5, 8 |
| [BIZ-01](../mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) | Nền tảng chung | 2, 3, 4, 5, 6, 7, 8 |
| [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) | Nền tảng chung | 2, 3, 4, 5, 6, 7, 8 |
| [BIZ-03](../mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) | Nền tảng chung | 2, 3, 4, 5, 6, 7, 8 |
| [BIZ-05](../mang/biz.md#biz-05) Kiến thức miền nghiệp vụ | Nền tảng chung | 2, 3, 4, 5, 6, 7, 8 |

### ◐ Cần (9)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-03](../mang/py.md#py-03) Kiểm thử và chất lượng code | Nền tảng chung | 2, 3, 4, 5, 6, 7, 8 |
| [DATA-05](../mang/data.md#data-05) Kiểm định chất lượng dữ liệu và nhãn | Nền tảng chung | 2, 3, 4, 5, 6, 7, 8 |
| [STAT-03](../mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test | Cầu nối liên họ | 4, 6, 8 |
| [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model | Nền tảng chung | 2, 3, 4, 5, 6, 7, 8 |
| [OPS-02](../mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập | Nền tảng chung | 2, 3, 4, 5, 6, 7, 8 |
| [OPS-03](../mang/ops.md#ops-03) Pipeline và điều phối tác vụ | Cầu nối liên họ | 2, 3, 4, 6 |
| [OPS-04](../mang/ops.md#ops-04) Giám sát model và drift | Cầu nối liên họ | 2, 3, 4, 5, 6, 8 |
| [OPS-08](../mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ | Cầu nối liên họ | 3, 5, 6, 7 |
| [BIZ-04](../mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) | Nền tảng chung | 2, 3, 4, 5, 6, 7, 8 |

### ○ Ít (11)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-04](../mang/py.md#py-04) Gọi API và I/O đồng thời bền vững | Cầu nối liên họ | 3, 5, 6, 7 |
| [STAT-04](../mang/stat.md#stat-04) Dự báo xác suất và định lượng bất định | Dùng chung trong họ | 2, 8 |
| [STAT-06](../mang/stat.md#stat-06) Suy luận nhân quả và uplift | Dùng chung trong họ | 4, 8 |
| [ML-05](../mang/ml.md#ml-05) Học không giám sát và phát hiện bất thường | Dùng chung trong họ | 3, 4 |
| [DL-01](../mang/dl.md#dl-01) PyTorch nền tảng | Cầu nối liên họ | 2, 3, 4, 5, 6 |
| [LLM-01](../mang/llm.md#llm-01) Gọi LLM API và prompt engineering | Dùng chung trong họ | 5, 6, 7 |
| [BIZ-06](../mang/biz.md#biz-06) Đọc và tái hiện paper | Bổ trợ | — |
| [EFF-04](../mang/eff.md#eff-04) Định tuyến và cascade — đúng việc, đúng công cụ | Dùng chung trong họ | 5, 6, 7 |
| [EFF-06](../mang/eff.md#eff-06) Xử lý theo lô và bất đồng bộ | Dùng chung trong họ | 5, 6 |
| [EFF-07](../mang/eff.md#eff-07) Kiểm chứng xác định và "không lỗi im lặng" | Dùng chung trong họ | 5, 6, 7 |
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
11. [STAT-03](../mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test — ◐ Cần
12. [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn — ● Cốt lõi
13. [STAT-05](../mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc — ● Cốt lõi
14. [ML-02](../mang/ml.md#ml-02) Gradient boosting — ● Cốt lõi
15. [ML-03](../mang/ml.md#ml-03) Dữ liệu mất cân bằng và sự kiện hiếm — ● Cốt lõi
16. [ML-04](../mang/ml.md#ml-04) Giải thích mô hình — ● Cốt lõi
17. [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model — ◐ Cần
18. [OPS-02](../mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập — ◐ Cần
19. [OPS-03](../mang/ops.md#ops-03) Pipeline và điều phối tác vụ — ◐ Cần
20. [OPS-04](../mang/ops.md#ops-04) Giám sát model và drift — ◐ Cần
21. [OPS-08](../mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ — ◐ Cần
22. [BIZ-01](../mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) — ● Cốt lõi
23. [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) — ● Cốt lõi
24. [BIZ-03](../mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) — ● Cốt lõi
25. [BIZ-04](../mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) — ◐ Cần
26. [BIZ-05](../mang/biz.md#biz-05) Kiến thức miền nghiệp vụ — ● Cốt lõi

## Tổ hợp có nhóm này

- [CMB-01 · Hồ sơ vay / eKYC từ đầu đến cuối](../to-hop-ky-nang.md#cmb-01) — Đọc giấy tờ và trích trường (Nhóm 5) → chấm điểm tín dụng (Nhóm 1) → điều phối quy trình, người duyệt ở bước rủi ro (Nhóm 7)
- [CMB-06 · Dự đoán rồi can thiệp (churn + uplift)](../to-hop-ky-nang.md#cmb-06) — Dự đoán khả năng rời bỏ (Nhóm 1) → chọn khách mà can thiệp thật sự thay đổi kết quả (Nhóm 8, uplift)
- [CMB-08 · Phân loại lai ML + LLM (cascade tiết kiệm token)](../to-hop-ky-nang.md#cmb-08) — Luật → model nhỏ (TF-IDF/PhoBERT, kỹ năng Nhóm 1) xử lý ca dễ có độ tin cậy cao → LLM xử lý ca khó (Nhóm 6) → người xử lý ca vẫn nghi ngờ
