# web/ — trang lộ trình (GitHub Pages)

Trang web tĩnh hiển thị lộ trình học **từng bước, từ cơ bản đến nâng cao**, sinh hoàn toàn từ `catalog/*.yaml`.
Không cần Node hay build tool: HTML/CSS/JavaScript thuần, dữ liệu được nhúng vào `index.html` lúc build. Mọi tài liệu
Markdown của repo **đọc ngay trên trang** (khung xem toàn màn hình, định dạng như GitHub), không phải chuyển sang GitHub.

Địa chỉ sau khi bật Pages: `https://superken-python.github.io/ai-architecture/`

## Có gì trên trang

| Trang | Nội dung |
|---|---|
| Tổng quan | Thẻ **Tiếp tục học** (bước kế tiếp + bài học, lab của bước), số liệu chính, 4 giai đoạn, 2 họ bài toán, kỹ năng đòn bẩy |
| Lộ trình | 4 giai đoạn (A Nền tảng → B GenAI → C Chuyên sâu → D Nâng cao/production); mỗi bước có **Học ngay** (bài học + lab của bước, hoặc tài liệu liên quan), việc cần làm, sản phẩm nộp, kỹ năng + mức mục tiêu; 6 hướng chuyên sâu; thanh ngang chữ T |
| Nhóm bài toán | Quiz nhận diện bài toán trong 30 giây; nhóm có `demo` trong catalog hiện **video mẫu** (Nhóm 9: trình phát + nút nhảy tới từng chữ cái); trang từng nhóm có **Học và thực hành** (dự án, tài liệu, giai đoạn dùng nhóm làm dự án) và lộ trình 3 chặng Cơ bản → Trung cấp → Nâng cao, mỗi kỹ năng có nút học ngay |
| Kỹ năng | Tìm kiếm (gõ không dấu được), lọc theo mảng/tầng/nhóm; trang từng kỹ năng có **Học kỹ năng này** (bài học, lab, tài liệu theo mức; dự án áp dụng), thang 3 mức, tiên quyết, mở khóa, vị trí trong lộ trình |
| Tài liệu | Mọi tài liệu viết tay theo chủ đề; mỗi thẻ mở khung xem và dẫn tới bước, kỹ năng, nhóm liên quan |
| Khung xem tài liệu (`#/doc/<đường dẫn>`) | Markdown render như GitHub: bảng, task list, alert, code tô màu + nút sao chép, sơ đồ mermaid, công thức, ảnh, video/âm thanh/phụ đề (`<video>`, `<track>`), anchor tiêu đề; file code có số dòng (`#L10-L20`); mục lục, đầu trang ghi bài thuộc bước/kỹ năng nào và học cùng lab nào, cuối trang đánh dấu kỹ năng đã đạt + bài trước/tiếp + cùng thư mục. Link tới thẻ kỹ năng/nhóm/lộ trình sinh tự động mở trang tương tác; link permalink theo commit vẫn mở GitHub |
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
Kiểm thử mở **mọi** tài liệu đã render trên cả hai cỡ màn hình: sơ đồ mermaid và công thức phải vẽ được (một sơ đồ sai
cú pháp — cũng hỏng trên GitHub — làm test đỏ), không tràn ngang; cùng các luồng mở/đóng/Esc/chuyển tài liệu.

Khung xem tài liệu tải nội dung bằng `fetch`, nên cần mở trang qua HTTP (`make site-serve` hoặc GitHub Pages). Mở thẳng
file `_site/index.html` thì các trang lộ trình vẫn chạy, riêng tài liệu sẽ báo cần chạy `make site-serve`.

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
├── index.html          # khung trang + khung xem tài liệu; dòng <!--CATALOG_DATA--> được thay bằng dữ liệu lúc build
├── assets/
│   ├── style.css       # giao diện, sáng/tối theo hệ điều hành + nút chuyển; Markdown kiểu GitHub, màu code GitHub
│   ├── app.js          # điều hướng (#/...), các trang, liên kết học, khung xem tài liệu, tiến độ, quiz, bộ lọc
│   └── vendor/         # mermaid + KaTeX (ghim phiên bản, kiểm mã băm) — chỉ tải khi tài liệu có sơ đồ/công thức
└── README.md
catalog/docs.yaml       # tài liệu theo chủ đề + quan hệ với bước/kỹ năng/nhóm/tổ hợp → liên kết chéo trên web
src/aiarch/site.py      # build: đọc catalog, kiểm tra, tính sẵn dữ liệu + liên kết học, ghi _site/
src/aiarch/docview.py   # build: gom tài liệu theo liên kết, render Markdown giống GitHub → _site/md/<đường dẫn>.html
scripts/smoke_site.py   # kiểm thử bằng trình duyệt thật
scripts/vendor_web.py   # tải lại thư viện trong assets/vendor/ (đổi phiên bản)
```

Trang tài liệu được gom bắt đầu từ `catalog/docs.yaml`, README của lab/dự án, tài liệu sinh tự động, rồi đi theo mọi
liên kết tương đối (kèm các file `.md` cùng thư mục, như cây file của GitHub). **Chỉ file Git đang theo dõi** được đưa
lên trang: dữ liệu, model, `.env` nằm trong `.gitignore` nên không bao giờ lọt ra ngoài. Lưu ý: bật Pages công khai
cho repo private thì nội dung các tài liệu này cũng công khai theo.

## Sửa nội dung

Không sửa dữ liệu trong `web/` — sửa `catalog/*.yaml` (lộ trình ở `catalog/roadmap.yaml`), chạy `make catalog` để kiểm
tra và sinh lại Markdown, `make site-serve` để xem trang. Sửa giao diện thì sửa `web/assets/`.

Thêm bài học/lab/dự án mới: viết file `.md`, rồi khai báo trong `catalog/docs.yaml` (nhóm chủ đề + `kind` + `step` hoặc
`skills`/`groups`/`combos`). Trang web tự nối: bước đó hiện **Học ngay**, kỹ năng của bước có bài để học, nhóm/tổ hợp
có dự án. `make catalog` báo lỗi nếu file không tồn tại hoặc tham chiếu sai id.
