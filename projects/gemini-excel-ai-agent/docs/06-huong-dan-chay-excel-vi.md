# 06 · Hướng dẫn triển khai và chạy với Microsoft Excel (Tiếng Việt)

Tài liệu này hướng dẫn chi tiết từng bước từ cài đặt môi trường, cấu hình dịch vụ AI Agent, khởi động server cho đến cách nạp (sideload) plugin vào Microsoft Excel (cả bản Desktop trên Windows/macOS và bản Excel Online trên trình duyệt web).

---

## 1. Yêu cầu hệ thống cần chuẩn bị

- **Python:** Phiên bản 3.11 hoặc 3.12 (khuyến nghị dùng `poetry` theo chuẩn repo).
- **Microsoft Excel:** Một trong các phiên bản sau:
  - Excel trên Web (Microsoft 365 Online - Miễn phí hoặc tài khoản doanh nghiệp).
  - Excel Desktop trên Windows (Microsoft 365, Office 2019/2021).
  - Excel Desktop trên macOS (Microsoft 365).
- **Trình duyệt Web:** Microsoft Edge hoặc Google Chrome.

---

## 2. Bước 1: Cài đặt môi trường Backend

Mở terminal tại thư mục dự án `projects/gemini-excel-ai-agent`:

```bash
cd projects/gemini-excel-ai-agent

# Cài đặt các gói phụ thuộc bằng Poetry
poetry install
```

---

## 3. Bước 2: Cấu hình biến môi trường (.env)

Tạo file `.env` từ file mẫu `.env.example`:

```bash
cp .env.example .env
```

Mở file `.env` và điền thông tin Azure OpenAI API Key của bạn (hoặc để trống để hệ thống tự động chạy chế độ Mock Test):

```dotenv
# Cấu hình Azure OpenAI Service
AZURE_OPENAI_API_KEY=your-actual-azure-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_DEPLOYMENT_NAME=gpt-5-mini
AZURE_OPENAI_MODEL=gpt-5-mini

# Cấu hình Server
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

> [!NOTE]
> Hệ thống được trang bị cơ chế **Smart Fallback Strategy**. Nếu bạn chưa có sẵn Azure API Key, hệ thống vẫn khởi động mượt mà và cho phép bạn thử nghiệm 100% tính năng tra cứu `/search`, Preview Diff và chèn dòng dữ liệu vào Excel!

---

## 4. Bước 3: Khởi động Server Backend & Taskpane UI

Chạy lệnh dev server:

```bash
poetry run uvicorn excel_agent.main:app --reload --host 0.0.0.0 --port 8000
```
*(Hoặc dùng lệnh ngắn gọn: `make dev`)*

Kiểm tra trạng thái server:
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)
- Giao diện Taskpane: [http://localhost:8000/taskpane/index.html](http://localhost:8000/taskpane/index.html)

---

## 5. Bước 4: Kiểm thử nhanh trên Web Browser Simulator

Trước khi mở Excel, bạn có thể kiểm tra trực tiếp giao diện Add-in trên trình duyệt thông thường:
1. Mở trình duyệt truy cập: `http://localhost:8000/taskpane/index.html`.
2. Bấm nút pill: `🔍 /search Áo thun` hoặc gõ lệnh `/search Vải` vào ô chat.
3. Chatbot sẽ hiển thị các sản phẩm tìm được trong Mock Database.
4. Bấm nút `+ Chèn vào Excel` → Thẻ **Preview Diff** sẽ hiện lên hỏi bạn xác nhận.
5. Bấm `Xác nhận ghi (Apply)` → Dòng dữ liệu sẽ được tự động chèn ngay lập tức vào bảng tính mẫu trong tab **"Bảng tính mẫu"**!

---

## 6. Bước 5: Nạp (Sideload) Plugin vào Microsoft Excel thật

Có 2 phương thức phổ biến để nạp file `addin/manifest.xml` vào Excel:

### Phương pháp 1: Chạy trên Excel on the Web (Office 365 Browser) — Khuyến nghị vì nhanh nhất
1. Truy cập [https://excel.new](https://excel.new) hoặc [https://office.com](https://office.com) và mở một file Excel mới.
2. Trên thanh menu Ribbon trên cùng, chọn thẻ **Insert (Chèn)**.
3. Bấm vào nút **Office Add-ins (Tiện ích bổ sung Office)**.
4. Chọn tab **Upload My Add-in (Tải lên Tiện ích bổ sung của tôi)**.
5. Bấm **Browse (Duyệt)** và chọn file:
   `projects/gemini-excel-ai-agent/addin/manifest.xml`.
6. Bấm **Upload (Tải lên)**.
7. Ngay lập tức, thanh Taskpane **"Excel AI Copilot"** sẽ xuất hiện ở cạnh phải của bảng tính!

### Phương pháp 2: Chạy trên Excel Desktop Windows
1. Mở ứng dụng **Excel** trên máy tính.
2. Tạo một thư mục chia sẻ cục bộ (Shared Folder) trên Windows (ví dụ: `C:\OfficeManifests`), copy file `manifest.xml` vào đó.
3. Trong Excel, vào **File** > **Options** > **Trust Center** > **Trust Center Settings** > **Trusted Add-in Catalogs**.
4. Điền đường dẫn thư mục `C:\OfficeManifests`, bấm **Add catalog**, tích chọn **Show in Menu** và bấm **OK**.
5. Khởi động lại Excel. Vào thẻ **Insert** > **My Add-ins** > chọn tab **Shared Folder** và chọn **Excel AI Copilot**.

### Phương pháp 3: Chạy trên Excel Desktop macOS
1. Mở Finder trên macOS, bấm tổ hợp phím `Cmd + Shift + G` và dán đường dẫn:
   `~/Library/Containers/com.microsoft.Excel/Data/Documents/wef/`
   *(Nếu thư mục `wef` chưa tồn tại, hãy tạo mới nó)*.
2. Sao chép file `manifest.xml` vào thư mục `wef/` này.
3. Mở Excel for Mac. Vào thẻ **Insert** > bấm mũi tên bên cạnh **My Add-ins** → Bạn sẽ thấy **AI Agent Copilot** xuất hiện trong danh sách.

> [!TIP]
> **Về chứng chỉ HTTPS khi chạy trong Excel Desktop:**
> Office Desktop yêu cầu Add-in phải chạy qua kết nối bảo mật HTTPS. Để cấp SSL cho localhost, bạn chỉ cần chạy lệnh:
> ```bash
> npx office-addin-dev-certs install
> ```
> Hoặc mở trực tiếp trên Excel on the Web (Google Chrome) vốn chấp nhận HTTP localhost linh hoạt.

---

## 7. Kịch bản kiểm thử mẫu (Test Cases)

Sau khi Taskpane đã mở bên cạnh bảng tính Excel:

### Kịch bản 1: Tra cứu danh mục bằng lệnh `/search`
- **Gõ vào chat:** `/search Áo thun`
- **Kết quả:** Trả về danh sách sản phẩm khớp từ Mock DB với mã `SP-001`, giá `250.000 đ`. Bấm nút chèn để đẩy vào bảng tính.

### Kịch bản 2: Ra lệnh bằng ngôn ngữ tự nhiên
- **Gõ vào chat:** *"Tìm trong kho mã hàng SP-002 rồi chèn dòng mới vào bảng giúp tôi"*
- **Kết quả:** Agent tự động hiểu ý định, truy vấn DB, tạo thẻ Preview Diff dòng 2 (hoặc dòng trống tiếp theo) và chờ bạn bấm `Apply`.

### Kịch bản 3: Tra cứu trực tiếp trên tab "Tra cứu DB"
- Chuyển sang Tab 2 trên Taskpane.
- Gõ từ khóa `Vải` hoặc `Carton` vào ô tìm kiếm.
- Bấm `Tìm kiếm` và bấm `➕ Chèn vào Excel`.
- Quan sát dữ liệu xuất hiện trực tiếp trên worksheet Excel của bạn!
