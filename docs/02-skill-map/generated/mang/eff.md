<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# EFF · Tiết kiệm token & độ tin cậy

Giảm token/chi phí mà không đánh đổi độ chính xác — đo, cache, tinh gọn, định tuyến, kiểm chứng.

| Kỹ năng | Tầng | Tóm tắt |
|---|---|---|
| [EFF-01](#eff-01) Đo token và chi phí trên mỗi tác vụ | Dùng chung trong họ | Biết chính xác mỗi tác vụ hoàn thành tốn bao nhiêu token, tiền và thời gian. |
| [EFF-02](#eff-02) Prompt caching và tái sử dụng kết quả | Dùng chung trong họ | Không trả tiền đầy đủ hai lần cho cùng một phần ngữ cảnh hoặc cùng một câu hỏi. |
| [EFF-03](#eff-03) Tinh gọn ngữ cảnh đầu vào | Dùng chung trong họ | Gửi cho model đúng thứ nó cần — không thiếu (sai) và không thừa (đắt, dễ nhiễu). |
| [EFF-04](#eff-04) Định tuyến và cascade — đúng việc, đúng công cụ | Dùng chung trong họ | Code làm được thì không gọi LLM; model nhỏ làm được thì không gọi model lớn. |
| [EFF-05](#eff-05) Kiểm soát đầu ra và mức suy luận | Dùng chung trong họ | Token đầu ra thường đắt hơn đầu vào nhiều lần — chỉ sinh những gì cần dùng. |
| [EFF-06](#eff-06) Xử lý theo lô và bất đồng bộ | Dùng chung trong họ | Việc không cần trả lời ngay thì chạy theo lô với giá rẻ hơn. |
| [EFF-07](#eff-07) Kiểm chứng xác định và "không lỗi im lặng" | Dùng chung trong họ | Độ chính xác do hệ thống bảo đảm — mọi đầu ra tự động đều qua lớp kiểm chứng bằng code. |
| [EFF-08](#eff-08) Tiết kiệm token khi dùng AI hỗ trợ lập trình | Bổ trợ | Dùng trợ lý lập trình AI hiệu quả — ít token, ít vòng lặp sửa, kết quả kiểm chứng được. |

<a id="eff-01"></a>

### EFF-01 · Đo token và chi phí trên mỗi tác vụ

> Biết chính xác mỗi tác vụ hoàn thành tốn bao nhiêu token, tiền và thời gian.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 5  
**Dùng cho:** ● Cốt lõi: Nhóm 6 LLM/RAG · ● Cốt lõi: Nhóm 7 Agent · ◐ Cần: Nhóm 5 Ảnh/TL

| Mức | Làm được |
|---|---|
| Cơ bản | Đếm token bằng tokenizer/endpoint đếm token của đúng nhà cung cấp (mỗi hãng một tokenizer; tiếng Việt thường tốn nhiều token hơn tiếng Anh — đo, đừng đoán); đọc trường usage trong response. |
| Trung cấp | Chi phí trên mỗi TÁC VỤ HOÀN THÀNH (không phải mỗi request) — tách input thường / input cache / output / retry; bảng chi phí–chất lượng cho từng cấu hình. |
| Nâng cao | Dự báo chi phí theo lưu lượng, ngân sách và cảnh báo theo tính năng, chọn điểm Pareto chất lượng–chi phí–độ trễ. |

- **Tiên quyết:** [LLM-01](../mang/llm.md#llm-01) Gọi LLM API và prompt engineering
- **Mở khóa:** [EFF-02](../mang/eff.md#eff-02), [EFF-03](../mang/eff.md#eff-03), [EFF-04](../mang/eff.md#eff-04), [EFF-05](../mang/eff.md#eff-05), [EFF-06](../mang/eff.md#eff-06)
- **Công cụ:** usage trong response API, endpoint đếm token của nhà cung cấp, Langfuse
- **Đạt khi:** Có bảng baseline "chất lượng / chi phí mỗi tác vụ / độ trễ" trước khi áp dụng bất kỳ tối ưu nào.
- **Trong lộ trình:** Bước B2 · Đo chi phí, tracing và golden set đầu tiên (Cơ bản) · Bước D3 · Chi phí và độ tin cậy của hệ LLM ở quy mô (Nâng cao) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="eff-02"></a>

### EFF-02 · Prompt caching và tái sử dụng kết quả

> Không trả tiền đầy đủ hai lần cho cùng một phần ngữ cảnh hoặc cùng một câu hỏi.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 5  
**Dùng cho:** ● Cốt lõi: Nhóm 6 LLM/RAG · ● Cốt lõi: Nhóm 7 Agent · ◐ Cần: Nhóm 5 Ảnh/TL

| Mức | Làm được |
|---|---|
| Cơ bản | Đặt phần cố định (system prompt, tài liệu, định nghĩa tool) ở đầu, phần thay đổi ở cuối; cache kết quả ở tầng ứng dụng cho input trùng (hash). |
| Trung cấp | Prompt caching của nhà cung cấp (đọc cache rẻ hơn nhiều so với input thường, ghi cache đắt hơn một chút); kiểm tra tỷ lệ cache hit từ usage; tránh "phá cache" (timestamp, JSON không sắp xếp, đổi bộ tool). |
| Nâng cao | Chọn TTL theo khoảng cách giữa các request, agent loop chỉ nối thêm (append-only) để giữ cache, semantic cache có ngưỡng an toàn chỉ cho câu hỏi lặp lại đã kiểm định. |

- **Tiên quyết:** [EFF-01](../mang/eff.md#eff-01) Đo token và chi phí trên mỗi tác vụ
- **Mở khóa:** —
- **Công cụ:** prompt caching của nhà cung cấp, Redis
- **Đạt khi:** Tỷ lệ token đọc từ cache được đo hằng ngày; ở agent loop, phần lớn input đến từ cache.
- **Token & độ chính xác:** Không đổi output → không ảnh hưởng độ chính xác (với cache prefix của nhà cung cấp). Semantic cache thì CÓ rủi ro, phải qua eval.
- **Trong lộ trình:** Bước B6 · Tiết kiệm token có kiểm soát (Trung cấp) · Bước D3 · Chi phí và độ tin cậy của hệ LLM ở quy mô (Nâng cao) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="eff-03"></a>

### EFF-03 · Tinh gọn ngữ cảnh đầu vào

> Gửi cho model đúng thứ nó cần — không thiếu (sai) và không thừa (đắt, dễ nhiễu).

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 5  
**Dùng cho:** ● Cốt lõi: Nhóm 6 LLM/RAG · ● Cốt lõi: Nhóm 7 Agent · ◐ Cần: Nhóm 5 Ảnh/TL

| Mức | Làm được |
|---|---|
| Cơ bản | Trích đoạn liên quan thay vì cả tài liệu, bỏ boilerplate/HTML, giới hạn số lượt hội thoại gửi lại. |
| Trung cấp | RAG với top-k nhỏ + rerank, schema linking cho text-to-SQL, tóm tắt/cắt kết quả tool trước khi đưa lại cho model, ảnh đúng độ phân giải cần thiết. |
| Nâng cao | Quản lý ngữ cảnh agent dài (compaction, bộ nhớ ngoài, chỉ tải tool khi cần), ablation đo đóng góp của từng phần ngữ cảnh lên chất lượng. |

- **Tiên quyết:** [EFF-01](../mang/eff.md#eff-01) Đo token và chi phí trên mỗi tác vụ
- **Mở khóa:** —
- **Công cụ:** reranker, sqlglot, tokenizer
- **Đạt khi:** Mỗi phần ngữ cảnh trong prompt đều có lý do tồn tại được chứng minh bằng ablation trên golden set.
- **Token & độ chính xác:** Cắt ngữ cảnh CÓ thể làm giảm chính xác — luôn đo lại trên golden set; ngữ cảnh gọn thường còn tăng độ chính xác.
- **Trong lộ trình:** Bước B6 · Tiết kiệm token có kiểm soát (Cơ bản) · Hướng LLM ứng dụng & Agent (Trung cấp) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="eff-04"></a>

### EFF-04 · Định tuyến và cascade — đúng việc, đúng công cụ

> Code làm được thì không gọi LLM; model nhỏ làm được thì không gọi model lớn.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 5  
**Dùng cho:** ● Cốt lõi: Nhóm 6 LLM/RAG · ● Cốt lõi: Nhóm 7 Agent · ◐ Cần: Nhóm 5 Ảnh/TL · ○ Ít: Nhóm 1 Bảng

| Mức | Làm được |
|---|---|
| Cơ bản | Dùng code/regex/SQL cho việc xác định được; chỉ gọi LLM cho phần mơ hồ. |
| Trung cấp | Cascade luật → model nhỏ (TF-IDF/PhoBERT) → LLM; chuyển tầng theo độ tin cậy; chọn model và mức suy luận (effort) theo độ khó — đo trên golden set. |
| Nâng cao | Router học từ dữ liệu, distill tác vụ lưu lượng lớn sang model nhỏ; so sánh "model mạnh + mức suy luận thấp" với cascade nhiều model (cache tách theo model) trước khi chọn. |

- **Tiên quyết:** [EFF-01](../mang/eff.md#eff-01) Đo token và chi phí trên mỗi tác vụ, [LLM-04](../mang/llm.md#llm-04) Đánh giá hệ LLM (evals), [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn
- **Mở khóa:** —
- **Công cụ:** scikit-learn, PhoBERT, LLM API
- **Đạt khi:** Đường coverage–accuracy của từng tầng được đo; tổng chi phí giảm trong khi độ chính xác chung không giảm ngoài biên sai số.
- **Token & độ chính xác:** Rủi ro chính là tầng rẻ "tự tin sai" — ngưỡng chuyển tầng phải chọn bằng calibration (STAT-05), không chọn theo cảm giác.
- **Trong lộ trình:** Bước B8 · Cascade và trình bày — mốc giai đoạn B (Cơ bản) · Hướng LLM ứng dụng & Agent (Trung cấp) · Bước D3 · Chi phí và độ tin cậy của hệ LLM ở quy mô (Nâng cao) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="eff-05"></a>

### EFF-05 · Kiểm soát đầu ra và mức suy luận

> Token đầu ra thường đắt hơn đầu vào nhiều lần — chỉ sinh những gì cần dùng.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 5  
**Dùng cho:** ● Cốt lõi: Nhóm 6 LLM/RAG · ● Cốt lõi: Nhóm 7 Agent · ◐ Cần: Nhóm 5 Ảnh/TL

| Mức | Làm được |
|---|---|
| Cơ bản | Đầu ra ngắn theo schema (enum, mã nhãn) thay vì văn xuôi; đặt max_tokens hợp lý (quá thấp gây cắt cụt và phải gọi lại). |
| Trung cấp | Chỉ yêu cầu giải thích khi cần (ví dụ chỉ cho ca bị từ chối); chỉnh mức suy luận/effort theo từng loại tác vụ. |
| Nâng cao | Quét mức effort/model trên golden set để chọn điểm rẻ nhất vẫn đạt ngưỡng; tách bước suy luận khó khỏi bước định dạng đầu ra. |

- **Tiên quyết:** [EFF-01](../mang/eff.md#eff-01) Đo token và chi phí trên mỗi tác vụ, [LLM-02](../mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra
- **Mở khóa:** —
- **Công cụ:** structured outputs, tham số effort/reasoning của nhà cung cấp
- **Đạt khi:** Token đầu ra trung bình mỗi tác vụ giảm mà eval không giảm; không có output bị cắt cụt.
- **Trong lộ trình:** Bước B6 · Tiết kiệm token có kiểm soát (Cơ bản) · Hướng LLM ứng dụng & Agent (Trung cấp) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="eff-06"></a>

### EFF-06 · Xử lý theo lô và bất đồng bộ

> Việc không cần trả lời ngay thì chạy theo lô với giá rẻ hơn.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 2  
**Dùng cho:** ◐ Cần: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 6 LLM/RAG · ○ Ít: Nhóm 1 Bảng · ○ Ít: Nhóm 2 Thời gian · ○ Ít: Nhóm 3 Bất thường · ○ Ít: Nhóm 4 Gợi ý · ○ Ít: Nhóm 7 Agent

| Mức | Làm được |
|---|---|
| Cơ bản | Gom việc không cần realtime (gán nhãn, tóm tắt hàng loạt, chạy eval) để chạy theo lô. |
| Trung cấp | Batch API của nhà cung cấp (nhiều hãng giảm khoảng 50%, có hãng cộng dồn với giảm giá cache), khử trùng lặp trước khi gửi, checkpoint/resume. |
| Nâng cao | Lập lịch xử lý lớn, kết hợp batch + cache cho pipeline hàng triệu tài liệu. |

- **Tiên quyết:** [EFF-01](../mang/eff.md#eff-01) Đo token và chi phí trên mỗi tác vụ, [PY-04](../mang/py.md#py-04) Gọi API và I/O đồng thời bền vững
- **Mở khóa:** —
- **Công cụ:** Batch API của nhà cung cấp
- **Đạt khi:** Toàn bộ eval và tác vụ offline chạy qua batch; kết quả được ghép lại theo custom_id, không theo thứ tự.
- **Token & độ chính xác:** Cùng model, cùng prompt → cùng chất lượng, chỉ đổi độ trễ lấy giá; là tối ưu "miễn phí" về độ chính xác.
- **Trong lộ trình:** Bước B6 · Tiết kiệm token có kiểm soát (Trung cấp) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="eff-07"></a>

### EFF-07 · Kiểm chứng xác định và "không lỗi im lặng"

> Độ chính xác do hệ thống bảo đảm — mọi đầu ra tự động đều qua lớp kiểm chứng bằng code.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 6  
**Dùng cho:** ● Cốt lõi: Nhóm 5 Ảnh/TL · ● Cốt lõi: Nhóm 6 LLM/RAG · ● Cốt lõi: Nhóm 7 Agent · ○ Ít: Nhóm 1 Bảng

| Mức | Làm được |
|---|---|
| Cơ bản | Kiểm tra định dạng (regex, độ dài, checksum), ràng buộc nghiệp vụ (tổng tiền = Σ dòng + thuế; ngày hợp lệ), đối chiếu danh mục chuẩn (mã hàng, khách hàng). |
| Trung cấp | Đối chiếu chéo nhiều nguồn (OCR vs VLM, hai lần chạy), để LLM gọi tool tính toán/SQL thay vì tự tính, bắt buộc trích dẫn và kiểm tra trích dẫn có thật trong tài liệu. |
| Nâng cao | Thiết kế lớp kiểm chứng cho mọi đầu ra tự động; đo precision trên phần tự động đạt mục tiêu (ví dụ 99,5%) và chuyển phần còn lại cho người; giám sát liên tục tỷ lệ lỗi lọt. |

- **Tiên quyết:** [LLM-02](../mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra, [STAT-05](../mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc
- **Mở khóa:** —
- **Công cụ:** pydantic validators, sqlglot, regex, rapidfuzz
- **Đạt khi:** Không có đầu ra nào được ghi vào hệ thống nghiệp vụ mà chưa qua kiểm chứng; tỷ lệ lỗi lọt được đo bằng kiểm tra mẫu định kỳ.
- **Token & độ chính xác:** Lớp kiểm chứng cho phép dùng model rẻ hơn một cách an toàn — sai sẽ bị bắt và chuyển tầng, không lọt ra ngoài.
- **Trong lộ trình:** Bước B5 · Đánh giá nghiêm túc và lớp kiểm chứng (Trung cấp) · Hướng Document AI (Nâng cao) · Bước D3 · Chi phí và độ tin cậy của hệ LLM ở quy mô (Nâng cao) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="eff-08"></a>

### EFF-08 · Tiết kiệm token khi dùng AI hỗ trợ lập trình

> Dùng trợ lý lập trình AI hiệu quả — ít token, ít vòng lặp sửa, kết quả kiểm chứng được.

**Tầng:** Bổ trợ · **Điểm đòn bẩy:** 0  
**Dùng cho:** ○ Ít: Nhóm 1 Bảng · ○ Ít: Nhóm 2 Thời gian · ○ Ít: Nhóm 3 Bất thường · ○ Ít: Nhóm 4 Gợi ý · ○ Ít: Nhóm 5 Ảnh/TL · ○ Ít: Nhóm 6 LLM/RAG · ○ Ít: Nhóm 7 Agent · ○ Ít: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | Mô tả việc cụ thể, chỉ rõ file/hàm liên quan thay vì "đọc cả repo"; yêu cầu kế hoạch ngắn trước khi sửa lớn. |
| Trung cấp | File hướng dẫn dự án (CLAUDE.md/AGENTS.md) ngắn, cập nhật; phiên mới cho việc mới; dùng test làm tiêu chí xác nhận. |
| Nâng cao | Chia nhỏ việc lớn, giao tìm kiếm rộng cho tác vụ phụ, tự động hóa lint/test/eval để trợ lý tự sửa lỗi mà không phải dán log. |

- **Tiên quyết:** [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án
- **Mở khóa:** —
- **Công cụ:** Claude Code, Cursor, GitHub Copilot, Makefile, pytest
- **Đạt khi:** Phần lớn thay đổi do trợ lý AI tạo ra qua được test/lint ngay lần đầu.
- **Trong lộ trình:** Thói quen xuyên suốt (Cơ bản) — xem [lộ trình theo bước](../lo-trinh.md)
