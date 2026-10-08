# web/ — trang lộ trình (GitHub Pages)

Trang web tĩnh hiển thị lộ trình học **từng bước, từ cơ bản đến nâng cao**, sinh hoàn toàn từ `catalog/*.yaml`.
Không cần Node hay build tool: HTML/CSS/JavaScript thuần, dữ liệu được nhúng vào `index.html` lúc build.

Địa chỉ sau khi bật Pages: `https://superken-python.github.io/ai-architecture/`

## Có gì trên trang

| Trang | Nội dung |
|---|---|
| Tổng quan | Số liệu chính, 4 giai đoạn, 2 họ bài toán, kỹ năng đòn bẩy, tài liệu |
| Lộ trình | 4 giai đoạn (A Nền tảng → B GenAI → C Chuyên sâu → D Nâng cao/production); mỗi bước có việc cần làm, sản phẩm nộp, kỹ năng + mức mục tiêu; 5 hướng chuyên sâu; thanh ngang chữ T |
| Nhóm bài toán | Quiz nhận diện bài toán trong 30 giây; trang từng nhóm có lộ trình 3 chặng Cơ bản → Trung cấp → Nâng cao |
| Kỹ năng | Tìm kiếm (gõ không dấu được), lọc theo mảng/tầng/nhóm; trang từng kỹ năng có thang 3 mức, tiên quyết, mở khóa, vị trí trong lộ trình |
| Ma trận | Kỹ năng × nhóm; bản đồ nhiệt mức chia sẻ kỹ năng giữa các nhóm |
| Tổ hợp | Dự án ghép nhiều nhóm, kỹ năng keo, bẫy khi ghép |
| Tiến độ | Đánh dấu mức đã đạt; tổng hợp theo giai đoạn, mảng, nhóm; xuất/nhập file JSON |

Tiến độ lưu trong `localStorage` của trình duyệt người xem — không gửi đi đâu. Muốn chuyển máy hoặc gửi người hướng
dẫn: trang **Tiến độ** → *Xuất file tiến độ*, rồi *Nhập file* ở máy kia.

## Xem thử tại máy

```bash
make site          # sinh vào _site/ (đã nằm trong .gitignore)
make site-serve    # sinh rồi mở http://localhost:8000
make site-test     # kiểm thử bằng Chromium thật (Playwright): mọi trang, desktop + điện thoại
```

`make site-test` cần Chromium cho Playwright, tải một lần: `uv run --with playwright playwright install chromium`.

## Triển khai lên GitHub Pages

Workflow [.github/workflows/pages.yml](../.github/workflows/pages.yml) tự sinh và triển khai trang mỗi khi `main` thay đổi.
Chỉ cần bật **một lần**:

1. Vào repo trên GitHub → **Settings** → **Pages**.
2. Mục **Build and deployment** → **Source**: chọn **GitHub Actions**.
3. Merge một thay đổi vào `main` (hoặc vào tab **Actions** → *Pages* → **Run workflow**).
4. Sau khi workflow xanh, địa chỉ trang hiện ở **Settings → Pages** và trong job *deploy*.

Repo private: GitHub Pages cho repo private cần gói GitHub có hỗ trợ (Pro/Team/Enterprise); với repo public thì miễn phí.

## Cấu trúc

```
web/
├── index.html        # khung trang; dòng <!--CATALOG_DATA--> được thay bằng dữ liệu lúc build
├── assets/
│   ├── style.css     # giao diện, sáng/tối theo hệ điều hành + nút chuyển
│   └── app.js        # điều hướng (#/...), các trang, tiến độ, quiz, bộ lọc
└── README.md
src/aiarch/site.py    # build: đọc catalog, kiểm tra, tính sẵn dữ liệu, ghi _site/
scripts/smoke_site.py # kiểm thử bằng trình duyệt thật
```

## Sửa nội dung

Không sửa dữ liệu trong `web/` — sửa `catalog/*.yaml` (lộ trình ở `catalog/roadmap.yaml`), chạy `make catalog` để kiểm
tra và sinh lại Markdown, `make site-serve` để xem trang. Sửa giao diện thì sửa `web/assets/`.
