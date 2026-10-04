<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# Nhóm 5 · Thị giác máy tính và Document AI

> “Trong ảnh hay tài liệu này có gì?” — Khối B · Hiểu

**Ví dụ trong doanh nghiệp:** eKYC (đọc giấy tờ tùy thân, so khớp khuôn mặt), kiểm tra lỗi sản phẩm, trích xuất hóa đơn, hợp đồng, chứng từ.

| Đầu vào | Kỹ thuật chính | Đầu ra | Quyết định kinh doanh |
|---|---|---|---|
| Ảnh, video, PDF scan, ảnh chụp giấy tờ | Detection, OCR, VLM (mô hình thị giác–ngôn ngữ) | Nhãn, vùng lỗi, trường dữ liệu có cấu trúc | Tự động duyệt hồ sơ, loại sản phẩm lỗi |

## Mức năng lực của nhóm (từ bản đồ bài toán)

| Mức | Nội dung |
|---|---|
| Cơ bản | Transfer learning, YOLO cho phát hiện vật thể, OCR có sẵn. Metric gồm mAP, IoU và độ chính xác theo từng trường thông tin. |
| Trung cấp | Chiến lược gán nhãn, augmentation, segmentation. Dùng VLM để trích xuất tài liệu có nhiều mẫu khác nhau. |
| Nâng cao | Triển khai trên thiết bị biên (ONNX, TensorRT, quantization), active learning, xử lý ảnh chất lượng xấu ngoài thực tế. Đo tỷ lệ hồ sơ được xử lý tự động hoàn toàn. |

- **Metric chính:** mAP, IoU; độ chính xác theo từng trường; tỷ lệ hồ sơ xử lý tự động hoàn toàn.
- **Công cụ:** PyTorch, Ultralytics YOLO, OpenCV, PaddleOCR, VietOCR, Label Studio, ONNX Runtime
- **Bẫy thường gặp:** Dữ liệu huấn luyện quá "sạch" so với ảnh chụp thực tế; chỉ đo độ chính xác chung thay vì theo từng trường.
- **Dự án luyện tập:** Trích xuất ngày, tổng tiền, mã số thuế từ ảnh hóa đơn; so sánh OCR + luật với VLM về độ chính xác và chi phí.

## Kỹ năng cần cho nhóm này

### ● Cốt lõi (12)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI | Nền tảng chung | 1, 2, 3, 4, 6, 7, 8 |
| [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án | Nền tảng chung | 1, 2, 3, 4, 6, 7, 8 |
| [DL-01](../mang/dl.md#dl-01) PyTorch nền tảng | Cầu nối liên họ | 2, 3, 4, 6 |
| [DL-02](../mang/dl.md#dl-02) Transfer learning và fine-tune mô hình pretrained | Dùng chung trong họ | 6 |
| [DL-04](../mang/dl.md#dl-04) Thị giác máy tính (detection, segmentation, OCR) | Chuyên biệt | — |
| [DL-05](../mang/dl.md#dl-05) Document AI và mô hình thị giác–ngôn ngữ (VLM) | Dùng chung trong họ | 6, 7 |
| [LLM-02](../mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra | Dùng chung trong họ | 6, 7 |
| [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model | Nền tảng chung | 1, 2, 3, 4, 6, 7, 8 |
| [OPS-05](../mang/ops.md#ops-05) Tối ưu suy luận và serving model | Cầu nối liên họ | 3, 4, 6 |
| [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) | Nền tảng chung | 1, 2, 3, 4, 6, 7, 8 |
| [BIZ-03](../mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) | Nền tảng chung | 1, 2, 3, 4, 6, 7, 8 |
| [EFF-07](../mang/eff.md#eff-07) Kiểm chứng xác định và "không lỗi im lặng" | Dùng chung trong họ | 6, 7 |

### ◐ Cần (28)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-03](../mang/py.md#py-03) Kiểm thử và chất lượng code | Nền tảng chung | 1, 2, 3, 4, 6, 7, 8 |
| [PY-04](../mang/py.md#py-04) Gọi API và I/O đồng thời bền vững | Cầu nối liên họ | 3, 6, 7 |
| [DATA-05](../mang/data.md#data-05) Kiểm định chất lượng dữ liệu và nhãn | Nền tảng chung | 1, 2, 3, 4, 6, 7, 8 |
| [DATA-06](../mang/data.md#data-06) Văn bản tiếng Việt và dữ liệu phi cấu trúc | Dùng chung trong họ | 6 |
| [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả | Nền tảng chung | 1, 2, 3, 4, 6, 7, 8 |
| [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá | Nền tảng chung | 1, 2, 3, 4, 6, 7, 8 |
| [STAT-05](../mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc | Cầu nối liên họ | 1, 3, 6, 7, 8 |
| [ML-03](../mang/ml.md#ml-03) Dữ liệu mất cân bằng và sự kiện hiếm | Cầu nối liên họ | 1, 3 |
| [ML-04](../mang/ml.md#ml-04) Giải thích mô hình | Cầu nối liên họ | 1, 3, 8 |
| [ML-07](../mang/ml.md#ml-07) Truy xuất và xếp hạng hai tầng (retrieve → rerank) | Cầu nối liên họ | 4, 6, 7 |
| [DL-03](../mang/dl.md#dl-03) Embedding và học biểu diễn | Cầu nối liên họ | 3, 4, 6 |
| [LLM-01](../mang/llm.md#llm-01) Gọi LLM API và prompt engineering | Dùng chung trong họ | 6, 7 |
| [LLM-04](../mang/llm.md#llm-04) Đánh giá hệ LLM (evals) | Dùng chung trong họ | 6, 7 |
| [LLM-06](../mang/llm.md#llm-06) An toàn và bảo mật hệ LLM | Dùng chung trong họ | 6, 7 |
| [LLM-07](../mang/llm.md#llm-07) Fine-tune, distill và tự host LLM | Dùng chung trong họ | 6 |
| [OPS-02](../mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập | Nền tảng chung | 1, 2, 3, 4, 6, 7, 8 |
| [OPS-04](../mang/ops.md#ops-04) Giám sát model và drift | Cầu nối liên họ | 1, 2, 3, 4, 6, 8 |
| [OPS-06](../mang/ops.md#ops-06) LLMOps — tracing, chi phí, độ trễ | Dùng chung trong họ | 6, 7 |
| [OPS-08](../mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ | Cầu nối liên họ | 1, 3, 6, 7 |
| [BIZ-01](../mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) | Nền tảng chung | 1, 2, 3, 4, 6, 7, 8 |
| [BIZ-04](../mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) | Nền tảng chung | 1, 2, 3, 4, 6, 7, 8 |
| [BIZ-05](../mang/biz.md#biz-05) Kiến thức miền nghiệp vụ | Nền tảng chung | 1, 2, 3, 4, 6, 7, 8 |
| [EFF-01](../mang/eff.md#eff-01) Đo token và chi phí trên mỗi tác vụ | Dùng chung trong họ | 6, 7 |
| [EFF-02](../mang/eff.md#eff-02) Prompt caching và tái sử dụng kết quả | Dùng chung trong họ | 6, 7 |
| [EFF-03](../mang/eff.md#eff-03) Tinh gọn ngữ cảnh đầu vào | Dùng chung trong họ | 6, 7 |
| [EFF-04](../mang/eff.md#eff-04) Định tuyến và cascade — đúng việc, đúng công cụ | Dùng chung trong họ | 6, 7 |
| [EFF-05](../mang/eff.md#eff-05) Kiểm soát đầu ra và mức suy luận | Dùng chung trong họ | 6, 7 |
| [EFF-06](../mang/eff.md#eff-06) Xử lý theo lô và bất đồng bộ | Dùng chung trong họ | 6 |

### ○ Ít (5)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [DATA-01](../mang/data.md#data-01) SQL phân tích | Cầu nối liên họ | 1, 2, 3, 4, 6, 7, 8 |
| [DATA-02](../mang/data.md#data-02) Xử lý dữ liệu bảng | Dùng chung trong họ | 1, 2, 3, 4, 8 |
| [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn | Cầu nối liên họ | 1, 2, 3, 4, 6, 8 |
| [BIZ-06](../mang/biz.md#biz-06) Đọc và tái hiện paper | Bổ trợ | — |
| [EFF-08](../mang/eff.md#eff-08) Tiết kiệm token khi dùng AI hỗ trợ lập trình | Bổ trợ | — |

## Lộ trình học cho nhóm này

Thứ tự đã tôn trọng tiên quyết. Kỹ năng đánh dấu *(tiên quyết)* không trực tiếp thuộc nhóm nhưng cần để học các kỹ năng phía sau. Gợi ý: đạt **Cơ bản** cho cả danh sách trước, rồi mới lên **Trung cấp** ở các kỹ năng Cốt lõi.

1. [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI — ● Cốt lõi
2. [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án — ● Cốt lõi
3. [PY-03](../mang/py.md#py-03) Kiểm thử và chất lượng code — ◐ Cần
4. [PY-04](../mang/py.md#py-04) Gọi API và I/O đồng thời bền vững — ◐ Cần
5. [DATA-02](../mang/data.md#data-02) Xử lý dữ liệu bảng — *(tiên quyết)*
6. [DATA-05](../mang/data.md#data-05) Kiểm định chất lượng dữ liệu và nhãn — ◐ Cần
7. [DATA-06](../mang/data.md#data-06) Văn bản tiếng Việt và dữ liệu phi cấu trúc — ◐ Cần
8. [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả — ◐ Cần
9. [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá — ◐ Cần
10. [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn — *(tiên quyết)*
11. [STAT-05](../mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc — ◐ Cần
12. [ML-02](../mang/ml.md#ml-02) Gradient boosting — *(tiên quyết)*
13. [ML-03](../mang/ml.md#ml-03) Dữ liệu mất cân bằng và sự kiện hiếm — ◐ Cần
14. [ML-04](../mang/ml.md#ml-04) Giải thích mô hình — ◐ Cần
15. [DL-01](../mang/dl.md#dl-01) PyTorch nền tảng — ● Cốt lõi
16. [DL-02](../mang/dl.md#dl-02) Transfer learning và fine-tune mô hình pretrained — ● Cốt lõi
17. [DL-03](../mang/dl.md#dl-03) Embedding và học biểu diễn — ◐ Cần
18. [ML-07](../mang/ml.md#ml-07) Truy xuất và xếp hạng hai tầng (retrieve → rerank) — ◐ Cần
19. [DL-04](../mang/dl.md#dl-04) Thị giác máy tính (detection, segmentation, OCR) — ● Cốt lõi
20. [LLM-01](../mang/llm.md#llm-01) Gọi LLM API và prompt engineering — ◐ Cần
21. [LLM-02](../mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra — ● Cốt lõi
22. [DL-05](../mang/dl.md#dl-05) Document AI và mô hình thị giác–ngôn ngữ (VLM) — ● Cốt lõi
23. [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model — ● Cốt lõi
24. [OPS-02](../mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập — ◐ Cần
25. [OPS-04](../mang/ops.md#ops-04) Giám sát model và drift — ◐ Cần
26. [OPS-05](../mang/ops.md#ops-05) Tối ưu suy luận và serving model — ● Cốt lõi
27. [OPS-06](../mang/ops.md#ops-06) LLMOps — tracing, chi phí, độ trễ — ◐ Cần
28. [OPS-08](../mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ — ◐ Cần
29. [LLM-06](../mang/llm.md#llm-06) An toàn và bảo mật hệ LLM — ◐ Cần
30. [BIZ-01](../mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) — ◐ Cần
31. [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) — ● Cốt lõi
32. [LLM-04](../mang/llm.md#llm-04) Đánh giá hệ LLM (evals) — ◐ Cần
33. [LLM-07](../mang/llm.md#llm-07) Fine-tune, distill và tự host LLM — ◐ Cần
34. [BIZ-03](../mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) — ● Cốt lõi
35. [BIZ-04](../mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) — ◐ Cần
36. [BIZ-05](../mang/biz.md#biz-05) Kiến thức miền nghiệp vụ — ◐ Cần
37. [EFF-01](../mang/eff.md#eff-01) Đo token và chi phí trên mỗi tác vụ — ◐ Cần
38. [EFF-02](../mang/eff.md#eff-02) Prompt caching và tái sử dụng kết quả — ◐ Cần
39. [EFF-03](../mang/eff.md#eff-03) Tinh gọn ngữ cảnh đầu vào — ◐ Cần
40. [EFF-04](../mang/eff.md#eff-04) Định tuyến và cascade — đúng việc, đúng công cụ — ◐ Cần
41. [EFF-05](../mang/eff.md#eff-05) Kiểm soát đầu ra và mức suy luận — ◐ Cần
42. [EFF-06](../mang/eff.md#eff-06) Xử lý theo lô và bất đồng bộ — ◐ Cần
43. [EFF-07](../mang/eff.md#eff-07) Kiểm chứng xác định và "không lỗi im lặng" — ● Cốt lõi

## Tổ hợp có nhóm này

- [CMB-01 · Hồ sơ vay / eKYC từ đầu đến cuối](../to-hop-ky-nang.md#cmb-01) — Đọc giấy tờ và trích trường (Nhóm 5) → chấm điểm tín dụng (Nhóm 1) → điều phối quy trình, người duyệt ở bước rủi ro (Nhóm 7)
