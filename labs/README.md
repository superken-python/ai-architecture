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

| Lab | Kỹ năng · mức | Nội dung |
|---|---|---|
| [biz-01-co-ban-framing-churn](biz-01-co-ban-framing-churn/README.md) | BIZ-01 · Cơ bản (+ PY-01, PY-02) | **A1** Quy bài toán churn ra tiền trước khi có model: giá trị một khách, xác suất hoà vốn, precision@500 cần đạt |
| [data-01-co-ban-kham-pha-du-lieu](data-01-co-ban-kham-pha-du-lieu/README.md) | DATA-01 · Cơ bản (+ DATA-02, STAT-01) | **A2** Khám phá 8 bảng vận hành bằng DuckDB và pandas: lỗi dữ liệu thô, bảng khách-tháng, ASOF JOIN, 5 nhận xét có số liệu |
| [stat-02-co-ban-bootstrap](stat-02-co-ban-bootstrap/README.md) | STAT-02 · Cơ bản (+ ML-01, BIZ-02) | **A3** Khoảng tin cậy cho bộ đánh giá đóng băng: công thức nhanh vs bootstrap, theo khách vs theo dòng, chênh lệch cặp, lời nguyền người thắng |
| [data-03-trung-cap-ro-ri-du-lieu](data-03-trung-cap-ro-ri-du-lieu/README.md) | DATA-03 · Trung cấp (+ DATA-04, DATA-05) | **A4** Cố tình gây ba loại rò rỉ (AUC 0,73 → 0,97) rồi bắt bằng bốn cách, kể cả test đúng thời điểm; backtest cuốn chiếu |
| [stat-05-trung-cap-nguong-chi-phi](stat-05-trung-cap-nguong-chi-phi/README.md) | STAT-05 · Trung cấp (+ ML-02, ML-03) | **A5** LightGBM + early stopping, class weight phá xác suất, hiệu chỉnh, ngưỡng hoà vốn vs năng lực, đường coverage–precision–lợi nhuận |
| [biz-03-trung-cap-phan-tich-loi](biz-03-trung-cap-phan-tich-loi/README.md) | BIZ-03 · Trung cấp (+ ML-04, PY-03) | **A6** Đọc 100 ca bỏ sót, nhóm theo nguyên nhân, sửa nhóm lớn nhất bằng dữ liệu marketing, SHAP toàn cục |
| [ops-01-co-ban-dong-goi-api](ops-01-co-ban-dong-goi-api/README.md) | OPS-01 · Cơ bản (+ OPS-02, OPS-08) | **A7** Gọi API chấm điểm (đúng, sai, độ trễ) và rà soát secret/lịch sử Git/PII trước khi push |
| [biz-04-co-ban-trinh-bay](biz-04-co-ban-trinh-bay/README.md) | BIZ-04 · Cơ bản (+ PY-02) | **A8** Phân tích độ nhạy (tornado), điểm hoà vốn của chương trình, khung câu chuyện 3 phút |
| [llm-05-trung-cap-harness-langchain](llm-05-trung-cap-harness-langchain/README.md) | LLM-05 · Trung cấp | Harness agent bằng LangChain tương đương Agno (lịch sử N run, memory theo user, tool client có tạm dừng, người duyệt, trần số bước) + các lớp cải tiến kiểu Claude Code + phần còn lại của Agno (output có schema, state, guardrail, RAG, MCP, team, workflow `StateGraph`); 72 test với model kịch bản |
| [llm-05-trung-cap-agno-agentos](llm-05-trung-cap-agno-agentos/README.md) | LLM-05 · Trung cấp | Project tham chiếu của Lab 01 tự học: Agno 3.1.3 + AgentOS từng phần — agent, tool, structured output, streaming, session, memory, knowledge, HITL, guardrail, MCP client, team, workflow, AgentOS (REST, khoá, trace), AG-UI, A2A, MCP server, eval; 117 test với model giả lập |

Tám lab **A1–A8** đi kèm các bài của [Giai đoạn A · Nền tảng](../docs/03-giai-doan-a-nen-tang/README.md) và chạy bằng môi trường của dự án `projects/g1-churn-telco` (`uv run --project ../../projects/g1-churn-telco python <script>.py`); mọi lab có test trong dự án đó. Các lab còn lại bổ sung theo thứ tự [lộ trình học](../docs/02-skill-map/04-lo-trinh-hoc.md).
