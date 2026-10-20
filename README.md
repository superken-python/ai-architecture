# ai-architecture

Bản đồ học và làm AI trong doanh nghiệp: từ **các bài toán thị trường cần** đến **các kỹ năng lập trình cần có**
(cơ bản → trung cấp → nâng cao), cách **ghép kỹ năng** cho dự án thật, và cách **tiết kiệm token mà vẫn chính xác**.

## Các giai đoạn

| Giai đoạn | Nội dung | Trạng thái |
|---|---|---|
| [00 · Setup](docs/00-setup/README.md) | Chuẩn bị môi trường: công cụ, Python/uv, API key, GPU, dữ liệu | ✅ |
| [01 · Bản đồ bài toán](docs/01-problem-map/README.md) | 9 nhóm bài toán AI doanh nghiệp, 5 khối, cách nhận diện, lộ trình 6 tháng | ✅ |
| [02 · Bản đồ kỹ năng](docs/02-skill-map/README.md) | 67 kỹ năng × 10 mảng × 3 mức; dùng chung / riêng / kết hợp; tiết kiệm token & độ chính xác | ✅ |
| [Giai đoạn A · Nền tảng](docs/03-giai-doan-a-nen-tang/README.md) | 8 bài lý thuyết + lab chi tiết (tuần 1–8), cùng xây một real case từ đầu: dự đoán khách rời mạng từ 8 bảng vận hành tới API Docker và báo cáo 1 trang | ✅ |
| [Radar agent · Nhóm 7](docs/agent-radar/README.md) | Chọn framework/công cụ cho agent: 19 framework + 18 công cụ hỗ trợ, vòng Adopt/Trial/Assess/Hold, số liệu registry cập nhật tự động hằng tháng | 🔄 |
| [Trang web lộ trình](web/README.md) | Lộ trình 4 giai đoạn từng bước, cơ bản → nâng cao, tự đánh dấu tiến độ — GitHub Pages | ✅ |
| [03 · Labs](labs/README.md) | Bài lab ngắn cho từng kỹ năng, theo thứ tự lộ trình | ⏳ |
| [04 · Dự án](projects/README.md) | Dự án luyện tập cho 9 nhóm và các tổ hợp; mới: [video dạy chữ cái](projects/g9-video-chu-cai/README.md) (Nhóm 9) | ⏳ |
| 05 · Production | Mẫu triển khai, giám sát, vận hành chi phí cho dự án thật | 🔜 |

## Bắt đầu

```bash
git clone https://github.com/superken-python/ai-architecture.git && cd ai-architecture
make setup      # cần Git + uv — xem docs/00-setup
make doctor     # kiểm tra môi trường
make check      # lint + test + kiểm tra catalog
```

Rồi đọc theo thứ tự: [setup](docs/00-setup/README.md) → [bản đồ bài toán](docs/01-problem-map/README.md) →
[bản đồ kỹ năng](docs/02-skill-map/README.md) → [lộ trình học](docs/02-skill-map/04-lo-trinh-hoc.md).
Hoặc mở **trang web lộ trình** (`https://superken-python.github.io/ai-architecture/` sau khi bật Pages; xem thử tại
máy bằng `make site-serve`): lộ trình, kỹ năng, nhóm bài toán và tài liệu nối với nhau — từ một bước hay một kỹ năng
bấm **Học ngay** là mở bài học, lab ngay trên trang (Markdown hiển thị như GitHub: code, bảng, sơ đồ mermaid, công thức).

## Cấu trúc thư mục

```
ai-architecture/
├── catalog/                    # NGUỒN DỮ LIỆU DUY NHẤT (YAML) cho bài toán, kỹ năng, tổ hợp
│   ├── problems.yaml           #   9 nhóm, 2 họ, ma trận giai đoạn 1
│   ├── skills.yaml             #   10 mảng, 67 kỹ năng
│   ├── combinations.yaml       #   10 tổ hợp dự án nhiều nhóm
│   ├── roadmap.yaml            #   lộ trình 4 giai đoạn, từng bước + mức mục tiêu
│   ├── docs.yaml               #   tài liệu theo chủ đề + bài nào dạy bước/kỹ năng nào → liên kết chéo trên web
│   └── agent_landscape.yaml    #   radar framework agent (+ .snapshot.json do `make landscape-refresh` kéo)
├── docs/
│   ├── 00-setup/               # chuẩn bị môi trường (đọc đầu tiên)
│   ├── 01-problem-map/         # giai đoạn 1 — bản đồ bài toán (+ file .docx gốc)
│   ├── 02-skill-map/           # giai đoạn 2 — bản đồ kỹ năng
│   │   ├── 0x-*.md             #   tài liệu viết tay: kiến trúc, kết hợp, token, lộ trình
│   │   └── generated/          #   SINH TỰ ĐỘNG từ catalog/: ma trận, thẻ kỹ năng, lộ trình theo nhóm
│   ├── 03-giai-doan-a-nen-tang/ # bài học Giai đoạn A (A1–A8), code trích nguyên văn từ projects/g1-churn-telco
│   └── agent-radar/            # tài liệu sống: radar framework agent (Nhóm 7), bảng sinh từ catalog/agent_landscape.*
├── web/                        # trang web lộ trình (HTML/CSS/JS thuần) → GitHub Pages
├── src/aiarch/                 # thư viện dùng chung (catalog: kiểm tra + sinh Markdown; site + docview: sinh trang web)
├── labs/                       # giai đoạn 3 — lab theo kỹ năng: labs/<id>-<mức>-<tên>/
├── projects/                   # giai đoạn 4 — dự án theo nhóm: projects/g<N>-<tên>/
├── templates/                  # mẫu: kỹ năng (YAML), lab, dự án
├── scripts/check_env.py        # `make doctor`
├── tests/                      # test cho catalog và liên kết tài liệu
├── data/                       # dữ liệu cục bộ — KHÔNG commit (trừ README)
├── pyproject.toml · uv.lock    # phụ thuộc chia theo nhóm bài toán (uv dependency groups)
└── Makefile                    # setup, doctor, catalog, lint, test, check
```

Nguyên tắc mở rộng:

- **Dữ liệu tách khỏi trình bày:** thêm nhóm/kỹ năng/tổ hợp = sửa YAML, chạy `make catalog`; ma trận, thẻ kỹ năng,
  lộ trình theo nhóm và bảng tự đánh giá tự cập nhật. Bộ kiểm tra chặn id trùng, tiên quyết lỗi, vòng lặp và
  **thiếu độ phủ** so với ma trận bài toán.
- **Mã ổn định** (`G1`, `ML-07`, `CMB-03`) nối tài liệu ↔ lab ↔ dự án.
- **Giai đoạn mới = thư mục `docs/0N-...` mới**, không phá cấu trúc cũ.
- **Kỹ năng dùng chung → code dùng chung:** khi hai dự án cần cùng một tiện ích (harness đánh giá, client LLM đo chi
  phí...), đưa nó vào `src/aiarch/`.

Việc sắp làm: [CHECKLIST.md](CHECKLIST.md) · Đã làm: [HISTORY.md](HISTORY.md) · Đóng góp: [CONTRIBUTING.md](CONTRIBUTING.md).
