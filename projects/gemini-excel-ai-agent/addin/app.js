/* ==========================================================================
   EXCEL AI AGENT COPILOT — JAVASCRIPT CLIENT & OFFICE.JS BRIDGE
   ========================================================================== */

const API_BASE_URL = window.location.origin.includes("localhost") 
  ? window.location.origin 
  : "http://localhost:8000";

let isExcelHost = false;
let currentPendingAction = null;
let simRowCount = 1;

// 1. Khởi tạo Office Add-in
Office.onReady((info) => {
  if (info.host === Office.HostType.Excel) {
    isExcelHost = true;
    console.log("✅ Đã kết nối thành công với Microsoft Excel Host!");
    updateStatus("online", "Excel Native API");
  } else {
    isExcelHost = false;
    console.log("ℹ️ Đang chạy ở chế độ Web Browser Simulator (ngoài Excel)");
    updateStatus("online", "Web Simulator");
  }
  setupTabs();
  executeDbSearch(); // Nạp sẵn danh mục mẫu ban đầu
});

function updateStatus(status, label) {
  const el = document.getElementById("connection-status");
  if (el) {
    el.className = `status-indicator status-${status}`;
    el.title = `Chế độ: ${label}`;
  }
}

// 2. Chuyển đổi Navigation Tabs
function setupTabs() {
  const tabs = document.querySelectorAll(".tab-btn");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
      tab.classList.add("active");
      const targetId = tab.getAttribute("data-tab");
      document.getElementById(targetId).classList.add("active");
    });
  });
}

// 3. Xử lý Gửi Chat / Lệnh Slash Command
async function handleChatSubmit(event) {
  event.preventDefault();
  const inputEl = document.getElementById("user-input");
  const text = inputEl.value.trim();
  if (!text) return;

  inputEl.value = "";
  appendMessage("user", text);

  // Hiển thị chỉ báo đang suy luận
  const loadingId = appendLoadingMessage();

  try {
    if (text.startsWith("/search")) {
      // Xử lý riêng qua endpoint Slash Command
      const res = await fetch(`${API_BASE_URL}/api/v1/chat/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command_text: text, session_id: "excel-session" }),
      });
      const data = await res.json();
      removeMessage(loadingId);

      if (data.success && data.data) {
        const cmdData = data.data;
        let htmlContent = `<p>${formatMarkdown(cmdData.reply_text)}</p>`;

        if (cmdData.items && cmdData.items.length > 0) {
          htmlContent += `<div class="chat-action-card">
            <div class="action-card-header">📦 Kết quả tra cứu nhanh:</div>`;
          cmdData.items.forEach((item) => {
            htmlContent += `
              <div style="margin-bottom:6px; font-size:12px;">
                <strong>${item.name}</strong> (${item.sku})<br/>
                Giá: <code>${Number(item.unit_price).toLocaleString()} đ</code> | Tồn: ${item.stock_quantity}
                <button class="action-card-btn" onclick='proposeInsertFromItem(${JSON.stringify(item)})'>+ Chèn vào Excel</button>
              </div>`;
          });
          htmlContent += `</div>`;
        }
        appendMessage("bot", htmlContent, true);
      } else {
        appendMessage("bot", "Lỗi: " + (data.message || "Không thể thực thi lệnh"));
      }
    } else {
      // Gửi chat thông thường qua Agent ReAct Loop
      const res = await fetch(`${API_BASE_URL}/api/v1/chat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          session_id: "excel-session",
          active_sheet_name: "Bán Hàng Quý 4",
          table_headers: ["Mã hàng", "Tên sản phẩm", "Danh mục", "Số lượng", "Đơn giá", "Thành tiền"],
          row_count: isExcelHost ? await getExcelRowCount() : simRowCount,
        }),
      });
      const data = await res.json();
      removeMessage(loadingId);

      if (data.success && data.data) {
        const chatData = data.data;
        let replyHtml = `<p>${formatMarkdown(chatData.reply_text)}</p>`;

        if (chatData.preview_diff) {
          currentPendingAction = chatData.suggested_action;
          replyHtml += `
            <div class="chat-action-card">
              <div class="action-card-header">⚡ Đề xuất thao tác bảng tính:</div>
              <p style="font-size:12px;">${chatData.preview_diff.summary}</p>
              <button class="action-card-btn" onclick='openPreviewModal(${JSON.stringify(chatData.preview_diff)})'>
                👁️ Xem chi tiết & Chèn dòng
              </button>
            </div>`;
        }
        appendMessage("bot", replyHtml, true);
      } else {
        appendMessage("bot", "Lỗi phản hồi: " + (data.message || "Server bận"));
      }
    }
  } catch (err) {
    removeMessage(loadingId);
    appendMessage("bot", `⚠️ Không thể kết nối tới server (${API_BASE_URL}). Chi tiết: ${err.message}`);
  }
}

function sendQuickCommand(cmd) {
  document.getElementById("user-input").value = cmd;
  document.getElementById("chat-form").dispatchEvent(new Event("submit"));
}

// 4. Tra cứu danh mục sản phẩm trong Tab 2
async function executeDbSearch() {
  const query = document.getElementById("db-search-input").value.trim();
  const container = document.getElementById("search-results-container");
  container.innerHTML = "<p style='color:#64748b; font-size:12px;'>Đang tìm kiếm...</p>";

  try {
    const url = query 
      ? `${API_BASE_URL}/api/v1/search/products?q=${encodeURIComponent(query)}&limit=10`
      : `${API_BASE_URL}/api/v1/search/products?q=&limit=10`;
    
    const res = await fetch(url);
    const data = await res.json();

    if (data.success && data.data && data.data.items) {
      const items = data.data.items;
      document.getElementById("search-count-label").innerText = `Tìm thấy ${items.length} sản phẩm:`;
      if (items.length === 0) {
        container.innerHTML = "<p style='color:#64748b; font-size:12px;'>Không tìm thấy sản phẩm nào.</p>";
        return;
      }

      container.innerHTML = items.map((item) => `
        <div class="product-card">
          <div class="product-card-top">
            <span class="product-sku">${item.sku}</span>
            <span class="product-price">${Number(item.unit_price).toLocaleString()} đ</span>
          </div>
          <div class="product-name">${item.name}</div>
          <div class="product-meta">
            <span>Danh mục: ${item.category}</span>
            <span>Tồn kho: ${item.stock_quantity} ${item.unit}</span>
          </div>
          <button class="btn-insert-row" onclick='proposeInsertFromItem(${JSON.stringify(item)})'>
            ➕ Chèn vào Excel
          </button>
        </div>
      `).join("");
    }
  } catch (err) {
    container.innerHTML = `<p style='color:#ef4444; font-size:12px;'>Lỗi tải dữ liệu: ${err.message}</p>`;
  }
}

// 5. Đề xuất chèn dòng từ thẻ sản phẩm
function proposeInsertFromItem(item) {
  const targetRow = simRowCount + 1;
  const insertReq = {
    sheet_name: "Bán Hàng Quý 4",
    target_row_index: targetRow,
    row_values: [
      { column_name: "Mã hàng", value: item.sku },
      { column_name: "Tên sản phẩm", value: item.name },
      { column_name: "Danh mục", value: item.category },
      { column_name: "Số lượng", value: 1 },
      { column_name: "Đơn giá", value: item.unit_price },
      { column_name: "Thành tiền", value: item.unit_price, formula: `=D${targetRow}*E${targetRow}` },
    ],
    highlight_inserted_row: true,
  };

  const previewDiff = {
    action_type: "INSERT_ROW",
    sheet_name: "Bán Hàng Quý 4",
    target_row: targetRow,
    summary: `Chèn dòng mới cho sản phẩm ${item.name} (${item.sku})`,
    diff_items: insertReq.row_values.map((v) => ({
      column_name: v.column_name,
      new_value: String(v.value),
      is_new_row: true,
    })),
  };

  currentPendingAction = insertReq;
  openPreviewModal(previewDiff);
}

// 6. Modal Preview Diff (Human-in-the-Loop)
function openPreviewModal(previewDiff) {
  const modal = document.getElementById("preview-modal");
  const bodyContent = document.getElementById("modal-body-content");

  let html = `
    <p style="font-size:12.5px; margin-bottom:8px;">
      Vị trí: <strong>Dòng ${previewDiff.target_row}</strong> (Worksheet: <em>${previewDiff.sheet_name}</em>)
    </p>
    <table class="diff-table">
      <thead>
        <tr><th>Cột</th><th>Dữ liệu ghi vào</th></tr>
      </thead>
      <tbody>
  `;

  previewDiff.diff_items.forEach((item) => {
    html += `
      <tr>
        <td><strong>${item.column_name}</strong></td>
        <td class="diff-new-val">${item.new_value}</td>
      </tr>
    `;
  });

  html += `</tbody></table>`;
  bodyContent.innerHTML = html;
  modal.classList.add("active");
}

function closePreviewModal() {
  document.getElementById("preview-modal").classList.remove("active");
}

// 7. Thực thi hành động Ghi vào Excel
async function applyPreviewAction() {
  if (!currentPendingAction) return;
  closePreviewModal();

  const req = currentPendingAction;
  appendMessage("bot", `⏳ Đang thực thi ghi dữ liệu vào dòng ${req.target_row_index}...`);

  if (isExcelHost) {
    // --- GHI QUA NATIVE OFFICE.JS ---
    try {
      await Excel.run(async (context) => {
        const sheet = context.workbook.worksheets.getActiveWorksheet();
        const rowIdx = req.target_row_index;

        // Chèn dòng đẩy các dòng dưới xuống
        const rowRange = sheet.getRange(`${rowIdx}:${rowIdx}`);
        rowRange.insert(Excel.InsertShiftDirection.down);

        // Ghi dữ liệu từng ô
        const cols = ["A", "B", "C", "D", "E", "F"];
        req.row_values.forEach((val, i) => {
          if (i < cols.length) {
            const cell = sheet.getRange(`${cols[i]}${rowIdx}`);
            if (val.formula) {
              cell.formulas = [[val.formula]];
            } else {
              cell.values = [[val.value]];
            }
          }
        });

        // Bôi màu highlight nhẹ
        rowRange.format.fill.color = "#dcfce7";
        await context.sync();
      });

      appendMessage("bot", `✅ **Thành công!** Đã chèn dòng ${req.target_row_index} vào bảng tính Excel.`);
    } catch (excelErr) {
      appendMessage("bot", `❌ Lỗi khi ghi Excel qua Office.js: ${excelErr.message}`);
    }
  } else {
    // --- GHI VÀO BẢNG SIMULATOR WEB ---
    simRowCount++;
    const tbody = document.getElementById("sim-table-body");
    const tr = document.createElement("tr");
    tr.className = "highlight-new";

    const vals = req.row_values.map((v) => v.value);
    tr.innerHTML = `
      <td>${simRowCount}</td>
      <td>${vals[0] || ""}</td>
      <td>${vals[1] || ""}</td>
      <td>${vals[2] || ""}</td>
      <td>${vals[3] || 1}</td>
      <td>${Number(vals[4] || 0).toLocaleString()}</td>
      <td>${Number((vals[3] || 1) * (vals[4] || 0)).toLocaleString()}</td>
    `;
    tbody.appendChild(tr);

    appendMessage("bot", `✅ **Thành công (Simulator)!** Đã chèn dòng số ${simRowCount} vào bảng tính mẫu. Chuyển sang tab "Bảng tính mẫu" để xem.`);
    // Tự động nhảy sang tab Simulator 1 chút để xem kết quả
    document.getElementById("btn-tab-sim").click();
  }
}

// Tiện ích lấy row count trên Excel thật
async function getExcelRowCount() {
  try {
    let count = 0;
    await Excel.run(async (context) => {
      const sheet = context.workbook.worksheets.getActiveWorksheet();
      const usedRange = sheet.getUsedRange();
      usedRange.load("rowCount");
      await context.sync();
      count = usedRange.rowCount;
    });
    return count;
  } catch {
    return 1;
  }
}

function resetSimTable() {
  simRowCount = 1;
  document.getElementById("sim-table-body").innerHTML = `
    <tr>
      <td>1</td>
      <td>SP-001</td>
      <td>Áo thun Polo Nam Cotton Cao Cấp</td>
      <td>Thời trang nam</td>
      <td>2</td>
      <td>250,000</td>
      <td>500,000</td>
    </tr>
  `;
}

// Render tin nhắn vào khung chat
function appendMessage(sender, content, isHtml = false) {
  const container = document.getElementById("messages-container");
  const div = document.createElement("div");
  div.className = `message message-${sender}`;
  const avatar = sender === "bot" ? "🤖" : "👤";

  div.innerHTML = `
    <div class="message-avatar">${avatar}</div>
    <div class="message-body">${isHtml ? content : `<p>${content}</p>`}</div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function appendLoadingMessage() {
  const id = "loading-" + Date.now();
  const container = document.getElementById("messages-container");
  const div = document.createElement("div");
  div.id = id;
  div.className = "message message-bot";
  div.innerHTML = `
    <div class="message-avatar">🤖</div>
    <div class="message-body"><p><em>Đang phân tích & tra cứu...</em></p></div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeMessage(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function formatMarkdown(text) {
  if (!text) return "";
  return text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`(.*?)`/g, "<code>$1</code>")
    .replace(/\n/g, "<br/>");
}
