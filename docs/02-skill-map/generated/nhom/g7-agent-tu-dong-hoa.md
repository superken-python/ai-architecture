<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# Nhóm 7 · AI Agent và tự động hóa quy trình

> “Làm giúp tôi cả chuỗi việc này.” — Khối C · Hành động

**Ví dụ trong doanh nghiệp:** xử lý hồ sơ vay từ đầu đến cuối, đối soát, trợ lý thao tác trên CRM/ERP, tự động lập báo cáo.

| Đầu vào | Kỹ thuật chính | Đầu ra | Quyết định kinh doanh |
|---|---|---|---|
| Yêu cầu của người dùng + công cụ: API, CRM, ERP | LLM gọi công cụ (tool calling, MCP) theo workflow | Chuỗi hành động đã thực hiện, log và kết quả | Hoàn tất quy trình; người duyệt ở bước rủi ro |

## Mức năng lực của nhóm (từ bản đồ bài toán)

| Mức | Nội dung |
|---|---|
| Cơ bản | Tool/function calling, workflow cố định (chuỗi bước LLM xen code), có người duyệt ở bước rủi ro. |
| Trung cấp | Orchestration bằng LangGraph hoặc agent SDK của các hãng, MCP để kết nối công cụ và dữ liệu, quản lý state/context, guardrails, tracing. |
| Nâng cao | Đánh giá cả quá trình agent thực hiện (trajectory) chứ không chỉ kết quả cuối, multi-agent, computer-use, bảo mật (prompt injection, cấp quyền tối thiểu). |

- **Metric chính:** Tỷ lệ hoàn thành nhiệm vụ; chi phí và số bước mỗi nhiệm vụ; tỷ lệ cần người can thiệp; số lỗi nghiêm trọng.
- **Công cụ:** LangGraph, agent SDK của các hãng, MCP, Langfuse
- **Bẫy thường gặp:** Dùng agent tự chủ cho việc mà workflow cố định làm tốt hơn; cấp quyền quá rộng; không ghi log được agent đã làm gì.
- **Dự án luyện tập:** Agent đọc email yêu cầu báo giá, tra bảng giá, soạn báo giá và chờ người duyệt trước khi gửi.
- **Nguyên tắc:** Dùng workflow đơn giản nhất chạy được; chỉ dùng agent tự chủ khi bài toán thật sự cần.

## Kỹ năng cần cho nhóm này

### ● Cốt lõi (22)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI | Nền tảng chung | 1, 2, 3, 4, 5, 6, 8 |
| [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án | Nền tảng chung | 1, 2, 3, 4, 5, 6, 8 |
| [PY-03](../mang/py.md#py-03) Kiểm thử và chất lượng code | Nền tảng chung | 1, 2, 3, 4, 5, 6, 8 |
| [PY-04](../mang/py.md#py-04) Gọi API và I/O đồng thời bền vững | Cầu nối liên họ | 3, 5, 6 |
| [LLM-01](../mang/llm.md#llm-01) Gọi LLM API và prompt engineering | Dùng chung trong họ | 5, 6 |
| [LLM-02](../mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra | Dùng chung trong họ | 5, 6 |
| [LLM-04](../mang/llm.md#llm-04) Đánh giá hệ LLM (evals) | Dùng chung trong họ | 5, 6 |
| [LLM-05](../mang/llm.md#llm-05) Tool calling và điều phối workflow/agent | Dùng chung trong họ | 6 |
| [LLM-06](../mang/llm.md#llm-06) An toàn và bảo mật hệ LLM | Dùng chung trong họ | 5, 6 |
| [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model | Nền tảng chung | 1, 2, 3, 4, 5, 6, 8 |
| [OPS-06](../mang/ops.md#ops-06) LLMOps — tracing, chi phí, độ trễ | Dùng chung trong họ | 5, 6 |
| [OPS-08](../mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ | Cầu nối liên họ | 1, 3, 5, 6 |
| [BIZ-01](../mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) | Nền tảng chung | 1, 2, 3, 4, 5, 6, 8 |
| [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) | Nền tảng chung | 1, 2, 3, 4, 5, 6, 8 |
| [BIZ-03](../mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) | Nền tảng chung | 1, 2, 3, 4, 5, 6, 8 |
| [BIZ-05](../mang/biz.md#biz-05) Kiến thức miền nghiệp vụ | Nền tảng chung | 1, 2, 3, 4, 5, 6, 8 |
| [EFF-01](../mang/eff.md#eff-01) Đo token và chi phí trên mỗi tác vụ | Dùng chung trong họ | 5, 6 |
| [EFF-02](../mang/eff.md#eff-02) Prompt caching và tái sử dụng kết quả | Dùng chung trong họ | 5, 6 |
| [EFF-03](../mang/eff.md#eff-03) Tinh gọn ngữ cảnh đầu vào | Dùng chung trong họ | 5, 6 |
| [EFF-04](../mang/eff.md#eff-04) Định tuyến và cascade — đúng việc, đúng công cụ | Dùng chung trong họ | 5, 6 |
| [EFF-05](../mang/eff.md#eff-05) Kiểm soát đầu ra và mức suy luận | Dùng chung trong họ | 5, 6 |
| [EFF-07](../mang/eff.md#eff-07) Kiểm chứng xác định và "không lỗi im lặng" | Dùng chung trong họ | 5, 6 |

### ◐ Cần (11)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [DATA-01](../mang/data.md#data-01) SQL phân tích | Cầu nối liên họ | 1, 2, 3, 4, 6, 8 |
| [DATA-05](../mang/data.md#data-05) Kiểm định chất lượng dữ liệu và nhãn | Nền tảng chung | 1, 2, 3, 4, 5, 6, 8 |
| [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả | Nền tảng chung | 1, 2, 3, 4, 5, 6, 8 |
| [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá | Nền tảng chung | 1, 2, 3, 4, 5, 6, 8 |
| [STAT-05](../mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc | Cầu nối liên họ | 1, 3, 5, 6, 8 |
| [ML-07](../mang/ml.md#ml-07) Truy xuất và xếp hạng hai tầng (retrieve → rerank) | Cầu nối liên họ | 4, 5, 6 |
| [DL-05](../mang/dl.md#dl-05) Document AI và mô hình thị giác–ngôn ngữ (VLM) | Dùng chung trong họ | 5, 6 |
| [LLM-03](../mang/llm.md#llm-03) RAG — trả lời dựa trên tài liệu | Dùng chung trong họ | 6 |
| [LLM-08](../mang/llm.md#llm-08) Text-to-SQL và hỏi đáp số liệu | Dùng chung trong họ | 6 |
| [OPS-02](../mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập | Nền tảng chung | 1, 2, 3, 4, 5, 6, 8 |
| [BIZ-04](../mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) | Nền tảng chung | 1, 2, 3, 4, 5, 6, 8 |

### ○ Ít (10)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [DATA-02](../mang/data.md#data-02) Xử lý dữ liệu bảng | Dùng chung trong họ | 1, 2, 3, 4, 8 |
| [DATA-06](../mang/data.md#data-06) Văn bản tiếng Việt và dữ liệu phi cấu trúc | Dùng chung trong họ | 5, 6 |
| [STAT-03](../mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test | Cầu nối liên họ | 1, 4, 6, 8 |
| [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn | Cầu nối liên họ | 1, 2, 3, 4, 6, 8 |
| [DL-01](../mang/dl.md#dl-01) PyTorch nền tảng | Cầu nối liên họ | 2, 3, 4, 5, 6 |
| [DL-03](../mang/dl.md#dl-03) Embedding và học biểu diễn | Cầu nối liên họ | 3, 4, 5, 6 |
| [LLM-07](../mang/llm.md#llm-07) Fine-tune, distill và tự host LLM | Dùng chung trong họ | 5, 6 |
| [BIZ-06](../mang/biz.md#biz-06) Đọc và tái hiện paper | Bổ trợ | — |
| [EFF-06](../mang/eff.md#eff-06) Xử lý theo lô và bất đồng bộ | Dùng chung trong họ | 5, 6 |
| [EFF-08](../mang/eff.md#eff-08) Tiết kiệm token khi dùng AI hỗ trợ lập trình | Bổ trợ | — |

## Lộ trình học cho nhóm này

Thứ tự đã tôn trọng tiên quyết. Kỹ năng đánh dấu *(tiên quyết)* không trực tiếp thuộc nhóm nhưng cần để học các kỹ năng phía sau. Gợi ý: đạt **Cơ bản** cho cả danh sách trước, rồi mới lên **Trung cấp** ở các kỹ năng Cốt lõi.

1. [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI — ● Cốt lõi
2. [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án — ● Cốt lõi
3. [PY-03](../mang/py.md#py-03) Kiểm thử và chất lượng code — ● Cốt lõi
4. [PY-04](../mang/py.md#py-04) Gọi API và I/O đồng thời bền vững — ● Cốt lõi
5. [DATA-01](../mang/data.md#data-01) SQL phân tích — ◐ Cần
6. [DATA-02](../mang/data.md#data-02) Xử lý dữ liệu bảng — *(tiên quyết)*
7. [DATA-05](../mang/data.md#data-05) Kiểm định chất lượng dữ liệu và nhãn — ◐ Cần
8. [DATA-06](../mang/data.md#data-06) Văn bản tiếng Việt và dữ liệu phi cấu trúc — *(tiên quyết)*
9. [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả — ◐ Cần
10. [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá — ◐ Cần
11. [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn — *(tiên quyết)*
12. [STAT-05](../mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc — ◐ Cần
13. [DL-01](../mang/dl.md#dl-01) PyTorch nền tảng — *(tiên quyết)*
14. [DL-02](../mang/dl.md#dl-02) Transfer learning và fine-tune mô hình pretrained — *(tiên quyết)*
15. [DL-03](../mang/dl.md#dl-03) Embedding và học biểu diễn — *(tiên quyết)*
16. [ML-07](../mang/ml.md#ml-07) Truy xuất và xếp hạng hai tầng (retrieve → rerank) — ◐ Cần
17. [DL-04](../mang/dl.md#dl-04) Thị giác máy tính (detection, segmentation, OCR) — *(tiên quyết)*
18. [LLM-01](../mang/llm.md#llm-01) Gọi LLM API và prompt engineering — ● Cốt lõi
19. [LLM-02](../mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra — ● Cốt lõi
20. [DL-05](../mang/dl.md#dl-05) Document AI và mô hình thị giác–ngôn ngữ (VLM) — ◐ Cần
21. [LLM-03](../mang/llm.md#llm-03) RAG — trả lời dựa trên tài liệu — ◐ Cần
22. [LLM-05](../mang/llm.md#llm-05) Tool calling và điều phối workflow/agent — ● Cốt lõi
23. [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model — ● Cốt lõi
24. [OPS-02](../mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập — ◐ Cần
25. [OPS-06](../mang/ops.md#ops-06) LLMOps — tracing, chi phí, độ trễ — ● Cốt lõi
26. [OPS-08](../mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ — ● Cốt lõi
27. [LLM-06](../mang/llm.md#llm-06) An toàn và bảo mật hệ LLM — ● Cốt lõi
28. [BIZ-01](../mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) — ● Cốt lõi
29. [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) — ● Cốt lõi
30. [LLM-04](../mang/llm.md#llm-04) Đánh giá hệ LLM (evals) — ● Cốt lõi
31. [LLM-08](../mang/llm.md#llm-08) Text-to-SQL và hỏi đáp số liệu — ◐ Cần
32. [BIZ-03](../mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) — ● Cốt lõi
33. [BIZ-04](../mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) — ◐ Cần
34. [BIZ-05](../mang/biz.md#biz-05) Kiến thức miền nghiệp vụ — ● Cốt lõi
35. [EFF-01](../mang/eff.md#eff-01) Đo token và chi phí trên mỗi tác vụ — ● Cốt lõi
36. [EFF-02](../mang/eff.md#eff-02) Prompt caching và tái sử dụng kết quả — ● Cốt lõi
37. [EFF-03](../mang/eff.md#eff-03) Tinh gọn ngữ cảnh đầu vào — ● Cốt lõi
38. [EFF-04](../mang/eff.md#eff-04) Định tuyến và cascade — đúng việc, đúng công cụ — ● Cốt lõi
39. [EFF-05](../mang/eff.md#eff-05) Kiểm soát đầu ra và mức suy luận — ● Cốt lõi
40. [EFF-07](../mang/eff.md#eff-07) Kiểm chứng xác định và "không lỗi im lặng" — ● Cốt lõi

## Tổ hợp có nhóm này

- [CMB-01 · Hồ sơ vay / eKYC từ đầu đến cuối](../to-hop-ky-nang.md#cmb-01) — Đọc giấy tờ và trích trường (Nhóm 5) → chấm điểm tín dụng (Nhóm 1) → điều phối quy trình, người duyệt ở bước rủi ro (Nhóm 7)
- [CMB-03 · Trợ lý nội bộ có RAG và thao tác được](../to-hop-ky-nang.md#cmb-03) — Truy xuất tài liệu/quy trình có trích dẫn (Nhóm 6) → thực hiện thao tác trên CRM/ERP theo quy trình (Nhóm 7)
- [CMB-04 · Phát hiện rồi giải thích (cảnh báo gian lận cho điều tra viên)](../to-hop-ky-nang.md#cmb-04) — Chấm điểm bất thường (Nhóm 3) → LLM tóm tắt bằng chứng cho từng cảnh báo (Nhóm 6) → hàng đợi xử lý + ghi nhận phản hồi (Nhóm 7)
- [CMB-07 · Tổng đài thông minh](../to-hop-ky-nang.md#cmb-07) — Ghi âm → ASR → phân loại/tóm tắt (Nhóm 6) → chuyển ticket (Nhóm 7); lưu lượng lịch sử → dự báo cuộc gọi (Nhóm 2) → xếp ca (Nhóm 8)
- [CMB-09 · Hỏi số liệu bằng tiếng Việt (text-to-SQL agent)](../to-hop-ky-nang.md#cmb-09) — Câu hỏi tự nhiên → chọn bảng/metric (schema linking) → sinh và kiểm tra SQL → chạy → diễn giải kết quả (Nhóm 6 + 7)
