// Web POC: khung chat + bảng Excel mô phỏng (file .xlsx trên server). Mở http://127.0.0.1:7777
import { createChat } from "./chat.js";
import { WebGridHost } from "./hosts/web-host.js";

const host = new WebGridHost();
createChat({
  host,
  threadKey: "excel-agent-thread-web",
  welcome:
    "Xin chào! Mình là agent Excel (Agno trên AgentOS, nói chuyện qua AG-UI). Công cụ Excel chạy ngay trên bảng bên phải.\n" +
    "- **Tạo file Excel khách hàng ở Hà Nội** → bấm thẻ file để mở.\n" +
    "- **Thêm khách hàng KH-0012 vào bảng** → xem trước → bấm xác nhận.\n" +
    "- `/search Đà Nẵng` hoặc `/search Thành phố: Đà Nẵng` → chọn kết quả → **Ghi vào cột** / **Thêm thành dòng mới**.",
});
host.loadRecent();
