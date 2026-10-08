<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# BIZ · Nghiệp vụ & phương pháp

Framing, baseline & bộ đánh giá, phân tích lỗi, trình bày — quy trình ĐÚNG → NHANH → CHÍNH XÁC → THUYẾT PHỤC.

| Kỹ năng | Tầng | Tóm tắt |
|---|---|---|
| [BIZ-01](#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) | Nền tảng chung | Chốt quyết định nào thay đổi, KPI nào, loại sai nào đắt hơn — trước khi viết code. |
| [BIZ-02](#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) | Nền tảng chung | Có baseline trong 1–2 ngày cùng một bộ đánh giá cố định từ dữ liệu thật. |
| [BIZ-03](#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) | Nền tảng chung | Đọc ca sai, nhóm theo nguyên nhân, sửa nhóm lớn nhất — cách tăng chính xác hiệu quả nhất. |
| [BIZ-04](#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) | Nền tảng chung | So với baseline, quy ra tiền hoặc giờ công, demo chạy được, nói rõ giới hạn. |
| [BIZ-05](#biz-05) Kiến thức miền nghiệp vụ | Nền tảng chung | Hiểu quy trình, thuật ngữ, ràng buộc của ngành để model phục vụ đúng người dùng. |
| [BIZ-06](#biz-06) Đọc và tái hiện paper | Bổ trợ | Cập nhật kỹ thuật mới một cách có phê phán, gắn với bài toán đang làm. |

<a id="biz-01"></a>

### BIZ-01 · Framing bài toán và quy đổi giá trị (ĐÚNG)

> Chốt quyết định nào thay đổi, KPI nào, loại sai nào đắt hơn — trước khi viết code.

**Tầng:** Nền tảng chung · **Điểm đòn bẩy:** 13  
**Dùng cho:** ● Cốt lõi: Nhóm 1 Bảng · ● Cốt lõi: Nhóm 2 Thời gian · ● Cốt lõi: Nhóm 3 Bất thường · ● Cốt lõi: Nhóm 7 Agent · ● Cốt lõi: Nhóm 8 Tối ưu · ◐ Cần: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 6 LLM/RAG

| Mức | Làm được |
|---|---|
| Cơ bản | Viết 1 trang — quyết định thay đổi, KPI, chi phí từng loại sai, cách làm hiện tại; xếp bài toán vào đúng nhóm (cây quyết định 30 giây). |
| Trung cấp | Tách dự án thành bài toán con (hồ sơ vay = Nhóm 5 + 1 + 7), quy metric kỹ thuật ra tiền/giờ công, nhận ra khi nào chỉ cần luật if-else. |
| Nâng cao | Business case và ROI, thiết kế quy trình người–máy (ai duyệt gì), tiêu chí dừng dự án. |

- **Tiên quyết:** —
- **Mở khóa:** [BIZ-02](../mang/biz.md#biz-02)
- **Công cụ:** Mẫu 1 trang framing (templates/project)
- **Đạt khi:** Mục tiêu mơ hồ ("giảm churn") được viết lại thành bài toán đo được ("precision@500 mỗi tuần cho CSKH").
- **Token & độ chính xác:** Framing đúng loại bỏ việc dùng LLM cho chỗ luật đơn giản làm được — khoản tiết kiệm lớn nhất là lời gọi không cần thực hiện.
- **Trong lộ trình:** Bước A1 · Python, Git và framing bài toán (Cơ bản) · Bước C1 · Chọn hướng, hiểu nghiệp vụ và lấp khoảng trống (Trung cấp) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="biz-02"></a>

### BIZ-02 · Baseline nhanh và bộ đánh giá cố định (NHANH)

> Có baseline trong 1–2 ngày cùng một bộ đánh giá cố định từ dữ liệu thật.

**Tầng:** Nền tảng chung · **Điểm đòn bẩy:** 16  
**Dùng cho:** ● Cốt lõi: Nhóm 1 Bảng · ● Cốt lõi: Nhóm 2 Thời gian · ● Cốt lõi: Nhóm 3 Bất thường · ● Cốt lõi: Nhóm 4 Gợi ý · ● Cốt lõi: Nhóm 5 Ảnh/TL · ● Cốt lõi: Nhóm 6 LLM/RAG · ● Cốt lõi: Nhóm 7 Agent · ● Cốt lõi: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | Baseline bằng luật, LightGBM mặc định hoặc LLM API + prompt; tách tập đánh giá cố định từ dữ liệu thật trước khi thử bất cứ gì. |
| Trung cấp | Harness đánh giá một lệnh (`make eval`) in metric + chi phí + độ trễ; bảng so sánh mọi thí nghiệm với baseline. |
| Nâng cao | Đánh giá nhiều tầng (offline → shadow → A/B), quản lý tập đánh giá để không bị "học thuộc", eval chạy trong CI. |

- **Tiên quyết:** [BIZ-01](../mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG)
- **Mở khóa:** [LLM-04](../mang/llm.md#llm-04), [BIZ-03](../mang/biz.md#biz-03), [BIZ-04](../mang/biz.md#biz-04)
- **Công cụ:** pytest, MLflow, Langfuse
- **Đạt khi:** Ngày thứ 2 của dự án đã có con số baseline và một lệnh tái tạo nó.
- **Trong lộ trình:** Bước A3 · Baseline và bộ đánh giá cố định (Cơ bản) · Bước C2 · Dự án chuyên sâu theo hướng đã chọn (Trung cấp) · Bước D5 · Phương pháp ở quy mô team (Nâng cao) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="biz-03"></a>

### BIZ-03 · Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC)

> Đọc ca sai, nhóm theo nguyên nhân, sửa nhóm lớn nhất — cách tăng chính xác hiệu quả nhất.

**Tầng:** Nền tảng chung · **Điểm đòn bẩy:** 16  
**Dùng cho:** ● Cốt lõi: Nhóm 1 Bảng · ● Cốt lõi: Nhóm 2 Thời gian · ● Cốt lõi: Nhóm 3 Bất thường · ● Cốt lõi: Nhóm 4 Gợi ý · ● Cốt lõi: Nhóm 5 Ảnh/TL · ● Cốt lõi: Nhóm 6 LLM/RAG · ● Cốt lõi: Nhóm 7 Agent · ● Cốt lõi: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | Đọc 50–100 ca sai, gán nhãn nguyên nhân, đếm theo nhóm. |
| Trung cấp | Sửa nhóm lỗi lớn nhất trước (dữ liệu/feature/prompt/luật hậu kiểm) rồi đo lại; phân tích theo phân khúc (slice). |
| Nâng cao | Vòng lặp lỗi → nhãn mới → huấn luyện lại liên tục; taxonomy lỗi dùng chung cho cả team. |

- **Tiên quyết:** [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH)
- **Mở khóa:** —
- **Công cụ:** Notebook, bảng tính, Label Studio, Langfuse
- **Đạt khi:** Mỗi vòng cải tiến có bảng "nhóm lỗi – số ca – đã sửa – metric trước/sau".
- **Token & độ chính xác:** Phân tích lỗi thường chỉ ra phần ngữ cảnh/prompt thừa — sửa đúng chỗ vừa tăng chính xác vừa giảm token.
- **Trong lộ trình:** Bước A6 · Phân tích lỗi, giải thích và kiểm thử (Trung cấp) · Bước D5 · Phương pháp ở quy mô team (Nâng cao) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="biz-04"></a>

### BIZ-04 · Trình bày, demo và thuyết phục (THUYẾT PHỤC)

> So với baseline, quy ra tiền hoặc giờ công, demo chạy được, nói rõ giới hạn.

**Tầng:** Nền tảng chung · **Điểm đòn bẩy:** 8  
**Dùng cho:** ◐ Cần: Nhóm 1 Bảng · ◐ Cần: Nhóm 2 Thời gian · ◐ Cần: Nhóm 3 Bất thường · ◐ Cần: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 6 LLM/RAG · ◐ Cần: Nhóm 7 Agent · ◐ Cần: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | Bảng so sánh với baseline; nói rõ giới hạn và rủi ro. |
| Trung cấp | Demo chạy được (Streamlit/Gradio), quy ra tiền/giờ công, biểu đồ đúng và dễ đọc. |
| Nâng cao | Design doc, trình bày cho lãnh đạo và pháp chế, kế hoạch triển khai theo giai đoạn có tiêu chí go/no-go. |

- **Tiên quyết:** [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH)
- **Mở khóa:** —
- **Công cụ:** Streamlit, Gradio, matplotlib, slide
- **Đạt khi:** Người ngoài ngành hiểu được kết quả và quyết định có triển khai hay không sau 10 phút trình bày.
- **Trong lộ trình:** Bước A8 · Trình bày kết quả — mốc giai đoạn A (Cơ bản) · Bước B8 · Cascade và trình bày — mốc giai đoạn B (Trung cấp) · Bước C4 · Bảo vệ kết quả — mốc giai đoạn C (Trung cấp) · Bước D5 · Phương pháp ở quy mô team (Nâng cao) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="biz-05"></a>

### BIZ-05 · Kiến thức miền nghiệp vụ

> Hiểu quy trình, thuật ngữ, ràng buộc của ngành để model phục vụ đúng người dùng.

**Tầng:** Nền tảng chung · **Điểm đòn bẩy:** 13  
**Dùng cho:** ● Cốt lõi: Nhóm 1 Bảng · ● Cốt lõi: Nhóm 2 Thời gian · ● Cốt lõi: Nhóm 3 Bất thường · ● Cốt lõi: Nhóm 7 Agent · ● Cốt lõi: Nhóm 8 Tối ưu · ◐ Cần: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 6 LLM/RAG

| Mức | Làm được |
|---|---|
| Cơ bản | Vẽ được sơ đồ quy trình đang làm, biết thuật ngữ và người dùng cuối. |
| Trung cấp | Hiểu ràng buộc pháp lý/vận hành (tín dụng cần lý do từ chối; tồn kho có lead time; tổng đài có SLA). |
| Nâng cao | Đề xuất thay đổi quy trình nhờ AI thay vì chỉ tự động hóa quy trình cũ. |

- **Tiên quyết:** —
- **Mở khóa:** —
- **Công cụ:** Phỏng vấn người dùng, sơ đồ BPMN
- **Đạt khi:** Người làm nghiệp vụ xác nhận sơ đồ quy trình và danh sách loại sai của bạn là đúng.
- **Trong lộ trình:** Bước C1 · Chọn hướng, hiểu nghiệp vụ và lấp khoảng trống (Trung cấp) — xem [lộ trình theo bước](../lo-trinh.md)

<a id="biz-06"></a>

### BIZ-06 · Đọc và tái hiện paper

> Cập nhật kỹ thuật mới một cách có phê phán, gắn với bài toán đang làm.

**Tầng:** Bổ trợ · **Điểm đòn bẩy:** 0  
**Dùng cho:** ○ Ít: Nhóm 1 Bảng · ○ Ít: Nhóm 2 Thời gian · ○ Ít: Nhóm 3 Bất thường · ○ Ít: Nhóm 4 Gợi ý · ○ Ít: Nhóm 5 Ảnh/TL · ○ Ít: Nhóm 6 LLM/RAG · ○ Ít: Nhóm 7 Agent · ○ Ít: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | Đọc abstract, hình, bảng kết quả; tìm code đi kèm. |
| Trung cấp | Tái hiện kết quả chính trên dữ liệu công khai, so với baseline của mình. |
| Nâng cao | Đánh giá benchmark có giống dữ liệu công ty không; chuyển ý tưởng vào bài toán thật. |

- **Tiên quyết:** —
- **Mở khóa:** —
- **Công cụ:** arXiv, Papers with Code, Hugging Face
- **Đạt khi:** Mỗi tuần một paper gắn với bài toán đang làm, có ghi chú và (khi được) kết quả tái hiện.
- **Trong lộ trình:** Thói quen xuyên suốt (Cơ bản) — xem [lộ trình theo bước](../lo-trinh.md)
