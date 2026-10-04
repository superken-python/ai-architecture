<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# ML · ML cổ điển

Học có giám sát, boosting, bất thường, chuỗi thời gian, truy xuất & xếp hạng.

| Kỹ năng | Tầng | Tóm tắt |
|---|---|---|
| [ML-01](#ml-01) Quy trình học có giám sát chuẩn | Cầu nối liên họ | Dựng baseline đúng cách và so sánh model công bằng. |
| [ML-02](#ml-02) Gradient boosting | Dùng chung trong họ | Công cụ mạnh nhất cho dữ liệu bảng; nền cho dự báo, xếp hạng, uplift. |
| [ML-03](#ml-03) Dữ liệu mất cân bằng và sự kiện hiếm | Cầu nối liên họ | Đánh giá và huấn luyện đúng khi lớp quan tâm chỉ chiếm vài phần nghìn. |
| [ML-04](#ml-04) Giải thích mô hình | Cầu nối liên họ | Trả lời "vì sao model quyết định vậy" cho người dùng, quản lý và pháp chế. |
| [ML-05](#ml-05) Học không giám sát và phát hiện bất thường | Dùng chung trong họ | Tìm điểm lạ khi gần như không có nhãn. |
| [ML-06](#ml-06) Mô hình chuỗi thời gian | Dùng chung trong họ | Dự báo theo thời gian, luôn đánh bại được baseline đơn giản. |
| [ML-07](#ml-07) Truy xuất và xếp hạng hai tầng (retrieve → rerank) | Cầu nối liên họ | Kiến trúc dùng chung của hệ gợi ý và RAG — lấy nhanh ứng viên rồi xếp hạng kỹ. |
| [ML-08](#ml-08) Hệ gợi ý chuyên biệt | Chuyên biệt | Cá nhân hóa danh sách gợi ý và đo bằng doanh thu thật. |

<a id="ml-01"></a>

### ML-01 · Quy trình học có giám sát chuẩn

> Dựng baseline đúng cách và so sánh model công bằng.

**Tầng:** Cầu nối liên họ · **Điểm đòn bẩy:** 10  
**Dùng cho:** ● Cốt lõi: Nhóm 1 Bảng · ● Cốt lõi: Nhóm 2 Thời gian · ● Cốt lõi: Nhóm 3 Bất thường · ● Cốt lõi: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 6 LLM/RAG · ◐ Cần: Nhóm 8 Tối ưu · ○ Ít: Nhóm 5 Ảnh/TL · ○ Ít: Nhóm 7 Agent

| Mức | Làm được |
|---|---|
| Cơ bản | train/val/test, cross-validation, Pipeline + ColumnTransformer, baseline (dummy, logistic regression), metric đúng cho phân loại/hồi quy. |
| Trung cấp | CV theo nhóm/thời gian, tuning có ngân sách (Optuna), so sánh model trên cùng split, lưu/tải pipeline. |
| Nâng cao | Ensemble/stacking có kiểm soát, học bán giám sát, active learning chọn mẫu cần gán nhãn. |

- **Tiên quyết:** [DATA-02](../mang/data.md#data-02) Xử lý dữ liệu bảng, [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả
- **Mở khóa:** [STAT-04](../mang/stat.md#stat-04), [STAT-05](../mang/stat.md#stat-05), [ML-02](../mang/ml.md#ml-02), [ML-03](../mang/ml.md#ml-03), [ML-05](../mang/ml.md#ml-05), [ML-07](../mang/ml.md#ml-07), [DL-01](../mang/dl.md#dl-01), [OPS-02](../mang/ops.md#ops-02), [EFF-04](../mang/eff.md#eff-04)
- **Công cụ:** scikit-learn, Optuna
- **Đạt khi:** Có baseline trong 1–2 ngày và bảng so sánh mọi thí nghiệm trên cùng một tập đánh giá cố định.
- **Token & độ chính xác:** TF-IDF + logistic regression phân loại văn bản gần như miễn phí — tầng đầu của cascade trước khi gọi LLM.

<a id="ml-02"></a>

### ML-02 · Gradient boosting

> Công cụ mạnh nhất cho dữ liệu bảng; nền cho dự báo, xếp hạng, uplift.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 8  
**Dùng cho:** ● Cốt lõi: Nhóm 1 Bảng · ● Cốt lõi: Nhóm 2 Thời gian · ● Cốt lõi: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 3 Bất thường · ◐ Cần: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | Train với tham số mặc định, early stopping, đọc feature importance. |
| Trung cấp | Biến phân loại (CatBoost/categorical_feature), tuning có kiểm soát, objective tùy chỉnh (quantile, tweedie, lambdarank), mô hình toàn cục cho nhiều chuỗi. |
| Nâng cao | Ràng buộc đơn điệu (quan trọng với chấm điểm tín dụng), tối ưu tốc độ suy luận, so sánh với TabPFN khi dữ liệu ít. |

- **Tiên quyết:** [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn
- **Mở khóa:** [STAT-06](../mang/stat.md#stat-06), [ML-04](../mang/ml.md#ml-04), [ML-06](../mang/ml.md#ml-06), [ML-08](../mang/ml.md#ml-08)
- **Công cụ:** LightGBM, XGBoost, CatBoost, TabPFN
- **Đạt khi:** Một mô hình LightGBM vượt baseline có ý nghĩa thống kê trên backtest theo thời gian.

<a id="ml-03"></a>

### ML-03 · Dữ liệu mất cân bằng và sự kiện hiếm

> Đánh giá và huấn luyện đúng khi lớp quan tâm chỉ chiếm vài phần nghìn.

**Tầng:** Cầu nối liên họ · **Điểm đòn bẩy:** 5  
**Dùng cho:** ● Cốt lõi: Nhóm 1 Bảng · ● Cốt lõi: Nhóm 3 Bất thường · ◐ Cần: Nhóm 5 Ảnh/TL · ○ Ít: Nhóm 4 Gợi ý

| Mức | Làm được |
|---|---|
| Cơ bản | Vì sao accuracy đánh lừa; PR-AUC, precision@k, recall tại mức cảnh báo cố định. |
| Trung cấp | class weight, focal loss, lấy mẫu lại (và tác hại của nó lên calibration), đánh giá phân tầng. |
| Nâng cao | Học từ phản hồi điều tra viên (nhãn trễ, nhãn có chọn lọc), positive-unlabeled learning. |

- **Tiên quyết:** [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn
- **Mở khóa:** —
- **Công cụ:** scikit-learn, imbalanced-learn
- **Đạt khi:** Báo cáo metric theo đúng năng lực xử lý của đội vận hành (precision@k) thay vì accuracy.

<a id="ml-04"></a>

### ML-04 · Giải thích mô hình

> Trả lời "vì sao model quyết định vậy" cho người dùng, quản lý và pháp chế.

**Tầng:** Cầu nối liên họ · **Điểm đòn bẩy:** 5  
**Dùng cho:** ● Cốt lõi: Nhóm 1 Bảng · ◐ Cần: Nhóm 3 Bất thường · ◐ Cần: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 8 Tối ưu · ○ Ít: Nhóm 4 Gợi ý · ○ Ít: Nhóm 6 LLM/RAG

| Mức | Làm được |
|---|---|
| Cơ bản | Feature importance, permutation importance, giải thích bằng ví dụ cụ thể. |
| Trung cấp | SHAP (toàn cục và từng ca), lý do từ chối (reason codes) cho tín dụng, PDP/ICE. |
| Nâng cao | Giải thích cho người không chuyên, kiểm tra công bằng theo nhóm, Grad-CAM cho ảnh, trích dẫn nguồn như "lời giải thích" của hệ LLM. |

- **Tiên quyết:** [ML-02](../mang/ml.md#ml-02) Gradient boosting
- **Mở khóa:** —
- **Công cụ:** SHAP, scikit-learn inspection, Captum
- **Đạt khi:** Danh sách top khách cho CSKH có kèm 3 lý do dễ hiểu cho từng người.

<a id="ml-05"></a>

### ML-05 · Học không giám sát và phát hiện bất thường

> Tìm điểm lạ khi gần như không có nhãn.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 3  
**Dùng cho:** ● Cốt lõi: Nhóm 3 Bất thường · ◐ Cần: Nhóm 4 Gợi ý · ○ Ít: Nhóm 1 Bảng · ○ Ít: Nhóm 2 Thời gian

| Mức | Làm được |
|---|---|
| Cơ bản | z-score, IQR, luật nghiệp vụ, Isolation Forest, K-means. |
| Trung cấp | LOF, kết hợp luật + điểm ML, đánh giá khi thiếu nhãn (gán nhãn top-k), PyOD. |
| Nâng cao | Autoencoder, bất thường theo ngữ cảnh/mùa vụ, drift của "mức bình thường", học từ phản hồi người điều tra. |

- **Tiên quyết:** [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn
- **Mở khóa:** —
- **Công cụ:** scikit-learn, PyOD
- **Đạt khi:** Danh sách cảnh báo top-k có tỷ lệ đúng đủ cao để đội vận hành chấp nhận xử lý hằng ngày.

<a id="ml-06"></a>

### ML-06 · Mô hình chuỗi thời gian

> Dự báo theo thời gian, luôn đánh bại được baseline đơn giản.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 4  
**Dùng cho:** ● Cốt lõi: Nhóm 2 Thời gian · ◐ Cần: Nhóm 3 Bất thường · ◐ Cần: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | Seasonal naive, ETS/ARIMA (statsforecast), WAPE/MASE, backtest cuốn chiếu. |
| Trung cấp | LightGBM toàn cục (mlforecast) với lag/rolling/lịch lễ, chuỗi gián đoạn (Croston/TSB) cho hàng bán chậm, cold-start mã hàng mới. |
| Nâng cao | Hierarchical reconciliation, mô hình nền tảng (Chronos, TimesFM) so với baseline, dự báo theo kịch bản khuyến mãi. |

- **Tiên quyết:** [ML-02](../mang/ml.md#ml-02) Gradient boosting, [DATA-03](../mang/data.md#data-03) Đúng thời điểm và chống rò rỉ dữ liệu
- **Mở khóa:** —
- **Công cụ:** statsforecast, mlforecast, Darts, Chronos
- **Đạt khi:** Backtest nhiều mốc cho thấy model giảm WAPE so với seasonal naive ở các mã hàng quan trọng.

<a id="ml-07"></a>

### ML-07 · Truy xuất và xếp hạng hai tầng (retrieve → rerank)

> Kiến trúc dùng chung của hệ gợi ý và RAG — lấy nhanh ứng viên rồi xếp hạng kỹ.

**Tầng:** Cầu nối liên họ · **Điểm đòn bẩy:** 6  
**Dùng cho:** ● Cốt lõi: Nhóm 4 Gợi ý · ● Cốt lõi: Nhóm 6 LLM/RAG · ◐ Cần: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 7 Agent

| Mức | Làm được |
|---|---|
| Cơ bản | BM25, embedding + cosine, Recall@K, MRR, NDCG; tự xây tập truy vấn–kết quả đúng. |
| Trung cấp | Hybrid search (BM25 + vector, RRF), chỉ mục ANN (HNSW, Faiss, Qdrant, pgvector), reranker cross-encoder, learning-to-rank. |
| Nâng cao | Fine-tune embedding/reranker trên dữ liệu nội bộ, lọc metadata và phân quyền ngay khi truy xuất, quantization vector để giảm bộ nhớ. |

- **Tiên quyết:** [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn, [DL-03](../mang/dl.md#dl-03) Embedding và học biểu diễn
- **Mở khóa:** [ML-08](../mang/ml.md#ml-08), [LLM-03](../mang/llm.md#llm-03)
- **Công cụ:** rank-bm25, Faiss, Qdrant, pgvector, sentence-transformers
- **Đạt khi:** Đo được Recall@K của tầng truy xuất tách biệt với chất lượng cuối, và cải thiện từng tầng độc lập.
- **Token & độ chính xác:** Truy xuất tốt cho phép gửi top-k nhỏ vào LLM thay vì cả tài liệu — đòn bẩy giảm token lớn nhất của RAG.

<a id="ml-08"></a>

### ML-08 · Hệ gợi ý chuyên biệt

> Cá nhân hóa danh sách gợi ý và đo bằng doanh thu thật.

**Tầng:** Chuyên biệt · **Điểm đòn bẩy:** 2  
**Dùng cho:** ● Cốt lõi: Nhóm 4 Gợi ý

| Mức | Làm được |
|---|---|
| Cơ bản | Baseline phổ biến/hay mua cùng, collaborative filtering (ALS), Recall@K/NDCG offline. |
| Trung cấp | Kiến trúc 2 tầng retrieval + ranking, two-tower, cold-start bằng nội dung, loại thứ đã mua, đa dạng hóa. |
| Nâng cao | Mô hình chuỗi hành vi (SASRec/transformer), cân bằng nhiều mục tiêu, chống popularity bias, A/B đo doanh thu. |

- **Tiên quyết:** [ML-07](../mang/ml.md#ml-07) Truy xuất và xếp hạng hai tầng (retrieve → rerank), [ML-02](../mang/ml.md#ml-02) Gradient boosting
- **Mở khóa:** —
- **Công cụ:** implicit, LightGBM LambdaRank, Faiss, RecBole
- **Đạt khi:** ALS hoặc two-tower vượt baseline phổ biến về Recall@10 và NDCG@10 trên split theo thời gian.
