<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# STAT · Thống kê & thực nghiệm

Đo lường bất định, thí nghiệm, calibration, nhân quả — để kết luận đúng.

| Kỹ năng | Tầng | Tóm tắt |
|---|---|---|
| [STAT-01](#stat-01) Xác suất và thống kê mô tả | Nền tảng chung | Đọc dữ liệu và metric đúng, hiểu vì sao tỷ lệ nền quyết định ý nghĩa của mọi con số. |
| [STAT-02](#stat-02) Đo lường bất định của kết quả đánh giá | Nền tảng chung | Biết khi nào chênh lệch giữa hai model/prompt là thật, khi nào chỉ là nhiễu. |
| [STAT-03](#stat-03) Thiết kế thí nghiệm và A/B test | Cầu nối liên họ | Đo tác động thật của model/tính năng lên KPI kinh doanh. |
| [STAT-04](#stat-04) Dự báo xác suất và định lượng bất định | Dùng chung trong họ | Đưa ra khoảng dự báo thay vì một con số, để quyết định tính được rủi ro. |
| [STAT-05](#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc | Cầu nối liên họ | Biến điểm số của model thành quyết định — tự động ca chắc chắn, chuyển người ca nghi ngờ. |
| [STAT-06](#stat-06) Suy luận nhân quả và uplift | Dùng chung trong họ | Ước lượng tác động thật của một hành động, không nhầm tương quan với nhân quả. |

<a id="stat-01"></a>

### STAT-01 · Xác suất và thống kê mô tả

> Đọc dữ liệu và metric đúng, hiểu vì sao tỷ lệ nền quyết định ý nghĩa của mọi con số.

**Tầng:** Nền tảng chung · **Điểm đòn bẩy:** 12  
**Dùng cho:** ● Cốt lõi: Nhóm 1 Bảng · ● Cốt lõi: Nhóm 2 Thời gian · ● Cốt lõi: Nhóm 3 Bất thường · ● Cốt lõi: Nhóm 8 Tối ưu · ◐ Cần: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 6 LLM/RAG · ◐ Cần: Nhóm 7 Agent

| Mức | Làm được |
|---|---|
| Cơ bản | Phân phối, trung bình/trung vị/phân vị, phương sai, tương quan, tỷ lệ nền (base rate); đọc histogram/boxplot. |
| Trung cấp | Định lý giới hạn trung tâm, luật Bayes (vì sao 99% accuracy vô dụng khi gian lận chỉ 0,1%), sai lệch chọn mẫu. |
| Nâng cao | Mô hình Bayes/phân cấp, dữ liệu bị kiểm duyệt (survival cho churn), phân tích công suất thống kê. |

- **Tiên quyết:** —
- **Mở khóa:** [STAT-02](../mang/stat.md#stat-02), [STAT-04](../mang/stat.md#stat-04), [STAT-05](../mang/stat.md#stat-05), [ML-01](../mang/ml.md#ml-01)
- **Công cụ:** numpy, scipy, statsmodels, matplotlib
- **Đạt khi:** Giải thích được cho người ngoài ngành vì sao một model "99% chính xác" có thể không có giá trị.

<a id="stat-02"></a>

### STAT-02 · Đo lường bất định của kết quả đánh giá

> Biết khi nào chênh lệch giữa hai model/prompt là thật, khi nào chỉ là nhiễu.

**Tầng:** Nền tảng chung · **Điểm đòn bẩy:** 13  
**Dùng cho:** ● Cốt lõi: Nhóm 1 Bảng · ● Cốt lõi: Nhóm 2 Thời gian · ● Cốt lõi: Nhóm 3 Bất thường · ● Cốt lõi: Nhóm 6 LLM/RAG · ● Cốt lõi: Nhóm 8 Tối ưu · ◐ Cần: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 7 Agent

| Mức | Làm được |
|---|---|
| Cơ bản | Khoảng tin cậy cho tỷ lệ — golden set 100 câu đạt 90% thì khoảng tin cậy 95% xấp xỉ ±6 điểm phần trăm; không kết luận từ chênh lệch nhỏ hơn sai số. |
| Trung cấp | Bootstrap cho mọi metric (F1, NDCG, WAPE), so sánh cặp hai hệ trên cùng tập (paired bootstrap, McNemar), ước lượng cỡ golden set cần thiết. |
| Nâng cao | Kiểm soát nhiều phép so sánh khi thử nhiều prompt/model (tránh overfit tập đánh giá), tách dev/test cho eval, lấy mẫu phân tầng để người kiểm tra. |

- **Tiên quyết:** [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả
- **Mở khóa:** [STAT-03](../mang/stat.md#stat-03), [LLM-04](../mang/llm.md#llm-04), [OPS-04](../mang/ops.md#ops-04)
- **Công cụ:** scipy.stats, numpy, statsmodels
- **Đạt khi:** Mọi bảng so sánh model/prompt đều kèm khoảng tin cậy, và quyết định chọn được giải thích bằng nó.
- **Token & độ chính xác:** Là công cụ để chứng minh một tối ưu token "không làm giảm chất lượng" — không có nó thì chỉ là cảm giác.

<a id="stat-03"></a>

### STAT-03 · Thiết kế thí nghiệm và A/B test

> Đo tác động thật của model/tính năng lên KPI kinh doanh.

**Tầng:** Cầu nối liên họ · **Điểm đòn bẩy:** 6  
**Dùng cho:** ● Cốt lõi: Nhóm 4 Gợi ý · ● Cốt lõi: Nhóm 8 Tối ưu · ◐ Cần: Nhóm 1 Bảng · ◐ Cần: Nhóm 6 LLM/RAG · ○ Ít: Nhóm 2 Thời gian · ○ Ít: Nhóm 3 Bất thường · ○ Ít: Nhóm 7 Agent

| Mức | Làm được |
|---|---|
| Cơ bản | Giả thuyết, nhóm đối chứng, ngẫu nhiên hóa, p-value và ý nghĩa thực tế, tính cỡ mẫu trước khi chạy. |
| Trung cấp | Lỗi "nhìn trộm" và dừng sớm, metric bảo vệ (guardrail), đơn vị ngẫu nhiên hóa (người dùng vs phiên), CUPED giảm phương sai. |
| Nâng cao | Thử nghiệm tuần tự (sequential), switchback cho hệ có hiệu ứng mạng, interleaving cho xếp hạng. |

- **Tiên quyết:** [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá
- **Mở khóa:** [STAT-06](../mang/stat.md#stat-06), [OPT-04](../mang/opt.md#opt-04)
- **Công cụ:** statsmodels, scipy, GrowthBook
- **Đạt khi:** Thiết kế được một A/B test có cỡ mẫu, thời gian chạy và tiêu chí dừng chốt trước khi bắt đầu.

<a id="stat-04"></a>

### STAT-04 · Dự báo xác suất và định lượng bất định

> Đưa ra khoảng dự báo thay vì một con số, để quyết định tính được rủi ro.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 4  
**Dùng cho:** ● Cốt lõi: Nhóm 2 Thời gian · ● Cốt lõi: Nhóm 8 Tối ưu · ○ Ít: Nhóm 1 Bảng · ○ Ít: Nhóm 3 Bất thường

| Mức | Làm được |
|---|---|
| Cơ bản | Khoảng dự báo vs dự báo điểm; đọc quantile P10/P50/P90; pinball loss. |
| Trung cấp | Quantile regression (LightGBM objective=quantile), conformal prediction cho khoảng có bảo đảm độ phủ. |
| Nâng cao | Dự báo phân phối đầy đủ, mô phỏng Monte Carlo làm đầu vào tối ưu, theo dõi độ phủ thực tế theo thời gian. |

- **Tiên quyết:** [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả, [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn
- **Mở khóa:** [OPT-03](../mang/opt.md#opt-03)
- **Công cụ:** LightGBM, MAPIE, statsforecast
- **Đạt khi:** Khoảng dự báo 80% thực sự chứa giá trị thật khoảng 80% số lần trên dữ liệu backtest.

<a id="stat-05"></a>

### STAT-05 · Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc

> Biến điểm số của model thành quyết định — tự động ca chắc chắn, chuyển người ca nghi ngờ.

**Tầng:** Cầu nối liên họ · **Điểm đòn bẩy:** 8  
**Dùng cho:** ● Cốt lõi: Nhóm 1 Bảng · ● Cốt lõi: Nhóm 3 Bất thường · ◐ Cần: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 6 LLM/RAG · ◐ Cần: Nhóm 7 Agent · ◐ Cần: Nhóm 8 Tối ưu · ○ Ít: Nhóm 4 Gợi ý

| Mức | Làm được |
|---|---|
| Cơ bản | Ma trận nhầm lẫn, precision/recall theo ngưỡng, chọn ngưỡng theo chi phí từng loại sai và năng lực xử lý (top-k mỗi ngày). |
| Trung cấp | Hiệu chỉnh xác suất (Platt, isotonic), biểu đồ reliability, đường coverage–accuracy để chọn phần được tự động hóa. |
| Nâng cao | Selective prediction có bảo đảm (conformal risk control); điểm tin cậy cho đầu ra LLM/OCR từ tín hiệu ngoài model (luật kiểm tra, đối chiếu chéo, đồng thuận nhiều lần chạy). |

- **Tiên quyết:** [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả, [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn
- **Mở khóa:** [EFF-07](../mang/eff.md#eff-07)
- **Công cụ:** scikit-learn calibration, MAPIE
- **Đạt khi:** Vẽ được đường coverage–accuracy và chọn được mức tự động hóa đạt độ chính xác mục tiêu trên phần tự động.
- **Token & độ chính xác:** Kỹ năng then chốt để vừa rẻ vừa "chính xác tuyệt đối" trên phần tự động — phần nghi ngờ đi đường đắt hơn (model lớn hoặc người).

<a id="stat-06"></a>

### STAT-06 · Suy luận nhân quả và uplift

> Ước lượng tác động thật của một hành động, không nhầm tương quan với nhân quả.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 3  
**Dùng cho:** ● Cốt lõi: Nhóm 8 Tối ưu · ◐ Cần: Nhóm 4 Gợi ý · ○ Ít: Nhóm 1 Bảng

| Mức | Làm được |
|---|---|
| Cơ bản | Tương quan ≠ nhân quả; biến gây nhiễu; vì sao cần nhóm đối chứng. |
| Trung cấp | DAG nhân quả, difference-in-differences, uplift modeling (T-/X-learner), đánh giá bằng đường Qini/uplift. |
| Nâng cao | DoWhy/EconML (double ML, causal forest), synthetic control, off-policy evaluation cho chính sách và gợi ý. |

- **Tiên quyết:** [STAT-03](../mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test, [ML-02](../mang/ml.md#ml-02) Gradient boosting
- **Mở khóa:** —
- **Công cụ:** DoWhy, EconML, CausalML
- **Đạt khi:** Chọn được nhóm khách "thuyết phục được" bằng uplift và chứng minh bằng thí nghiệm rằng họ mang lại lợi nhuận cao hơn nhóm điểm churn cao nhất.
