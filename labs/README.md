# labs/ — bài lab theo kỹ năng (giai đoạn 3)

Mỗi lab luyện **một kỹ năng** trong [danh mục](../docs/02-skill-map/generated/README.md) ở **một mức**, trên dữ liệu
nhỏ, chạy xong trong 1–3 giờ. Lab là nơi luyện tay; dự án (`projects/`) là nơi áp dụng.

## Quy ước

```
labs/
└── <ID kỹ năng viết thường>-<mức>-<tên-ngắn>/      # ví dụ: ml-07-co-ban-bm25-vs-embedding/
    ├── README.md          # theo mẫu templates/lab/README.md
    ├── lab.ipynb          # hoặc lab.py — một luồng chạy từ đầu đến cuối
    ├── data/              # chỉ dữ liệu nhỏ, công khai (< 5 MB); dữ liệu lớn để ở ../../data/
    └── solution.ipynb     # (tùy chọn) lời giải tham khảo
```

- **Tên thư mục** bắt đầu bằng ID kỹ năng (`py-01`, `ml-07`, `eff-02`...) và mức (`co-ban`, `trung-cap`,
  `nang-cao`) để tra ngược từ thẻ kỹ năng.
- Lab dùng thư viện trong các nhóm phụ thuộc của `pyproject.toml`. Nếu cần gói đặc thù (PaddleOCR, vLLM...),
  ghi rõ trong README của lab và cài bằng `uv run --with <gói>` hoặc môi trường riêng — không thêm vào lockfile chung.
- Lab có gọi LLM API phải in ra **token và chi phí** đã dùng (kỹ năng EFF-01) và tôn trọng `LLM_DAILY_BUDGET_USD`.
- Không commit output notebook chứa dữ liệu thật hoặc khóa bí mật.

## Thêm lab mới

```bash
mkdir -p labs/ml-07-co-ban-bm25-vs-embedding
cp templates/lab/README.md labs/ml-07-co-ban-bm25-vs-embedding/README.md
```

## Danh sách lab

*(Chưa có — giai đoạn 3 sẽ bổ sung theo thứ tự [lộ trình học](../docs/02-skill-map/04-lo-trinh-hoc.md).)*
