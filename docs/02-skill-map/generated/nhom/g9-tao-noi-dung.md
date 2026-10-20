<!-- FILE SINH TỰ ĐỘNG từ catalog/*.yaml bằng `make catalog`. KHÔNG sửa tay — sửa YAML rồi sinh lại. -->

# Nhóm 9 · Tạo nội dung đa phương tiện

> “Làm giúp tôi video, hình ảnh hay giọng đọc này.” — Khối E · Sáng tạo

**Ví dụ trong doanh nghiệp:** video bài giảng và e-learning, video giới thiệu sản phẩm, giọng đọc và lồng tiếng tự động, ảnh minh họa và nhân vật thương hiệu.

| Đầu vào | Kỹ thuật chính | Đầu ra | Quyết định kinh doanh |
|---|---|---|---|
| Kịch bản hoặc bài học, nhân vật và nhận diện thương hiệu, dữ liệu sản phẩm | LLM viết kịch bản; TTS; mô hình sinh ảnh/video; dựng hình bằng code (ffmpeg, Pillow, Remotion) | Video, ảnh, giọng đọc đúng nội dung và đúng nhân vật | Duyệt rồi đăng lên kênh học tập, mạng xã hội, website |

## Mức năng lực của nhóm (từ bản đồ bài toán)

| Mức | Nội dung |
|---|---|
| Cơ bản | Dựng video bằng code từ ảnh có sẵn (Pillow/ffmpeg) + giọng TTS + phụ đề; chữ trên hình do code vẽ từ kịch bản; người duyệt trước khi đăng. |
| Trung cấp | Dây chuyền chạy lại được bằng một lệnh (kịch bản → giọng → nhạc → hình), nhân vật nhất quán, máy tự nghe lại lời đọc (ASR) và báo câu cần sửa; đo thời gian và chi phí mỗi phút video. |
| Nâng cao | Mô hình sinh ảnh/video có ảnh tham chiếu (giữ nhân vật qua nhiều cảnh), giọng hoặc LoRA nhân vật riêng, sản xuất hàng loạt, kiểm duyệt nội dung và bản quyền, đo hiệu quả thật (tỷ lệ xem hết, kết quả học). |

- **Metric chính:** Tỷ lệ câu đọc đúng (máy nghe lại + người nghe); lỗi chữ trên hình; tỷ lệ video được duyệt ngay lần đầu; thời gian và chi phí mỗi phút video; tỷ lệ xem hết.
- **Công cụ:** Claude Code, ffmpeg, Pillow, Remotion, Piper / sherpa-onnx, TTS thương mại (FPT.AI, Google, Azure, ElevenLabs), Kling, Veo, Sora
- **Bẫy thường gặp:** Để mô hình sinh vẽ chữ (sai dấu tiếng Việt); tin giọng TTS mà không nghe lại; nhân vật lệch nét giữa các cảnh; quên bản quyền nhân vật, nhạc, giọng đọc; nội dung cho trẻ em không có người duyệt.
- **Dự án luyện tập:** Video 2 phút dạy 29 chữ cái tiếng Việt trên nền nhạc, một nhân vật xuyên suốt, dựng hoàn toàn bằng code (kịch bản YAML → giọng đọc → nhạc → hình) và tự kiểm tra lời đọc bằng ASR. Đã làm bản đầu — dự án g9-video-chu-cai.
- **Mục tiêu đạt được:** Một lệnh dựng lại cả video (~3 phút, không tốn phí API); ≥ 90% câu đọc được máy nghe lại đúng cả khi có nhạc (bản đầu: 28/29); 100% chữ trên hình đúng chính tả; giáo viên duyệt.
- **Dữ liệu:** Tự tạo: kịch bản 29 chữ cái (cách đọc âm, từ ví dụ), ảnh nhân vật; hình Noto Emoji (Apache 2.0); giọng Piper vi_VN vais1000 (dữ liệu VAIS-1000, CC BY 4.0). Lĩnh vực giáo dục. [Mô tả chi tiết dự án và dữ liệu](../../../00-setup/05-du-lieu-luyen-tap.md#g9)
- **Nguyên tắc:** Chữ, số và lời dạy phải đúng tuyệt đối — để code vẽ chữ và máy nghe lại lời đọc; AI lo phần giọng và hình.

## Kỹ năng cần cho nhóm này

### ● Cốt lõi (10)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7, 8 |
| [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7, 8 |
| [PY-05](../mang/py.md#py-05) Xử lý và dựng media bằng code | Chuyên biệt | — |
| [DL-07](../mang/dl.md#dl-07) Sinh giọng nói, hình ảnh và video | Chuyên biệt | — |
| [LLM-01](../mang/llm.md#llm-01) Gọi LLM API và prompt engineering | Dùng chung trong họ | 5, 6, 7 |
| [OPS-03](../mang/ops.md#ops-03) Pipeline và điều phối tác vụ | Cầu nối liên họ | 1, 2, 3, 4, 6 |
| [BIZ-01](../mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7, 8 |
| [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7, 8 |
| [BIZ-03](../mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7, 8 |
| [BIZ-05](../mang/biz.md#biz-05) Kiến thức miền nghiệp vụ | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7, 8 |

### ◐ Cần (18)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [PY-03](../mang/py.md#py-03) Kiểm thử và chất lượng code | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7, 8 |
| [PY-04](../mang/py.md#py-04) Gọi API và I/O đồng thời bền vững | Cầu nối liên họ | 3, 5, 6, 7 |
| [DATA-05](../mang/data.md#data-05) Kiểm định chất lượng dữ liệu và nhãn | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7, 8 |
| [DATA-06](../mang/data.md#data-06) Văn bản tiếng Việt và dữ liệu phi cấu trúc | Dùng chung trong họ | 5, 6 |
| [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7, 8 |
| [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7, 8 |
| [DL-06](../mang/dl.md#dl-06) Xử lý giọng nói (ASR) | Dùng chung trong họ | 6 |
| [LLM-02](../mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra | Dùng chung trong họ | 5, 6, 7 |
| [LLM-04](../mang/llm.md#llm-04) Đánh giá hệ LLM (evals) | Dùng chung trong họ | 5, 6, 7 |
| [LLM-05](../mang/llm.md#llm-05) Tool calling và điều phối workflow/agent | Dùng chung trong họ | 6, 7 |
| [LLM-06](../mang/llm.md#llm-06) An toàn và bảo mật hệ LLM | Dùng chung trong họ | 5, 6, 7 |
| [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7, 8 |
| [OPS-02](../mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7, 8 |
| [OPS-06](../mang/ops.md#ops-06) LLMOps — tracing, chi phí, độ trễ | Dùng chung trong họ | 5, 6, 7 |
| [OPS-08](../mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ | Cầu nối liên họ | 1, 3, 5, 6, 7 |
| [BIZ-04](../mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) | Nền tảng chung | 1, 2, 3, 4, 5, 6, 7, 8 |
| [EFF-01](../mang/eff.md#eff-01) Đo token và chi phí trên mỗi tác vụ | Dùng chung trong họ | 5, 6, 7 |
| [EFF-07](../mang/eff.md#eff-07) Kiểm chứng xác định và "không lỗi im lặng" | Dùng chung trong họ | 5, 6, 7 |

### ○ Ít (5)

| Kỹ năng | Tầng | Dùng chung với nhóm |
|---|---|---|
| [STAT-03](../mang/stat.md#stat-03) Thiết kế thí nghiệm và A/B test | Cầu nối liên họ | 1, 4, 6, 8 |
| [DL-02](../mang/dl.md#dl-02) Transfer learning và fine-tune mô hình pretrained | Dùng chung trong họ | 5, 6 |
| [BIZ-06](../mang/biz.md#biz-06) Đọc và tái hiện paper | Bổ trợ | — |
| [EFF-06](../mang/eff.md#eff-06) Xử lý theo lô và bất đồng bộ | Dùng chung trong họ | 5, 6 |
| [EFF-08](../mang/eff.md#eff-08) Tiết kiệm token khi dùng AI hỗ trợ lập trình | Bổ trợ | — |

## Lộ trình học cho nhóm này

Thứ tự đã tôn trọng tiên quyết. Kỹ năng đánh dấu *(tiên quyết)* không trực tiếp thuộc nhóm nhưng cần để học các kỹ năng phía sau. Gợi ý: đạt **Cơ bản** cho cả danh sách trước, rồi mới lên **Trung cấp** ở các kỹ năng Cốt lõi.

1. [PY-01](../mang/py.md#py-01) Python cho dữ liệu và AI — ● Cốt lõi
2. [PY-02](../mang/py.md#py-02) Git, môi trường và cấu trúc dự án — ● Cốt lõi
3. [PY-03](../mang/py.md#py-03) Kiểm thử và chất lượng code — ◐ Cần
4. [PY-04](../mang/py.md#py-04) Gọi API và I/O đồng thời bền vững — ◐ Cần
5. [PY-05](../mang/py.md#py-05) Xử lý và dựng media bằng code — ● Cốt lõi
6. [DATA-02](../mang/data.md#data-02) Xử lý dữ liệu bảng — *(tiên quyết)*
7. [DATA-05](../mang/data.md#data-05) Kiểm định chất lượng dữ liệu và nhãn — ◐ Cần
8. [DATA-06](../mang/data.md#data-06) Văn bản tiếng Việt và dữ liệu phi cấu trúc — ◐ Cần
9. [STAT-01](../mang/stat.md#stat-01) Xác suất và thống kê mô tả — ◐ Cần
10. [STAT-02](../mang/stat.md#stat-02) Đo lường bất định của kết quả đánh giá — ◐ Cần
11. [ML-01](../mang/ml.md#ml-01) Quy trình học có giám sát chuẩn — *(tiên quyết)*
12. [STAT-05](../mang/stat.md#stat-05) Calibration, ngưỡng theo chi phí và dự đoán có chọn lọc — *(tiên quyết)*
13. [DL-01](../mang/dl.md#dl-01) PyTorch nền tảng — *(tiên quyết)*
14. [DL-02](../mang/dl.md#dl-02) Transfer learning và fine-tune mô hình pretrained — *(tiên quyết)*
15. [DL-06](../mang/dl.md#dl-06) Xử lý giọng nói (ASR) — ◐ Cần
16. [LLM-01](../mang/llm.md#llm-01) Gọi LLM API và prompt engineering — ● Cốt lõi
17. [DL-07](../mang/dl.md#dl-07) Sinh giọng nói, hình ảnh và video — ● Cốt lõi
18. [LLM-02](../mang/llm.md#llm-02) Structured output và kiểm chứng đầu ra — ◐ Cần
19. [LLM-05](../mang/llm.md#llm-05) Tool calling và điều phối workflow/agent — ◐ Cần
20. [OPS-01](../mang/ops.md#ops-01) Đóng gói và phục vụ model — ◐ Cần
21. [OPS-02](../mang/ops.md#ops-02) Theo dõi thực nghiệm và tái lập — ◐ Cần
22. [OPS-03](../mang/ops.md#ops-03) Pipeline và điều phối tác vụ — ● Cốt lõi
23. [OPS-06](../mang/ops.md#ops-06) LLMOps — tracing, chi phí, độ trễ — ◐ Cần
24. [OPS-08](../mang/ops.md#ops-08) Bảo mật dữ liệu và tuân thủ — ◐ Cần
25. [LLM-06](../mang/llm.md#llm-06) An toàn và bảo mật hệ LLM — ◐ Cần
26. [BIZ-01](../mang/biz.md#biz-01) Framing bài toán và quy đổi giá trị (ĐÚNG) — ● Cốt lõi
27. [BIZ-02](../mang/biz.md#biz-02) Baseline nhanh và bộ đánh giá cố định (NHANH) — ● Cốt lõi
28. [LLM-04](../mang/llm.md#llm-04) Đánh giá hệ LLM (evals) — ◐ Cần
29. [BIZ-03](../mang/biz.md#biz-03) Phân tích lỗi và cải tiến lấy dữ liệu làm trung tâm (CHÍNH XÁC) — ● Cốt lõi
30. [BIZ-04](../mang/biz.md#biz-04) Trình bày, demo và thuyết phục (THUYẾT PHỤC) — ◐ Cần
31. [BIZ-05](../mang/biz.md#biz-05) Kiến thức miền nghiệp vụ — ● Cốt lõi
32. [EFF-01](../mang/eff.md#eff-01) Đo token và chi phí trên mỗi tác vụ — ◐ Cần
33. [EFF-07](../mang/eff.md#eff-07) Kiểm chứng xác định và "không lỗi im lặng" — ◐ Cần
