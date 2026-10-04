<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# DATA · SQL & dữ liệu

Truy vấn, xử lý, kiểm định dữ liệu và làm đặc trưng; đúng thời điểm, không rò rỉ.

| Kỹ năng | Tầng | Tóm tắt |
|---|---|---|
| [DATA-01](#data-01) SQL phân tích | Cầu nối liên họ | Lấy đúng dữ liệu, đúng thời điểm từ kho dữ liệu doanh nghiệp. |
| [DATA-02](#data-02) Xử lý dữ liệu bảng | Dùng chung trong họ | Làm sạch, biến đổi, ghép nối dữ liệu bảng nhanh và đúng. |
| [DATA-03](#data-03) Đúng thời điểm và chống rò rỉ dữ liệu | Dùng chung trong họ | Bảo đảm model chỉ "nhìn thấy" thông tin có sẵn tại thời điểm ra quyết định. |
| [DATA-04](#data-04) Feature engineering cho bảng và chuỗi thời gian | Dùng chung trong họ | Biến dữ liệu thô thành tín hiệu mà model học được. |
| [DATA-05](#data-05) Kiểm định chất lượng dữ liệu và nhãn | Nền tảng chung | Phát hiện dữ liệu hỏng, nhãn sai trước khi chúng làm hỏng model. |
| [DATA-06](#data-06) Văn bản tiếng Việt và dữ liệu phi cấu trúc | Dùng chung trong họ | Chuẩn hóa và làm sạch văn bản tiếng Việt để tìm kiếm, phân loại, đếm token chính xác. |
| [DATA-07](#data-07) Dữ liệu đồ thị | Chuyên biệt | Biểu diễn quan hệ (tài khoản–thiết bị–giao dịch) để phát hiện mẫu mà dữ liệu bảng bỏ sót. |

<a id="data-01"></a>

### DATA-01 · SQL phân tích

> Lấy đúng dữ liệu, đúng thời điểm từ kho dữ liệu doanh nghiệp.

**Tầng:** Cầu nối liên họ · **Điểm đòn bẩy:** 11  
**Dùng cho:** ● Cốt lõi: Nhóm 1 Bảng · ● Cốt lõi: Nhóm 2 Thời gian · ● Cốt lõi: Nhóm 3 Bất thường · ● Cốt lõi: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 6 LLM/RAG · ◐ Cần: Nhóm 7 Agent · ◐ Cần: Nhóm 8 Tối ưu · ○ Ít: Nhóm 5 Ảnh/TL

| Mức | Làm được |
|---|---|
| Cơ bản | SELECT/WHERE/GROUP BY/JOIN, xử lý NULL, kiểu ngày giờ; truy vấn KPI tổng hợp. |
| Trung cấp | Window function (LAG, ROW_NUMBER, rolling), CTE, truy vấn "as-of" theo mốc thời gian, đọc EXPLAIN; DuckDB để phân tích tại máy. |
| Nâng cao | Mô hình dữ liệu (star schema, SCD type 2), dbt, tầng ngữ nghĩa (semantic layer) cho text-to-SQL, phân quyền theo hàng/cột. |

- **Tiên quyết:** —
- **Mở khóa:** [DATA-03](../mang/data.md#data-03), [LLM-08](../mang/llm.md#llm-08)
- **Công cụ:** PostgreSQL, DuckDB, dbt
- **Đạt khi:** Viết được truy vấn tạo bảng huấn luyện theo từng mốc thời gian, kết quả khớp với số liệu báo cáo chính thức.

<a id="data-02"></a>

### DATA-02 · Xử lý dữ liệu bảng

> Làm sạch, biến đổi, ghép nối dữ liệu bảng nhanh và đúng.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 9  
**Dùng cho:** ● Cốt lõi: Nhóm 1 Bảng · ● Cốt lõi: Nhóm 2 Thời gian · ● Cốt lõi: Nhóm 3 Bất thường · ● Cốt lõi: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 8 Tối ưu · ○ Ít: Nhóm 5 Ảnh/TL · ○ Ít: Nhóm 6 LLM/RAG · ○ Ít: Nhóm 7 Agent

| Mức | Làm được |
|---|---|
| Cơ bản | Đọc, lọc, groupby, merge, pivot; xử lý thiếu/trùng; ép kiểu dữ liệu. |
| Trung cấp | polars/DuckDB cho dữ liệu lớn hơn RAM, Parquet, ngày giờ và múi giờ, kiểm tra trùng khóa sau merge. |
| Nâng cao | Pipeline tăng dần (incremental) tái lập được, tối ưu bộ nhớ cho hàng chục triệu dòng. |

- **Tiên quyết:** [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI
- **Mở khóa:** [DATA-03](../mang/data.md#data-03), [DATA-04](../mang/data.md#data-04), [DATA-05](../mang/data.md#data-05), [DATA-07](../mang/data.md#data-07), [ML-01](../mang/ml.md#ml-01)
- **Công cụ:** pandas, polars, DuckDB, pyarrow
- **Đạt khi:** Xử lý bảng 10 triệu dòng trên laptop trong vài phút, không sinh dòng trùng sau khi ghép.

<a id="data-03"></a>

### DATA-03 · Đúng thời điểm và chống rò rỉ dữ liệu

> Bảo đảm model chỉ "nhìn thấy" thông tin có sẵn tại thời điểm ra quyết định.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 9  
**Dùng cho:** ● Cốt lõi: Nhóm 1 Bảng · ● Cốt lõi: Nhóm 2 Thời gian · ● Cốt lõi: Nhóm 3 Bất thường · ● Cốt lõi: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | Nhận biết leakage; chia train/test theo thời gian; loại cột được tạo sau thời điểm dự đoán. |
| Trung cấp | Xây feature "as-of" (chỉ dùng dữ liệu trước mốc cắt), backtest cuốn chiếu, phát hiện leakage qua feature importance bất thường. |
| Nâng cao | Point-in-time join trong feature store, cửa sổ nhãn và khoảng trống (gap) giữa feature và nhãn, mô phỏng đúng độ trễ dữ liệu ở production. |

- **Tiên quyết:** [DATA-01](../mang/data.md#data-01) SQL phân tích, [DATA-02](../mang/data.md#data-02) Xử lý dữ liệu bảng
- **Mở khóa:** [DATA-04](../mang/data.md#data-04), [ML-06](../mang/ml.md#ml-06)
- **Công cụ:** SQL window function, pandas merge_asof, scikit-learn TimeSeriesSplit
- **Đạt khi:** Kết quả offline và kết quả chạy thật lệch nhau trong biên sai số đã ước lượng, không "đẹp bất thường".

<a id="data-04"></a>

### DATA-04 · Feature engineering cho bảng và chuỗi thời gian

> Biến dữ liệu thô thành tín hiệu mà model học được.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 9  
**Dùng cho:** ● Cốt lõi: Nhóm 1 Bảng · ● Cốt lõi: Nhóm 2 Thời gian · ● Cốt lõi: Nhóm 3 Bất thường · ● Cốt lõi: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | Biến đổi số/phân loại, aggregate theo khách hàng (RFM), đặc trưng ngày (thứ, tháng, ngày lễ). |
| Trung cấp | lag/rolling/EWM, target encoding out-of-fold, đặc trưng lịch âm (Tết, rằm), khuyến mãi, ngày nhận lương. |
| Nâng cao | Đặc trưng chuỗi hành vi, đặc trưng đồ thị, tự động hóa và giám sát chất lượng feature. |

- **Tiên quyết:** [DATA-02](../mang/data.md#data-02) Xử lý dữ liệu bảng, [DATA-03](../mang/data.md#data-03) Đúng thời điểm và chống rò rỉ dữ liệu
- **Mở khóa:** [OPS-07](../mang/ops.md#ops-07)
- **Công cụ:** pandas, polars, Featuretools, lunardate hoặc lịch âm tự xây
- **Đạt khi:** Feature mới cải thiện metric trên backtest theo thời gian, không chỉ trên split ngẫu nhiên.

<a id="data-05"></a>

### DATA-05 · Kiểm định chất lượng dữ liệu và nhãn

> Phát hiện dữ liệu hỏng, nhãn sai trước khi chúng làm hỏng model.

**Tầng:** Nền tảng chung · **Điểm đòn bẩy:** 8  
**Dùng cho:** ◐ Cần: Nhóm 1 Bảng · ◐ Cần: Nhóm 2 Thời gian · ◐ Cần: Nhóm 3 Bất thường · ◐ Cần: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 6 LLM/RAG · ◐ Cần: Nhóm 7 Agent · ◐ Cần: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | Kiểm tra schema, giá trị thiếu, trùng, khoảng giá trị; profile dữ liệu trước khi train. |
| Trung cấp | Validation tự động trong pipeline (pandera/Great Expectations), kiểm tra chất lượng nhãn (độ đồng thuận người gán, nhãn mâu thuẫn). |
| Nâng cao | Data contract giữa các team, cảnh báo khi nguồn đổi định dạng, tìm và sửa nhãn sai có hệ thống (cleanlab). |

- **Tiên quyết:** [DATA-02](../mang/data.md#data-02) Xử lý dữ liệu bảng
- **Mở khóa:** —
- **Công cụ:** pandera, Great Expectations, cleanlab
- **Đạt khi:** Pipeline tự dừng và báo lỗi rõ ràng khi dữ liệu đầu vào sai schema hoặc lệch phân phối mạnh.

<a id="data-06"></a>

### DATA-06 · Văn bản tiếng Việt và dữ liệu phi cấu trúc

> Chuẩn hóa và làm sạch văn bản tiếng Việt để tìm kiếm, phân loại, đếm token chính xác.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 2  
**Dùng cho:** ◐ Cần: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 6 LLM/RAG · ○ Ít: Nhóm 7 Agent

| Mức | Làm được |
|---|---|
| Cơ bản | Chuẩn hóa Unicode NFC (dấu dựng sẵn vs dấu tổ hợp), làm sạch HTML/khoảng trắng, regex cho số điện thoại, CCCD, mã số thuế, số tiền. |
| Trung cấp | Tách từ tiếng Việt (underthesea, pyvi) cho BM25, xử lý văn bản không dấu/viết tắt, chuẩn hóa số và ngày kiểu Việt Nam (1.000.000,50 vs 1,000,000.50). |
| Nâng cao | Pipeline làm sạch quy mô lớn, khử trùng lặp gần đúng (MinHash), ẩn danh hóa PII trước khi gửi ra API bên ngoài. |

- **Tiên quyết:** [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI
- **Mở khóa:** [LLM-03](../mang/llm.md#llm-03)
- **Công cụ:** unicodedata, underthesea, pyvi, regex, datasketch
- **Đạt khi:** Cùng một câu gõ bằng hai bộ gõ khác nhau cho ra cùng kết quả tìm kiếm; PII được che trước khi rời hệ thống.
- **Token & độ chính xác:** Làm sạch boilerplate/HTML và khử trùng lặp trước khi gửi LLM giảm token đầu vào trực tiếp.

<a id="data-07"></a>

### DATA-07 · Dữ liệu đồ thị

> Biểu diễn quan hệ (tài khoản–thiết bị–giao dịch) để phát hiện mẫu mà dữ liệu bảng bỏ sót.

**Tầng:** Chuyên biệt · **Điểm đòn bẩy:** 1  
**Dùng cho:** ◐ Cần: Nhóm 3 Bất thường · ○ Ít: Nhóm 4 Gợi ý · ○ Ít: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | Dựng đồ thị từ bảng quan hệ; bậc, thành phần liên thông. |
| Trung cấp | Đặc trưng đồ thị (PageRank, cộng đồng) đưa vào model bảng; truy vấn đồ thị. |
| Nâng cao | Phát hiện vòng gian lận (fraud ring), graph neural network khi đã có baseline vững. |

- **Tiên quyết:** [DATA-02](../mang/data.md#data-02) Xử lý dữ liệu bảng
- **Mở khóa:** —
- **Công cụ:** NetworkX, igraph, Neo4j, PyTorch Geometric
- **Đạt khi:** Thêm đặc trưng đồ thị làm tăng precision@k của mô hình gian lận so với chỉ dùng đặc trưng bảng.
