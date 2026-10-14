# 06 · Hướng dẫn chi tiết cài đặt & sử dụng trên Excel Web và Excel Desktop App (macOS & Windows)

Tài liệu này là cẩm nang toàn diện hướng dẫn **từng bước chi tiết** từ chuẩn bị môi trường, nạp (sideload) plugin vào Microsoft Excel (cả bản **Web** và bản **Desktop App trên macOS / Windows**), cho đến hướng dẫn sử dụng thực tế toàn bộ tính năng của trợ lý AI Agent.

---

## MỤC LỤC
1. [Phần I: Chuẩn bị môi trường & Khởi động dịch vụ](#phan-1)
2. [Phần II: Hướng dẫn cài đặt / nạp (Sideload) vào Excel](#phan-2)
   - [Mục A: Excel on the Web (Office 365 Trình duyệt)](#muc-a-web)
   - [Mục B: Excel Desktop App trên macOS](#muc-b-macos)
   - [Mục C: Excel Desktop App trên Windows](#muc-c-windows)
   - [Mục D: Triển khai tập trung cho toàn công ty (M365 Admin)](#muc-d-admin)
3. [Phần III: Hướng dẫn chi tiết sử dụng các tính năng](#phan-3)
   - [3.1. Mở và ghim thanh công cụ AI Copilot](#hd-31)
   - [3.2. Tra cứu dữ liệu nhanh bằng lệnh `/search`](#hd-32)
   - [3.3. Duyệt danh mục qua Tab "Tra cứu DB" & Chèn 1-click](#hd-33)
   - [3.4. Cơ chế kiểm tra an toàn Preview Diff (Human-in-the-Loop)](#hd-34)
   - [3.5. Ra lệnh hội thoại tự nhiên với AI Agent](#hd-35)
   - [3.6. Tự động kế thừa và tính toán công thức Excel](#hd-36)
4. [Phần IV: Xử lý sự cố thường gặp (Troubleshooting)](#phan-4)

---

<a id="phan-1"></a>
## PHẦN I: CHUẨN BỊ MÔI TRƯỜNG & KHỞI ĐỘNG DỊCH VỤ

### Bước 1.1: Khởi động Backend AI Agent (FastAPI + Agno SDK)
Mở cửa sổ Terminal tại thư mục dự án:
```bash
cd projects/gemini-excel-ai-agent

# 1. Cài đặt các thư viện cần thiết
poetry install

# 2. Tạo file cấu hình từ template
cp .env.example .env

# 3. Khởi chạy server
poetry run uvicorn excel_agent.main:app --reload --host 0.0.0.0 --port 8000
```
*(Hoặc dùng lệnh tắt: `make dev`)*

> [!NOTE]
> Hệ thống tích hợp sẵn **Smart Mock Fallback Strategy**. Nếu bạn chưa điền Azure API Key trong `.env`, hệ thống vẫn hoạt động đầy đủ để bạn thử nghiệm 100% tính năng tra cứu `/search`, Preview Diff và ghi dữ liệu vào Excel!

### Bước 1.2: Thiết lập chứng chỉ HTTPS SSL cho Localhost (Bắt buộc cho Desktop App)
Khác với Excel on the Web, **Excel Desktop App trên cả Mac và Windows chạy trong môi trường WebView bảo mật (Apple WebKit / Edge WebView2) và bắt buộc URL Add-in phải là HTTPS có chứng chỉ tin cậy**.

Chạy lệnh chính thức của Microsoft để cấp chứng chỉ SSL cục bộ:
```bash
npx office-addin-dev-certs install
```
Khi hộp thoại hệ điều hành hiện lên hỏi quyền thêm chứng chỉ vào Trusted Root, chọn **Yes / Cho phép**.

### Bước 1.3: Kiểm tra hệ thống trước khi nạp
Mở trình duyệt truy cập:
- Kiểm tra API Backend: [http://localhost:8000/health](http://localhost:8000/health) → Báo `"status": "healthy"`.
- Kiểm tra giao diện Taskpane: [http://localhost:8000/taskpane/index.html](http://localhost:8000/taskpane/index.html).

---

<a id="phan-2"></a>
## PHẦN II: HƯỚNG DẪN CÀI ĐẶT / NẠP (SIDELOAD) VÀO EXCEL

File manifest dùng để nạp vào Excel nằm tại:
`projects/gemini-excel-ai-agent/addin/manifest.xml`

---

<a id="muc-a-web"></a>
### MỤC A: Cài trên Excel on the Web (Microsoft 365 trên trình duyệt)
*Cách này tiện lợi nhất, chạy được ngay trên mọi máy tính không cần cài đặt phần mềm.*

1. Mở trình duyệt web, truy cập [https://excel.new](https://excel.new) (hoặc [https://office.com](https://office.com)) và đăng nhập tài khoản Microsoft.
2. Mở một **Sổ làm việc trống mới (Blank workbook)**.
3. Trên thanh công cụ Ribbon trên cùng, bấm chọn thẻ **Insert (Chèn)**.
4. Bấm vào nút **Add-ins (Tiện ích bổ sung)** hoặc **Office Add-ins**.
5. Trong cửa sổ popup hiện lên, nhìn lên menu trên cùng và chọn tab **Upload My Add-in (Tải lên tiện ích bổ sung của tôi)**.
6. Bấm nút **Browse... (Duyệt...)** và tìm chọn file:
   `projects/gemini-excel-ai-agent/addin/manifest.xml`
7. Bấm nút **Upload (Tải lên)**.
8. **Kết quả:** Ngay lập tức, thanh tác vụ **Excel AI Copilot** sẽ xuất hiện ở cạnh phải màn hình!

---

<a id="muc-b-macos"></a>
### MỤC B: Cài trên Excel Desktop App trên macOS (Bản quyền Mac)
*Dành cho ứng dụng Microsoft Excel cài trực tiếp trên máy Mac.*

Excel for Mac sử dụng thư mục hệ thống có tên **`wef` (Web Extension Framework)** để tự động nhận diện Add-in nội bộ.

#### Bước 1: Sao chép file manifest vào thư mục `wef` của macOS
Mở ứng dụng **Terminal** trên Mac và chạy 2 lệnh sau:
```bash
# Tạo thư mục wef nếu chưa tồn tại
mkdir -p ~/Library/Containers/com.microsoft.Excel/Data/Documents/wef

# Copy manifest.xml vào thư mục wef
cp /Users/duc.nguyen/data/projects/success/motives/motivesidp-ai-learning/ai-architecture/projects/gemini-excel-ai-agent/addin/manifest.xml ~/Library/Containers/com.microsoft.Excel/Data/Documents/wef/
```

*(Hoặc mở **Finder** > bấm tổ hợp phím `Cmd + Shift + G` > dán `~/Library/Containers/com.microsoft.Excel/Data/Documents/wef/` và kéo thả file `manifest.xml` vào đó).*

#### Bước 2: Bật plugin trong ứng dụng Excel for Mac
1. Mở ứng dụng **Microsoft Excel** trên máy Mac.
2. Mở một file Excel bất kỳ.
3. Bấm vào thẻ **Insert (Chèn)** trên thanh Ribbon.
4. Nhìn sang bên phải mục *Add-ins*, bấm vào **mũi tên nhỏ thả xuống (drop-down)** nằm ngay cạnh nút **My Add-ins (Tiện ích của tôi)**.
5. Bạn sẽ thấy danh mục **Developer Add-ins (Tiện ích của nhà phát triển)** hiển thị mục: **AI Agent Copilot**.
6. Bấm vào **AI Agent Copilot**:
   - Khung Taskpane trượt ra bên phải màn hình.
   - Bạn đã sẵn sàng sử dụng!

*(Mẹo: Nếu chưa thấy xuất hiện, hãy thoát hoàn toàn Excel bằng `Cmd + Q` rồi mở lại).*

---

<a id="muc-c-windows"></a>
### MỤC C: Cài trên Excel Desktop App trên Windows (Bản quyền Windows)
*Dành cho ứng dụng Microsoft Excel cài trên Windows 10/11.*

Có 2 cách nạp trên Windows:

#### Cách C.1: Dùng tính năng Thư mục dùng chung (Shared Folder Catalog - Chuẩn của Microsoft)
1. Tạo một thư mục trên ổ cứng máy tính, ví dụ: `C:\OfficeManifests`.
2. Sao chép file `manifest.xml` vào thư mục `C:\OfficeManifests`.
3. Nhấp chuột phải vào thư mục `C:\OfficeManifests` > chọn **Properties (Thuộc tính)** > chọn thẻ **Sharing (Chia sẻ)**.
4. Bấm nút **Share...** > chọn tài khoản của bạn > bấm **Share** > bấm **Done**.
5. Copy đường dẫn mạng nội bộ (UNC path) vừa sinh ra, ví dụ: `\\localhost\OfficeManifests` hoặc `\\TEN-MAY\OfficeManifests`.
6. Mở ứng dụng **Excel** trên Windows:
   - Vào **File (Tệp)** > **Options (Tùy chọn)** ở góc dưới trái.
   - Chọn **Trust Center (Trung tâm tin cậy)** > bấm nút **Trust Center Settings... (Cài đặt trung tâm tin cậy...)**.
   - Ở cột trái chọn **Trusted Add-in Catalogs (Danh mục tiện ích bổ sung tin cậy)**.
   - Tại ô **Catalog Url**, dán đường dẫn: `\\localhost\OfficeManifests`.
   - Bấm nút **Add catalog (Thêm danh mục)**.
   - **Tích chọn ô vuông "Show in Menu" (Hiển thị trong menu)** bên cạnh đường dẫn vừa thêm.
   - Bấm **OK** > **OK**.
7. Khởi động lại Excel. Mở 1 trang tính > vào thẻ **Insert (Chèn)** > bấm **My Add-ins (Tiện ích của tôi)** > chọn tab **Shared Folder (Thư mục dùng chung)** ở trên > bấm vào **AI Agent Copilot** > bấm **Add**.

#### Cách C.2: Dùng lệnh CLI tự động (Dành cho Lập trình viên)
Trong thư mục dự án trên Windows, chạy lệnh:
```bash
npx office-addin-debugging start addin/manifest.xml desktop --app excel
```
Lệnh này tự động đăng ký manifest vào Windows Registry và khởi chạy Excel Desktop kèm plugin đã được cài sẵn trên Ribbon.

---

<a id="muc-d-admin"></a>
### MỤC D: Triển khai tập trung cho toàn công ty (Microsoft 365 Admin Center)
*Dành cho Quản trị viên IT của doanh nghiệp có gói bản quyền Microsoft 365 Business / Enterprise.*

Với phương pháp này, **nhân viên không cần tự cài đặt bất cứ thứ gì**:
1. IT Admin truy cập cổng quản trị: [https://admin.microsoft.com](https://admin.microsoft.com).
2. Vào mục **Settings (Cài đặt)** > **Integrated apps (Ứng dụng tích hợp)**.
3. Bấm **Upload custom apps (Tải ứng dụng tùy chỉnh)** > chọn **Office Add-in**.
4. Chọn **Upload manifest file (.xml)** và tải file `addin/manifest.xml` lên.
5. Chỉ định người dùng: Toàn bộ công ty (*Entire organization*) hoặc các phòng ban cụ thể (Kế toán, Mua hàng, Bán hàng).
6. Bấm **Deploy**.
7. **Kết quả:** Khi bất kỳ nhân viên nào mở Excel Desktop (Windows hoặc Mac), nút **AI Copilot** sẽ tự động hiển thị vĩnh viễn trên thanh Ribbon!

---

<a id="phan-3"></a>
## PHẦN III: HƯỚNG DẪN CHI TIẾT SỬ DỤNG CÁC TÍNH NĂNG

<a id="hd-31"></a>
### 3.1. Mở và ghim thanh công cụ AI Copilot
- Khi đã nạp plugin, trên thanh Ribbon của Excel sẽ có nhóm nút **Motives AI** với nút bấm **"Mở AI Copilot"**.
- Bấm vào nút để mở khung Taskpane ở bên phải bảng tính.
- Trên đầu Taskpane có đèn báo trạng thái màu xanh: **Online**.

---

<a id="hd-32"></a>
### 3.2. Tra cứu dữ liệu nhanh bằng lệnh `/search` (Slash Command)
Khi cần tìm kiếm thông tin hàng hóa, nguyên vật liệu từ cơ sở dữ liệu doanh nghiệp:
1. Trong ô nhập liệu ở cuối Taskpane, gõ cú pháp:
   ```
   /search <từ khóa>
   ```
   *Ví dụ thực tế:*
   - `/search Áo thun`
   - `/search SP-002`
   - `/search Vải`
   - `/search Carton`
2. Bấm **Enter** (hoặc nút Gửi).
3. Chatbot sẽ phản hồi kết quả trực tiếp với mã hàng, tên sản phẩm, đơn giá niêm yết và số lượng tồn kho.
4. Dưới mỗi mục có nút **`+ Chèn vào Excel`**.

---

<a id="hd-33"></a>
### 3.3. Duyệt danh mục qua Tab "Tra cứu DB" & Chèn 1-click
Nếu không muốn gõ lệnh chat, bạn có thể dùng giao diện duyệt trực quan:
1. Bấm vào tab **🔍 Tra cứu DB** trên thanh menu của Taskpane.
2. Nhập từ khóa vào thanh tìm kiếm hoặc để trống để xem toàn bộ danh mục.
3. Danh sách thẻ sản phẩm hiển thị đầy đủ:
   - Thẻ SKU (ví dụ: `SP-001`, `SP-004`).
   - Đơn giá định dạng chuẩn VND (ví dụ: `250.000 đ`).
   - Tồn kho và đơn vị tính (Cái, Mét, Cuộn, Thùng).
4. Bấm nút **➕ Chèn vào Excel** trên bất kỳ sản phẩm nào bạn muốn đưa vào trang tính.

---

<a id="hd-34"></a>
### 3.4. Cơ chế kiểm tra an toàn Preview Diff (Human-in-the-Loop)
Để bảo vệ an toàn cho bảng tính và tránh việc AI ghi đè làm mất dữ liệu của bạn:
1. Khi bạn bấm chèn dữ liệu hoặc khi AI đề xuất thao tác, một hộp thoại **⚡ Xác nhận ghi dữ liệu vào Excel (Preview Diff)** sẽ xuất hiện:
   ```
   +-------------------------------------------------------+
   | ⚡ Xác nhận ghi dữ liệu vào Excel                      |
   | Vị trí: Dòng 2 (Worksheet: Bán Hàng Quý 4)            |
   |-------------------------------------------------------|
   | Cột               | Dữ liệu ghi vào                    |
   | Mã hàng           | SP-001                            |
   | Tên sản phẩm      | Áo thun Polo Nam Cotton Cao Cấp   |
   | Danh mục          | Thời trang nam                    |
   | Số lượng          | 1                                 |
   | Đơn giá           | 250,000                           |
   | Thành tiền        | =D2*E2                            |
   |-------------------------------------------------------|
   |          [Hủy bỏ]    [Xác nhận ghi (Apply)]            |
   +-------------------------------------------------------+
   ```
2. Bạn kiểm tra lại vị trí dòng và giá trị từng cột.
3. Bấm **Xác nhận ghi (Apply)**:
   - Dòng dữ liệu được ghi ngay lập tức vào bảng tính Excel của bạn qua API `Office.js`.
   - Dòng vừa chèn sẽ được bôi màu xanh lá nhẹ trong 2 giây để bạn dễ nhận biết vị trí.
4. Nếu phát hiện sai sót, bấm **Hủy bỏ** để hủy lệnh mà không ảnh hưởng gì đến bảng tính.

---

<a id="hd-35"></a>
### 3.5. Ra lệnh hội thoại tự nhiên với AI Agent
Bạn có thể giao tiếp với AI Agent như một người trợ lý số bằng tiếng Việt:
- *"Tìm mã SP-003 xem có phải áo sơ mi không, rồi thêm vào bảng giúp tôi"*
- *"Thêm cho tôi sản phẩm vải kháng khuẩn vào dòng tiếp theo"*
- *"Kiểm tra trong kho còn máy quét mã vạch không và điền thông tin vào sheet"*

Agent sẽ tự động suy luận (ReAct reasoning), gọi tool truy vấn database, trích xuất thông tin và tạo đề xuất chèn dòng kèm thẻ xem trước.

---

<a id="hd-36"></a>
### 3.6. Tự động kế thừa và tính toán công thức Excel
Khi AI chèn dòng vào bảng tính:
- Không chỉ ghi số cứng, cột **Thành tiền** được tự động điền công thức động: `=D<dòng>*E<dòng>` (Số lượng × Đơn giá).
- Khi bạn thay đổi số lượng ở cột D trực tiếp trên Excel, ô Thành tiền sẽ tự động nhảy số theo đúng logic của Excel!

---

<a id="phan-4"></a>
## PHẦN IV: XỬ LÝ SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING)

### Sự cố 1: Màn hình Taskpane trắng tinh (Blank screen) trên Excel Desktop
- **Nguyên nhân:** Chưa cài chứng chỉ HTTPS SSL cho `localhost`. Excel Desktop chặn các kết nối HTTP không bảo mật.
- **Cách khắc phục:**
  1. Mở Terminal chạy: `npx office-addin-dev-certs install`.
  2. Bấm Cho phép cài chứng chỉ.
  3. Khởi động lại Excel.

### Sự cố 2: Đã copy vào thư mục `wef` trên Mac nhưng không thấy trong Menu
- **Cách khắc phục:**
  1. Đảm bảo tên file chính xác là `manifest.xml`.
  2. Thoát hoàn toàn Excel bằng phím tắt `Cmd + Q` (không chỉ đóng cửa sổ).
  3. Mở lại Excel, vào **Insert** > bấm vào **mũi tên nhỏ bên cạnh nút My Add-ins**.

### Sự cố 3: Báo lỗi "Cannot connect to server" trên khung chat
- **Cách khắc phục:**
  1. Kiểm tra xem server backend đã chạy chưa (`poetry run uvicorn excel_agent.main:app` tại cổng 8000).
  2. Mở trình duyệt vào [http://localhost:8000/health](http://localhost:8000/health) để xác nhận server đang phản hồi.

### Sự cố 4: Cách bật F12 Inspect Element trên Excel Desktop
- **Trên macOS:** Chạy lệnh Terminal:
  ```bash
  defaults write com.microsoft.Excel OfficeWebAddinDeveloperExtras -bool true
  ```
  Sau đó nhấp chuột phải vào Taskpane trong Excel > chọn **Inspect Element**.
- **Trên Windows:** Cài đặt ứng dụng **Microsoft Edge DevTools Preview** từ Microsoft Store để xem log console của WebView2.
