// Giao diện POC: chat qua AG-UI (POST /agui của AgentOS) + bảng Excel xem/chọn/áp dữ liệu.
// Không dùng framework hay bundler: client AG-UI tối giản đọc stream SSE bằng fetch.

const $ = (sel, root = document) => root.querySelector(sel);
const THREAD_KEY = "excel-agent-thread";
const PAGE = 200;

const state = {
  threadId: sessionStorage.getItem(THREAD_KEY) || newId(),
  running: false,
  config: null,
  workbook: null, // WorkbookInfo
  sheet: null,
  columns: [],
  rows: [],
  totalRows: 0,
  selectedColumn: null,
  selectedRows: new Set(),
  lastRow: null,
  flash: null, // {rows: Set, column: string|null}
  selectionListeners: new Set(),
};
sessionStorage.setItem(THREAD_KEY, state.threadId);

// ------------------------------------------------------------------ tiện ích
function newId() {
  return globalThis.crypto?.randomUUID ? crypto.randomUUID() : `id-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function esc(text) {
  return String(text ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function inline(text) {
  return esc(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[\s(])\*([^*\n]+)\*/g, "$1<em>$2</em>")
    .replace(/(^|[\s(])_([^_\n]+)_/g, "$1<em>$2</em>");
}

function markdown(text) {
  const out = [];
  let list = [];
  const flush = () => {
    if (list.length) out.push(`<ul>${list.map((li) => `<li>${inline(li)}</li>`).join("")}</ul>`);
    list = [];
  };
  for (const line of String(text).split("\n")) {
    const m = line.match(/^\s*[-*]\s+(.*)$/);
    if (m) {
      list.push(m[1]);
      continue;
    }
    flush();
    if (line.trim()) out.push(`<p>${inline(line)}</p>`);
  }
  flush();
  return out.join("");
}

function fmt(value) {
  if (typeof value === "number") return value.toLocaleString("vi-VN");
  return value ?? "";
}

function colLetter(index) {
  let s = "";
  for (let n = index + 1; n > 0; n = Math.floor((n - 1) / 26)) s = String.fromCharCode(65 + ((n - 1) % 26)) + s;
  return s;
}

function norm(text) {
  return String(text ?? "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/đ/gi, "d")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

async function api(path, options = {}) {
  const resp = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.detail ? (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)) : `HTTP ${resp.status}`);
  return data;
}

let toastTimer;
function toast(text, isError = false) {
  const el = $("#toast");
  el.textContent = text;
  el.classList.toggle("err", isError);
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 3500);
}

// ------------------------------------------------------------------ khung chat
const messages = $("#messages");
let typingEl = null;

function append(el) {
  if (typingEl && typingEl.parentNode === messages) messages.insertBefore(el, typingEl);
  else messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
  return el;
}

function addMessage(role, html) {
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  el.innerHTML = html;
  return append(el);
}

function setTyping(on) {
  if (on && !typingEl) {
    typingEl = document.createElement("div");
    typingEl.className = "typing";
    typingEl.textContent = "Agent đang xử lý";
    messages.appendChild(typingEl);
  } else if (!on && typingEl) {
    typingEl.remove();
    typingEl = null;
  }
  messages.scrollTop = messages.scrollHeight;
}

const TOOL_LABELS = {
  export_excel: "Gọi API xuất Excel",
  search_data: "Gọi API tìm kiếm",
  list_datasets: "Lấy danh mục dữ liệu",
};

function toolLabel(name) {
  if (name?.startsWith("transfer_to_")) return `Chuyển cho ${name.slice(12).replace(/_/g, " ")}`;
  return TOOL_LABELS[name] || name;
}

function uiContext() {
  return {
    active_workbook_id: state.workbook?.id ?? null,
    sheet: state.sheet,
    selected_column: state.selectedColumn,
    selected_rows: [...state.selectedRows].sort((a, b) => a - b),
  };
}

async function runAgent(text) {
  const run = { texts: new Map(), tools: new Map() };
  const body = {
    threadId: state.threadId,
    runId: newId(),
    state: {},
    tools: [],
    forwardedProps: {},
    context: [{ description: "excel_ui", value: JSON.stringify(uiContext()) }],
    messages: [{ id: newId(), role: "user", content: text }],
  };
  const resp = await fetch("/agui", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
  });
  if (!resp.ok || !resp.body) throw new Error(`AG-UI trả lỗi HTTP ${resp.status}`);
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let cut;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const chunk = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      const data = chunk
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trimStart())
        .join("\n");
      if (data) handleEvent(JSON.parse(data), run);
    }
  }
}

function handleEvent(ev, run) {
  switch (ev.type) {
    case "RUN_STARTED":
      setTyping(true);
      break;
    case "TEXT_MESSAGE_START": {
      const el = addMessage("assistant", "");
      run.texts.set(ev.messageId, { el, text: "" });
      break;
    }
    case "TEXT_MESSAGE_CONTENT": {
      let entry = run.texts.get(ev.messageId);
      if (!entry) {
        entry = { el: addMessage("assistant", ""), text: "" };
        run.texts.set(ev.messageId, entry);
      }
      entry.text += ev.delta || "";
      entry.el.innerHTML = markdown(entry.text);
      messages.scrollTop = messages.scrollHeight;
      break;
    }
    case "TOOL_CALL_START": {
      const chip = document.createElement("div");
      chip.className = "tool-chip pending";
      chip.textContent = toolLabel(ev.toolCallName);
      append(chip);
      run.tools.set(ev.toolCallId, { name: ev.toolCallName, chip });
      break;
    }
    case "TOOL_CALL_RESULT": {
      const tool = run.tools.get(ev.toolCallId);
      tool?.chip.classList.replace("pending", "done");
      let data = null;
      try {
        data = JSON.parse(ev.content);
      } catch {
        /* kết quả không phải JSON → chỉ hiện chip */
      }
      if (data?.type === "workbook") append(fileCard(data));
      else if (data?.type === "search_results") append(searchCard(data));
      else if (data?.type === "handoff" && tool) tool.chip.textContent = `Đã chuyển cho ${data.to}`;
      break;
    }
    case "RUN_ERROR":
      addMessage("error", esc(ev.message || "Agent gặp lỗi"));
      break;
    case "RUN_FINISHED":
      setTyping(false);
      break;
    default:
      break;
  }
}

async function send(text) {
  text = text.trim();
  if (!text || state.running) return;
  state.running = true;
  $("#send").disabled = true;
  $("#suggestions").hidden = true;
  addMessage("user", esc(text));
  try {
    await runAgent(text);
  } catch (err) {
    addMessage("error", esc(err.message));
  } finally {
    setTyping(false);
    state.running = false;
    $("#send").disabled = false;
  }
}

// ------------------------------------------------------------------ thẻ file Excel
function fileCard(data) {
  const card = document.createElement("div");
  card.className = "card file-card";
  card.tabIndex = 0;
  card.setAttribute("role", "button");
  card.dataset.workbook = data.workbook_id;
  const filters = (data.filters || []).map((f) => `<span class="chip">${esc(f.column)} ${esc(f.op)} ${esc(f.value)}</span>`).join("");
  card.innerHTML = `
    <div class="card-head">
      <span class="file-icon" aria-hidden="true">X</span>
      <div>
        <strong>${esc(data.name)}</strong>
        <div class="meta">${data.rows} dòng · ${(data.columns || []).length} cột · ${esc(data.dataset)}</div>
        ${filters ? `<div class="chips">${filters}</div>` : ""}
      </div>
      <div class="actions">
        <button class="btn small primary" type="button">Xem dữ liệu</button>
        <a class="btn small" href="${esc(data.download_url)}" download title="Tải file .xlsx">⬇</a>
      </div>
    </div>`;
  const open = (e) => {
    if (e.target.closest("a")) return;
    openWorkbook(data.workbook_id);
  };
  card.addEventListener("click", open);
  card.addEventListener("keydown", (e) => (e.key === "Enter" || e.key === " ") && open(e));
  return card;
}

function markActiveCards() {
  document.querySelectorAll(".file-card").forEach((c) => c.classList.toggle("active", c.dataset.workbook === state.workbook?.id));
}

// ------------------------------------------------------------------ bảng Excel
async function openWorkbook(id, sheet = null) {
  try {
    const info = await api(`/api/v1/workbooks/${id}`);
    if (state.workbook?.id !== id) {
      state.selectedColumn = null;
      state.selectedRows.clear();
    }
    state.workbook = info;
    await loadPreview(sheet || info.sheets[0]);
    $("#sheet-empty").hidden = true;
    $("#sheet-view").hidden = false;
    markActiveCards();
  } catch (err) {
    toast(err.message, true);
  }
}

async function loadPreview(sheet, { append: more = false } = {}) {
  const offset = more ? state.rows.length : 0;
  const limit = more ? PAGE : Math.max(PAGE, Math.min(state.rows.length, 500));
  const pv = await api(`/api/v1/workbooks/${state.workbook.id}/preview?sheet=${encodeURIComponent(sheet)}&offset=${offset}&limit=${limit}`);
  if (state.sheet !== pv.sheet) {
    state.selectedColumn = null;
    state.selectedRows.clear();
  }
  state.sheet = pv.sheet;
  state.columns = pv.columns;
  state.rows = more ? state.rows.concat(pv.rows) : pv.rows;
  state.totalRows = pv.total_rows;
  state.workbook.version = pv.version;
  renderSheet(pv);
}

function renderSheet(pv) {
  const wb = state.workbook;
  $("#wb-name").textContent = wb.name;
  $("#wb-meta").textContent = ` · phiên bản ${pv.version} · ${pv.total_rows} dòng · ${pv.columns.length} cột`;
  $("#btn-download").href = `${wb.download_url}?v=${pv.version}`;
  $("#btn-download").setAttribute("download", wb.name);
  $("#btn-undo").disabled = pv.version <= 1;
  const tabs = $("#sheet-tabs");
  tabs.innerHTML = pv.sheets
    .map((s) => `<button type="button" role="tab" aria-selected="${s === pv.sheet}" data-sheet="${esc(s)}">${esc(s)}</button>`)
    .join("");
  renderGrid();
}

function renderGrid() {
  const flash = state.flash;
  const head =
    `<thead><tr class="letters"><th class="corner"></th>${state.columns.map((_, i) => `<th>${colLetter(i)}</th>`).join("")}</tr>` +
    `<tr class="headers"><th class="corner">#</th>${state.columns
      .map((c) => `<th data-col="${esc(c)}" class="${c === state.selectedColumn ? "col-sel" : ""}" title="Bấm để chọn cột">${esc(c)}</th>`)
      .join("")}</tr></thead>`;
  const body = state.rows
    .map((row, r) => {
      const selected = state.selectedRows.has(r);
      const cells = state.columns
        .map((c, i) => {
          const v = row[i];
          const cls = [typeof v === "number" ? "num" : "", c === state.selectedColumn ? "col-sel" : ""];
          if (flash && flash.rows.has(r) && (!flash.column || flash.column === c)) cls.push("flash");
          return `<td class="${cls.join(" ").trim()}">${esc(fmt(v))}</td>`;
        })
        .join("");
      return `<tr class="${selected ? "row-sel" : ""}" data-row="${r}"><td class="rownum" data-row="${r}" title="Bấm để chọn dòng">${r + 2}</td>${cells}</tr>`;
    })
    .join("");
  $("#grid").innerHTML = head + `<tbody>${body}</tbody>`;
  $("#grid-range").textContent = `Hiển thị ${state.rows.length}/${state.totalRows} dòng dữ liệu (số bên trái là số dòng trong Excel)`;
  $("#btn-more").hidden = state.rows.length >= state.totalRows;
  updateSelectionText();
}

function updateSelectionText() {
  const n = state.selectedRows.size;
  const parts = [];
  if (state.selectedColumn) parts.push(`Cột đang chọn: <strong>${esc(state.selectedColumn)}</strong>`);
  if (n) parts.push(`<strong>${n}</strong> dòng đang chọn`);
  $("#selection-text").innerHTML = parts.length
    ? parts.join(" · ")
    : "Bấm tiêu đề cột để chọn cột · bấm số dòng để chọn dòng (Shift để chọn liên tiếp)";
  $("#btn-clear-selection").hidden = !parts.length;
  state.selectionListeners.forEach((fn) => fn());
}

$("#grid").addEventListener("click", (e) => {
  const th = e.target.closest("th[data-col]");
  if (th) {
    state.selectedColumn = state.selectedColumn === th.dataset.col ? null : th.dataset.col;
    renderGrid();
    return;
  }
  const rn = e.target.closest("td.rownum");
  if (rn) {
    const r = Number(rn.dataset.row);
    if (e.shiftKey && state.lastRow !== null) {
      const [a, b] = [Math.min(state.lastRow, r), Math.max(state.lastRow, r)];
      for (let i = a; i <= b; i++) state.selectedRows.add(i);
    } else if (state.selectedRows.has(r)) state.selectedRows.delete(r);
    else state.selectedRows.add(r);
    state.lastRow = r;
    renderGrid();
  }
});

$("#sheet-tabs").addEventListener("click", (e) => {
  const tab = e.target.closest("button[data-sheet]");
  if (tab) loadPreview(tab.dataset.sheet).catch((err) => toast(err.message, true));
});
$("#btn-clear-selection").addEventListener("click", () => {
  state.selectedColumn = null;
  state.selectedRows.clear();
  renderGrid();
});
$("#btn-refresh").addEventListener("click", () => loadPreview(state.sheet).catch((err) => toast(err.message, true)));
$("#btn-more").addEventListener("click", () => loadPreview(state.sheet, { append: true }).catch((err) => toast(err.message, true)));
$("#btn-undo").addEventListener("click", async () => {
  try {
    const info = await api(`/api/v1/workbooks/${state.workbook.id}/undo`, { method: "POST" });
    state.workbook = info;
    await loadPreview(state.sheet);
    toast(`Đã hoàn tác về phiên bản ${info.version}`);
  } catch (err) {
    toast(err.message, true);
  }
});

// ------------------------------------------------------------------ thẻ kết quả /search
function searchCard(data) {
  const card = document.createElement("div");
  card.className = "card results-card";
  const records = data.records || [];
  const cols = data.columns || Object.keys(records[0] || {});
  const scope = data.column ? ` · cột ${esc(data.column)}` : " · mọi cột";
  card.innerHTML = `
    <div class="card-head"><div>
      <div class="results-title">🔎 Kết quả “${esc(data.query)}”</div>
      <div class="meta small muted">${esc(data.dataset)}${scope} · ${data.shown}/${data.total} kết quả</div>
    </div></div>
    <div class="card-body">
      ${
        records.length
          ? `<div class="results-table-wrap"><table class="results-table">
              <thead><tr><th><input type="checkbox" data-all aria-label="Chọn tất cả"></th>${cols.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead>
              <tbody>${records
                .map(
                  (r, i) =>
                    `<tr data-i="${i}"><td><input type="checkbox" data-i="${i}" aria-label="Chọn kết quả ${i + 1}"></td>${cols
                      .map((c) => `<td class="${typeof r[c] === "number" ? "num" : ""}">${esc(fmt(r[c]))}</td>`)
                      .join("")}</tr>`,
                )
                .join("")}</tbody></table></div>
            <div class="results-actions">
              <button class="btn small primary" type="button" data-act="set">Ghi vào cột…</button>
              <button class="btn small" type="button" data-act="append">Thêm thành dòng mới</button>
              <span class="small muted" data-count>Chưa chọn kết quả</span>
            </div>
            <div class="target-hint"></div>
            <div class="apply-form" hidden></div>
            <div class="apply-result" hidden></div>`
          : `<p class="muted">Không có kết quả.</p>`
      }
    </div>`;
  if (!records.length) return card;

  const checked = () => [...card.querySelectorAll("tbody input:checked")].map((x) => Number(x.dataset.i));
  const form = $(".apply-form", card);
  const result = $(".apply-result", card);
  let mode = null;

  const refresh = () => {
    const sel = checked();
    card.querySelectorAll("tbody tr").forEach((tr) => tr.classList.toggle("checked", sel.includes(Number(tr.dataset.i))));
    $("[data-count]", card).textContent = sel.length ? `Đã chọn ${sel.length} kết quả` : "Chưa chọn kết quả";
    $(".target-hint", card).textContent = state.workbook
      ? `Áp vào: ${state.workbook.name} · sheet ${state.sheet}${state.selectedColumn ? ` · cột ${state.selectedColumn}` : ""}${
          state.selectedRows.size ? ` · ${state.selectedRows.size} dòng đang chọn` : ""
        }`
      : "Mở một file Excel (bấm thẻ file) trước khi áp kết quả vào bảng.";
    if (mode) renderForm();
  };

  const renderForm = () => {
    const sel = checked();
    if (!state.workbook) {
      form.innerHTML = `<div class="apply-summary">Chưa mở file Excel nào.</div>`;
      return;
    }
    if (!sel.length) {
      form.innerHTML = `<div class="apply-summary">Tích chọn ít nhất một kết quả.</div>`;
      return;
    }
    if (mode === "append") {
      form.innerHTML = `
        <div class="apply-summary">Thêm <strong>${sel.length}</strong> dòng mới vào sheet <strong>${esc(state.sheet)}</strong>;
        trường nào trùng tên cột thì được điền vào cột đó.</div>
        <div><button class="btn small primary" type="button" data-confirm>Xác nhận thêm</button>
        <button class="btn small ghost" type="button" data-cancel>Hủy</button></div>`;
      return;
    }
    const prevTarget = $("select[data-target]", form)?.value;
    const prevSource = $("select[data-source]", form)?.value;
    const prevNew = $("input[data-newcol]", form)?.value || "";
    const target = prevTarget || state.selectedColumn || state.columns.find((c) => norm(c) === norm(data.column)) || state.columns[0];
    const source = prevSource || cols.find((c) => norm(c) === norm(target)) || data.column || cols[0];
    const rows = [...state.selectedRows].sort((a, b) => a - b);
    let warn = "";
    if (!rows.length) warn = "Chọn dòng trên bảng Excel (bấm số dòng bên trái) để biết ghi vào đâu.";
    else if (target === "__new__" && !prevNew.trim()) warn = "Nhập tên cột mới.";
    else if (sel.length > 1 && sel.length !== rows.length)
      warn = `Đã chọn ${sel.length} kết quả cho ${rows.length} dòng: chọn 1 kết quả (ghi cùng giá trị) hoặc số kết quả bằng số dòng.`;
    form.innerHTML = `
      <label>Cột đích trong Excel
        <select data-target>${state.columns.map((c) => `<option ${c === target ? "selected" : ""}>${esc(c)}</option>`).join("")}
          <option value="__new__" ${target === "__new__" ? "selected" : ""}>+ Tạo cột mới…</option></select></label>
      <input data-newcol placeholder="Tên cột mới" value="${esc(prevNew)}" ${target === "__new__" ? "" : "hidden"}>
      <label>Lấy giá trị từ trường của kết quả
        <select data-source>${cols.map((c) => `<option ${c === source ? "selected" : ""}>${esc(c)}</option>`).join("")}</select></label>
      <div class="apply-summary">${
        warn
          ? `⚠ ${esc(warn)}`
          : `Ghi <strong>${esc(source)}</strong> của ${sel.length} kết quả vào cột <strong>${esc(target === "__new__" ? `${prevNew} (mới)` : target)}</strong> cho ${rows.length} dòng: ${rows
              .slice(0, 8)
              .map((r) => r + 2)
              .join(", ")}${rows.length > 8 ? "…" : ""}`
      }</div>
      <div><button class="btn small primary" type="button" data-confirm ${warn ? "disabled" : ""}>Xác nhận ghi</button>
      <button class="btn small ghost" type="button" data-cancel>Hủy</button></div>`;
  };

  card.addEventListener("input", (e) => {
    if (!e.target.matches("input[data-newcol]")) return;
    const pos = e.target.selectionStart;
    renderForm();
    const again = $("input[data-newcol]", form);
    again.focus();
    again.setSelectionRange(pos, pos);
  });

  card.addEventListener("change", (e) => {
    if (e.target.matches("input[data-newcol]")) return;
    if (e.target.matches("[data-all]")) card.querySelectorAll("tbody input").forEach((x) => (x.checked = e.target.checked));
    if (e.target.matches("select[data-target]")) {
      $("input[data-newcol]", form).hidden = e.target.value !== "__new__";
      renderForm();
      return;
    }
    if (e.target.matches("select[data-source]")) {
      renderForm();
      return;
    }
    refresh();
  });

  card.addEventListener("click", async (e) => {
    const act = e.target.closest("[data-act]");
    if (act) {
      mode = act.dataset.act;
      result.hidden = true;
      form.hidden = false;
      renderForm();
      return;
    }
    if (e.target.closest("[data-cancel]")) {
      mode = null;
      form.hidden = true;
      return;
    }
    if (e.target.closest("[data-confirm]")) await confirmApply();
  });

  async function confirmApply() {
    const sel = checked().map((i) => records[i]);
    const body = { mode: mode === "append" ? "append_rows" : "set_column", records: sel, sheet: state.sheet, expected_version: state.workbook.version };
    if (mode === "set") {
      const target = $("select[data-target]", form).value;
      const newName = $("input[data-newcol]", form).value.trim();
      Object.assign(body, {
        target_column: target === "__new__" ? newName : target,
        create_column: target === "__new__",
        source_field: $("select[data-source]", form).value,
        row_indexes: [...state.selectedRows].sort((a, b) => a - b),
      });
    }
    try {
      const res = await api(`/api/v1/workbooks/${state.workbook.id}/apply`, { method: "POST", body: JSON.stringify(body) });
      state.workbook = res.workbook;
      state.flash = { rows: new Set(res.changed_rows), column: res.changed_column };
      if (body.mode === "set_column" && res.changed_column) state.selectedColumn = res.changed_column;
      await loadPreview(state.sheet);
      setTimeout(() => (state.flash = null), 4000);
      result.className = "apply-result";
      result.innerHTML = `✓ ${esc(res.message)} · phiên bản ${res.workbook.version}${res.warnings.map((w) => `<br>• ${esc(w)}`).join("")}`;
      if (body.mode === "append_rows") document.querySelector("#grid tr.flash, #grid td.flash")?.scrollIntoView({ block: "center" });
      toast(res.message);
      mode = null;
      form.hidden = true;
    } catch (err) {
      result.className = "apply-result err";
      result.textContent = err.message;
    }
    result.hidden = false;
  }

  state.selectionListeners.add(refresh);
  setTimeout(refresh);
  return card;
}

// ------------------------------------------------------------------ khởi động
async function loadConfig() {
  try {
    state.config = await api("/api/v1/config");
    const badge = $("#mode-badge");
    const offline = state.config.mode !== "openai";
    badge.textContent = offline
      ? "Offline · chưa có OPENAI_API_KEY"
      : `OpenAI · ${state.config.model}${state.config.triage ? " · có agent điều phối" : ""}`;
    badge.classList.toggle("offline", offline);
  } catch {
    $("#mode-badge").textContent = "Không kết nối được server";
  }
}

async function loadRecent() {
  try {
    const list = await api("/api/v1/workbooks?limit=5");
    $("#recent").innerHTML = list.length
      ? `<div class="small muted">File gần đây</div>` +
        list
          .map((w) => `<button type="button" data-open="${esc(w.id)}"><span>📗 ${esc(w.name)}</span><span class="muted small">${w.rows} dòng · v${w.version}</span></button>`)
          .join("")
      : "";
  } catch {
    /* chưa có file nào */
  }
}

$("#recent").addEventListener("click", (e) => {
  const btn = e.target.closest("[data-open]");
  if (btn) openWorkbook(btn.dataset.open);
});
$("#composer").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = $("#input");
  const text = input.value;
  input.value = "";
  send(text);
});
$("#input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    $("#composer").requestSubmit();
  }
});
$("#suggestions").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-text]");
  if (btn) send(btn.dataset.text);
});
$("#new-chat").addEventListener("click", () => {
  state.threadId = newId();
  sessionStorage.setItem(THREAD_KEY, state.threadId);
  messages.innerHTML = "";
  state.selectionListeners.clear();
  $("#suggestions").hidden = false;
  addMessage("assistant", markdown("Đã bắt đầu hội thoại mới. Gõ `/help` để xem hướng dẫn."));
});

addMessage(
  "assistant",
  markdown(
    "Xin chào! Mình là agent Excel (OpenAI Agents SDK chạy trên AgentOS, nói chuyện qua AG-UI).\n" +
      "- Gõ **Tạo file Excel khách hàng ở Hà Nội** → bấm vào thẻ file để xem dữ liệu.\n" +
      "- Gõ `/search Đà Nẵng` hoặc `/search Thành phố: Đà Nẵng` → chọn kết quả → **Ghi vào cột** hoặc **Thêm thành dòng mới**.",
  ),
);
loadConfig();
loadRecent();
