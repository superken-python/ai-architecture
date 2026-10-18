# Dự đoán khách rời mạng — nhà mạng Sóng Xanh

**Nhóm bài toán:** [Nhóm 1 · Dự đoán trên dữ liệu bảng](../../docs/02-skill-map/generated/nhom/g1-du-lieu-bang.md) ·
**Vai trò:** real case xuyên suốt [Giai đoạn A · Nền tảng](../../docs/03-giai-doan-a-nen-tang/README.md) (8 bài, mỗi bài
viết một phần của dự án này) · **Trạng thái:** hoàn thành — mốc giai đoạn A

Mỗi tháng đội CSKH của nhà mạng Sóng Xanh (tên hư cấu, dữ liệu mô phỏng) gọi được 500 khách. Dự án dựng danh sách 500
khách đáng gọi nhất, kèm 3 lý do và việc nên làm cho từng người. Dự án đi từ 8 bảng dữ liệu vận hành tới API chấm điểm
trong Docker và báo cáo 1 trang. Xem kết quả: [báo cáo 1 trang](reports/README.md).

## 1 · ĐÚNG — framing (viết trước khi code)

| Câu hỏi | Trả lời |
|---|---|
| Quyết định nào sẽ thay đổi nhờ model? | Danh sách 500 khách được gọi giữ chân mỗi tháng (thay danh sách "sắp hết hợp đồng") |
| Ai dùng kết quả, dùng thế nào, bao lâu một lần? | Đội CSKH; đầu mỗi tháng nhận file danh sách + 3 lý do/khách; gọi trong tháng. Màn hình CRM có thể gọi API cho từng khách |
| KPI nghiệp vụ | Số khách giữ được mỗi tháng; lợi nhuận ròng của chương trình gọi |
| Metric kỹ thuật tương ứng | **precision@500 theo tháng** (chính); recall@500, PR-AUC, AUC (phụ) |
| Loại sai nào đắt hơn? Ước tính chi phí mỗi loại | Bỏ sót một khách sắp rời: mất ~1,07–2,43 triệu đ lợi nhuận (cước × 12 tháng × 45%). Gọi nhầm: 25.000 đ + làm phiền khách |
| Cách làm hiện tại (baseline nghiệp vụ) | Luật: sắp hết hợp đồng → báo lỗi mạng → không kỳ hạn → trả trễ. Đo được precision@500 = 7,5% |
| Có cần AI không, hay luật if-else là đủ? | Hoà vốn cần precision@500 ≥ ~5,4%. Luật hiện tại chỉ vừa đủ; một luật một dòng (dùng ít đi) đạt 21,7%; model đạt 28,7% |
| Ràng buộc: dữ liệu, quyền riêng tư, độ trễ, chi phí | 500 cuộc/tháng; dữ liệu khách là dữ liệu cá nhân (bỏ PII ngay bước làm sạch, không vào Git); danh sách cần trước ngày 1 hằng tháng; API < 200 ms/khách |

Giả định nghiệp vụ nằm trong [`config.py`](src/churn_telco/config.py): cuộc gọi 25.000 đ; 30% khách sắp rời đồng ý ở lại
khi được gọi; ưu đãi 150.000 đ; ở thêm 12 tháng; biên lợi nhuận 45%.

## 2 · NHANH — baseline và bộ đánh giá

- **Bộ đánh giá đóng băng**: 3 tháng chấm điểm 10–12/2025, 60.912 lượt khách (21.246 khách, 1.386 ca rời mạng). Chia
  theo thời gian: train 07/2024–06/2025, valid 07–09/2025. Manifest có mã băm khoá + nhãn:
  [`eval/manifest.json`](eval/manifest.json).
- **Lệnh tái tạo**: `make eval` → [`reports/eval_test.md`](reports/eval_test.md). Mọi ô có KTC 95% bootstrap theo khách.

| Model | AUC | PR-AUC | precision@500 | Δ precision@500 so với logistic |
|---|---|---|---|---|
| Ngẫu nhiên | 0.493 [0.478–0.509] | 0.022 [0.021–0.024] | 0.021 [0.014–0.028] | −0.234 [−0.259…−0.211] |
| Luật CSKH hiện tại | 0.668 [0.654–0.683] | 0.052 [0.047–0.060] | 0.075 [0.062–0.088] | −0.180 [−0.204…−0.156] |
| Luật giảm sử dụng | 0.683 [0.666–0.700] | 0.108 [0.096–0.124] | 0.217 [0.193–0.236] | −0.037 [−0.061…−0.021] |
| Logistic regression | 0.763 [0.749–0.778] | 0.190 [0.169–0.215] | 0.255 [0.231–0.278] | — |
| LightGBM v1 | 0.791 [0.778–0.804] | 0.240 [0.217–0.266] | 0.287 [0.261–0.309] | +0.032 [+0.017…+0.043] |
| **LightGBM v2** (chọn) | 0.797 [0.784–0.810] | 0.240 [0.217–0.266] | 0.283 [0.258–0.307] | +0.028 [+0.015…+0.040] |

## 3 · CHÍNH XÁC — các vòng cải tiến

| Vòng | Nhóm lỗi lớn nhất | Thay đổi | Metric trước → sau (± KTC) |
|---|---|---|---|
| 1 | (baseline tuyến tính) | LightGBM, early stopping theo PR-AUC trên valid | precision@500 test 0,255 → 0,287 (Δ +0,032 [+0,017…+0,043]) |
| 2 | Đối thủ khuyến mãi ở HCM, Bình Dương: 45/100 ca bỏ sót trên valid; model dự đoán chỉ 0,68–0,72 lần thực tế ở hai tỉnh này | thêm lịch khuyến mãi của phòng marketing (feature as-of) → v2 | valid: AUC 0,739 → 0,759; recall@500 HCM+BD 0,131 → 0,152; dự đoán HCM+BD 2,05% → 2,59% (thực tế 2,88%). Test (không khuyến mãi): ngang v1 |
| — | Chuyển nhà/đi xa: 22/100 ca bỏ sót, không có dấu hiệu trước | không sửa bằng model | đề xuất cách khác (dịch vụ chuyển địa điểm) |

Chi tiết từng vòng: [bài A5](../../docs/03-giai-doan-a-nen-tang/a5-lightgbm-nguong-chi-phi.md),
[bài A6](../../docs/03-giai-doan-a-nen-tang/a6-phan-tich-loi-shap-test.md).

## 4 · THUYẾT PHỤC — kết quả

- **So với cách làm hiện tại** (mỗi tháng, 500 cuộc gọi): gọi trúng 140 người sắp rời thay vì 37 (+103, KTC 90…114);
  giữ được 42 khách thay vì 11.
- **Quy ra tiền**: lợi nhuận ròng tăng thêm **44,5 triệu đ/tháng** (KTC 39,0…49,6). Kết luận đúng ở mọi mức giả định
  đã thử. Chương trình gọi theo model có lãi khi chỉ cần ≥ 6,5% khách đồng ý ở lại; danh sách hiện tại cần ≥ 24,5%.
- **Demo**: `make docker-up` → http://127.0.0.1:8000 (nhập khoá trong `.env`) → danh sách gọi kèm lý do; tài liệu API ở
  `/docs`.
- **Giới hạn và rủi ro**: dữ liệu mô phỏng; tỷ lệ giữ chân 30% là giả định (cần thử nghiệm có nhóm đối chứng); không
  bắt được churn do chuyển nhà và churn đột ngột khi đối thủ khuyến mãi (nên dùng ưu đãi theo vùng); cần theo dõi dự
  đoán so với thực tế theo tỉnh hằng tháng. Xem [báo cáo](reports/README.md#giới-hạn-và-rủi-ro).

## Chạy dự án

```bash
make setup     # cài môi trường đúng theo uv.lock, tạo .env từ mẫu (đổi CHURN_API_KEY)
make all       # ~1 phút 20 giây: dữ liệu → feature → train v1, v2 → đánh giá → danh sách gọi → MLflow → báo cáo
make test      # toàn bộ test trên dữ liệu nhỏ tự sinh (không cần make all)
make           # danh sách lệnh, mỗi lệnh ghi bài học sinh ra nó
```

| Lệnh | Bước | Kết quả |
|---|---|---|
| `make data` | A2 | `data/raw/` — 8 bảng của 4 hệ thống nguồn (mô phỏng, cố định theo seed) + `data/marketing/` |
| `make clean-data` | A2 | `data/interim/` — bảng sạch, đã bỏ PII |
| `make features` | A4 | `data/processed/features.parquet` — bảng học as-of, qua kiểm tra schema |
| `make eval` | A3 | `reports/eval_test.md` — mọi baseline + model trên bộ đánh giá đóng băng |
| `make train` / `make train-v2` | A5 / A6 | `models/lgbm-v1/`, `models/lgbm-v2/` — `model.txt` + `bundle.json` |
| `make score` | A6 | `data/outputs/call_list_2026-01-01.csv` — top 500 kèm 3 lý do |
| `make serve` / `make docker-up` | A7 | API tại http://127.0.0.1:8000 |
| `make track` / `make mlflow-ui` | A7 | lịch sử thí nghiệm trong `mlruns/` |
| `make report` | A8 | [`reports/README.md`](reports/README.md) |

```text
src/churn_telco/
├── config.py       đường dẫn, mốc thời gian, giả định nghiệp vụ          (A1)
├── simulate.py     hệ thống nguồn giả lập                                (A2)
├── clean.py        làm sạch có quy tắc, bỏ PII                           (A2)
├── split.py        chia theo thời gian, đóng băng bộ đánh giá            (A3)
├── metrics.py      AUC, PR-AUC, precision@k theo tháng, bootstrap cụm    (A3)
├── baselines.py    ngẫu nhiên, luật CSKH, luật dùng ít đi, logistic      (A3)
├── evaluate.py     harness `make eval`                                   (A3)
├── features.py     bảng học as-of bằng một câu SQL DuckDB                (A4)
├── schemas.py      hợp đồng dữ liệu pandera + kiểm tra phân phối         (A4)
├── train.py        LightGBM, early stopping, Platt, bundle text + JSON   (A5)
├── decision.py     hiệu chỉnh, giá trị kỳ vọng, danh sách gọi, lợi nhuận (A5)
├── marketing.py    feature khuyến mãi của đối thủ                        (A6)
├── explain.py      SHAP → nhóm lý do → câu tiếng Việt + việc nên làm     (A6)
├── score.py        chấm điểm tháng mới, xuất danh sách cho CSKH          (A6)
├── api.py          FastAPI: /health /version /score /top / (demo)        (A7)
├── tracking.py     ghi bundle vào MLflow                                 (A7)
└── report.py       báo cáo 1 trang                                       (A8)
```

Dữ liệu, model, `mlruns/` và `.env` **không** nằm trong Git (`.gitignore`). Mọi thứ sinh lại được bằng `make all`.
Tài liệu học đi kèm từng file: [Giai đoạn A · Nền tảng](../../docs/03-giai-doan-a-nen-tang/README.md). Code trong tài
liệu được kiểm tra khớp nguyên văn với code ở đây (`tests/test_doc_sync.py`, cập nhật bằng
`uv run python scripts/sync_doc.py`).

## Kỹ năng đã luyện

PY-01, PY-02 (Trung cấp), PY-03 (Trung cấp), BIZ-01, BIZ-02, BIZ-03 (Trung cấp), BIZ-04, DATA-01, DATA-02, DATA-03
(Trung cấp), DATA-04, DATA-05, STAT-01, STAT-02, STAT-05 (Trung cấp), ML-01, ML-02 (Trung cấp), ML-03 (Trung cấp),
ML-04 (Trung cấp), OPS-01, OPS-02, OPS-08 — đối chiếu tiêu chí "Đạt khi" ở
[bảng tự đánh giá cuối giai đoạn](../../docs/03-giai-doan-a-nen-tang/README.md#tự-đánh-giá-cuối-giai-đoạn).
