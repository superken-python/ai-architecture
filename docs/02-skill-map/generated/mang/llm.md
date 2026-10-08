<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# LLM · LLM, RAG & Agent

Gọi LLM, structured output, RAG, đánh giá, tool calling, bảo mật, fine-tune.

| Kỹ năng | Tầng | Tóm tắt |
|---|---|---|
| [LLM-01](#llm-01) Gọi LLM API và prompt engineering | Dùng chung trong họ | Viết prompt rõ ràng, có cấu trúc, quản lý như code. |
| [LLM-02](#llm-02) Structured output và kiểm chứng đầu ra | Dùng chung trong họ | Ép LLM trả về dữ liệu có cấu trúc hợp lệ, kiểm tra được bằng code. |
| [LLM-03](#llm-03) RAG — trả lời dựa trên tài liệu | Dùng chung trong họ | Trả lời có trích dẫn từ tài liệu nội bộ, biết nói "không tìm thấy". |
| [LLM-04](#llm-04) Đánh giá hệ LLM (evals) | Dùng chung trong họ | Đo chất lượng hệ LLM bằng số liệu thay vì cảm giác, trước và sau mọi thay đổi. |
| [LLM-05](#llm-05) Tool calling và điều phối workflow/agent | Dùng chung trong họ | Để LLM gọi công cụ, chạy chuỗi bước có trạng thái, có người duyệt ở bước rủi ro. |
| [LLM-06](#llm-06) An toàn và bảo mật hệ LLM | Dùng chung trong họ | Chặn rò rỉ dữ liệu, prompt injection và hành động vượt quyền. |
| [LLM-07](#llm-07) Fine-tune, distill và tự host LLM | Dùng chung trong họ | Làm model riêng rẻ hơn/nhanh hơn cho tác vụ hẹp, lưu lượng lớn. |
| [LLM-08](#llm-08) Text-to-SQL và hỏi đáp số liệu | Dùng chung trong họ | Cho người dùng hỏi số liệu bằng tiếng Việt mà kết quả vẫn đúng tuyệt đối. |

<a id="llm-01"></a>

### LLM-01 · Gọi LLM API và prompt engineering

> Viết prompt rõ ràng, có cấu trúc, quản lý như code.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 5  
**Dùng cho:** ● Cốt lõi: Nhóm 6 LLM/RAG · ● Cốt lõi: Nhóm 7 Agent · ◐ Cần: Nhóm 5 Ảnh/TL · ○ Ít: Nhóm 1 Bảng · ○ Ít: Nhóm 2 Thời gian · ○ Ít: Nhóm 3 Bất thường · ○ Ít: Nhóm 4 Gợi ý · ○ Ít: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | Cấu trúc messages/system prompt, ví dụ mẫu (few-shot), chỉ dẫn rõ có tiêu chí, max_tokens; prompt lưu trong file có version. |
| Trung cấp | Tách tác vụ thành chuỗi bước (prompt chaining), ngữ cảnh có cấu trúc (thẻ XML/markdown), cho phép trả lời "không biết", chọn model theo độ khó. |
| Nâng cao | Tối ưu prompt có hệ thống trên golden set, prompt cho tiếng Việt và đa ngôn ngữ, review/A-B/rollback prompt như code. |

- **Tiên quyết:** [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI
- **Mở khóa:** [LLM-02](../mang/llm.md#llm-02), [LLM-06](../mang/llm.md#llm-06), [OPS-06](../mang/ops.md#ops-06), [EFF-01](../mang/eff.md#eff-01)
- **Công cụ:** LLM API (Anthropic, OpenAI, Gemini…), Jinja2
- **Đạt khi:** Mọi prompt nằm trong repo, có version, có golden set đi kèm và lịch sử thay đổi có số liệu.
- **Trong lộ trình:** Bước B1 · Gọi LLM, structured output và gọi API bền vững (Cơ bản) · Thanh ngang chữ T · Nhóm 6 (Cơ bản) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="llm-02"></a>

### LLM-02 · Structured output và kiểm chứng đầu ra

> Ép LLM trả về dữ liệu có cấu trúc hợp lệ, kiểm tra được bằng code.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 6  
**Dùng cho:** ● Cốt lõi: Nhóm 5 Ảnh/TL · ● Cốt lõi: Nhóm 6 LLM/RAG · ● Cốt lõi: Nhóm 7 Agent

| Mức | Làm được |
|---|---|
| Cơ bản | Yêu cầu JSON theo schema, validate bằng pydantic, dùng enum cho nhãn thay vì văn bản tự do. |
| Trung cấp | Structured outputs/strict tool schema của nhà cung cấp, retry kèm thông báo lỗi validation, kiểm tra ràng buộc nghiệp vụ giữa các trường. |
| Nâng cao | Constrained decoding cho model tự host, thiết kế schema tối giản, theo dõi tỷ lệ output hợp lệ và tỷ lệ retry như metric production. |

- **Tiên quyết:** [LLM-01](../mang/llm.md#llm-01) Gọi LLM API và prompt engineering
- **Mở khóa:** [DL-05](../mang/dl.md#dl-05), [LLM-03](../mang/llm.md#llm-03), [LLM-04](../mang/llm.md#llm-04), [LLM-05](../mang/llm.md#llm-05), [LLM-08](../mang/llm.md#llm-08), [EFF-05](../mang/eff.md#eff-05), [EFF-07](../mang/eff.md#eff-07)
- **Công cụ:** pydantic, JSON Schema, instructor, outlines
- **Đạt khi:** 100% output đi vào hệ thống phía sau đều qua validate; ca không hợp lệ được retry hoặc chuyển người, không bao giờ lọt.
- **Token & độ chính xác:** Output ngắn theo schema (mã nhãn, enum) rẻ hơn văn xuôi nhiều lần và kiểm tra được tự động.
- **Trong lộ trình:** Bước B1 · Gọi LLM, structured output và gọi API bền vững (Trung cấp) · Thanh ngang chữ T · Nhóm 6 (Cơ bản) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="llm-03"></a>

### LLM-03 · RAG — trả lời dựa trên tài liệu

> Trả lời có trích dẫn từ tài liệu nội bộ, biết nói "không tìm thấy".

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 3  
**Dùng cho:** ● Cốt lõi: Nhóm 6 LLM/RAG · ◐ Cần: Nhóm 7 Agent

| Mức | Làm được |
|---|---|
| Cơ bản | parse → chunk → embedding → vector store → trả lời có trích dẫn; trả lời "không tìm thấy" khi không có căn cứ. |
| Trung cấp | Chunk theo cấu trúc (mục, bảng), hybrid search + rerank, metadata/lọc, đánh giá tách riêng retrieval (recall@k) và generation (faithfulness). |
| Nâng cao | Phân quyền tài liệu theo người dùng, cập nhật chỉ mục tăng dần, viết lại/tách câu hỏi, kết hợp text-to-SQL cho số liệu, GraphRAG khi thật sự cần. |

- **Tiên quyết:** [LLM-02](../mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra, [ML-07](../mang/ml.md#ml-07) Truy xuất và xếp hạng hai tầng (retrieve → rerank), [DATA-06](../mang/data.md#data-06) Văn bản tiếng Việt và dữ liệu phi cấu trúc
- **Mở khóa:** —
- **Công cụ:** Qdrant, pgvector, BM25, cross-encoder reranker, Docling
- **Đạt khi:** Golden set ~100 câu tiếng Việt có recall@k, faithfulness và độ đúng được đo; mọi câu trả lời có nguồn kiểm tra được.
- **Token & độ chính xác:** Top-k nhỏ + rerank thay vì nhồi cả tài liệu; chunk sạch giảm token mà còn tăng độ chính xác.
- **Trong lộ trình:** Bước B4 · RAG có trích dẫn (Trung cấp) · Thanh ngang chữ T · Nhóm 6 (Cơ bản) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="llm-04"></a>

### LLM-04 · Đánh giá hệ LLM (evals)

> Đo chất lượng hệ LLM bằng số liệu thay vì cảm giác, trước và sau mọi thay đổi.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 5  
**Dùng cho:** ● Cốt lõi: Nhóm 6 LLM/RAG · ● Cốt lõi: Nhóm 7 Agent · ◐ Cần: Nhóm 5 Ảnh/TL

| Mức | Làm được |
|---|---|
| Cơ bản | Golden set từ dữ liệu thật (≥100 mẫu có đáp án), chấm tự động bằng so khớp chính xác/so khớp từng trường, đọc thủ công các ca sai. |
| Trung cấp | LLM-as-judge với rubric rõ, đo độ đồng thuận judge–người, bộ hồi quy chạy mỗi khi đổi prompt/model, báo cáo chi phí và độ trễ cùng chất lượng. |
| Nâng cao | Đánh giá trajectory của agent, dữ liệu kiểm thử đối kháng (prompt injection), đánh giá online từ phản hồi người dùng. |

- **Tiên quyết:** [LLM-02](../mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra, [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá, [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH)
- **Mở khóa:** [LLM-07](../mang/llm.md#llm-07), [LLM-08](../mang/llm.md#llm-08), [EFF-04](../mang/eff.md#eff-04)
- **Công cụ:** pytest, Langfuse, promptfoo, Inspect
- **Đạt khi:** Một lệnh `make eval` in ra chất lượng + chi phí + độ trễ, so với baseline, kèm khoảng tin cậy.
- **Token & độ chính xác:** Không có eval thì không thể tối ưu token an toàn — mọi cắt giảm phải qua cổng eval.
- **Trong lộ trình:** Bước B2 · Đo chi phí, tracing và golden set đầu tiên (Cơ bản) · Bước B5 · Đánh giá nghiêm túc và lớp kiểm chứng (Trung cấp) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="llm-05"></a>

### LLM-05 · Tool calling và điều phối workflow/agent

> Để LLM gọi công cụ, chạy chuỗi bước có trạng thái, có người duyệt ở bước rủi ro.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 3  
**Dùng cho:** ● Cốt lõi: Nhóm 7 Agent · ◐ Cần: Nhóm 6 LLM/RAG

| Mức | Làm được |
|---|---|
| Cơ bản | Định nghĩa tool bằng JSON schema, vòng lặp gọi tool, workflow cố định (chuỗi bước LLM xen code), người duyệt ở bước rủi ro. |
| Trung cấp | Các mẫu workflow (chaining, routing, song song, orchestrator–workers, evaluator–optimizer), quản lý state (LangGraph hoặc agent SDK), MCP, xử lý lỗi/timeout của tool, tracing. |
| Nâng cao | Agent tự chủ có ngân sách bước/token, quản lý ngữ cảnh dài (nén, bộ nhớ ngoài), multi-agent, computer-use; thiết kế bộ tool "ít mà đủ". |

- **Tiên quyết:** [LLM-02](../mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra, [PY-04](../mang/py.md#py-04) Gọi API và I/O đồng thời bền vững
- **Mở khóa:** —
- **Công cụ:** LangGraph, agent SDK của các hãng, MCP, Langfuse
- **Đạt khi:** Agent báo giá chạy end-to-end, mọi hành động có log, bước gửi email luôn chờ người duyệt.
- **Token & độ chính xác:** Workflow cố định rẻ và dễ kiểm chứng hơn agent tự chủ; ít tool, mô tả tool ngắn gọn giảm token mỗi lượt.
- **Trong lộ trình:** Bước B7 · Tool calling, workflow và bảo mật LLM (Cơ bản) · Hướng LLM ứng dụng & Agent (Trung cấp) · Thanh ngang chữ T · Nhóm 7 (Cơ bản) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="llm-06"></a>

### LLM-06 · An toàn và bảo mật hệ LLM

> Chặn rò rỉ dữ liệu, prompt injection và hành động vượt quyền.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 5  
**Dùng cho:** ● Cốt lõi: Nhóm 6 LLM/RAG · ● Cốt lõi: Nhóm 7 Agent · ◐ Cần: Nhóm 5 Ảnh/TL

| Mức | Làm được |
|---|---|
| Cơ bản | Không đưa secret vào prompt, che PII trước khi gửi API bên ngoài, giới hạn phạm vi trả lời. |
| Trung cấp | Phòng prompt injection (tách dữ liệu và chỉ dẫn, không tin nội dung tài liệu/email), guardrails đầu vào/đầu ra, phân quyền tài liệu trong RAG, audit log. |
| Nâng cao | Quyền tối thiểu cho agent, sandbox cho tool nguy hiểm, red-teaming định kỳ, đáp ứng yêu cầu bảo vệ dữ liệu cá nhân. |

- **Tiên quyết:** [LLM-01](../mang/llm.md#llm-01) Gọi LLM API và prompt engineering, [OPS-08](../mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ
- **Mở khóa:** —
- **Công cụ:** Presidio, guardrails, sandbox container
- **Đạt khi:** Bộ test prompt injection nằm trong eval; agent không thể thực hiện hành động ngoài danh sách cho phép.
- **Trong lộ trình:** Bước B7 · Tool calling, workflow và bảo mật LLM (Cơ bản) · Hướng LLM ứng dụng & Agent (Trung cấp) · Bước D4 · Bảo mật, quyền và tuân thủ (Nâng cao) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="llm-07"></a>

### LLM-07 · Fine-tune, distill và tự host LLM

> Làm model riêng rẻ hơn/nhanh hơn cho tác vụ hẹp, lưu lượng lớn.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 2  
**Dùng cho:** ◐ Cần: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 6 LLM/RAG · ○ Ít: Nhóm 7 Agent

| Mức | Làm được |
|---|---|
| Cơ bản | Biết khi nào KHÔNG cần fine-tune (prompt + RAG trước); chuẩn bị dữ liệu instruction sạch. |
| Trung cấp | SFT với LoRA/QLoRA trên model open-weight nhỏ, đánh giá trước/sau trên golden set, tự host bằng vLLM. |
| Nâng cao | DPO/preference tuning, distill từ model lớn sang model nhỏ, quantization (AWQ/GPTQ), tính tổng chi phí GPU so với API. |

- **Tiên quyết:** [LLM-04](../mang/llm.md#llm-04) Đánh giá hệ LLM (evals), [DL-02](../mang/dl.md#dl-02) Transfer learning và fine-tune mô hình pretrained
- **Mở khóa:** —
- **Công cụ:** PEFT, TRL, Unsloth, vLLM
- **Đạt khi:** Model distill đạt chất lượng trong biên sai số của model lớn trên golden set, với chi phí mỗi request thấp hơn rõ rệt.
- **Token & độ chính xác:** Đòn bẩy chi phí mạnh nhất khi lưu lượng lớn và tác vụ ổn định — nhưng chỉ sau khi đã có eval vững.
- **Trong lộ trình:** Hướng Document AI (Cơ bản) · Bước D3 · Chi phí và độ tin cậy của hệ LLM ở quy mô (Trung cấp) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="llm-08"></a>

### LLM-08 · Text-to-SQL và hỏi đáp số liệu

> Cho người dùng hỏi số liệu bằng tiếng Việt mà kết quả vẫn đúng tuyệt đối.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 2  
**Dùng cho:** ◐ Cần: Nhóm 6 LLM/RAG · ◐ Cần: Nhóm 7 Agent

| Mức | Làm được |
|---|---|
| Cơ bản | Đưa schema + mô tả cột + ví dụ vào prompt, sinh SQL chỉ đọc, chạy trên bản sao dữ liệu. |
| Trung cấp | Schema linking (chỉ đưa bảng liên quan), kiểm tra SQL (parse, EXPLAIN, danh sách bảng cho phép), golden set so sánh KẾT QUẢ truy vấn chứ không so chuỗi SQL. |
| Nâng cao | Tầng ngữ nghĩa với metric định nghĩa sẵn để LLM chọn metric thay vì viết SQL tự do, phân quyền hàng/cột, hỏi lại khi câu hỏi mơ hồ. |

- **Tiên quyết:** [DATA-01](../mang/data.md#data-01) SQL phân tích, [LLM-02](../mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra, [LLM-04](../mang/llm.md#llm-04) Đánh giá hệ LLM (evals)
- **Mở khóa:** —
- **Công cụ:** sqlglot, DuckDB, dbt semantic layer
- **Đạt khi:** Trên golden set câu hỏi số liệu, kết quả truy vấn khớp 100% với đáp án ở phần được trả lời tự động; câu mơ hồ được hỏi lại.
- **Token & độ chính xác:** Schema linking giảm mạnh token ngữ cảnh; con số do SQL tính chứ không do LLM tự "nhẩm" → chính xác tuyệt đối.
- **Trong lộ trình:** Hướng LLM ứng dụng & Agent (Trung cấp) — xem [lộ trình theo bước](../lo-trinh.md)
