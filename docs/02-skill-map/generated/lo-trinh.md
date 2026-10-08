<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# Lộ trình học theo bước

Từ cơ bản đến nâng cao: mỗi bước nêu việc cần làm, sản phẩm phải nộp và kỹ năng cần đạt kèm **mức mục tiêu**. Bộ kiểm tra bảo đảm kỹ năng tiên quyết luôn xuất hiện ở bước trước, mức mục tiêu không giảm, và lộ trình phủ **65/65 kỹ năng**. Nguyên tắc và cách dùng: [04-lo-trinh-hoc.md](../04-lo-trinh-hoc.md).

| Giai đoạn | Thời gian | Mục tiêu | Mốc |
|---|---|---|---|
| [A · Nền tảng](#giai-doan-a) | Tháng 1–2 | Viết code dữ liệu sạch, dựng baseline đúng cách và đóng gói được một model dữ liệu bảng. | Dự án Nhóm 1 (churn Telco) chạy qua API FastAPI + Docker, có bộ đánh giá cố định và danh sách top 500 khách kèm lý do SHAP. |
| [B · GenAI](#giai-doan-b) | Tháng 3–4 | Xây hệ LLM/RAG tiếng Việt có bộ đánh giá, tracing và kiểm soát chi phí token. | Hệ RAG tiếng Việt có golden set ~100 câu (recall@k, faithfulness, độ đúng), có tracing và bảng chất lượng–chi phí–độ trễ trước/sau tối ưu token. |
| [C · Chuyên sâu](#giai-doan-c) | Tháng 5–6 | Đi sâu 1–2 nhóm sát nhu cầu công ty — kỹ năng Cốt lõi của hướng đã chọn lên Trung cấp, một phần lên Nâng cao. | Một dự án chuyên sâu cho công ty (hoặc một tổ hợp) có baseline, bộ đánh giá, kết quả quy ra tiền/giờ công, demo và tài liệu giới hạn. |
| [D · Nâng cao · Production](#giai-doan-d) | Tháng 7 trở đi | Vận hành ổn định ở production — tối ưu chi phí, giám sát, giải thích được, mở rộng quy mô (định nghĩa mức Nâng cao của giai đoạn 1). | Một hệ đang chạy thật có SLO chất lượng/độ trễ/chi phí, giám sát, quy trình cập nhật model an toàn và báo cáo chi phí theo đơn vị nghiệp vụ. |

<a id="giai-doan-a"></a>

## A · Nền tảng — Tháng 1–2

**Mục tiêu:** Viết code dữ liệu sạch, dựng baseline đúng cách và đóng gói được một model dữ liệu bảng.  
**Mốc:** Dự án Nhóm 1 (churn Telco) chạy qua API FastAPI + Docker, có bộ đánh giá cố định và danh sách top 500 khách kèm lý do SHAP.  
**Cài đặt:** `make setup-tabular setup-mlops` · **Đọc:** Hands-On Machine Learning — Aurélien Géron

| Bước | Tuần | Việc cần làm | Kỹ năng → mức mục tiêu | Sản phẩm |
|---|---|---|---|---|
| **A1** Python, Git và framing bài toán | 1 | Dựng repo cá nhân theo cấu trúc src/ tests/ notebooks/ với uv; viết framing 1 trang cho bài toán churn. | [PY-01](mang/py.md#py-01) Python cho dữ liệu và AI — *Cơ bản*<br>[PY-02](mang/py.md#py-02) Git, môi trường và cấu trúc dự án — *Cơ bản*<br>[BIZ-01](mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) — *Cơ bản* | Repo chạy được bằng một lệnh setup + file framing (quyết định, KPI, chi phí từng loại sai). |
| **A2** SQL, xử lý bảng và thống kê mô tả | 2 | Khám phá bộ Telco Customer Churn bằng DuckDB và pandas/polars; tính tỷ lệ churn nền, phân phối các biến chính. | [DATA-01](mang/data.md#data-01) SQL phân tích — *Cơ bản*<br>[DATA-02](mang/data.md#data-02) Xử lý dữ liệu bảng — *Cơ bản*<br>[STAT-01](mang/stat.md#stat-01) Xác suất và thống kê mô tả — *Cơ bản* | Notebook EDA có truy vấn SQL, biểu đồ và 5 nhận xét có số liệu. |
| **A3** Baseline và bộ đánh giá cố định | 3 | Tách và đóng băng tập đánh giá trước khi thử model; dựng baseline dummy + logistic regression trong một Pipeline. | [ML-01](mang/ml.md#ml-01) Quy trình học có giám sát chuẩn — *Cơ bản*<br>[BIZ-02](mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) — *Cơ bản*<br>[STAT-02](mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá — *Cơ bản* | `make eval` in AUC/F1 của baseline kèm khoảng tin cậy bootstrap. |
| **A4** Dữ liệu đúng thời điểm và feature | 4 | Xây feature as-of theo mốc thời gian, cố tình tạo một leakage rồi phát hiện nó; thêm kiểm tra schema cho pipeline. | [DATA-03](mang/data.md#data-03) Đúng thời điểm và chống rò rỉ dữ liệu — *Trung cấp*<br>[DATA-04](mang/data.md#data-04) Feature engineering cho bảng và chuỗi thời gian — *Cơ bản*<br>[DATA-05](mang/data.md#data-05) Kiểm định chất lượng dữ liệu và nhãn — *Cơ bản* | Pipeline feature có kiểm tra pandera và ghi chú chứng minh không rò rỉ dữ liệu. |
| **A5** Gradient boosting, mất cân bằng và ngưỡng theo chi phí | 5 | Huấn luyện LightGBM, đánh giá bằng PR-AUC và precision@500; hiệu chỉnh xác suất và chọn ngưỡng theo năng lực gọi của CSKH. | [ML-02](mang/ml.md#ml-02) Gradient boosting — *Trung cấp*<br>[ML-03](mang/ml.md#ml-03) Dữ liệu mất cân bằng và sự kiện hiếm — *Trung cấp*<br>[STAT-05](mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc — *Trung cấp* | Bảng so sánh với baseline (có khoảng tin cậy) + đường coverage–accuracy + ngưỡng đã chọn. |
| **A6** Phân tích lỗi, giải thích và kiểm thử | 6 | Đọc 50–100 ca sai, nhóm theo nguyên nhân và sửa nhóm lớn nhất; sinh lý do SHAP cho từng khách; viết test cho pipeline. | [BIZ-03](mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) — *Trung cấp*<br>[ML-04](mang/ml.md#ml-04) Giải thích mô hình — *Trung cấp*<br>[PY-03](mang/py.md#py-03) Kiểm thử và chất lượng code — *Trung cấp* | Bảng "nhóm lỗi – số ca – đã sửa – metric trước/sau" + danh sách top 500 khách kèm 3 lý do. |
| **A7** Đóng gói, theo dõi thực nghiệm và bảo mật dữ liệu | 7 | Bọc model bằng FastAPI + Docker có health check và version; ghi mọi lần chạy vào MLflow; rà soát secret và dữ liệu thật. | [OPS-01](mang/ops.md#ops-01) Đóng gói và phục vụ model — *Cơ bản*<br>[OPS-02](mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập — *Cơ bản*<br>[OPS-08](mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ — *Cơ bản* | `docker compose up` ra API chấm điểm; MLflow có lịch sử thí nghiệm; repo không chứa secret/dữ liệu thật. |
| **A8** Trình bày kết quả — mốc giai đoạn A | 8 | Quy kết quả ra số cuộc gọi tiết kiệm/khách giữ được; làm demo; viết rõ giới hạn. | [BIZ-04](mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) — *Cơ bản*<br>[PY-02](mang/py.md#py-02) Git, môi trường và cấu trúc dự án — *Trung cấp* | Demo chạy được + trang báo cáo 1 trang so với baseline. |

<a id="giai-doan-b"></a>

## B · GenAI — Tháng 3–4

**Mục tiêu:** Xây hệ LLM/RAG tiếng Việt có bộ đánh giá, tracing và kiểm soát chi phí token.  
**Mốc:** Hệ RAG tiếng Việt có golden set ~100 câu (recall@k, faithfulness, độ đúng), có tracing và bảng chất lượng–chi phí–độ trễ trước/sau tối ưu token.  
**Cài đặt:** `make setup-llm setup-agent` · **Đọc:** AI Engineering — Chip Huyen

| Bước | Tuần | Việc cần làm | Kỹ năng → mức mục tiêu | Sản phẩm |
|---|---|---|---|---|
| **B1** Gọi LLM, structured output và gọi API bền vững | 9 | Viết script phân loại ticket tiếng Việt trả JSON theo schema, validate bằng pydantic, gọi song song có giới hạn và retry. | [LLM-01](mang/llm.md#llm-01) Gọi LLM API và prompt engineering — *Cơ bản*<br>[LLM-02](mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra — *Trung cấp*<br>[PY-04](mang/py.md#py-04) Gọi API và I/O đồng thời bền vững — *Trung cấp* | Script xử lý 1.000 ticket không lỗi schema, không gọi trùng khi chạy lại. |
| **B2** Đo chi phí, tracing và golden set đầu tiên | 10 | Ghi token vào/ra, chi phí, độ trễ cho mọi lời gọi; dựng golden set 30 mẫu rồi mở rộng lên 100. | [EFF-01](mang/eff.md#eff-01) Đo token và chi phí trên mỗi tác vụ — *Cơ bản*<br>[OPS-06](mang/ops.md#ops-06) LLMOps — tracing, chi phí, độ trễ — *Cơ bản*<br>[LLM-04](mang/llm.md#llm-04) Đánh giá hệ LLM (evals) — *Cơ bản* | Bảng baseline "chất lượng / chi phí mỗi tác vụ / độ trễ" + trace xem được trong Langfuse. |
| **B3** Văn bản tiếng Việt, embedding và truy xuất | 11 | Chuẩn hóa NFC, tách từ cho BM25; so sánh BM25, embedding và hybrid + rerank trên bộ câu hỏi tiếng Việt. | [DATA-06](mang/data.md#data-06) Văn bản tiếng Việt và dữ liệu phi cấu trúc — *Cơ bản*<br>[DL-03](mang/dl.md#dl-03) Embedding và học biểu diễn — *Cơ bản*<br>[ML-07](mang/ml.md#ml-07) Truy xuất và xếp hạng hai tầng (retrieve → rerank) — *Trung cấp* | Bảng Recall@5/MRR của 3 cách truy xuất trên cùng bộ truy vấn. |
| **B4** RAG có trích dẫn | 12 | Dựng RAG trên văn bản công khai — chunk theo cấu trúc, hybrid search, rerank, trả lời có trích dẫn và biết nói "không tìm thấy". | [LLM-03](mang/llm.md#llm-03) RAG — trả lời dựa trên tài liệu — *Trung cấp* | RAG trả lời golden set, mọi câu trả lời có nguồn kiểm tra được. |
| **B5** Đánh giá nghiêm túc và lớp kiểm chứng | 13 | LLM-as-judge với rubric, đo độ đồng thuận với nhãn người; kiểm tra tự động đoạn trích dẫn có thật trong tài liệu. | [LLM-04](mang/llm.md#llm-04) Đánh giá hệ LLM (evals) — *Trung cấp*<br>[EFF-07](mang/eff.md#eff-07) Kiểm chứng xác định và "không lỗi im lặng" — *Trung cấp* | Báo cáo eval tách retrieval / generation + tỷ lệ trích dẫn hợp lệ. |
| **B6** Tiết kiệm token có kiểm soát | 14 | Áp dụng lần lượt prompt caching, tinh gọn ngữ cảnh, rút gọn đầu ra, batch cho eval — mỗi đòn bẩy một lần đo. | [EFF-02](mang/eff.md#eff-02) Prompt caching và tái sử dụng kết quả — *Trung cấp*<br>[EFF-03](mang/eff.md#eff-03) Tinh gọn ngữ cảnh đầu vào — *Cơ bản*<br>[EFF-05](mang/eff.md#eff-05) Kiểm soát đầu ra và mức suy luận — *Cơ bản*<br>[EFF-06](mang/eff.md#eff-06) Xử lý theo lô và bất đồng bộ — *Trung cấp* | Bảng chất lượng–chi phí trước/sau từng đòn bẩy, chất lượng không giảm ngoài biên sai số. |
| **B7** Tool calling, workflow và bảo mật LLM | 15 | Workflow cố định tra cứu tài liệu rồi tạo ticket, có người duyệt bước gửi; thêm bộ test prompt injection vào eval. | [LLM-05](mang/llm.md#llm-05) Tool calling và điều phối workflow/agent — *Cơ bản*<br>[LLM-06](mang/llm.md#llm-06) An toàn và bảo mật hệ LLM — *Cơ bản* | Workflow có log mọi hành động + test injection chạy trong eval. |
| **B8** Cascade và trình bày — mốc giai đoạn B | 16 | Dựng cascade luật → model nhỏ → LLM → người cho phân loại ticket; trình bày bảng chất lượng–chi phí. | [EFF-04](mang/eff.md#eff-04) Định tuyến và cascade — đúng việc, đúng công cụ — *Cơ bản*<br>[BIZ-04](mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) — *Trung cấp* | Báo cáo cascade (độ chính xác phần tự động, tỷ lệ tự động, chi phí mỗi ticket) + demo RAG. |

<a id="giai-doan-c"></a>

## C · Chuyên sâu — Tháng 5–6

**Mục tiêu:** Đi sâu 1–2 nhóm sát nhu cầu công ty — kỹ năng Cốt lõi của hướng đã chọn lên Trung cấp, một phần lên Nâng cao.  
**Mốc:** Một dự án chuyên sâu cho công ty (hoặc một tổ hợp) có baseline, bộ đánh giá, kết quả quy ra tiền/giờ công, demo và tài liệu giới hạn.  
**Cài đặt:** `make setup-<nhóm của hướng đã chọn>` · **Đọc:** Designing Machine Learning Systems — Chip Huyen

| Bước | Tuần | Việc cần làm | Kỹ năng → mức mục tiêu | Sản phẩm |
|---|---|---|---|---|
| **C1** Chọn hướng, hiểu nghiệp vụ và lấp khoảng trống | 17–18 | Chọn một hướng chuyên sâu bên dưới; phỏng vấn người dùng nghiệp vụ; đạt Cơ bản ở các kỹ năng của hướng còn thiếu. | [BIZ-05](mang/biz.md#biz-05) Kiến thức miền nghiệp vụ — *Trung cấp*<br>[BIZ-01](mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) — *Trung cấp* | Framing dự án chuyên sâu đã được người nghiệp vụ xác nhận + danh sách kỹ năng còn thiếu. |
| **C2** Dự án chuyên sâu theo hướng đã chọn | 19–22 | Làm dự án theo quy trình ĐÚNG → NHANH → CHÍNH XÁC → THUYẾT PHỤC, luyện các kỹ năng của hướng (xem bảng hướng chuyên sâu). | [BIZ-02](mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) — *Trung cấp* | Baseline + ít nhất 2 vòng cải tiến có bảng phân tích lỗi. |
| **C3** MLOps cho dự án chuyên sâu | 23 | Đưa dự án vào pipeline chạy theo lịch, model registry và giám sát drift/chi phí. | [OPS-02](mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập — *Trung cấp*<br>[OPS-03](mang/ops.md#ops-03) Pipeline và điều phối tác vụ — *Cơ bản*<br>[OPS-04](mang/ops.md#ops-04) Giám sát model và drift — *Trung cấp* | Pipeline chạy lại được cho một ngày bất kỳ + dashboard giám sát. |
| **C4** Bảo vệ kết quả — mốc giai đoạn C | 24 | Trình bày cho lãnh đạo/nghiệp vụ, đề xuất kế hoạch triển khai theo giai đoạn có tiêu chí go/no-go. | [BIZ-04](mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) — *Trung cấp* | Design doc + demo + kế hoạch triển khai. |

### Hướng chuyên sâu (chọn 1–2)

| Hướng | Nhóm | Kỹ năng → mức mục tiêu | Tổ hợp tiêu biểu |
|---|---|---|---|
| **Rủi ro & tín dụng** | [1 · Bảng](nhom/g1-du-lieu-bang.md), [3 · Bất thường](nhom/g3-bat-thuong.md) | [ML-02](mang/ml.md#ml-02) Gradient boosting — *Nâng cao*<br>[ML-03](mang/ml.md#ml-03) Dữ liệu mất cân bằng và sự kiện hiếm — *Nâng cao*<br>[ML-04](mang/ml.md#ml-04) Giải thích mô hình — *Nâng cao*<br>[STAT-05](mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc — *Nâng cao*<br>[ML-05](mang/ml.md#ml-05) Học không giám sát và phát hiện bất thường — *Trung cấp*<br>[DATA-07](mang/data.md#data-07) Dữ liệu đồ thị — *Trung cấp*<br>[STAT-03](mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test — *Cơ bản*<br>[STAT-06](mang/stat.md#stat-06) Suy luận nhân quả và uplift — *Cơ bản*<br>[OPS-07](mang/ops.md#ops-07) Real-time và streaming — *Cơ bản* | [CMB-04](to-hop-ky-nang.md#cmb-04) Phát hiện rồi giải thích (cảnh báo gian lận cho điều tra viên), [CMB-06](to-hop-ky-nang.md#cmb-06) Dự đoán rồi can thiệp (churn + uplift) |
| **Dự báo & vận hành** | [2 · Thời gian](nhom/g2-chuoi-thoi-gian.md), [8 · Tối ưu](nhom/g8-toi-uu-nhan-qua.md) | [ML-06](mang/ml.md#ml-06) Mô hình chuỗi thời gian — *Trung cấp*<br>[STAT-04](mang/stat.md#stat-04) Dự báo xác suất và định lượng bất định — *Trung cấp*<br>[OPT-01](mang/opt.md#opt-01) Quy hoạch tuyến tính và nguyên (LP/MIP) — *Trung cấp*<br>[OPT-02](mang/opt.md#opt-02) Tối ưu tổ hợp — định tuyến và lập lịch — *Trung cấp*<br>[OPT-03](mang/opt.md#opt-03) Ra quyết định dưới bất định (dự báo rồi tối ưu) — *Trung cấp* | [CMB-02](to-hop-ky-nang.md#cmb-02) Dự báo rồi tối ưu (tồn kho, xếp ca) |
| **Cá nhân hóa & tăng trưởng** | [4 · Gợi ý](nhom/g4-goi-y-xep-hang.md), [8 · Tối ưu](nhom/g8-toi-uu-nhan-qua.md) | [ML-07](mang/ml.md#ml-07) Truy xuất và xếp hạng hai tầng (retrieve → rerank) — *Nâng cao*<br>[ML-08](mang/ml.md#ml-08) Hệ gợi ý chuyên biệt — *Trung cấp*<br>[STAT-03](mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test — *Trung cấp*<br>[STAT-06](mang/stat.md#stat-06) Suy luận nhân quả và uplift — *Trung cấp*<br>[OPT-04](mang/opt.md#opt-04) Bandit và học tăng cường cơ bản — *Cơ bản* | [CMB-05](to-hop-ky-nang.md#cmb-05) Gợi ý và kiểm chứng bằng thí nghiệm, [CMB-06](to-hop-ky-nang.md#cmb-06) Dự đoán rồi can thiệp (churn + uplift) |
| **Document AI** | [5 · Ảnh/TL](nhom/g5-anh-tai-lieu.md), [6 · LLM/RAG](nhom/g6-llm-rag.md) | [DL-01](mang/dl.md#dl-01) PyTorch nền tảng — *Trung cấp*<br>[DL-02](mang/dl.md#dl-02) Transfer learning và fine-tune mô hình pretrained — *Trung cấp*<br>[DL-04](mang/dl.md#dl-04) Thị giác máy tính (detection, segmentation, OCR) — *Trung cấp*<br>[DL-05](mang/dl.md#dl-05) Document AI và mô hình thị giác–ngôn ngữ (VLM) — *Trung cấp*<br>[OPS-05](mang/ops.md#ops-05) Tối ưu suy luận và serving model — *Cơ bản*<br>[EFF-07](mang/eff.md#eff-07) Kiểm chứng xác định và "không lỗi im lặng" — *Nâng cao*<br>[LLM-07](mang/llm.md#llm-07) Fine-tune, distill và tự host LLM — *Cơ bản* | [CMB-01](to-hop-ky-nang.md#cmb-01) Hồ sơ vay / eKYC từ đầu đến cuối |
| **LLM ứng dụng & Agent** | [6 · LLM/RAG](nhom/g6-llm-rag.md), [7 · Agent](nhom/g7-agent-tu-dong-hoa.md) | [LLM-05](mang/llm.md#llm-05) Tool calling và điều phối workflow/agent — *Trung cấp*<br>[LLM-06](mang/llm.md#llm-06) An toàn và bảo mật hệ LLM — *Trung cấp*<br>[LLM-08](mang/llm.md#llm-08) Text-to-SQL và hỏi đáp số liệu — *Trung cấp*<br>[EFF-03](mang/eff.md#eff-03) Tinh gọn ngữ cảnh đầu vào — *Trung cấp*<br>[EFF-04](mang/eff.md#eff-04) Định tuyến và cascade — đúng việc, đúng công cụ — *Trung cấp*<br>[EFF-05](mang/eff.md#eff-05) Kiểm soát đầu ra và mức suy luận — *Trung cấp*<br>[OPS-06](mang/ops.md#ops-06) LLMOps — tracing, chi phí, độ trễ — *Trung cấp*<br>[DATA-06](mang/data.md#data-06) Văn bản tiếng Việt và dữ liệu phi cấu trúc — *Trung cấp*<br>[DL-01](mang/dl.md#dl-01) PyTorch nền tảng — *Cơ bản*<br>[DL-02](mang/dl.md#dl-02) Transfer learning và fine-tune mô hình pretrained — *Cơ bản*<br>[DL-06](mang/dl.md#dl-06) Xử lý giọng nói (ASR) — *Cơ bản* | [CMB-03](to-hop-ky-nang.md#cmb-03) Trợ lý nội bộ có RAG và thao tác được, [CMB-07](to-hop-ky-nang.md#cmb-07) Tổng đài thông minh, [CMB-08](to-hop-ky-nang.md#cmb-08) Phân loại lai ML + LLM (cascade tiết kiệm token), [CMB-09](to-hop-ky-nang.md#cmb-09) Hỏi số liệu bằng tiếng Việt (text-to-SQL agent) |

<a id="giai-doan-d"></a>

## D · Nâng cao · Production — Tháng 7 trở đi

**Mục tiêu:** Vận hành ổn định ở production — tối ưu chi phí, giám sát, giải thích được, mở rộng quy mô (định nghĩa mức Nâng cao của giai đoạn 1).  
**Mốc:** Một hệ đang chạy thật có SLO chất lượng/độ trễ/chi phí, giám sát, quy trình cập nhật model an toàn và báo cáo chi phí theo đơn vị nghiệp vụ.  
**Cài đặt:** `make setup-all` · **Đọc:** Đọc tài liệu vận hành của công cụ đang dùng + 1 paper mỗi tuần

> Phần đề xuất thêm ở giai đoạn 2 (lộ trình gốc dừng ở tháng 6). Thứ tự các bước linh hoạt theo nhu cầu dự án.

| Bước | Tuần | Việc cần làm | Kỹ năng → mức mục tiêu | Sản phẩm |
|---|---|---|---|---|
| **D1** Vận hành dịch vụ model | — | Canary/shadow deploy, autoscaling, SLA độ trễ; tối ưu suy luận (quantization, batching); real-time khi nghiệp vụ thật sự cần. | [OPS-01](mang/ops.md#ops-01) Đóng gói và phục vụ model — *Nâng cao*<br>[OPS-05](mang/ops.md#ops-05) Tối ưu suy luận và serving model — *Trung cấp*<br>[OPS-07](mang/ops.md#ops-07) Real-time và streaming — *Trung cấp* | Dịch vụ có SLA đo được, triển khai phiên bản mới không downtime. |
| **D2** Giám sát và vòng đời model | — | Giám sát drift theo phân khúc, huấn luyện lại tự động có cổng kiểm định, data contract với các team nguồn. | [OPS-04](mang/ops.md#ops-04) Giám sát model và drift — *Nâng cao*<br>[OPS-02](mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập — *Nâng cao*<br>[OPS-03](mang/ops.md#ops-03) Pipeline và điều phối tác vụ — *Trung cấp*<br>[DATA-05](mang/data.md#data-05) Kiểm định chất lượng dữ liệu và nhãn — *Nâng cao* | Model mới chỉ được deploy khi tốt hơn champion; cảnh báo khi nguồn dữ liệu đổi định dạng. |
| **D3** Chi phí và độ tin cậy của hệ LLM ở quy mô | — | Ngân sách và cảnh báo theo tính năng, TTL cache theo lưu lượng, router/distill cho tác vụ lưu lượng lớn, lớp kiểm chứng cho mọi đầu ra tự động. | [EFF-01](mang/eff.md#eff-01) Đo token và chi phí trên mỗi tác vụ — *Nâng cao*<br>[EFF-02](mang/eff.md#eff-02) Prompt caching và tái sử dụng kết quả — *Nâng cao*<br>[EFF-04](mang/eff.md#eff-04) Định tuyến và cascade — đúng việc, đúng công cụ — *Nâng cao*<br>[EFF-07](mang/eff.md#eff-07) Kiểm chứng xác định và "không lỗi im lặng" — *Nâng cao*<br>[OPS-06](mang/ops.md#ops-06) LLMOps — tracing, chi phí, độ trễ — *Nâng cao*<br>[LLM-07](mang/llm.md#llm-07) Fine-tune, distill và tự host LLM — *Trung cấp* | Báo cáo chi phí mỗi tác vụ theo đơn vị nghiệp vụ + tỷ lệ lỗi lọt đo bằng kiểm tra mẫu định kỳ. |
| **D4** Bảo mật, quyền và tuân thủ | — | Quyền tối thiểu cho agent, sandbox cho tool nguy hiểm, red-teaming định kỳ, tuân thủ bảo vệ dữ liệu cá nhân cùng pháp chế. | [OPS-08](mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ — *Nâng cao*<br>[LLM-06](mang/llm.md#llm-06) An toàn và bảo mật hệ LLM — *Nâng cao* | Báo cáo red-team + danh mục dữ liệu được phép gửi ra ngoài đã được pháp chế duyệt. |
| **D5** Phương pháp ở quy mô team | — | Eval nhiều tầng (offline → shadow → A/B) chạy trong CI, taxonomy lỗi dùng chung, design doc và kế hoạch go/no-go. | [BIZ-02](mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) — *Nâng cao*<br>[BIZ-03](mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) — *Nâng cao*<br>[BIZ-04](mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) — *Nâng cao*<br>[PY-03](mang/py.md#py-03) Kiểm thử và chất lượng code — *Nâng cao*<br>[STAT-02](mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá — *Nâng cao* | Một quy trình đánh giá và phát hành dùng chung cho mọi dự án AI của team. |

## Thanh ngang chữ T — baseline cho cả 8 nhóm

Ngoài kỹ năng nền tảng, mỗi nhóm cần thêm các kỹ năng sau ở mức **Cơ bản** để dựng được baseline.

| Nhóm | Kỹ năng | Gợi ý baseline |
|---|---|---|
| [1 · Dự đoán trên dữ liệu bảng](nhom/g1-du-lieu-bang.md) | [ML-01](mang/ml.md#ml-01) Quy trình học có giám sát chuẩn, [ML-02](mang/ml.md#ml-02) Gradient boosting | Logistic regression rồi LightGBM mặc định |
| [2 · Dự báo chuỗi thời gian](nhom/g2-chuoi-thoi-gian.md) | [ML-06](mang/ml.md#ml-06) Mô hình chuỗi thời gian | Seasonal naive, ETS, backtest cuốn chiếu |
| [3 · Phát hiện bất thường](nhom/g3-bat-thuong.md) | [ML-05](mang/ml.md#ml-05) Học không giám sát và phát hiện bất thường, [ML-03](mang/ml.md#ml-03) Dữ liệu mất cân bằng và sự kiện hiếm | Luật + Isolation Forest, đo precision@k |
| [4 · Gợi ý và xếp hạng](nhom/g4-goi-y-xep-hang.md) | [ML-08](mang/ml.md#ml-08) Hệ gợi ý chuyên biệt | Baseline phổ biến, ALS |
| [5 · Thị giác máy tính và Document AI](nhom/g5-anh-tai-lieu.md) | [DL-04](mang/dl.md#dl-04) Thị giác máy tính (detection, segmentation, OCR), [DL-05](mang/dl.md#dl-05) Document AI và mô hình thị giác–ngôn ngữ (VLM) | YOLO/OCR có sẵn, VLM + schema |
| [6 · Ngôn ngữ, LLM và RAG](nhom/g6-llm-rag.md) | [LLM-01](mang/llm.md#llm-01) Gọi LLM API và prompt engineering, [LLM-02](mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra, [LLM-03](mang/llm.md#llm-03) RAG — trả lời dựa trên tài liệu | Prompt + structured output + RAG tối giản |
| [7 · AI Agent và tự động hóa quy trình](nhom/g7-agent-tu-dong-hoa.md) | [LLM-05](mang/llm.md#llm-05) Tool calling và điều phối workflow/agent | Workflow cố định + người duyệt |
| [8 · Tối ưu hóa và suy luận nhân quả](nhom/g8-toi-uu-nhan-qua.md) | [OPT-01](mang/opt.md#opt-01) Quy hoạch tuyến tính và nguyên (LP/MIP), [STAT-03](mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test | LP với OR-Tools, A/B test đúng cách |

## Thói quen xuyên suốt

- [BIZ-06](mang/biz.md#biz-06) — Mỗi tuần một paper gắn với bài toán đang làm, thử tái hiện kết quả.
- [EFF-08](mang/eff.md#eff-08) — Dùng AI hỗ trợ lập trình có kỷ luật — để `make check` làm lớp kiểm chứng.
