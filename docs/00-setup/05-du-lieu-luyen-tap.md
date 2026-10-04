# 5 · Dữ liệu luyện tập

Mỗi nhóm bài toán có một dự án luyện tập (từ [bản đồ bài toán](../01-problem-map/README.md)). Bảng dưới
là nguồn dữ liệu công khai gợi ý. Luôn **đọc giấy phép/điều khoản** của bộ dữ liệu trước khi dùng, nhất là
khi đưa kết quả vào tài liệu công ty.

| Nhóm | Dự án luyện tập | Dữ liệu gợi ý | Nguồn |
|---|---|---|---|
| 1 · Bảng | Top 500 khách churn kèm lý do SHAP | Telco Customer Churn | Kaggle `blastchar/telco-customer-churn` |
| 2 · Thời gian | Dự báo cửa hàng × mặt hàng, so với seasonal naive | M5 Forecasting – Accuracy (Walmart) | Kaggle competition `m5-forecasting-accuracy` (cần bấm chấp nhận luật thi) |
| 3 · Bất thường | Gian lận thẻ, ngưỡng theo năng lực xử lý | Credit Card Fraud Detection | Kaggle `mlg-ulb/creditcardfraud` |
| 4 · Gợi ý | ALS vs phổ biến theo Recall@10, NDCG@10 | MovieLens (bắt đầu với bản *latest-small*) | grouplens.org/datasets/movielens |
| 5 · Ảnh/TL | Trích ngày, tổng tiền, MST từ ảnh hóa đơn; OCR + luật vs VLM | Hóa đơn bán lẻ tiếng Việt (ví dụ bộ MC-OCR 2021) hoặc SROIE; tốt nhất là 50–100 hóa đơn tự chụp, đã che thông tin cá nhân | Tìm theo tên bộ dữ liệu; kiểm tra điều khoản |
| 6 · LLM/RAG | Hỏi đáp có trích dẫn + golden set ~100 câu | Văn bản pháp luật công khai (ví dụ Bộ luật Lao động) hoặc sổ tay/quy chế công khai của một tổ chức | Cổng văn bản pháp luật nhà nước; trang công khai của tổ chức |
| 7 · Agent | Đọc email yêu cầu báo giá → tra bảng giá → soạn báo giá → chờ duyệt | Tự tạo: 30–50 email mẫu + file bảng giá CSV (có thể dùng LLM sinh rồi tự kiểm tra) | Tự tạo |
| 8 · Tối ưu | Tuyến giao hàng 1 kho × 20 điểm bằng OR-Tools | Tọa độ tự sinh hoặc lấy từ bản đồ; dữ liệu uplift: Hillstrom email marketing | Ví dụ trong tài liệu OR-Tools; MineThatData (Hillstrom) |

## Tải dữ liệu Kaggle bằng dòng lệnh

Điền `KAGGLE_USERNAME`, `KAGGLE_KEY` vào `.env` (hoặc đặt file `~/.kaggle/kaggle.json`), rồi:

```bash
set -a; source .env; set +a      # nạp biến từ .env vào shell hiện tại

uv run --with kaggle kaggle datasets download -d blastchar/telco-customer-churn -p data/raw/telco --unzip
uv run --with kaggle kaggle datasets download -d mlg-ulb/creditcardfraud -p data/raw/creditcard --unzip
uv run --with kaggle kaggle competitions download -c m5-forecasting-accuracy -p data/raw/m5
```

MovieLens:

```bash
mkdir -p data/raw/movielens && cd data/raw/movielens
curl -LO https://files.grouplens.org/datasets/movielens/ml-latest-small.zip && unzip ml-latest-small.zip
```

## Golden set — bộ đánh giá cố định

Với mỗi dự án, **trước khi** thử model đầu tiên, tách và đóng băng một bộ đánh giá (kỹ năng BIZ-02):

- Dữ liệu bảng/thời gian: tập test theo **thời gian** (giai đoạn cuối), không xáo trộn.
- LLM/RAG/Document AI: ≥ 100 mẫu thật có đáp án do người kiểm tra; lưu dạng JSONL trong
  `projects/<dự-án>/eval/` (nếu dữ liệu công khai) hoặc `data/processed/` (nếu nhạy cảm).
- Ghi lại phiên bản golden set; khi sửa golden set thì tăng phiên bản và chạy lại baseline.

Cấu trúc thư mục `data/`: xem [data/README.md](../../data/README.md).

Tiếp theo: [6 · Xử lý sự cố](06-xu-ly-su-co.md) — hoặc bắt đầu học: [bản đồ kỹ năng](../02-skill-map/README.md).
