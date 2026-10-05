# projects/ — dự án luyện tập theo nhóm bài toán (giai đoạn 4)

Mỗi nhóm bài toán có một dự án luyện tập (từ [bản đồ bài toán](../docs/01-problem-map/README.md)); mỗi tổ hợp có
thể có một dự án tích hợp. Dự án đi trọn quy trình ĐÚNG → NHANH → CHÍNH XÁC → THUYẾT PHỤC và là bằng chứng để tự
đánh giá mức **Trung cấp** của nhóm.

## Danh sách dự án dự kiến

| Thư mục | Nhóm / tổ hợp | Dự án | Dữ liệu |
|---|---|---|---|
| `g1-churn-telco/` | 1 · Bảng | Top 500 khách churn kèm lý do SHAP | Telco Customer Churn |
| `g2-forecast-m5/` | 2 · Thời gian | LightGBM toàn cục vs seasonal naive, backtest cuốn chiếu | M5 (Walmart) |
| `g3-fraud-creditcard/` | 3 · Bất thường | Ngưỡng theo số cảnh báo xử lý được mỗi ngày | Credit Card Fraud Detection |
| `g4-recsys-movielens/` | 4 · Gợi ý | ALS vs phổ biến theo Recall@10, NDCG@10 | MovieLens |
| `g5-invoice-extraction/` | 5 · Ảnh/TL | Trích ngày, tổng tiền, MST: OCR + luật vs VLM | Hóa đơn tiếng Việt |
| `g6-rag-handbook/` | 6 · LLM/RAG | Hỏi đáp có trích dẫn + golden set ~100 câu | Văn bản công khai |
| `g7-quote-agent/` | 7 · Agent | Đọc email → tra giá → soạn báo giá → chờ duyệt | Tự tạo |
| `g8-vrp-delivery/` | 8 · Tối ưu | Tuyến 1 kho × 20 điểm bằng OR-Tools | Tự sinh |
| `cmb-08-ticket-cascade/` | Tổ hợp CMB-08 | Phân loại ticket: model nhỏ → LLM → người, bảng chất lượng–chi phí | Tự tạo / công khai |
| [`cmb-09-data-agent-os/`](cmb-09-data-agent-os/README.md) | Tổ hợp CMB-09 | Data agent nhiều domain pack trên AgentOS, dùng lại skill của Data plugin, dữ liệu qua MCP DBHub — **thiết kế POC** | Giả lập (timesheet, finance) |

Chi tiết từng nhóm (metric, bẫy, kỹ năng cần): xem trang nhóm trong [bản đồ kỹ năng](../docs/02-skill-map/generated/README.md).

## Cấu trúc một dự án

```
projects/<thư-mục>/
├── README.md            # framing 1 trang + kết quả — theo mẫu templates/project/README.md
├── src/<tên_gói>/       # code dùng lại, có test
├── notebooks/           # khám phá, phân tích lỗi
├── eval/                # golden set (nếu công khai) + script đánh giá — `make eval` của dự án
├── tests/
└── Makefile             # setup / eval / serve của riêng dự án (gọi uv run ...)
```

Quy tắc:

- **Viết framing trước khi viết code** (phần đầu README theo mẫu): quyết định thay đổi, KPI, loại sai đắt hơn,
  baseline hiện tại.
- **Đóng băng bộ đánh giá trước model đầu tiên.** Mọi thí nghiệm báo cáo trên cùng bộ đánh giá, kèm khoảng tin cậy.
- Code dùng chung giữa nhiều dự án (đọc dữ liệu, harness đánh giá, client LLM có đo chi phí...) đưa lên
  `src/aiarch/` để các dự án khác dùng lại — đây là cách "kỹ năng dùng chung" trở thành "code dùng chung".

## Bắt đầu một dự án

```bash
mkdir -p projects/g1-churn-telco/{src,notebooks,eval,tests}
cp templates/project/README.md projects/g1-churn-telco/README.md
```
