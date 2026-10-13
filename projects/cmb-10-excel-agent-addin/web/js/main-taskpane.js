// Task pane của Office add-in: cùng khung chat, công cụ Excel chạy bằng Office.js trên workbook đang mở.
import { createChat } from "./chat.js";
import { OfficeHost } from "./hosts/office-host.js";
import { $, esc } from "./util.js";

function showStatus(host) {
  const sel = host.selection();
  $("#excel-status").innerHTML = host.isOpen()
    ? `<strong>${esc(host.label())}</strong>${sel.address ? ` · đang chọn ${esc(sel.address.split("!").pop())}` : ""}${
        sel.column ? ` · cột ${esc(sel.column)}` : ""
      }`
    : "Sheet đang mở chưa có dữ liệu";
}

function start() {
  const host = new OfficeHost();
  host.onChange(() => showStatus(host));
  createChat({
    host,
    threadKey: "excel-agent-thread-office",
    welcome:
      "Xin chào! Mình làm việc trực tiếp trên workbook đang mở (bảng dữ liệu có dòng tiêu đề, tốt nhất là Excel Table).\n" +
      "- **Tìm dòng có Thành phố là Đà Nẵng trong bảng**\n" +
      "- **Thêm khách hàng KH-0012 vào bảng** → xem trước → bấm xác nhận (Ctrl+Z để hoàn tác)\n" +
      "- `/search Đà Nẵng` → tích kết quả → **Ghi vào cột** cho các dòng đang chọn",
  });
  host.watchSelection();
}

if (globalThis.Office?.onReady) {
  Office.onReady((info) => {
    if (info.host === Office.HostType.Excel) start();
    else $("#excel-status").textContent = "Add-in này chỉ chạy trong Excel.";
  });
} else {
  $("#excel-status").textContent = "Không tải được Office.js — mở trang này từ add-in trong Excel (xem addin/README.md).";
}
