<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# Nhóm 6 · Ngôn ngữ, LLM và RAG

> “Văn bản này nói gì? Trả lời dựa trên tài liệu nội bộ.” — Khối B · Hiểu

**Ví dụ trong doanh nghiệp:** phân loại và chuyển ticket, tóm tắt cuộc gọi, chatbot CSKH, trợ lý tra cứu quy trình nội bộ, hỏi số liệu bằng ngôn ngữ tự nhiên (text-to-SQL).

| Đầu vào | Kỹ thuật chính | Đầu ra | Quyết định kinh doanh |
|---|---|---|---|
| Tài liệu nội bộ, ticket, email, ghi âm cuộc gọi | LLM + truy xuất (hybrid search, rerank), ASR cho giọng nói | Câu trả lời có trích dẫn, nhãn, JSON có cấu trúc | Giải đáp khách hàng, chuyển ticket đúng bộ phận |

## Mức năng lực của nhóm (từ bản đồ bài toán)

| Mức | Nội dung |
|---|---|
| Cơ bản | Prompt engineering, structured output theo JSON schema. Phân loại văn bản bằng LLM hoặc fine-tune encoder nhỏ như PhoBERT. |
| Trung cấp | RAG đầy đủ (parse PDF và bảng, chunking, hybrid search, reranking, trích dẫn nguồn). Xây golden set để đo retrieval recall, faithfulness và độ đúng, rồi chọn model theo độ khó và chi phí. |
| Nâng cao | Fine-tune (LoRA, SFT, DPO), distill sang model nhỏ cho rẻ, tự host model open-weight bằng vLLM, phân quyền tài liệu theo người dùng. Dùng LLM-as-judge đã đối chiếu với nhãn của người. Thêm ASR (như Whisper) cho bài toán tổng đài. |

- **Metric chính:** Retrieval recall@k, faithfulness, độ đúng câu trả lời; chi phí và độ trễ mỗi câu hỏi.
- **Công cụ:** LLM API, Hugging Face Transformers, Qdrant hoặc pgvector, BM25, vLLM, Langfuse
- **Bẫy thường gặp:** Không có bộ đánh giá nên chỉ "cảm thấy tốt"; parse PDF và bảng kém làm hỏng cả hệ; lộ tài liệu cho người không có quyền.
- **Dự án luyện tập:** Trợ lý hỏi đáp trên sổ tay nhân viên hoặc quy chế công khai, kèm golden set khoảng 100 câu hỏi có đáp án chuẩn.

## Kỹ năng cần cho nhóm này

### ● Cốt lõi (21)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI | Nền tảng chung | 1, 2, 3, 4, 5, 7, 8 |
| [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án | Nền tảng chung | 1, 2, 3, 4, 5, 7, 8 |
| [PY-03](../mang/py.md#py-03) Kiểm thử và chất lượng code | Nền tảng chung | 1, 2, 3, 4, 5, 7, 8 |
| [PY-04](../mang/py.md#py-04) Gọi API và I/O đồng thời bền vững | Cầu nối liên họ | 3, 5, 7 |
| [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá | Nền tảng chung | 1, 2, 3, 4, 5, 7, 8 |
| [ML-07](../mang/ml.md#ml-07) Truy xuất và xếp hạng hai tầng (retrieve → rerank) | Cầu nối liên họ | 4, 5, 7 |
| [LLM-01](../mang/llm.md#llm-01) Gọi LLM API và prompt engineering | Dùng chung trong họ | 5, 7 |
| [LLM-02](../mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra | Dùng chung trong họ | 5, 7 |
| [LLM-03](../mang/llm.md#llm-03) RAG — trả lời dựa trên tài liệu | Dùng chung trong họ | 7 |
| [LLM-04](../mang/llm.md#llm-04) Đánh giá hệ LLM (evals) | Dùng chung trong họ | 5, 7 |
| [LLM-06](../mang/llm.md#llm-06) An toàn và bảo mật hệ LLM | Dùng chung trong họ | 5, 7 |
| [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model | Nền tảng chung | 1, 2, 3, 4, 5, 7, 8 |
| [OPS-06](../mang/ops.md#ops-06) LLMOps — tracing, chi phí, độ trễ | Dùng chung trong họ | 5, 7 |
| [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) | Nền tảng chung | 1, 2, 3, 4, 5, 7, 8 |
| [BIZ-03](../mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) | Nền tảng chung | 1, 2, 3, 4, 5, 7, 8 |
| [EFF-01](../mang/eff.md#eff-01) Đo token và chi phí trên mỗi tác vụ | Dùng chung trong họ | 5, 7 |
| [EFF-02](../mang/eff.md#eff-02) Prompt caching và tái sử dụng kết quả | Dùng chung trong họ | 5, 7 |
| [EFF-03](../mang/eff.md#eff-03) Tinh gọn ngữ cảnh đầu vào | Dùng chung trong họ | 5, 7 |
| [EFF-04](../mang/eff.md#eff-04) Định tuyến và cascade — đúng việc, đúng công cụ | Dùng chung trong họ | 5, 7 |
| [EFF-05](../mang/eff.md#eff-05) Kiểm soát đầu ra và mức suy luận | Dùng chung trong họ | 5, 7 |
| [EFF-07](../mang/eff.md#eff-07) Kiểm chứng xác định và "không lỗi im lặng" | Dùng chung trong họ | 5, 7 |

### ◐ Cần (24)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [DATA-01](../mang/data.md#data-01) SQL phân tích | Cầu nối liên họ | 1, 2, 3, 4, 7, 8 |
| [DATA-05](../mang/data.md#data-05) Kiểm định chất lượng dữ liệu và nhãn | Nền tảng chung | 1, 2, 3, 4, 5, 7, 8 |
| [DATA-06](../mang/data.md#data-06) Văn bản tiếng Việt và dữ liệu phi cấu trúc | Dùng chung trong họ | 5 |
| [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả | Nền tảng chung | 1, 2, 3, 4, 5, 7, 8 |
| [STAT-03](../mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test | Cầu nối liên họ | 1, 4, 8 |
| [STAT-05](../mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc | Cầu nối liên họ | 1, 3, 5, 7, 8 |
| [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn | Cầu nối liên họ | 1, 2, 3, 4, 8 |
| [DL-01](../mang/dl.md#dl-01) PyTorch nền tảng | Cầu nối liên họ | 2, 3, 4, 5 |
| [DL-02](../mang/dl.md#dl-02) Transfer learning và fine-tune mô hình pretrained | Dùng chung trong họ | 5 |
| [DL-03](../mang/dl.md#dl-03) Embedding và học biểu diễn | Cầu nối liên họ | 3, 4, 5 |
| [DL-05](../mang/dl.md#dl-05) Document AI và mô hình thị giác–ngôn ngữ (VLM) | Dùng chung trong họ | 5, 7 |
| [DL-06](../mang/dl.md#dl-06) Xử lý giọng nói (ASR) | Chuyên biệt | — |
| [LLM-05](../mang/llm.md#llm-05) Tool calling và điều phối workflow/agent | Dùng chung trong họ | 7 |
| [LLM-07](../mang/llm.md#llm-07) Fine-tune, distill và tự host LLM | Dùng chung trong họ | 5 |
| [LLM-08](../mang/llm.md#llm-08) Text-to-SQL và hỏi đáp số liệu | Dùng chung trong họ | 7 |
| [OPS-02](../mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập | Nền tảng chung | 1, 2, 3, 4, 5, 7, 8 |
| [OPS-03](../mang/ops.md#ops-03) Pipeline và điều phối tác vụ | Cầu nối liên họ | 1, 2, 3, 4 |
| [OPS-04](../mang/ops.md#ops-04) Giám sát model và drift | Cầu nối liên họ | 1, 2, 3, 4, 5, 8 |
| [OPS-05](../mang/ops.md#ops-05) Tối ưu suy luận và serving model | Cầu nối liên họ | 3, 4, 5 |
| [OPS-08](../mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ | Cầu nối liên họ | 1, 3, 5, 7 |
| [BIZ-01](../mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) | Nền tảng chung | 1, 2, 3, 4, 5, 7, 8 |
| [BIZ-04](../mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) | Nền tảng chung | 1, 2, 3, 4, 5, 7, 8 |
| [BIZ-05](../mang/biz.md#biz-05) Kiến thức miền nghiệp vụ | Nền tảng chung | 1, 2, 3, 4, 5, 7, 8 |
| [EFF-06](../mang/eff.md#eff-06) Xử lý theo lô và bất đồng bộ | Dùng chung trong họ | 5 |

### ○ Ít (4)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [DATA-02](../mang/data.md#data-02) Xử lý dữ liệu bảng | Dùng chung trong họ | 1, 2, 3, 4, 8 |
| [ML-04](../mang/ml.md#ml-04) Giải thích mô hình | Cầu nối liên họ | 1, 3, 5, 8 |
| [BIZ-06](../mang/biz.md#biz-06) Đọc và tái hiện paper | Bổ trợ | — |
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
8. [DATA-06](../mang/data.md#data-06) Văn bản tiếng Việt và dữ liệu phi cấu trúc — ◐ Cần
9. [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả — ◐ Cần
10. [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá — ● Cốt lõi
11. [STAT-03](../mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test — ◐ Cần
12. [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn — ◐ Cần
13. [STAT-05](../mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc — ◐ Cần
14. [DL-01](../mang/dl.md#dl-01) PyTorch nền tảng — ◐ Cần
15. [DL-02](../mang/dl.md#dl-02) Transfer learning và fine-tune mô hình pretrained — ◐ Cần
16. [DL-03](../mang/dl.md#dl-03) Embedding và học biểu diễn — ◐ Cần
17. [ML-07](../mang/ml.md#ml-07) Truy xuất và xếp hạng hai tầng (retrieve → rerank) — ● Cốt lõi
18. [DL-04](../mang/dl.md#dl-04) Thị giác máy tính (detection, segmentation, OCR) — *(tiên quyết)*
19. [DL-06](../mang/dl.md#dl-06) Xử lý giọng nói (ASR) — ◐ Cần
20. [LLM-01](../mang/llm.md#llm-01) Gọi LLM API và prompt engineering — ● Cốt lõi
21. [LLM-02](../mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra — ● Cốt lõi
22. [DL-05](../mang/dl.md#dl-05) Document AI và mô hình thị giác–ngôn ngữ (VLM) — ◐ Cần
23. [LLM-03](../mang/llm.md#llm-03) RAG — trả lời dựa trên tài liệu — ● Cốt lõi
24. [LLM-05](../mang/llm.md#llm-05) Tool calling và điều phối workflow/agent — ◐ Cần
25. [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model — ● Cốt lõi
26. [OPS-02](../mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập — ◐ Cần
27. [OPS-03](../mang/ops.md#ops-03) Pipeline và điều phối tác vụ — ◐ Cần
28. [OPS-04](../mang/ops.md#ops-04) Giám sát model và drift — ◐ Cần
29. [OPS-05](../mang/ops.md#ops-05) Tối ưu suy luận và serving model — ◐ Cần
30. [OPS-06](../mang/ops.md#ops-06) LLMOps — tracing, chi phí, độ trễ — ● Cốt lõi
31. [OPS-08](../mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ — ◐ Cần
32. [LLM-06](../mang/llm.md#llm-06) An toàn và bảo mật hệ LLM — ● Cốt lõi
33. [BIZ-01](../mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) — ◐ Cần
34. [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) — ● Cốt lõi
35. [LLM-04](../mang/llm.md#llm-04) Đánh giá hệ LLM (evals) — ● Cốt lõi
36. [LLM-07](../mang/llm.md#llm-07) Fine-tune, distill và tự host LLM — ◐ Cần
37. [LLM-08](../mang/llm.md#llm-08) Text-to-SQL và hỏi đáp số liệu — ◐ Cần
38. [BIZ-03](../mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) — ● Cốt lõi
39. [BIZ-04](../mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) — ◐ Cần
40. [BIZ-05](../mang/biz.md#biz-05) Kiến thức miền nghiệp vụ — ◐ Cần
41. [EFF-01](../mang/eff.md#eff-01) Đo token và chi phí trên mỗi tác vụ — ● Cốt lõi
42. [EFF-02](../mang/eff.md#eff-02) Prompt caching và tái sử dụng kết quả — ● Cốt lõi
43. [EFF-03](../mang/eff.md#eff-03) Tinh gọn ngữ cảnh đầu vào — ● Cốt lõi
44. [EFF-04](../mang/eff.md#eff-04) Định tuyến và cascade — đúng việc, đúng công cụ — ● Cốt lõi
45. [EFF-05](../mang/eff.md#eff-05) Kiểm soát đầu ra và mức suy luận — ● Cốt lõi
46. [EFF-06](../mang/eff.md#eff-06) Xử lý theo lô và bất đồng bộ — ◐ Cần
47. [EFF-07](../mang/eff.md#eff-07) Kiểm chứng xác định và "không lỗi im lặng" — ● Cốt lõi

## Tổ hợp có nhóm này

- [CMB-03 · Trợ lý nội bộ có RAG và thao tác được](../to-hop-ky-nang.md#cmb-03) — Truy xuất tài liệu/quy trình có trích dẫn (Nhóm 6) → thực hiện thao tác trên CRM/ERP theo quy trình (Nhóm 7)
- [CMB-04 · Phát hiện rồi giải thích (cảnh báo gian lận cho điều tra viên)](../to-hop-ky-nang.md#cmb-04) — Chấm điểm bất thường (Nhóm 3) → LLM tóm tắt bằng chứng cho từng cảnh báo (Nhóm 6) → hàng đợi xử lý + ghi nhận phản hồi (Nhóm 7)
- [CMB-07 · Tổng đài thông minh](../to-hop-ky-nang.md#cmb-07) — Ghi âm → ASR → phân loại/tóm tắt (Nhóm 6) → chuyển ticket (Nhóm 7); lưu lượng lịch sử → dự báo cuộc gọi (Nhóm 2) → xếp ca (Nhóm 8)
- [CMB-08 · Phân loại lai ML + LLM (cascade tiết kiệm token)](../to-hop-ky-nang.md#cmb-08) — Luật → model nhỏ (TF-IDF/PhoBERT, kỹ năng Nhóm 1) xử lý ca dễ có độ tin cậy cao → LLM xử lý ca khó (Nhóm 6) → người xử lý ca vẫn nghi ngờ
- [CMB-09 · Hỏi số liệu bằng tiếng Việt (text-to-SQL agent)](../to-hop-ky-nang.md#cmb-09) — Câu hỏi tự nhiên → chọn bảng/metric (schema linking) → sinh và kiểm tra SQL → chạy → diễn giải kết quả (Nhóm 6 + 7)
