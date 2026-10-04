<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# OPS · Triển khai & MLOps

Đóng gói, theo dõi thực nghiệm, pipeline, giám sát, serving, LLMOps, bảo mật dữ liệu.

| Kỹ năng | Tầng | Tóm tắt |
|---|---|---|
| [OPS-01](#ops-01) Đóng gói và phục vụ model | Nền tảng chung | Đưa model/hệ LLM thành dịch vụ hoặc job chạy ổn định. |
| [OPS-02](#ops-02) Theo dõi thực nghiệm và tái lập | Nền tảng chung | Biết chính xác model/prompt nào, dữ liệu nào cho ra kết quả nào. |
| [OPS-03](#ops-03) Pipeline và điều phối tác vụ | Cầu nối liên họ | Chạy chuỗi xử lý dữ liệu/huấn luyện/chấm điểm theo lịch, an toàn khi chạy lại. |
| [OPS-04](#ops-04) Giám sát model và drift | Cầu nối liên họ | Phát hiện model xuống cấp trước khi nghiệp vụ phát hiện. |
| [OPS-05](#ops-05) Tối ưu suy luận và serving model | Cầu nối liên họ | Chạy model nhanh, rẻ, kể cả trên thiết bị biên. |
| [OPS-06](#ops-06) LLMOps — tracing, chi phí, độ trễ | Dùng chung trong họ | Nhìn thấy mọi lời gọi LLM: tốn bao nhiêu, chậm ở đâu, sai ở đâu. |
| [OPS-07](#ops-07) Real-time và streaming | Dùng chung trong họ | Chấm điểm sự kiện trong vài chục mili-giây khi nghiệp vụ thật sự cần. |
| [OPS-08](#ops-08) Bảo mật dữ liệu và tuân thủ | Cầu nối liên họ | Xử lý dữ liệu khách hàng đúng quy định, không rò rỉ. |

<a id="ops-01"></a>

### OPS-01 · Đóng gói và phục vụ model

> Đưa model/hệ LLM thành dịch vụ hoặc job chạy ổn định.

**Tầng:** Nền tảng chung · **Điểm đòn bẩy:** 13  
**Dùng cho:** ● Cốt lõi: Nhóm 3 Bất thường · ● Cốt lõi: Nhóm 4 Gợi ý · ● Cốt lõi: Nhóm 5 Ảnh/TL · ● Cốt lõi: Nhóm 6 LLM/RAG · ● Cốt lõi: Nhóm 7 Agent · ◐ Cần: Nhóm 1 Bảng · ◐ Cần: Nhóm 2 Thời gian · ◐ Cần: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | FastAPI + pydantic, Dockerfile, job chấm điểm batch hằng ngày ra bảng/CSV. |
| Trung cấp | Tách cấu hình/secret, health check, version model trong API, xử lý lỗi/timeout, test tải cơ bản. |
| Nâng cao | Autoscaling, canary/blue-green, shadow mode, SLA độ trễ. |

- **Tiên quyết:** [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án
- **Mở khóa:** [OPS-04](../mang/ops.md#ops-04), [OPS-05](../mang/ops.md#ops-05), [OPS-06](../mang/ops.md#ops-06), [OPS-07](../mang/ops.md#ops-07)
- **Công cụ:** FastAPI, Docker, uvicorn
- **Đạt khi:** `docker compose up` là có API chấm điểm chạy được, có health check và version model.

<a id="ops-02"></a>

### OPS-02 · Theo dõi thực nghiệm và tái lập

> Biết chính xác model/prompt nào, dữ liệu nào cho ra kết quả nào.

**Tầng:** Nền tảng chung · **Điểm đòn bẩy:** 8  
**Dùng cho:** ◐ Cần: Nhóm 1 Bảng · ◐ Cần: Nhóm 2 Thời gian · ◐ Cần: Nhóm 3 Bất thường · ◐ Cần: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 6 LLM/RAG · ◐ Cần: Nhóm 7 Agent · ◐ Cần: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | Ghi tham số, phiên bản dữ liệu, metric mỗi lần chạy (MLflow); cố định seed. |
| Trung cấp | Model registry, versioning dữ liệu và prompt, so sánh run, báo cáo tự động. |
| Nâng cao | Huấn luyện lại tự động có cổng kiểm định (chỉ deploy khi tốt hơn champion), lineage dữ liệu–model. |

- **Tiên quyết:** [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án, [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn
- **Mở khóa:** —
- **Công cụ:** MLflow, DVC, Weights & Biases
- **Đạt khi:** Tái tạo lại đúng metric của một thí nghiệm cũ từ registry trong vòng 10 phút.

<a id="ops-03"></a>

### OPS-03 · Pipeline và điều phối tác vụ

> Chạy chuỗi xử lý dữ liệu/huấn luyện/chấm điểm theo lịch, an toàn khi chạy lại.

**Tầng:** Cầu nối liên họ · **Điểm đòn bẩy:** 5  
**Dùng cho:** ◐ Cần: Nhóm 1 Bảng · ◐ Cần: Nhóm 2 Thời gian · ◐ Cần: Nhóm 3 Bất thường · ◐ Cần: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 6 LLM/RAG · ○ Ít: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | Script chạy theo lịch (cron), idempotent, log rõ ràng. |
| Trung cấp | Prefect/Airflow/Dagster, phụ thuộc giữa tác vụ, retry, backfill. |
| Nâng cao | Feature pipeline dùng chung cho train và serve, nền tảng dữ liệu/ML cho nhiều team. |

- **Tiên quyết:** [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án
- **Mở khóa:** —
- **Công cụ:** Prefect, Airflow, Dagster
- **Đạt khi:** Pipeline chạy lại cho một ngày bất kỳ trong quá khứ mà không tạo dữ liệu trùng.

<a id="ops-04"></a>

### OPS-04 · Giám sát model và drift

> Phát hiện model xuống cấp trước khi nghiệp vụ phát hiện.

**Tầng:** Cầu nối liên họ · **Điểm đòn bẩy:** 9  
**Dùng cho:** ● Cốt lõi: Nhóm 3 Bất thường · ● Cốt lõi: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 1 Bảng · ◐ Cần: Nhóm 2 Thời gian · ◐ Cần: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 6 LLM/RAG · ◐ Cần: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | Theo dõi phân phối input/output, số request, tỷ lệ lỗi. |
| Trung cấp | Drift (PSI, KS), hiệu năng khi nhãn về trễ, cảnh báo, dashboard (Evidently). |
| Nâng cao | Phát hiện vòng phản hồi (model ảnh hưởng dữ liệu tương lai), tự kích hoạt huấn luyện lại, giám sát theo phân khúc. |

- **Tiên quyết:** [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model, [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá
- **Mở khóa:** —
- **Công cụ:** Evidently, Prometheus, Grafana
- **Đạt khi:** Dashboard cảnh báo khi phân phối điểm số lệch mạnh so với lúc huấn luyện.

<a id="ops-05"></a>

### OPS-05 · Tối ưu suy luận và serving model

> Chạy model nhanh, rẻ, kể cả trên thiết bị biên.

**Tầng:** Cầu nối liên họ · **Điểm đòn bẩy:** 5  
**Dùng cho:** ● Cốt lõi: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 3 Bất thường · ◐ Cần: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 6 LLM/RAG

| Mức | Làm được |
|---|---|
| Cơ bản | Export ONNX, đo độ trễ/throughput, batch inference. |
| Trung cấp | Quantization int8, ONNX Runtime/TensorRT, tối ưu tiền xử lý, chọn GPU vs CPU theo chi phí. |
| Nâng cao | Triển khai biên (edge/mobile), dynamic batching (Triton, vLLM), distillation để đạt SLA. |

- **Tiên quyết:** [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model, [DL-01](../mang/dl.md#dl-01) PyTorch nền tảng
- **Mở khóa:** —
- **Công cụ:** ONNX Runtime, TensorRT, Triton, vLLM
- **Đạt khi:** Model sau quantization giữ chất lượng trong biên sai số và nhanh hơn đo được.

<a id="ops-06"></a>

### OPS-06 · LLMOps — tracing, chi phí, độ trễ

> Nhìn thấy mọi lời gọi LLM: tốn bao nhiêu, chậm ở đâu, sai ở đâu.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 5  
**Dùng cho:** ● Cốt lõi: Nhóm 6 LLM/RAG · ● Cốt lõi: Nhóm 7 Agent · ◐ Cần: Nhóm 5 Ảnh/TL

| Mức | Làm được |
|---|---|
| Cơ bản | Log mỗi lời gọi (version prompt, model, token vào/ra, chi phí, độ trễ). |
| Trung cấp | Tracing nhiều bước (Langfuse/OpenTelemetry), dashboard chi phí theo tính năng/người dùng, cảnh báo vượt ngân sách, lấy mẫu trace để đánh giá. |
| Nâng cao | Đổi model/nhà cung cấp không downtime, fallback khi lỗi, phân bổ chi phí theo đơn vị nghiệp vụ, SLO cho chất lượng. |

- **Tiên quyết:** [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model, [LLM-01](../mang/llm.md#llm-01) Gọi LLM API và prompt engineering
- **Mở khóa:** —
- **Công cụ:** Langfuse, OpenTelemetry, LiteLLM
- **Đạt khi:** Trả lời được "tháng này tính năng X tốn bao nhiêu, mỗi tác vụ hoàn thành tốn bao nhiêu" trong 1 phút.
- **Token & độ chính xác:** Không đo được thì không tối ưu được — tracing là nguồn dữ liệu cho mọi quyết định cắt giảm token.

<a id="ops-07"></a>

### OPS-07 · Real-time và streaming

> Chấm điểm sự kiện trong vài chục mili-giây khi nghiệp vụ thật sự cần.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 2  
**Dùng cho:** ◐ Cần: Nhóm 3 Bất thường · ◐ Cần: Nhóm 4 Gợi ý

| Mức | Làm được |
|---|---|
| Cơ bản | Phân biệt batch / near-real-time / real-time; biết khi nào thật sự cần real-time. |
| Trung cấp | Kafka/Redpanda, consumer, feature theo cửa sổ thời gian, lưu feature online (Redis). |
| Nâng cao | Chấm điểm dưới 100 ms, đồng nhất feature online/offline, xử lý sự kiện trễ/trùng. |

- **Tiên quyết:** [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model, [DATA-04](../mang/data.md#data-04) Feature engineering cho bảng và chuỗi thời gian
- **Mở khóa:** —
- **Công cụ:** Kafka, Redpanda, Redis, Faust/Bytewax
- **Đạt khi:** Feature tính online và offline cho cùng một giao dịch ra cùng giá trị.

<a id="ops-08"></a>

### OPS-08 · Bảo mật dữ liệu và tuân thủ

> Xử lý dữ liệu khách hàng đúng quy định, không rò rỉ.

**Tầng:** Cầu nối liên họ · **Điểm đòn bẩy:** 6  
**Dùng cho:** ● Cốt lõi: Nhóm 7 Agent · ◐ Cần: Nhóm 1 Bảng · ◐ Cần: Nhóm 3 Bất thường · ◐ Cần: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 6 LLM/RAG · ○ Ít: Nhóm 2 Thời gian · ○ Ít: Nhóm 4 Gợi ý · ○ Ít: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | Quản lý secret (.env, vault), không commit dữ liệu thật, nhận diện dữ liệu cá nhân (PII), ẩn danh hóa khi phân tích. |
| Trung cấp | Phân quyền theo vai trò, audit log, mã hóa khi lưu/truyền, chính sách lưu giữ, đánh giá rủi ro khi gửi dữ liệu ra API bên ngoài. |
| Nâng cao | Đáp ứng quy định bảo vệ dữ liệu cá nhân của Việt Nam (làm việc cùng pháp chế), triển khai on-premise/VPC cho dữ liệu nhạy cảm, đánh giá tác động xử lý dữ liệu. |

- **Tiên quyết:** [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án
- **Mở khóa:** [LLM-06](../mang/llm.md#llm-06)
- **Công cụ:** python-dotenv, HashiCorp Vault, Presidio
- **Đạt khi:** Không có secret/dữ liệu thật trong lịch sử Git; có danh sách dữ liệu nào được phép gửi ra ngoài.
