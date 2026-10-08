<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# PY · Lập trình nền tảng

Python, Git, môi trường, kiểm thử, gọi API bền vững — nền móng cho mọi nhóm.

| Kỹ năng | Tầng | Tóm tắt |
|---|---|---|
| [PY-01](#py-01) Python cho dữ liệu và AI | Nền tảng chung | Viết code Python rõ ràng, có kiểu, tái sử dụng được cho xử lý dữ liệu và gọi model. |
| [PY-02](#py-02) Git, môi trường và cấu trúc dự án | Nền tảng chung | Quản lý mã nguồn, môi trường tái lập được và cấu trúc dự án dễ mở rộng. |
| [PY-03](#py-03) Kiểm thử và chất lượng code | Nền tảng chung | Bảo đảm code và pipeline dữ liệu chạy đúng, kể cả với hệ có thành phần ngẫu nhiên như LLM. |
| [PY-04](#py-04) Gọi API và I/O đồng thời bền vững | Cầu nối liên họ | Gọi API (LLM, OCR, nội bộ) với số lượng lớn mà không mất dữ liệu, không vượt hạn mức. |

<a id="py-01"></a>

### PY-01 · Python cho dữ liệu và AI

> Viết code Python rõ ràng, có kiểu, tái sử dụng được cho xử lý dữ liệu và gọi model.

**Tầng:** Nền tảng chung · **Điểm đòn bẩy:** 16  
**Dùng cho:** ● Cốt lõi: Nhóm 1 Bảng · ● Cốt lõi: Nhóm 2 Thời gian · ● Cốt lõi: Nhóm 3 Bất thường · ● Cốt lõi: Nhóm 4 Gợi ý · ● Cốt lõi: Nhóm 5 Ảnh/TL · ● Cốt lõi: Nhóm 6 LLM/RAG · ● Cốt lõi: Nhóm 7 Agent · ● Cốt lõi: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | Cú pháp, cấu trúc dữ liệu, hàm, module; đọc/ghi CSV, JSON, Parquet; xử lý ngoại lệ; type hints cho hàm. |
| Trung cấp | dataclass/pydantic cho dữ liệu có cấu trúc, generator cho dữ liệu lớn, logging, cấu hình qua file/biến môi trường, CLI (typer/argparse). |
| Nâng cao | Profiling (cProfile, py-spy), vector hóa thay vòng lặp, đa tiến trình, viết thư viện nội bộ có tài liệu và phiên bản. |

- **Tiên quyết:** —
- **Mở khóa:** [PY-02](../mang/py.md#py-02), [PY-03](../mang/py.md#py-03), [PY-04](../mang/py.md#py-04), [DATA-02](../mang/data.md#data-02), [DATA-06](../mang/data.md#data-06), [DL-01](../mang/dl.md#dl-01), [DL-03](../mang/dl.md#dl-03), [LLM-01](../mang/llm.md#llm-01), [OPT-01](../mang/opt.md#opt-01)
- **Công cụ:** Python 3.12, VS Code, JupyterLab, pydantic, typer
- **Đạt khi:** Viết được một module xử lý dữ liệu có type hints, logging, CLI và người khác chạy được chỉ bằng README.
- **Trong lộ trình:** Bước A1 · Python, Git và framing bài toán (Cơ bản) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="py-02"></a>

### PY-02 · Git, môi trường và cấu trúc dự án

> Quản lý mã nguồn, môi trường tái lập được và cấu trúc dự án dễ mở rộng.

**Tầng:** Nền tảng chung · **Điểm đòn bẩy:** 16  
**Dùng cho:** ● Cốt lõi: Nhóm 1 Bảng · ● Cốt lõi: Nhóm 2 Thời gian · ● Cốt lõi: Nhóm 3 Bất thường · ● Cốt lõi: Nhóm 4 Gợi ý · ● Cốt lõi: Nhóm 5 Ảnh/TL · ● Cốt lõi: Nhóm 6 LLM/RAG · ● Cốt lõi: Nhóm 7 Agent · ● Cốt lõi: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | commit/branch/merge, .gitignore (không commit dữ liệu và secret), uv + pyproject.toml, cấu trúc src/ tests/ notebooks/. |
| Trung cấp | Pull request và code review, lockfile để tái lập môi trường, pre-commit, Makefile; chuyển code từ notebook sang module. |
| Nâng cao | Monorepo nhiều dự án, versioning dữ liệu/model (DVC hoặc Git LFS), semantic versioning, CI chạy lint/test/eval. |

- **Tiên quyết:** [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI
- **Mở khóa:** [OPS-01](../mang/ops.md#ops-01), [OPS-02](../mang/ops.md#ops-02), [OPS-03](../mang/ops.md#ops-03), [OPS-08](../mang/ops.md#ops-08), [EFF-08](../mang/eff.md#eff-08)
- **Công cụ:** Git, GitHub, uv, pre-commit, make, DVC
- **Đạt khi:** Clone repo sạch trên máy khác, chạy một lệnh setup là có môi trường giống hệt, mọi thay đổi đi qua PR.
- **Trong lộ trình:** Bước A1 · Python, Git và framing bài toán (Cơ bản) · Bước A8 · Trình bày kết quả — mốc giai đoạn A (Trung cấp) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="py-03"></a>

### PY-03 · Kiểm thử và chất lượng code

> Bảo đảm code và pipeline dữ liệu chạy đúng, kể cả với hệ có thành phần ngẫu nhiên như LLM.

**Tầng:** Nền tảng chung · **Điểm đòn bẩy:** 10  
**Dùng cho:** ● Cốt lõi: Nhóm 6 LLM/RAG · ● Cốt lõi: Nhóm 7 Agent · ◐ Cần: Nhóm 1 Bảng · ◐ Cần: Nhóm 2 Thời gian · ◐ Cần: Nhóm 3 Bất thường · ◐ Cần: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | pytest cho hàm thuần, ruff để lint/format, assert về shape và kiểu dữ liệu. |
| Trung cấp | Test pipeline dữ liệu bằng fixture nhỏ, kiểm tra schema (pandera), test thuộc tính (hypothesis), type check, chạy test trong CI. |
| Nâng cao | Eval-as-test — chạy golden set trong CI và chặn merge khi metric giảm quá ngưỡng; test hệ không tất định bằng ngưỡng thống kê thay vì so khớp chuỗi. |

- **Tiên quyết:** [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI
- **Mở khóa:** —
- **Công cụ:** pytest, ruff, mypy hoặc pyright, hypothesis, pandera
- **Đạt khi:** Mọi PR có test tự động; một thay đổi làm giảm chất lượng model/prompt bị CI phát hiện trước khi merge.
- **Token & độ chính xác:** Eval-as-test là "lưới an toàn" cho mọi tối ưu token — chỉ merge khi chất lượng không giảm.
- **Trong lộ trình:** Bước A6 · Phân tích lỗi, giải thích và kiểm thử (Trung cấp) · Bước D5 · Phương pháp ở quy mô team (Nâng cao) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="py-04"></a>

### PY-04 · Gọi API và I/O đồng thời bền vững

> Gọi API (LLM, OCR, nội bộ) với số lượng lớn mà không mất dữ liệu, không vượt hạn mức.

**Tầng:** Cầu nối liên họ · **Điểm đòn bẩy:** 6  
**Dùng cho:** ● Cốt lõi: Nhóm 6 LLM/RAG · ● Cốt lõi: Nhóm 7 Agent · ◐ Cần: Nhóm 3 Bất thường · ◐ Cần: Nhóm 5 Ảnh/TL · ○ Ít: Nhóm 1 Bảng · ○ Ít: Nhóm 2 Thời gian · ○ Ít: Nhóm 4 Gợi ý · ○ Ít: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | httpx/requests, timeout, xử lý mã lỗi HTTP, đọc tài liệu API, không hard-code khóa bí mật. |
| Trung cấp | asyncio + semaphore giới hạn đồng thời, retry exponential backoff + jitter cho lỗi 429/5xx, rate limit, idempotency key. |
| Nâng cao | Hàng đợi tác vụ (queue/worker), circuit breaker, streaming (SSE), xử lý hàng trăm nghìn request có checkpoint/resume. |

- **Tiên quyết:** [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI
- **Mở khóa:** [LLM-05](../mang/llm.md#llm-05), [EFF-06](../mang/eff.md#eff-06)
- **Công cụ:** httpx, asyncio, tenacity
- **Đạt khi:** Xử lý 10.000 tài liệu qua API có giới hạn tốc độ; chạy lại sau sự cố không gọi trùng, không mất bản ghi.
- **Token & độ chính xác:** Retry có kiểm soát + idempotency tránh trả tiền hai lần cho cùng một request.
- **Trong lộ trình:** Bước B1 · Gọi LLM, structured output và gọi API bền vững (Trung cấp) — xem [lộ trình theo bước](../lo-trinh.md)
