# web/assets/vendor — thư viện bên thứ ba của khung xem tài liệu

Trang web tự chứa thư viện thay vì gọi CDN, để sơ đồ và công thức luôn hiện được (kể cả khi mạng chặn CDN) và kiểm thử
chạy được không cần mạng. Mỗi thư viện chỉ được tải khi tài liệu đang mở cần đến nó.

| Thư viện | Phiên bản | Dùng cho | Giấy phép | Nguồn |
|---|---|---|---|---|
| [mermaid](https://mermaid.js.org) | 11.17.2 | Vẽ khối ` ```mermaid ` (flowchart, sequence, ER...) như GitHub | MIT (`mermaid/LICENSE`) | npm `mermaid`, file `dist/mermaid.min.js` |
| [KaTeX](https://katex.org) | 0.16.47 | Vẽ công thức `$…$`, `$$…$$`, ` ```math ` | MIT (`katex/LICENSE`) | npm `katex`, `dist/katex.min.{js,css}` + font woff2 |

Không sửa tay các file ở đây. Đổi phiên bản: sửa `PACKAGES` trong `scripts/vendor_web.py` (phiên bản + mã băm
`integrity` lấy ở `https://registry.npmjs.org/<tên>/<phiên bản>`), rồi chạy `make site-vendor` — script tải gói từ
registry npm, kiểm tra mã băm sha512, giải nén đúng các file cần. Sau đó chạy `make site-test`.
