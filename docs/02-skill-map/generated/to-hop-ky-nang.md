<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# Tổ hợp kỹ năng — dự án ghép nhiều nhóm

Dự án thật hiếm khi thuộc một nhóm. Mỗi tổ hợp dưới đây nêu luồng giữa các nhóm, kỹ năng cần, kỹ năng **keo** (🔗) ở điểm nối, bẫy khi ghép và metric đo từ đầu đến cuối. Nguyên tắc ghép: xem [02-ky-nang-ket-hop.md](../02-ky-nang-ket-hop.md).

| Tổ hợp | Nhóm |
|---|---|
| [CMB-01 · Hồ sơ vay / eKYC từ đầu đến cuối](#cmb-01) | 5·Ảnh/TL → 1·Bảng → 7·Agent |
| [CMB-02 · Dự báo rồi tối ưu (tồn kho, xếp ca)](#cmb-02) | 2·Thời gian → 8·Tối ưu |
| [CMB-03 · Trợ lý nội bộ có RAG và thao tác được](#cmb-03) | 6·LLM/RAG → 7·Agent |
| [CMB-04 · Phát hiện rồi giải thích (cảnh báo gian lận cho điều tra viên)](#cmb-04) | 3·Bất thường → 6·LLM/RAG → 7·Agent |
| [CMB-05 · Gợi ý và kiểm chứng bằng thí nghiệm](#cmb-05) | 4·Gợi ý → 8·Tối ưu |
| [CMB-06 · Dự đoán rồi can thiệp (churn + uplift)](#cmb-06) | 1·Bảng → 8·Tối ưu |
| [CMB-07 · Tổng đài thông minh](#cmb-07) | 6·LLM/RAG → 7·Agent → 2·Thời gian → 8·Tối ưu |
| [CMB-08 · Phân loại lai ML + LLM (cascade tiết kiệm token)](#cmb-08) | 1·Bảng → 6·LLM/RAG |
| [CMB-09 · Hỏi số liệu bằng tiếng Việt (text-to-SQL agent)](#cmb-09) | 6·LLM/RAG → 7·Agent |

<a id="cmb-01"></a>

## CMB-01 · Hồ sơ vay / eKYC từ đầu đến cuối

**Luồng:** Đọc giấy tờ và trích trường (Nhóm 5) → chấm điểm tín dụng (Nhóm 1) → điều phối quy trình, người duyệt ở bước rủi ro (Nhóm 7)  
**Ví dụ:** duyệt khoản vay tiêu dùng, mở tài khoản online

| Kỹ năng | Tầng | Vai trò |
|---|---|---|
| [DL-04](mang/dl.md#dl-04) Thị giác máy tính (detection, segmentation, OCR) | Chuyên biệt |  |
| [DL-05](mang/dl.md#dl-05) Document AI và mô hình thị giác–ngôn ngữ (VLM) | Dùng chung trong họ |  |
| [EFF-07](mang/eff.md#eff-07) Kiểm chứng xác định và "không lỗi im lặng" | Dùng chung trong họ | 🔗 keo ở điểm nối |
| [ML-02](mang/ml.md#ml-02) Gradient boosting | Dùng chung trong họ |  |
| [ML-04](mang/ml.md#ml-04) Giải thích mô hình | Cầu nối liên họ |  |
| [STAT-05](mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc | Cầu nối liên họ | 🔗 keo ở điểm nối |
| [LLM-05](mang/llm.md#llm-05) Tool calling và điều phối workflow/agent | Dùng chung trong họ |  |
| [LLM-06](mang/llm.md#llm-06) An toàn và bảo mật hệ LLM | Dùng chung trong họ |  |
| [OPS-08](mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ | Cầu nối liên họ |  |
| [OPS-06](mang/ops.md#ops-06) LLMOps — tracing, chi phí, độ trễ | Dùng chung trong họ |  |
| [LLM-02](mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra | Dùng chung trong họ | 🔗 keo ở điểm nối |

**Bẫy khi ghép:**

- Lỗi trích xuất ở Nhóm 5 đi thẳng vào model tín dụng như dữ liệu đúng — phải truyền cả độ tin cậy của từng trường.
- Model tín dụng huấn luyện trên dữ liệu nhập tay sạch, nhưng chạy trên dữ liệu OCR có lỗi → lệch phân phối.
- Agent tự quyết khoản vay mà không có người duyệt và lý do từ chối.

**Metric end-to-end:** Tỷ lệ hồ sơ xử lý tự động hoàn toàn đúng; thời gian xử lý mỗi hồ sơ; tỷ lệ nợ xấu của nhóm được duyệt tự động.

<a id="cmb-02"></a>

## CMB-02 · Dự báo rồi tối ưu (tồn kho, xếp ca)

**Luồng:** Dự báo nhu cầu dạng quantile (Nhóm 2) → tối ưu đặt hàng / xếp ca dưới ràng buộc (Nhóm 8)  
**Ví dụ:** đặt hàng cho chuỗi bán lẻ, xếp ca tổng đài theo lưu lượng dự báo

| Kỹ năng | Tầng | Vai trò |
|---|---|---|
| [ML-06](mang/ml.md#ml-06) Mô hình chuỗi thời gian | Dùng chung trong họ |  |
| [STAT-04](mang/stat.md#stat-04) Dự báo xác suất và định lượng bất định | Dùng chung trong họ | 🔗 keo ở điểm nối |
| [DATA-03](mang/data.md#data-03) Đúng thời điểm và chống rò rỉ dữ liệu | Dùng chung trong họ |  |
| [DATA-04](mang/data.md#data-04) Feature engineering cho bảng và chuỗi thời gian | Dùng chung trong họ |  |
| [OPT-01](mang/opt.md#opt-01) Quy hoạch tuyến tính và nguyên (LP/MIP) | Dùng chung trong họ |  |
| [OPT-03](mang/opt.md#opt-03) Ra quyết định dưới bất định (dự báo rồi tối ưu) | Dùng chung trong họ | 🔗 keo ở điểm nối |
| [OPS-03](mang/ops.md#ops-03) Pipeline và điều phối tác vụ | Cầu nối liên họ |  |

**Bẫy khi ghép:**

- Tối ưu trên dự báo một điểm, bỏ qua bất định → thiếu hàng ngày cao điểm.
- Đánh giá dự báo bằng WAPE nhưng không đo chi phí quyết định cuối cùng.

**Metric end-to-end:** Tổng chi phí (thiếu hàng + tồn kho + nhân sự) so với cách làm hiện tại, trên mô phỏng và thực tế.

<a id="cmb-03"></a>

## CMB-03 · Trợ lý nội bộ có RAG và thao tác được

**Luồng:** Truy xuất tài liệu/quy trình có trích dẫn (Nhóm 6) → thực hiện thao tác trên CRM/ERP theo quy trình (Nhóm 7)  
**Ví dụ:** trợ lý HR trả lời chính sách và tạo đơn nghỉ phép, trợ lý CSKH tra cứu và mở ticket

| Kỹ năng | Tầng | Vai trò |
|---|---|---|
| [LLM-03](mang/llm.md#llm-03) RAG — trả lời dựa trên tài liệu | Dùng chung trong họ |  |
| [LLM-04](mang/llm.md#llm-04) Đánh giá hệ LLM (evals) | Dùng chung trong họ |  |
| [LLM-05](mang/llm.md#llm-05) Tool calling và điều phối workflow/agent | Dùng chung trong họ | 🔗 keo ở điểm nối |
| [LLM-06](mang/llm.md#llm-06) An toàn và bảo mật hệ LLM | Dùng chung trong họ | 🔗 keo ở điểm nối |
| [ML-07](mang/ml.md#ml-07) Truy xuất và xếp hạng hai tầng (retrieve → rerank) | Cầu nối liên họ |  |
| [EFF-02](mang/eff.md#eff-02) Prompt caching và tái sử dụng kết quả | Dùng chung trong họ |  |
| [EFF-03](mang/eff.md#eff-03) Tinh gọn ngữ cảnh đầu vào | Dùng chung trong họ | 🔗 keo ở điểm nối |
| [OPS-06](mang/ops.md#ops-06) LLMOps — tracing, chi phí, độ trễ | Dùng chung trong họ |  |

**Bẫy khi ghép:**

- Nội dung tài liệu truy xuất chứa chỉ dẫn độc hại (prompt injection) khiến agent thực hiện hành động ngoài ý muốn.
- Agent thấy được tài liệu mà người hỏi không có quyền xem.
- Ngữ cảnh phình to qua nhiều lượt → chi phí tăng nhanh, chất lượng giảm.

**Metric end-to-end:** Tỷ lệ hoàn thành nhiệm vụ đúng; tỷ lệ câu trả lời có trích dẫn đúng; chi phí mỗi nhiệm vụ.

<a id="cmb-04"></a>

## CMB-04 · Phát hiện rồi giải thích (cảnh báo gian lận cho điều tra viên)

**Luồng:** Chấm điểm bất thường (Nhóm 3) → LLM tóm tắt bằng chứng cho từng cảnh báo (Nhóm 6) → hàng đợi xử lý + ghi nhận phản hồi (Nhóm 7)  
**Ví dụ:** gian lận ví điện tử, giám sát giao dịch đáng ngờ

| Kỹ năng | Tầng | Vai trò |
|---|---|---|
| [ML-05](mang/ml.md#ml-05) Học không giám sát và phát hiện bất thường | Dùng chung trong họ |  |
| [ML-03](mang/ml.md#ml-03) Dữ liệu mất cân bằng và sự kiện hiếm | Cầu nối liên họ |  |
| [DATA-07](mang/data.md#data-07) Dữ liệu đồ thị | Chuyên biệt |  |
| [STAT-05](mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc | Cầu nối liên họ | 🔗 keo ở điểm nối |
| [LLM-02](mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra | Dùng chung trong họ | 🔗 keo ở điểm nối |
| [EFF-07](mang/eff.md#eff-07) Kiểm chứng xác định và "không lỗi im lặng" | Dùng chung trong họ |  |
| [OPS-07](mang/ops.md#ops-07) Real-time và streaming | Dùng chung trong họ |  |
| [OPS-04](mang/ops.md#ops-04) Giám sát model và drift | Cầu nối liên họ |  |

**Bẫy khi ghép:**

- LLM "bịa" lý do không có trong dữ liệu — tóm tắt phải dựa trên trường dữ liệu cụ thể, kiểm tra được.
- Không thu thập phản hồi của điều tra viên → model không học được từ sai lầm.

**Metric end-to-end:** precision@k theo năng lực xử lý; thời gian điều tra mỗi cảnh báo; số tiền gian lận chặn được.

<a id="cmb-05"></a>

## CMB-05 · Gợi ý và kiểm chứng bằng thí nghiệm

**Luồng:** Sinh danh sách gợi ý (Nhóm 4) → đo tác động thật bằng A/B test hoặc bandit (Nhóm 8)  
**Ví dụ:** gợi ý sản phẩm trên app, bán chéo bảo hiểm

| Kỹ năng | Tầng | Vai trò |
|---|---|---|
| [ML-07](mang/ml.md#ml-07) Truy xuất và xếp hạng hai tầng (retrieve → rerank) | Cầu nối liên họ |  |
| [ML-08](mang/ml.md#ml-08) Hệ gợi ý chuyên biệt | Chuyên biệt |  |
| [STAT-03](mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test | Cầu nối liên họ | 🔗 keo ở điểm nối |
| [OPT-04](mang/opt.md#opt-04) Bandit và học tăng cường cơ bản | Dùng chung trong họ | 🔗 keo ở điểm nối |
| [STAT-06](mang/stat.md#stat-06) Suy luận nhân quả và uplift | Dùng chung trong họ |  |
| [OPS-04](mang/ops.md#ops-04) Giám sát model và drift | Cầu nối liên họ |  |

**Bẫy khi ghép:**

- Metric offline tăng nhưng doanh thu online không đổi.
- Vòng lặp phản hồi — chỉ gợi ý thứ đã phổ biến, dữ liệu huấn luyện ngày càng lệch.

**Metric end-to-end:** Doanh thu mỗi phiên / tỷ lệ chuyển đổi tăng có ý nghĩa thống kê trong A/B test.

<a id="cmb-06"></a>

## CMB-06 · Dự đoán rồi can thiệp (churn + uplift)

**Luồng:** Dự đoán khả năng rời bỏ (Nhóm 1) → chọn khách mà can thiệp thật sự thay đổi kết quả (Nhóm 8, uplift)  
**Ví dụ:** giữ chân khách hàng viễn thông, tặng ưu đãi có chọn lọc

| Kỹ năng | Tầng | Vai trò |
|---|---|---|
| [ML-02](mang/ml.md#ml-02) Gradient boosting | Dùng chung trong họ |  |
| [ML-04](mang/ml.md#ml-04) Giải thích mô hình | Cầu nối liên họ |  |
| [STAT-05](mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc | Cầu nối liên họ |  |
| [STAT-06](mang/stat.md#stat-06) Suy luận nhân quả và uplift | Dùng chung trong họ | 🔗 keo ở điểm nối |
| [STAT-03](mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test | Cầu nối liên họ |  |
| [DATA-03](mang/data.md#data-03) Đúng thời điểm và chống rò rỉ dữ liệu | Dùng chung trong họ |  |

**Bẫy khi ghép:**

- Gọi cho khách có điểm churn cao nhất — nhiều người trong số đó sẽ rời đi dù có gọi hay không.
- Không có nhóm đối chứng nên không đo được hiệu quả chiến dịch.

**Metric end-to-end:** Lợi nhuận tăng thêm của chiến dịch so với nhóm đối chứng.

<a id="cmb-07"></a>

## CMB-07 · Tổng đài thông minh

**Luồng:** Ghi âm → ASR → phân loại/tóm tắt (Nhóm 6) → chuyển ticket (Nhóm 7); lưu lượng lịch sử → dự báo cuộc gọi (Nhóm 2) → xếp ca (Nhóm 8)  
**Ví dụ:** tổng đài ngân hàng, CSKH thương mại điện tử

| Kỹ năng | Tầng | Vai trò |
|---|---|---|
| [DL-06](mang/dl.md#dl-06) Xử lý giọng nói (ASR) | Chuyên biệt |  |
| [LLM-01](mang/llm.md#llm-01) Gọi LLM API và prompt engineering | Dùng chung trong họ |  |
| [LLM-02](mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra | Dùng chung trong họ | 🔗 keo ở điểm nối |
| [EFF-04](mang/eff.md#eff-04) Định tuyến và cascade — đúng việc, đúng công cụ | Dùng chung trong họ | 🔗 keo ở điểm nối |
| [EFF-06](mang/eff.md#eff-06) Xử lý theo lô và bất đồng bộ | Dùng chung trong họ |  |
| [LLM-05](mang/llm.md#llm-05) Tool calling và điều phối workflow/agent | Dùng chung trong họ |  |
| [ML-06](mang/ml.md#ml-06) Mô hình chuỗi thời gian | Dùng chung trong họ |  |
| [OPT-02](mang/opt.md#opt-02) Tối ưu tổ hợp — định tuyến và lập lịch | Chuyên biệt |  |

**Bẫy khi ghép:**

- Gửi toàn bộ transcript dài vào LLM cho mọi cuộc gọi — chi phí lớn trong khi phần lớn cuộc gọi là câu hỏi lặp lại.
- Lỗi ASR ở tên riêng/số tài khoản làm sai bước phân loại phía sau.

**Metric end-to-end:** Tỷ lệ chuyển đúng bộ phận; thời gian chờ; chi phí xử lý mỗi cuộc gọi; mức đáp ứng SLA theo ca.

<a id="cmb-08"></a>

## CMB-08 · Phân loại lai ML + LLM (cascade tiết kiệm token)

**Luồng:** Luật → model nhỏ (TF-IDF/PhoBERT, kỹ năng Nhóm 1) xử lý ca dễ có độ tin cậy cao → LLM xử lý ca khó (Nhóm 6) → người xử lý ca vẫn nghi ngờ  
**Ví dụ:** phân loại ticket, gắn nhãn email, phân loại giao dịch

| Kỹ năng | Tầng | Vai trò |
|---|---|---|
| [ML-01](mang/ml.md#ml-01) Quy trình học có giám sát chuẩn | Cầu nối liên họ |  |
| [DL-02](mang/dl.md#dl-02) Transfer learning và fine-tune mô hình pretrained | Dùng chung trong họ |  |
| [STAT-05](mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc | Cầu nối liên họ | 🔗 keo ở điểm nối |
| [LLM-02](mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra | Dùng chung trong họ |  |
| [LLM-04](mang/llm.md#llm-04) Đánh giá hệ LLM (evals) | Dùng chung trong họ |  |
| [EFF-04](mang/eff.md#eff-04) Định tuyến và cascade — đúng việc, đúng công cụ | Dùng chung trong họ | 🔗 keo ở điểm nối |
| [EFF-05](mang/eff.md#eff-05) Kiểm soát đầu ra và mức suy luận | Dùng chung trong họ |  |
| [EFF-07](mang/eff.md#eff-07) Kiểm chứng xác định và "không lỗi im lặng" | Dùng chung trong họ |  |

**Bẫy khi ghép:**

- Ngưỡng chuyển tầng chọn theo cảm giác → model nhỏ "tự tin sai" và lỗi lọt qua.
- Đo độ chính xác chung mà không đo riêng từng tầng.

**Metric end-to-end:** Độ chính xác trên phần tự động; tỷ lệ tự động; chi phí trung bình mỗi ticket.

<a id="cmb-09"></a>

## CMB-09 · Hỏi số liệu bằng tiếng Việt (text-to-SQL agent)

**Luồng:** Câu hỏi tự nhiên → chọn bảng/metric (schema linking) → sinh và kiểm tra SQL → chạy → diễn giải kết quả (Nhóm 6 + 7)  
**Ví dụ:** hỏi doanh thu theo chi nhánh, tra số dư công nợ

| Kỹ năng | Tầng | Vai trò |
|---|---|---|
| [DATA-01](mang/data.md#data-01) SQL phân tích | Cầu nối liên họ |  |
| [LLM-08](mang/llm.md#llm-08) Text-to-SQL và hỏi đáp số liệu | Dùng chung trong họ | 🔗 keo ở điểm nối |
| [LLM-02](mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra | Dùng chung trong họ |  |
| [LLM-04](mang/llm.md#llm-04) Đánh giá hệ LLM (evals) | Dùng chung trong họ |  |
| [EFF-03](mang/eff.md#eff-03) Tinh gọn ngữ cảnh đầu vào | Dùng chung trong họ |  |
| [EFF-07](mang/eff.md#eff-07) Kiểm chứng xác định và "không lỗi im lặng" | Dùng chung trong họ | 🔗 keo ở điểm nối |
| [OPS-08](mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ | Cầu nối liên họ |  |

**Bẫy khi ghép:**

- LLM tự "nhẩm" con số thay vì để SQL tính.
- So sánh chuỗi SQL thay vì so sánh kết quả truy vấn khi đánh giá.
- Truy vấn được phép đọc bảng nhạy cảm.

**Metric end-to-end:** Tỷ lệ câu trả lời có con số đúng tuyệt đối trên golden set; tỷ lệ hỏi lại đúng lúc với câu mơ hồ.
