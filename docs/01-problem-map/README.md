# 01 · Bản đồ bài toán AI trong doanh nghiệp (giai đoạn 1 — đã hoàn thành)

Tóm tắt của tài liệu gốc [ban-do-bai-toan-ai-doanh-nghiep_v1_20261004.docx](source/ban-do-bai-toan-ai-doanh-nghiep_v1_20261004.docx).
Dữ liệu có cấu trúc của từng nhóm (ví dụ, luồng giá trị, mức năng lực, metric, công cụ, bẫy, dự án luyện tập,
ma trận kỹ năng) nằm trong [catalog/problems.yaml](../../catalog/problems.yaml) và được hiển thị chi tiết ở
các trang nhóm trong [bản đồ kỹ năng](../02-skill-map/generated/README.md).

## 9 nhóm bài toán, 5 khối

Phân loại theo **đầu ra mà nghiệp vụ cần**, không theo loại dữ liệu hay thuật toán.

| Khối | Nhóm | Câu hỏi nghiệp vụ | Chi tiết + kỹ năng |
|---|---|---|---|
| A · Dự đoán | 1 · Dự đoán trên dữ liệu bảng | Khách này có rời bỏ, vỡ nợ hay mua hàng không? | [Nhóm 1](../02-skill-map/generated/nhom/g1-du-lieu-bang.md) |
| A · Dự đoán | 2 · Dự báo chuỗi thời gian | Tháng sau bán (hoặc cần) bao nhiêu? | [Nhóm 2](../02-skill-map/generated/nhom/g2-chuoi-thoi-gian.md) |
| A · Dự đoán | 3 · Phát hiện bất thường | Giao dịch hay máy móc này có gì lạ? | [Nhóm 3](../02-skill-map/generated/nhom/g3-bat-thuong.md) |
| A · Dự đoán | 4 · Gợi ý và xếp hạng | Nên hiển thị gì cho người này? | [Nhóm 4](../02-skill-map/generated/nhom/g4-goi-y-xep-hang.md) |
| B · Hiểu | 5 · Thị giác máy tính và Document AI | Trong ảnh hay tài liệu này có gì? | [Nhóm 5](../02-skill-map/generated/nhom/g5-anh-tai-lieu.md) |
| B · Hiểu | 6 · Ngôn ngữ, LLM và RAG | Văn bản này nói gì? Trả lời dựa trên tài liệu nội bộ. | [Nhóm 6](../02-skill-map/generated/nhom/g6-llm-rag.md) |
| C · Hành động | 7 · AI Agent và tự động hóa quy trình | Làm giúp tôi cả chuỗi việc này. | [Nhóm 7](../02-skill-map/generated/nhom/g7-agent-tu-dong-hoa.md) |
| D · Quyết định | 8 · Tối ưu hóa và suy luận nhân quả | Nên làm gì là tốt nhất? | [Nhóm 8](../02-skill-map/generated/nhom/g8-toi-uu-nhan-qua.md) |
| E · Sáng tạo | 9 · Tạo nội dung đa phương tiện | Làm giúp tôi video, hình ảnh hay giọng đọc này. | [Nhóm 9](../02-skill-map/generated/nhom/g9-tao-noi-dung.md) |

> [!NOTE]
> **Nhóm 9 bổ sung ngày 2026-10-20**, không có trong tài liệu gốc v1. Đầu ra là **nội dung mới** (video, hình, giọng
> đọc), không phải dự đoán, hiểu, hành động hay quyết định, nên cần khối mới *E · Sáng tạo*. Không đặt tên "nhóm mix"
> vì hai lẽ. Thứ nhất, trong repo "ghép nhiều nhóm" đã có tên là **tổ hợp** (CMB-01…). Thứ hai, lõi của bài toán (sinh
> giọng, hình, video và dựng media bằng code) là kỹ năng mới, không có trong 8 nhóm cũ: hai kỹ năng
> [DL-07](../02-skill-map/generated/mang/dl.md#dl-07) và [PY-05](../02-skill-map/generated/mang/py.md#py-05). Dự án mẫu:
> [video dạy chữ cái](../../projects/g9-video-chu-cai/README.md).

## Nhận diện bài toán trong 30 giây

Đi từ trên xuống, dừng ở câu trả lời "Có" đầu tiên. Thứ tự đi từ bài toán rộng (tạo nội dung, hành động, quyết định)
đến hẹp (dự đoán), vì bài toán rộng thường chứa bài toán hẹp bên trong. Câu về tạo nội dung đứng trước câu về chuỗi thao
tác vì dây chuyền làm video cũng là một chuỗi thao tác.

```mermaid
flowchart TD
    S([Doanh nghiệp cần đầu ra gì?]) --> Q1
    Q1{"Q1 · Sản phẩm cần giao là nội dung mới để xem/nghe —<br/>video, hình ảnh, giọng đọc, nhạc?"} -- Có --> N9[Nhóm 9 · Tạo nội dung đa phương tiện]
    Q1 -- Không --> Q2
    Q2{"Q2 · Cần thực hiện một chuỗi thao tác<br/>trên nhiều hệ thống?"} -- Có --> N7[Nhóm 7 · AI Agent & tự động hóa]
    Q2 -- Không --> Q3
    Q3{"Q3 · Cần chọn phương án tốt nhất dưới ràng buộc,<br/>hoặc đo tác động thật của một hành động?"} -- Có --> N8[Nhóm 8 · Tối ưu & nhân quả]
    Q3 -- Không --> Q4
    Q4{"Q4 · Cần xếp hạng/gợi ý<br/>mục phù hợp cho từng người?"} -- Có --> N4[Nhóm 4 · Gợi ý & xếp hạng]
    Q4 -- Không --> Q5
    Q5{"Q5 · Đầu vào chính là ảnh,<br/>video hoặc tài liệu scan?"} -- Có --> N5[Nhóm 5 · Thị giác máy tính & Document AI]
    Q5 -- Không --> Q6
    Q6{"Q6 · Đầu vào là văn bản, giọng nói,<br/>hoặc cần hỏi đáp trên tài liệu?"} -- Có --> N6[Nhóm 6 · Ngôn ngữ, LLM & RAG]
    Q6 -- Không --> Q7
    Q7{"Q7 · Cần dự báo một giá trị<br/>trong tương lai theo thời gian?"} -- Có --> N2[Nhóm 2 · Chuỗi thời gian]
    Q7 -- Không --> Q8
    Q8{"Q8 · Cần tìm điểm bất thường<br/>khi gần như không có nhãn?"} -- Có --> N3[Nhóm 3 · Phát hiện bất thường]
    Q8 -- Không --> N1[Nhóm 1 · Dự đoán trên dữ liệu bảng]
```

> Dự án thực tế thường ghép nhiều nhóm. Ví dụ: xử lý hồ sơ vay = Nhóm 5 (đọc giấy tờ) + Nhóm 1 (chấm điểm
> tín dụng) + Nhóm 7 (điều phối quy trình). Trợ lý AI trong Excel gọi agent của hệ thống = Nhóm 7 (thao tác trên
> Excel và hệ thống nghiệp vụ) + Nhóm 6 (hiểu yêu cầu, hỏi đáp số liệu) — tổ hợp
> [CMB-10](../02-skill-map/generated/to-hop-ky-nang.md#cmb-10). Tách dự án thành bài toán con rồi nhận diện từng phần —
> xem [tổ hợp kỹ năng](../02-skill-map/02-ky-nang-ket-hop.md).

## Use case bổ sung · Chatbot AI thao tác Excel

[GPT Excel Agent Chatbot](../../projects/gpt-excel-agent-chatbot/README.md) thuộc **G7 · AI Agent và tự động hóa
quy trình**, với **G6** hỗ trợ hiểu yêu cầu: chat trong Excel → tra dữ liệu theo cột hoặc từ hệ thống → kiểm tra
→ thêm bản ghi → báo kết quả. Đây là use case mới trong nhóm hiện có, **không cần thêm G9**. Dữ liệu nằm trong
Excel không tự làm bài toán thuộc G1; G1 chỉ tham gia khi có mục tiêu dự đoán/chấm điểm. Dự án hiện chỉ nghiên cứu
khả thi và solution approach, chưa triển khai.

## Use case bổ sung · Video dạy chữ cái tiếng Việt (Nhóm 9)

[Video dạy chữ cái cùng Thỏ Bông và Sách Vui](../../projects/g9-video-chu-cai/README.md) thuộc **G9 · Tạo nội dung đa
phương tiện**: video 3 phút dạy 29 chữ cái trên nền nhạc, bảng học ở giữa, hai nhân vật cử động đứng hai góc (tách nền
từ video Gemini), dựng bằng code (kịch bản YAML → giọng đọc → nhạc → hình → ffmpeg) và cho máy nghe lại lời đọc bằng
ASR. Tách bài toán con: viết kịch bản là G6, dây chuyền dựng là kỹ năng pipeline (OPS-03), còn phần lõi — sinh giọng
đọc, tách nhân vật, dựng media — là G9. Có [hướng dẫn tự làm bằng Claude
Code](../../projects/g9-video-chu-cai/docs/huong-dan-claude-code.md).

## Ma trận kỹ năng theo nhóm (giai đoạn 1)

Mức cần thiết của 8 mảng kỹ năng để làm tốt từng nhóm ở mức trung cấp trở lên (đánh giá định tính).
● Cốt lõi · ◐ Cần · ○ Ít.

| Nhóm | SQL & dữ liệu bảng | Thống kê & thực nghiệm | ML cổ điển | Deep learning | LLM & prompt | Tối ưu hóa (OR) | Triển khai & MLOps | Hiểu nghiệp vụ |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 1 · Bảng | ● | ● | ● | ○ | ○ | ○ | ◐ | ● |
| 2 · Thời gian | ● | ● | ● | ◐ | ○ | ◐ | ◐ | ● |
| 3 · Bất thường | ● | ● | ● | ◐ | ○ | ○ | ● | ● |
| 4 · Gợi ý | ● | ◐ | ● | ◐ | ○ | ○ | ● | ◐ |
| 5 · Ảnh/TL | ○ | ○ | ○ | ● | ◐ | ○ | ● | ◐ |
| 6 · LLM/RAG | ◐ | ◐ | ○ | ◐ | ● | ○ | ● | ◐ |
| 7 · Agent | ◐ | ○ | ○ | ○ | ● | ○ | ● | ● |
| 8 · Tối ưu | ◐ | ● | ◐ | ○ | ○ | ● | ◐ | ● |
| 9 · Nội dung | ○ | ◐ | ○ | ● | ● | ○ | ● | ● |

**Điều rút ra:** cột *Triển khai & MLOps* và *Hiểu nghiệp vụ* không có ô "Ít" ở nhóm nào — hai kỹ năng xương
sống. Giai đoạn 2 chi tiết hóa ma trận này thành 67 kỹ năng cụ thể và **kiểm tra tự động** rằng mọi ô Cốt lõi
ở trên đều được phủ (xem [đối chiếu](../02-skill-map/generated/ma-tran-ky-nang.md#doi-chieu-giai-doan-1)).

## Ba mức kỹ năng

| Cơ bản | Trung cấp | Nâng cao |
|---|---|---|
| Dựng được baseline, chọn đúng metric và đánh giá đúng cách. | Đạt chất lượng đủ để chạy thử (pilot) trên dữ liệu thật của doanh nghiệp. | Vận hành ổn định ở production: tối ưu chi phí, giám sát, giải thích được và mở rộng quy mô. |

## Cách làm: ĐÚNG → NHANH → CHÍNH XÁC → THUYẾT PHỤC

```mermaid
flowchart LR
    A["1 · ĐÚNG<br/>Chốt quyết định sẽ thay đổi,<br/>KPI, loại sai nào đắt hơn"] --> B["2 · NHANH<br/>Baseline 1–2 ngày +<br/>bộ đánh giá cố định"]
    B --> C["3 · CHÍNH XÁC<br/>Phân tích 50–100 ca sai,<br/>sửa nhóm lỗi lớn nhất"]
    C -- "lặp: đo → phân tích lỗi → sửa → đo lại" --> B
    C --> D["4 · THUYẾT PHỤC<br/>So với baseline, quy ra tiền/<br/>giờ công, demo chạy được"]
```

Bốn bước này trở thành bốn kỹ năng nền tảng BIZ-01 → BIZ-04 trong [catalog](../02-skill-map/generated/mang/biz.md).

## Lộ trình 6 tháng (giai đoạn 1)

| Giai đoạn | Nội dung | Mốc |
|---|---|---|
| Tháng 1–2 · Nền tảng | Python, SQL, thống kê, Git; một dự án dữ liệu bảng đóng gói thành API (FastAPI + Docker). Sách: *Hands-On Machine Learning* (Géron) | Cuối tháng 2: dự án bảng chạy qua API |
| Tháng 3–4 · GenAI | LLM API, structured output; hệ RAG tiếng Việt có bộ đánh giá và tracing. Sách: *AI Engineering* (Chip Huyen) | Cuối tháng 4: RAG tiếng Việt có bộ đánh giá |
| Tháng 5–6 · Chuyên sâu | 1–2 nhóm sát nhu cầu công ty; MLOps (MLflow, drift, chi phí, độ trễ). Sách: *Designing Machine Learning Systems* (Chip Huyen) | Cuối tháng 6: dự án chuyên sâu cho công ty |
| Xuyên suốt | Mô hình chữ T: nhận diện và dựng baseline cho cả 9 nhóm, thật sâu ở 1–2 nhóm; mỗi tuần một paper | — |

Giai đoạn 2 ánh xạ lộ trình này xuống từng kỹ năng: [04-lo-trinh-hoc.md](../02-skill-map/04-lo-trinh-hoc.md).
