<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# DL · Deep learning

PyTorch, transfer learning, embedding, thị giác máy tính, Document AI, giọng nói.

| Kỹ năng | Tầng | Tóm tắt |
|---|---|---|
| [DL-01](#dl-01) PyTorch nền tảng | Cầu nối liên họ | Tự viết và gỡ lỗi vòng huấn luyện mạng nơ-ron. |
| [DL-02](#dl-02) Transfer learning và fine-tune mô hình pretrained | Dùng chung trong họ | Tận dụng mô hình có sẵn để đạt chất lượng cao với ít dữ liệu. |
| [DL-03](#dl-03) Embedding và học biểu diễn | Cầu nối liên họ | Biểu diễn văn bản, ảnh, người dùng, sản phẩm thành vector để so sánh và tìm kiếm. |
| [DL-04](#dl-04) Thị giác máy tính (detection, segmentation, OCR) | Chuyên biệt | Nhận diện vật thể, vùng lỗi và chữ trong ảnh chụp thực tế. |
| [DL-05](#dl-05) Document AI và mô hình thị giác–ngôn ngữ (VLM) | Dùng chung trong họ | Trích xuất dữ liệu có cấu trúc từ hóa đơn, hợp đồng, giấy tờ nhiều mẫu. |
| [DL-06](#dl-06) Xử lý giọng nói (ASR) | Chuyên biệt | Chuyển ghi âm tổng đài tiếng Việt thành văn bản để phân tích. |

<a id="dl-01"></a>

### DL-01 · PyTorch nền tảng

> Tự viết và gỡ lỗi vòng huấn luyện mạng nơ-ron.

**Tầng:** Cầu nối liên họ · **Điểm đòn bẩy:** 6  
**Dùng cho:** ● Cốt lõi: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 2 Thời gian · ◐ Cần: Nhóm 3 Bất thường · ◐ Cần: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 6 LLM/RAG · ○ Ít: Nhóm 1 Bảng · ○ Ít: Nhóm 7 Agent · ○ Ít: Nhóm 8 Tối ưu

| Mức | Làm được |
|---|---|
| Cơ bản | Tensor, autograd, vòng huấn luyện, Dataset/DataLoader, chạy trên GPU, lưu checkpoint. |
| Trung cấp | Mixed precision, gradient accumulation, scheduler, theo dõi overfit, tái lập kết quả (seed). |
| Nâng cao | Huấn luyện phân tán (DDP), tối ưu bộ nhớ, loss/kiến trúc tùy chỉnh, gỡ lỗi khi không hội tụ. |

- **Tiên quyết:** [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI, [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn
- **Mở khóa:** [DL-02](../mang/dl.md#dl-02), [OPS-05](../mang/ops.md#ops-05)
- **Công cụ:** PyTorch, Lightning, TensorBoard
- **Đạt khi:** Tự viết vòng huấn luyện cho một bài phân loại ảnh, giải thích được đường loss.

<a id="dl-02"></a>

### DL-02 · Transfer learning và fine-tune mô hình pretrained

> Tận dụng mô hình có sẵn để đạt chất lượng cao với ít dữ liệu.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 3  
**Dùng cho:** ● Cốt lõi: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 6 LLM/RAG · ○ Ít: Nhóm 3 Bất thường · ○ Ít: Nhóm 4 Gợi ý

| Mức | Làm được |
|---|---|
| Cơ bản | Hugging Face pipeline; fine-tune ResNet/ViT phân loại ảnh; fine-tune PhoBERT phân loại văn bản tiếng Việt. |
| Trung cấp | PEFT/LoRA, augmentation, chiến lược đóng băng tầng, đánh giá theo từng lớp. |
| Nâng cao | Tiếp tục pretrain trên dữ liệu miền (domain-adaptive), distillation sang model nhỏ, đa nhiệm. |

- **Tiên quyết:** [DL-01](../mang/dl.md#dl-01) PyTorch nền tảng
- **Mở khóa:** [DL-04](../mang/dl.md#dl-04), [DL-06](../mang/dl.md#dl-06), [LLM-07](../mang/llm.md#llm-07)
- **Công cụ:** Hugging Face Transformers, PEFT, timm
- **Đạt khi:** Model fine-tune nhỏ đạt chất lượng gần LLM lớn trên một tác vụ phân loại hẹp, với chi phí suy luận thấp hơn nhiều.
- **Token & độ chính xác:** Model nhỏ fine-tune cho tác vụ hẹp, lưu lượng lớn thường rẻ hơn gọi LLM mỗi lần.

<a id="dl-03"></a>

### DL-03 · Embedding và học biểu diễn

> Biểu diễn văn bản, ảnh, người dùng, sản phẩm thành vector để so sánh và tìm kiếm.

**Tầng:** Cầu nối liên họ · **Điểm đòn bẩy:** 4  
**Dùng cho:** ◐ Cần: Nhóm 3 Bất thường · ◐ Cần: Nhóm 4 Gợi ý · ◐ Cần: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 6 LLM/RAG · ○ Ít: Nhóm 7 Agent

| Mức | Làm được |
|---|---|
| Cơ bản | Dùng embedding có sẵn (bge-m3, multilingual-e5 cho tiếng Việt; CLIP cho ảnh), cosine similarity, kiểm tra bằng ví dụ láng giềng gần. |
| Trung cấp | Chọn embedding theo benchmark trên dữ liệu thật của mình, contrastive learning cơ bản, autoencoder cho bất thường. |
| Nâng cao | Fine-tune embedding với hard negatives, Matryoshka/quantization để giảm chi phí lưu trữ, theo dõi drift embedding. |

- **Tiên quyết:** [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI
- **Mở khóa:** [ML-07](../mang/ml.md#ml-07)
- **Công cụ:** sentence-transformers, bge-m3, multilingual-e5, open_clip
- **Đạt khi:** So sánh ít nhất 3 embedding trên tập truy vấn tiếng Việt thật và chọn bằng số liệu.

<a id="dl-04"></a>

### DL-04 · Thị giác máy tính (detection, segmentation, OCR)

> Nhận diện vật thể, vùng lỗi và chữ trong ảnh chụp thực tế.

**Tầng:** Chuyên biệt · **Điểm đòn bẩy:** 2  
**Dùng cho:** ● Cốt lõi: Nhóm 5 Ảnh/TL

| Mức | Làm được |
|---|---|
| Cơ bản | YOLO (Ultralytics) phát hiện vật thể, OCR có sẵn (PaddleOCR, VietOCR), mAP/IoU, đo độ chính xác theo từng trường. |
| Trung cấp | Chiến lược gán nhãn (Label Studio), augmentation mô phỏng ảnh thật (mờ, lóa, nghiêng), segmentation, tiền xử lý (deskew, crop). |
| Nâng cao | Active learning, xử lý ảnh chất lượng xấu, so khớp khuôn mặt và chống giả mạo (liveness) cho eKYC. |

- **Tiên quyết:** [DL-02](../mang/dl.md#dl-02) Transfer learning và fine-tune mô hình pretrained
- **Mở khóa:** [DL-05](../mang/dl.md#dl-05)
- **Công cụ:** Ultralytics YOLO, OpenCV, PaddleOCR, VietOCR, Label Studio
- **Đạt khi:** Model chạy trên ảnh chụp điện thoại thật (không chỉ ảnh mẫu sạch) với độ chính xác theo trường được báo cáo riêng.

<a id="dl-05"></a>

### DL-05 · Document AI và mô hình thị giác–ngôn ngữ (VLM)

> Trích xuất dữ liệu có cấu trúc từ hóa đơn, hợp đồng, giấy tờ nhiều mẫu.

**Tầng:** Dùng chung trong họ · **Điểm đòn bẩy:** 4  
**Dùng cho:** ● Cốt lõi: Nhóm 5 Ảnh/TL · ◐ Cần: Nhóm 6 LLM/RAG · ◐ Cần: Nhóm 7 Agent

| Mức | Làm được |
|---|---|
| Cơ bản | Phân biệt PDF có text và PDF scan; trích text/bảng bằng công cụ có sẵn; VLM trích trường từ ảnh theo JSON schema. |
| Trung cấp | Phân tích bố cục, trích bảng, so sánh OCR + luật với VLM theo chi phí/độ chính xác, đo độ chính xác từng trường. |
| Nâng cao | Pipeline nhiều mẫu tài liệu (phân loại mẫu → trích xuất chuyên biệt), đối chiếu chéo trường, fine-tune cho mẫu khó, chuyển ca nghi ngờ cho người. |

- **Tiên quyết:** [DL-04](../mang/dl.md#dl-04) Thị giác máy tính (detection, segmentation, OCR), [LLM-02](../mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra
- **Mở khóa:** —
- **Công cụ:** PyMuPDF, pdfplumber, Docling, PaddleOCR, VLM API
- **Đạt khi:** Báo cáo được độ chính xác từng trường và tỷ lệ hồ sơ xử lý tự động hoàn toàn trên bộ hóa đơn thật.
- **Token & độ chính xác:** Chỉ gửi vùng ảnh/trang cần thiết, đúng độ phân giải cần thiết; OCR + luật cho mẫu cố định, VLM chỉ cho mẫu lạ.

<a id="dl-06"></a>

### DL-06 · Xử lý giọng nói (ASR)

> Chuyển ghi âm tổng đài tiếng Việt thành văn bản để phân tích.

**Tầng:** Chuyên biệt · **Điểm đòn bẩy:** 1  
**Dùng cho:** ◐ Cần: Nhóm 6 LLM/RAG

| Mức | Làm được |
|---|---|
| Cơ bản | Whisper/PhoWhisper chuyển giọng nói thành văn bản; đo WER/CER. |
| Trung cấp | Tách người nói (diarization), VAD cắt khoảng lặng, xử lý giọng vùng miền và thuật ngữ riêng. |
| Nâng cao | Streaming ASR độ trễ thấp, fine-tune trên ghi âm tổng đài, kết hợp tóm tắt và trích ý định. |

- **Tiên quyết:** [DL-02](../mang/dl.md#dl-02) Transfer learning và fine-tune mô hình pretrained
- **Mở khóa:** —
- **Công cụ:** Whisper, faster-whisper, PhoWhisper, pyannote
- **Đạt khi:** Đo được WER trên ghi âm thật của công ty và biết nhóm lỗi lớn nhất (tên riêng, số, giọng vùng miền).
- **Token & độ chính xác:** VAD cắt khoảng lặng trước khi ASR giảm thời lượng xử lý; transcript ngắn gọn giảm token cho bước tóm tắt.
