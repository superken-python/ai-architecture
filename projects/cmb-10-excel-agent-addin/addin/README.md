# Office add-in: chạy Excel Agent trong Excel thật

Task pane (`web/taskpane.html`) dùng chung khung chat với web POC; khác ở chỗ công cụ Excel chạy bằng **Office.js** trên
workbook đang mở (`web/js/hosts/office-host.js`). Manifest: [`manifest.xml`](manifest.xml) (dạng XML, add-in only,
nút **Mở Excel Agent** ở tab Home, yêu cầu ExcelApi 1.7).

## Cần có

- Excel Microsoft 365 (web, Windows hoặc Mac) — tài khoản được phép tải add-in lên (Upload My Add-in).
- Node.js (chỉ để tạo chứng chỉ HTTPS localhost) và môi trường POC đã `make setup`.

## Chạy trên máy dev

```bash
cd projects/cmb-10-excel-agent-addin
make addin-certs   # một lần: tạo + tin cậy chứng chỉ https://localhost (office-addin-dev-certs)
make dev-https     # server tại https://localhost:7777 — mở thử https://localhost:7777/static/taskpane.html
```

Sau đó nạp manifest vào Excel:

| Excel | Cách nạp `addin/manifest.xml` |
|---|---|
| **Web** (excel.office.com / SharePoint) | Mở một workbook → **Home → Add-ins → More Add-ins → My Add-ins → Upload My Add-in** → chọn file |
| **Windows** | `npx office-addin-debugging start addin/manifest.xml desktop` (tự mở Excel và nạp), hoặc thư mục chia sẻ làm Trusted Add-in Catalog |
| **Mac** | Chép `manifest.xml` vào `~/Library/Containers/com.microsoft.Excel/Data/Documents/wef/` rồi mở lại Excel |

Nút **Mở Excel Agent** xuất hiện ở tab **Home**. Thử với một sheet có dòng tiêu đề (tốt nhất là Excel Table): tải file
mẫu từ web POC (`http://127.0.0.1:7777`, tạo file rồi bấm ⬇) hoặc bấm **Chèn vào workbook** trên thẻ file trong task pane.

## Triển khai cho công ty

1. Đưa server lên domain HTTPS của công ty (cùng một server phục vụ `/agui`, `/api/v1`, `/static`).
2. `make addin-manifest BASE_URL=https://excel-agent.<công-ty>.vn` → `var/manifest.xml`.
3. Admin Microsoft 365: **Admin center → Settings → Integrated apps → Upload custom apps** → giao cho nhóm người dùng.
4. Trước khi dùng thật: thêm đăng nhập (NAA/Entra ID → JWT của AgentOS) — xem tài liệu 02, mục 7.

## Giới hạn đã biết của bản POC

- **Chưa chạy thử trên Excel thật** (môi trường làm POC không có Excel). Logic Office.js được kiểm bằng test Playwright với
  một bản Office.js giả lập (`tests/e2e/fake_office.js`) mô phỏng đúng các API đang dùng.
- Vùng dữ liệu = Excel Table đầu tiên của sheet, không có thì vùng đã dùng (dòng đầu là tiêu đề). Sheet có tiêu đề
  báo cáo phía trên bảng nên chuyển bảng thành Excel Table (Ctrl+T).
- Đọc tối đa 5.000 dòng mỗi lần tìm; ghi tối đa 200 dòng mỗi lần.
- Hoàn tác: Ctrl+Z như thao tác tay (Excel hỗ trợ hoàn tác thay đổi của add-in trên bản Microsoft 365 mới).
