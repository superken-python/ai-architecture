<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# Ma trận kỹ năng × nhóm bài toán

Chú giải: ● Cốt lõi · ◐ Cần · ○ Ít · ô trống = không liên quan. Tầng được tính tự động từ mức sử dụng (xem [README](README.md)).

## PY · Lập trình nền tảng

Python, Git, môi trường, kiểm thử, gọi API bền vững — nền móng cho mọi nhóm.

| Kỹ năng | Tầng | 1·Bảng | 2·Thời gian | 3·Bất thường | 4·Gợi ý | 5·Ảnh/TL | 6·LLM/RAG | 7·Agent | 8·Tối ưu |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| [PY-01](mang/py.md#py-01) Python cho dữ liệu và AI | Nền tảng chung | ● | ● | ● | ● | ● | ● | ● | ● |
| [PY-02](mang/py.md#py-02) Git, môi trường và cấu trúc dự án | Nền tảng chung | ● | ● | ● | ● | ● | ● | ● | ● |
| [PY-03](mang/py.md#py-03) Kiểm thử và chất lượng code | Nền tảng chung | ◐ | ◐ | ◐ | ◐ | ◐ | ● | ● | ◐ |
| [PY-04](mang/py.md#py-04) Gọi API và I/O đồng thời bền vững | Cầu nối liên họ | ○ | ○ | ◐ | ○ | ◐ | ● | ● | ○ |

## DATA · SQL & dữ liệu

Truy vấn, xử lý, kiểm định dữ liệu và làm đặc trưng; đúng thời điểm, không rò rỉ.

| Kỹ năng | Tầng | 1·Bảng | 2·Thời gian | 3·Bất thường | 4·Gợi ý | 5·Ảnh/TL | 6·LLM/RAG | 7·Agent | 8·Tối ưu |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| [DATA-01](mang/data.md#data-01) SQL phân tích | Cầu nối liên họ | ● | ● | ● | ● | ○ | ◐ | ◐ | ◐ |
| [DATA-02](mang/data.md#data-02) Xử lý dữ liệu bảng | Dùng chung trong họ | ● | ● | ● | ● | ○ | ○ | ○ | ◐ |
| [DATA-03](mang/data.md#data-03) Đúng thời điểm và chống rò rỉ dữ liệu | Dùng chung trong họ | ● | ● | ● | ● |  |  |  | ◐ |
| [DATA-04](mang/data.md#data-04) Feature engineering cho bảng và chuỗi thời gian | Dùng chung trong họ | ● | ● | ● | ● |  |  |  | ◐ |
| [DATA-05](mang/data.md#data-05) Kiểm định chất lượng dữ liệu và nhãn | Nền tảng chung | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ |
| [DATA-06](mang/data.md#data-06) Văn bản tiếng Việt và dữ liệu phi cấu trúc | Dùng chung trong họ |  |  |  |  | ◐ | ◐ | ○ |  |
| [DATA-07](mang/data.md#data-07) Dữ liệu đồ thị | Chuyên biệt |  |  | ◐ | ○ |  |  |  | ○ |

## STAT · Thống kê & thực nghiệm

Đo lường bất định, thí nghiệm, calibration, nhân quả — để kết luận đúng.

| Kỹ năng | Tầng | 1·Bảng | 2·Thời gian | 3·Bất thường | 4·Gợi ý | 5·Ảnh/TL | 6·LLM/RAG | 7·Agent | 8·Tối ưu |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| [STAT-01](mang/stat.md#stat-01) Xác suất và thống kê mô tả | Nền tảng chung | ● | ● | ● | ◐ | ◐ | ◐ | ◐ | ● |
| [STAT-02](mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá | Nền tảng chung | ● | ● | ● | ◐ | ◐ | ● | ◐ | ● |
| [STAT-03](mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test | Cầu nối liên họ | ◐ | ○ | ○ | ● |  | ◐ | ○ | ● |
| [STAT-04](mang/stat.md#stat-04) Dự báo xác suất và định lượng bất định | Dùng chung trong họ | ○ | ● | ○ |  |  |  |  | ● |
| [STAT-05](mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc | Cầu nối liên họ | ● |  | ● | ○ | ◐ | ◐ | ◐ | ◐ |
| [STAT-06](mang/stat.md#stat-06) Suy luận nhân quả và uplift | Dùng chung trong họ | ○ |  |  | ◐ |  |  |  | ● |

## ML · ML cổ điển

Học có giám sát, boosting, bất thường, chuỗi thời gian, truy xuất & xếp hạng.

| Kỹ năng | Tầng | 1·Bảng | 2·Thời gian | 3·Bất thường | 4·Gợi ý | 5·Ảnh/TL | 6·LLM/RAG | 7·Agent | 8·Tối ưu |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| [ML-01](mang/ml.md#ml-01) Quy trình học có giám sát chuẩn | Cầu nối liên họ | ● | ● | ● | ● | ○ | ◐ | ○ | ◐ |
| [ML-02](mang/ml.md#ml-02) Gradient boosting | Dùng chung trong họ | ● | ● | ◐ | ● |  |  |  | ◐ |
| [ML-03](mang/ml.md#ml-03) Dữ liệu mất cân bằng và sự kiện hiếm | Cầu nối liên họ | ● |  | ● | ○ | ◐ |  |  |  |
| [ML-04](mang/ml.md#ml-04) Giải thích mô hình | Cầu nối liên họ | ● |  | ◐ | ○ | ◐ | ○ |  | ◐ |
| [ML-05](mang/ml.md#ml-05) Học không giám sát và phát hiện bất thường | Dùng chung trong họ | ○ | ○ | ● | ◐ |  |  |  |  |
| [ML-06](mang/ml.md#ml-06) Mô hình chuỗi thời gian | Dùng chung trong họ |  | ● | ◐ |  |  |  |  | ◐ |
| [ML-07](mang/ml.md#ml-07) Truy xuất và xếp hạng hai tầng (retrieve → rerank) | Cầu nối liên họ |  |  |  | ● | ◐ | ● | ◐ |  |
| [ML-08](mang/ml.md#ml-08) Hệ gợi ý chuyên biệt | Chuyên biệt |  |  |  | ● |  |  |  |  |

## DL · Deep learning

PyTorch, transfer learning, embedding, thị giác máy tính, Document AI, giọng nói.

| Kỹ năng | Tầng | 1·Bảng | 2·Thời gian | 3·Bất thường | 4·Gợi ý | 5·Ảnh/TL | 6·LLM/RAG | 7·Agent | 8·Tối ưu |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| [DL-01](mang/dl.md#dl-01) PyTorch nền tảng | Cầu nối liên họ | ○ | ◐ | ◐ | ◐ | ● | ◐ | ○ | ○ |
| [DL-02](mang/dl.md#dl-02) Transfer learning và fine-tune mô hình pretrained | Dùng chung trong họ |  |  | ○ | ○ | ● | ◐ |  |  |
| [DL-03](mang/dl.md#dl-03) Embedding và học biểu diễn | Cầu nối liên họ |  |  | ◐ | ◐ | ◐ | ◐ | ○ |  |
| [DL-04](mang/dl.md#dl-04) Thị giác máy tính (detection, segmentation, OCR) | Chuyên biệt |  |  |  |  | ● |  |  |  |
| [DL-05](mang/dl.md#dl-05) Document AI và mô hình thị giác–ngôn ngữ (VLM) | Dùng chung trong họ |  |  |  |  | ● | ◐ | ◐ |  |
| [DL-06](mang/dl.md#dl-06) Xử lý giọng nói (ASR) | Chuyên biệt |  |  |  |  |  | ◐ |  |  |

## LLM · LLM, RAG & Agent

Gọi LLM, structured output, RAG, đánh giá, tool calling, bảo mật, fine-tune.

| Kỹ năng | Tầng | 1·Bảng | 2·Thời gian | 3·Bất thường | 4·Gợi ý | 5·Ảnh/TL | 6·LLM/RAG | 7·Agent | 8·Tối ưu |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| [LLM-01](mang/llm.md#llm-01) Gọi LLM API và prompt engineering | Dùng chung trong họ | ○ | ○ | ○ | ○ | ◐ | ● | ● | ○ |
| [LLM-02](mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra | Dùng chung trong họ |  |  |  |  | ● | ● | ● |  |
| [LLM-03](mang/llm.md#llm-03) RAG — trả lời dựa trên tài liệu | Dùng chung trong họ |  |  |  |  |  | ● | ◐ |  |
| [LLM-04](mang/llm.md#llm-04) Đánh giá hệ LLM (evals) | Dùng chung trong họ |  |  |  |  | ◐ | ● | ● |  |
| [LLM-05](mang/llm.md#llm-05) Tool calling và điều phối workflow/agent | Dùng chung trong họ |  |  |  |  |  | ◐ | ● |  |
| [LLM-06](mang/llm.md#llm-06) An toàn và bảo mật hệ LLM | Dùng chung trong họ |  |  |  |  | ◐ | ● | ● |  |
| [LLM-07](mang/llm.md#llm-07) Fine-tune, distill và tự host LLM | Dùng chung trong họ |  |  |  |  | ◐ | ◐ | ○ |  |
| [LLM-08](mang/llm.md#llm-08) Text-to-SQL và hỏi đáp số liệu | Dùng chung trong họ |  |  |  |  |  | ◐ | ◐ |  |

## OPT · Tối ưu hóa (OR)

LP/MIP, định tuyến, lập lịch, quyết định dưới bất định, bandit.

| Kỹ năng | Tầng | 1·Bảng | 2·Thời gian | 3·Bất thường | 4·Gợi ý | 5·Ảnh/TL | 6·LLM/RAG | 7·Agent | 8·Tối ưu |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| [OPT-01](mang/opt.md#opt-01) Quy hoạch tuyến tính và nguyên (LP/MIP) | Dùng chung trong họ |  | ◐ |  |  |  |  |  | ● |
| [OPT-02](mang/opt.md#opt-02) Tối ưu tổ hợp — định tuyến và lập lịch | Chuyên biệt |  |  |  |  |  |  |  | ● |
| [OPT-03](mang/opt.md#opt-03) Ra quyết định dưới bất định (dự báo rồi tối ưu) | Dùng chung trong họ |  | ◐ |  |  |  |  |  | ● |
| [OPT-04](mang/opt.md#opt-04) Bandit và học tăng cường cơ bản | Dùng chung trong họ |  |  |  | ◐ |  |  |  | ◐ |

## OPS · Triển khai & MLOps

Đóng gói, theo dõi thực nghiệm, pipeline, giám sát, serving, LLMOps, bảo mật dữ liệu.

| Kỹ năng | Tầng | 1·Bảng | 2·Thời gian | 3·Bất thường | 4·Gợi ý | 5·Ảnh/TL | 6·LLM/RAG | 7·Agent | 8·Tối ưu |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| [OPS-01](mang/ops.md#ops-01) Đóng gói và phục vụ model | Nền tảng chung | ◐ | ◐ | ● | ● | ● | ● | ● | ◐ |
| [OPS-02](mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập | Nền tảng chung | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ |
| [OPS-03](mang/ops.md#ops-03) Pipeline và điều phối tác vụ | Cầu nối liên họ | ◐ | ◐ | ◐ | ◐ |  | ◐ |  | ○ |
| [OPS-04](mang/ops.md#ops-04) Giám sát model và drift | Cầu nối liên họ | ◐ | ◐ | ● | ● | ◐ | ◐ |  | ◐ |
| [OPS-05](mang/ops.md#ops-05) Tối ưu suy luận và serving model | Cầu nối liên họ |  |  | ◐ | ◐ | ● | ◐ |  |  |
| [OPS-06](mang/ops.md#ops-06) LLMOps — tracing, chi phí, độ trễ | Dùng chung trong họ |  |  |  |  | ◐ | ● | ● |  |
| [OPS-07](mang/ops.md#ops-07) Real-time và streaming | Dùng chung trong họ |  |  | ◐ | ◐ |  |  |  |  |
| [OPS-08](mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ | Cầu nối liên họ | ◐ | ○ | ◐ | ○ | ◐ | ◐ | ● | ○ |

## BIZ · Nghiệp vụ & phương pháp

Framing, baseline & bộ đánh giá, phân tích lỗi, trình bày — quy trình ĐÚNG → NHANH → CHÍNH XÁC → THUYẾT PHỤC.

| Kỹ năng | Tầng | 1·Bảng | 2·Thời gian | 3·Bất thường | 4·Gợi ý | 5·Ảnh/TL | 6·LLM/RAG | 7·Agent | 8·Tối ưu |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| [BIZ-01](mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) | Nền tảng chung | ● | ● | ● | ◐ | ◐ | ◐ | ● | ● |
| [BIZ-02](mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) | Nền tảng chung | ● | ● | ● | ● | ● | ● | ● | ● |
| [BIZ-03](mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) | Nền tảng chung | ● | ● | ● | ● | ● | ● | ● | ● |
| [BIZ-04](mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) | Nền tảng chung | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ |
| [BIZ-05](mang/biz.md#biz-05) Kiến thức miền nghiệp vụ | Nền tảng chung | ● | ● | ● | ◐ | ◐ | ◐ | ● | ● |
| [BIZ-06](mang/biz.md#biz-06) Đọc và tái hiện paper | Bổ trợ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ |

## EFF · Tiết kiệm token & độ tin cậy

Giảm token/chi phí mà không đánh đổi độ chính xác — đo, cache, tinh gọn, định tuyến, kiểm chứng.

| Kỹ năng | Tầng | 1·Bảng | 2·Thời gian | 3·Bất thường | 4·Gợi ý | 5·Ảnh/TL | 6·LLM/RAG | 7·Agent | 8·Tối ưu |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| [EFF-01](mang/eff.md#eff-01) Đo token và chi phí trên mỗi tác vụ | Dùng chung trong họ |  |  |  |  | ◐ | ● | ● |  |
| [EFF-02](mang/eff.md#eff-02) Prompt caching và tái sử dụng kết quả | Dùng chung trong họ |  |  |  |  | ◐ | ● | ● |  |
| [EFF-03](mang/eff.md#eff-03) Tinh gọn ngữ cảnh đầu vào | Dùng chung trong họ |  |  |  |  | ◐ | ● | ● |  |
| [EFF-04](mang/eff.md#eff-04) Định tuyến và cascade — đúng việc, đúng công cụ | Dùng chung trong họ | ○ |  |  |  | ◐ | ● | ● |  |
| [EFF-05](mang/eff.md#eff-05) Kiểm soát đầu ra và mức suy luận | Dùng chung trong họ |  |  |  |  | ◐ | ● | ● |  |
| [EFF-06](mang/eff.md#eff-06) Xử lý theo lô và bất đồng bộ | Dùng chung trong họ | ○ | ○ | ○ | ○ | ◐ | ◐ | ○ |  |
| [EFF-07](mang/eff.md#eff-07) Kiểm chứng xác định và "không lỗi im lặng" | Dùng chung trong họ | ○ |  |  |  | ● | ● | ● |  |
| [EFF-08](mang/eff.md#eff-08) Tiết kiệm token khi dùng AI hỗ trợ lập trình | Bổ trợ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ |

<a id="chia-se"></a>

## Mức chia sẻ kỹ năng giữa các nhóm

Số kỹ năng ở mức Cốt lõi/Cần cho **cả hai** nhóm. Đường chéo = tổng số kỹ năng Cốt lõi/Cần của nhóm đó. Ô càng lớn, càng tận dụng được kỹ năng khi chuyển giữa hai nhóm.

| | 1·Bảng | 2·Thời gian | 3·Bất thường | 4·Gợi ý | 5·Ảnh/TL | 6·LLM/RAG | 7·Agent | 8·Tối ưu |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| **1·Bảng** | 26 | 21 | 25 | 22 | 18 | 20 | 16 | 23 |
| **2·Thời gian** | 21 | 26 | 23 | 22 | 15 | 18 | 14 | 24 |
| **3·Bất thường** | 25 | 23 | 33 | 26 | 22 | 23 | 17 | 23 |
| **4·Gợi ý** | 22 | 22 | 26 | 31 | 18 | 22 | 15 | 23 |
| **5·Ảnh/TL** | 18 | 15 | 22 | 18 | 40 | 37 | 29 | 16 |
| **6·LLM/RAG** | 20 | 18 | 23 | 22 | 37 | 45 | 33 | 18 |
| **7·Agent** | 16 | 14 | 17 | 15 | 29 | 33 | 33 | 15 |
| **8·Tối ưu** | 23 | 24 | 23 | 23 | 16 | 18 | 15 | 30 |

Trung bình số kỹ năng chung của một cặp nhóm (trong đó 13 kỹ năng nền tảng chung luôn có mặt ở mọi cặp):

| Cặp nhóm | Số cặp | Trung bình | Thấp nhất – cao nhất | Ngoài nền tảng chung |
|---|--:|--:|--:|--:|
| Cùng họ: Họ dữ liệu có cấu trúc & quyết định | 10 | 23.2 | 21 – 26 | 10.2 |
| Cùng họ: Họ dữ liệu phi cấu trúc & GenAI | 3 | 33.0 | 29 – 37 | 20.0 |
| Khác họ | 15 | 17.8 | 14 – 23 | 4.8 |

<a id="doi-chieu-giai-doan-1"></a>

## Đối chiếu với ma trận giai đoạn 1 (theo mảng)

Mỗi ô: mức cao nhất trong các kỹ năng của mảng / mức ở ma trận giai đoạn 1. Bộ kiểm tra bảo đảm mọi ô Cốt lõi của giai đoạn 1 đều có ít nhất một kỹ năng Cốt lõi.

| Mảng | 1·Bảng | 2·Thời gian | 3·Bất thường | 4·Gợi ý | 5·Ảnh/TL | 6·LLM/RAG | 7·Agent | 8·Tối ưu |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| PY · Lập trình nền tảng | ● / — | ● / — | ● / — | ● / — | ● / — | ● / — | ● / — | ● / — |
| DATA · SQL & dữ liệu | ● / ● | ● / ● | ● / ● | ● / ● | ◐ / ○ | ◐ / ◐ | ◐ / ◐ | ◐ / ◐ |
| STAT · Thống kê & thực nghiệm | ● / ● | ● / ● | ● / ● | ● / ◐ | ◐ / ○ | ● / ◐ | ◐ / ○ | ● / ● |
| ML · ML cổ điển | ● / ● | ● / ● | ● / ● | ● / ● | ◐ / ○ | ● / ○ | ◐ / ○ | ◐ / ◐ |
| DL · Deep learning | ○ / ○ | ◐ / ◐ | ◐ / ◐ | ◐ / ◐ | ● / ● | ◐ / ◐ | ◐ / ○ | ○ / ○ |
| LLM · LLM, RAG & Agent | ○ / ○ | ○ / ○ | ○ / ○ | ○ / ○ | ● / ◐ | ● / ● | ● / ● | ○ / ○ |
| OPT · Tối ưu hóa (OR) | · / ○ | ◐ / ◐ | · / ○ | ◐ / ○ | · / ○ | · / ○ | · / ○ | ● / ● |
| OPS · Triển khai & MLOps | ◐ / ◐ | ◐ / ◐ | ● / ● | ● / ● | ● / ● | ● / ● | ● / ● | ◐ / ◐ |
| BIZ · Nghiệp vụ & phương pháp | ● / ● | ● / ● | ● / ● | ● / ◐ | ● / ◐ | ● / ◐ | ● / ● | ● / ● |
| EFF · Tiết kiệm token & độ tin cậy | ○ / — | ○ / — | ○ / — | ○ / — | ● / — | ● / — | ● / — | ○ / — |

Ký hiệu “—”: mảng mới bổ sung ở giai đoạn 2, không có trong ma trận giai đoạn 1.
