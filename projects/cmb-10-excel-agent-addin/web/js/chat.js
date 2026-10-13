// Khung chat dùng chung cho web POC và task pane trong Excel.
//
// Một lượt chat:
//   1. Gửi RunAgentInput tới POST /agui: câu hỏi + trạng thái Excel (context "excel_ui") + định nghĩa công cụ Excel.
//   2. Đọc sự kiện AG-UI: chữ, tool phía server (có TOOL_CALL_RESULT), tool phía Excel (run tạm dừng, không có RESULT).
//   3. Nếu run tạm dừng: chạy tool Excel trên host (tool ghi phải được người dùng xác nhận), gửi kết quả bằng tin nhắn
//      role "tool" → run chạy tiếp. Lặp đến khi agent trả lời xong.
// Lệnh bắt đầu bằng "/" đi tới POST /api/v1/commands (chạy bằng code, không gọi model).

import { runAgui } from "./agui.js";
import { createExcelTools, planAppend, planSetValues, TOOL_LABELS } from "./excel-tools.js";
import { $, api, esc, fmt, markdown, newId, norm, toast } from "./util.js";

const MAX_ROUNDS = 8; // số lần tạm dừng/tiếp tục tối đa trong một câu hỏi

export function createChat({ host, threadKey, welcome }) {
  const messages = $("#messages");
  const state = { threadId: sessionStorage.getItem(threadKey) || newId(), running: false, config: null };
  sessionStorage.setItem(threadKey, state.threadId);
  const tools = createExcelTools({ host, confirm: (plan) => confirmCard(plan) });
  let typingEl = null;

  // ---------------------------------------------------------------- khung tin nhắn
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

  function setTyping(on, text = "Agent đang xử lý") {
    if (on && !typingEl) {
      typingEl = document.createElement("div");
      typingEl.className = "typing";
      messages.appendChild(typingEl);
    }
    if (on) typingEl.textContent = text;
    if (!on && typingEl) {
      typingEl.remove();
      typingEl = null;
    }
    messages.scrollTop = messages.scrollHeight;
  }

  const label = (name) => TOOL_LABELS[name] || name;

  // ---------------------------------------------------------------- agent qua AG-UI
  async function runAgent(text) {
    const userMsg = { id: newId(), role: "user", content: text };
    let msgs = [userMsg];
    for (let round = 0; round < MAX_ROUNDS; round++) {
      const ui = await host.context().catch((err) => ({ host: host.kind, error: err.message }));
      const input = {
        threadId: state.threadId,
        runId: newId(),
        state: {},
        tools: tools.definitions,
        forwardedProps: {},
        context: [{ description: "excel_ui", value: JSON.stringify(ui) }],
        messages: msgs,
      };
      const run = { texts: new Map(), calls: new Map() };
      setTyping(true);
      for await (const ev of runAgui("/agui", input)) handleEvent(ev, run);
      const pending = [...run.calls.values()].filter((c) => !c.done && tools.has(c.name));
      if (!pending.length) return;

      const results = [];
      for (const call of pending) {
        let args = {};
        try {
          args = JSON.parse(call.args || "{}");
        } catch {
          /* tham số hỏng → tool tự báo lỗi */
        }
        setTyping(true, tools.isWrite(call.name) ? "Chờ bạn xác nhận" : `Đang chạy trong Excel: ${label(call.name)}`);
        const result = await tools.execute(call.name, args);
        call.chip.classList.replace("pending", result.status === "error" || result.status === "rejected" ? "failed" : "done");
        if (result.status === "error") call.chip.title = result.message;
        results.push({ id: newId(), role: "tool", toolCallId: call.id, content: JSON.stringify(result) });
      }
      const toolCalls = pending.map((c) => ({ id: c.id, type: "function", function: { name: c.name, arguments: c.args || "{}" } }));
      msgs = [userMsg, { id: newId(), role: "assistant", content: "", toolCalls }, ...results];
    }
    addMessage("error", "Agent gọi công cụ quá nhiều lần cho một câu hỏi — hãy nói rõ yêu cầu hơn.");
  }

  function handleEvent(ev, run) {
    switch (ev.type) {
      case "TEXT_MESSAGE_START":
        run.texts.set(ev.messageId, { el: null, text: "" });
        break;
      case "TEXT_MESSAGE_CONTENT": {
        const entry = run.texts.get(ev.messageId) || { el: null, text: "" };
        run.texts.set(ev.messageId, entry);
        entry.text += ev.delta || "";
        if (!entry.text.trim()) break;
        entry.el ||= addMessage("assistant", "");
        entry.el.innerHTML = markdown(entry.text);
        messages.scrollTop = messages.scrollHeight;
        break;
      }
      case "TOOL_CALL_START": {
        let call = run.calls.get(ev.toolCallId);
        if (!call) {
          const chip = append(Object.assign(document.createElement("div"), { className: "tool-chip pending" }));
          call = { id: ev.toolCallId, name: ev.toolCallName, args: "", done: false, chip };
          run.calls.set(ev.toolCallId, call);
        }
        call.args = ""; // AgentOS gửi lại START + ARGS cho tool tạm dừng → lấy bản cuối
        call.chip.textContent = label(ev.toolCallName);
        if (tools.has(ev.toolCallName)) call.chip.classList.add("client");
        break;
      }
      case "TOOL_CALL_ARGS": {
        const call = run.calls.get(ev.toolCallId);
        if (call) call.args += ev.delta || "";
        break;
      }
      case "TOOL_CALL_RESULT": {
        const call = run.calls.get(ev.toolCallId);
        if (call) {
          call.done = true;
          call.chip.classList.replace("pending", "done");
        }
        let data = null;
        try {
          data = JSON.parse(ev.content);
        } catch {
          /* kết quả không phải JSON → chỉ hiện chip */
        }
        if (data?.type === "workbook") append(fileCard(data));
        else if (data?.type === "search_results") append(searchCard(data));
        else if (data?.type === "error" && call) {
          call.chip.classList.replace("done", "failed");
          call.chip.title = data.message;
        }
        break;
      }
      case "RUN_ERROR":
        addMessage("error", esc(ev.message || "Agent gặp lỗi"));
        break;
      default:
        break;
    }
  }

  // ---------------------------------------------------------------- lệnh "/"
  async function runCommand(text) {
    const ui = await host.context().catch(() => ({ host: host.kind }));
    const out = await api("/api/v1/commands", { method: "POST", body: JSON.stringify({ text, ui }) });
    if (out.result?.type === "search_results") {
      const chip = append(Object.assign(document.createElement("div"), { className: "tool-chip done", textContent: label("search_data") }));
      chip.title = "Lệnh / chạy bằng code, không gọi model";
      append(searchCard(out.result));
    }
    addMessage("assistant", markdown(out.text));
  }

  async function send(text) {
    text = text.trim();
    if (!text || state.running) return;
    state.running = true;
    $("#send").disabled = true;
    $("#suggestions") && ($("#suggestions").hidden = true);
    addMessage("user", esc(text));
    try {
      if (text.startsWith("/")) await runCommand(text);
      else await runAgent(text);
    } catch (err) {
      addMessage("error", esc(err.message));
    } finally {
      setTyping(false);
      state.running = false;
      $("#send").disabled = false;
    }
  }

  // ---------------------------------------------------------------- thẻ xác nhận ghi (tool Excel)
  function previewTable(plan) {
    if (plan.kind === "set") {
      const rows = plan.changes.slice(0, 15);
      return `<table class="results-table"><thead><tr><th>Dòng</th><th>Hiện tại</th><th>Ghi mới</th></tr></thead><tbody>${rows
        .map((c) => `<tr><td>${c.row}</td><td class="old">${esc(fmt(c.old))}</td><td class="new">${esc(fmt(c.value))}</td></tr>`)
        .join("")}</tbody></table>`;
    }
    const cols = plan.headers.filter((h) => plan.rows.some((r) => r[h] !== ""));
    const rows = plan.rows.slice(0, 15);
    return `<table class="results-table"><thead><tr><th>Dòng</th>${cols.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${rows
      .map((r, i) => `<tr><td>${plan.firstRow + i}</td>${cols.map((c) => `<td class="new">${esc(fmt(r[c]))}</td>`).join("")}</tr>`)
      .join("")}</tbody></table>`;
  }

  function confirmCard(plan) {
    const card = document.createElement("div");
    card.className = "card confirm-card";
    const n = plan.kind === "set" ? plan.changes.length : plan.rows.length;
    const more = n > 15 ? `<div class="small muted">… và ${n - 15} dòng nữa</div>` : "";
    const title =
      plan.kind === "set"
        ? `Ghi vào cột <strong>${esc(plan.column)}</strong>${plan.create ? " (cột mới)" : ""} · ${n} ô · sheet ${esc(plan.sheet)}`
        : `Thêm <strong>${n}</strong> dòng vào cuối sheet ${esc(plan.sheet)} (từ dòng ${plan.firstRow})`;
    card.innerHTML = `
      <div class="card-head"><div><div class="results-title">✍️ Agent đề xuất ghi vào Excel</div>
        <div class="meta small">${title}</div></div></div>
      <div class="card-body">
        <div class="results-table-wrap">${previewTable(plan)}</div>${more}
        ${plan.warnings.map((w) => `<div class="warn small">⚠ ${esc(w)}</div>`).join("")}
        <div class="results-actions">
          <button class="btn small primary" type="button" data-ok>${plan.kind === "set" ? "Xác nhận ghi" : "Xác nhận thêm"}</button>
          <button class="btn small ghost" type="button" data-no>Hủy</button>
          <span class="small muted">Chưa có gì được ghi cho tới khi bạn bấm xác nhận.</span>
        </div>
        <div class="apply-result" hidden></div>
      </div>`;
    append(card);
    $("[data-ok]", card).focus({ preventScroll: true });
    return new Promise((resolve) => {
      card.addEventListener("click", (e) => {
        const ok = e.target.closest("[data-ok]");
        if (!ok && !e.target.closest("[data-no]")) return;
        card.querySelectorAll("button").forEach((b) => (b.disabled = true));
        const result = $(".apply-result", card);
        result.hidden = false;
        result.className = ok ? "apply-result" : "apply-result muted-result";
        result.textContent = ok ? "Đã xác nhận — đang ghi…" : "Đã hủy, không ghi gì.";
        card.classList.add(ok ? "accepted" : "rejected");
        resolve(Boolean(ok));
      });
    });
  }

  // ---------------------------------------------------------------- thẻ file Excel (export_excel)
  function fileCard(data) {
    const card = document.createElement("div");
    card.className = "card file-card";
    card.dataset.workbook = data.workbook_id;
    const filters = (data.filters || []).map((f) => `<span class="chip">${esc(f.column)} ${esc(f.op)} ${esc(f.value)}</span>`).join("");
    const actions = host.fileActions(data);
    card.innerHTML = `
      <div class="card-head">
        <span class="file-icon" aria-hidden="true">X</span>
        <div>
          <strong>${esc(data.name)}</strong>
          <div class="meta">${data.rows} dòng · ${(data.columns || []).length} cột · ${esc(data.dataset)}</div>
          ${filters ? `<div class="chips">${filters}</div>` : ""}
        </div>
        <div class="actions">
          ${actions.map((a, i) => `<button class="btn small ${a.primary ? "primary" : ""}" type="button" data-action="${i}">${esc(a.label)}</button>`).join("")}
          <a class="btn small" href="${esc(data.download_url)}" download title="Tải file .xlsx">⬇</a>
        </div>
      </div>`;
    const run = async (i) => {
      try {
        const msg = await actions[i].run();
        if (typeof msg === "string") toast(msg);
      } catch (err) {
        toast(err.message, true);
      }
    };
    card.addEventListener("click", (e) => {
      if (e.target.closest("a")) return;
      const btn = e.target.closest("[data-action]");
      run(btn ? Number(btn.dataset.action) : 0);
    });
    return card;
  }

  // ---------------------------------------------------------------- thẻ kết quả tìm kiếm (search_data, /search)
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
      const hs = host.selection();
      card.querySelectorAll("tbody tr").forEach((tr) => tr.classList.toggle("checked", sel.includes(Number(tr.dataset.i))));
      $("[data-count]", card).textContent = sel.length ? `Đã chọn ${sel.length} kết quả` : "Chưa chọn kết quả";
      $(".target-hint", card).textContent = host.isOpen()
        ? `Áp vào: ${host.label()}${hs.column ? ` · cột ${hs.column}` : ""}${hs.rows.length ? ` · ${hs.rows.length} dòng đang chọn` : ""}`
        : "Mở một sheet Excel trước khi áp kết quả vào bảng.";
      if (mode) renderForm();
    };

    const renderForm = () => {
      const sel = checked();
      const headers = host.headers();
      if (!host.isOpen()) {
        form.innerHTML = `<div class="apply-summary">Chưa mở sheet Excel nào.</div>`;
        return;
      }
      if (!sel.length) {
        form.innerHTML = `<div class="apply-summary">Tích chọn ít nhất một kết quả.</div>`;
        return;
      }
      if (mode === "append") {
        form.innerHTML = `
          <div class="apply-summary">Thêm <strong>${sel.length}</strong> dòng mới vào cuối sheet;
          trường nào trùng tên cột thì được điền vào cột đó.</div>
          <div><button class="btn small primary" type="button" data-confirm>Xác nhận thêm</button>
          <button class="btn small ghost" type="button" data-cancel>Hủy</button></div>`;
        return;
      }
      const hs = host.selection();
      const prevTarget = $("select[data-target]", form)?.value;
      const prevSource = $("select[data-source]", form)?.value;
      const prevNew = $("input[data-newcol]", form)?.value || "";
      const target = prevTarget || hs.column || headers.find((c) => norm(c) === norm(data.column)) || headers[0];
      const source = prevSource || cols.find((c) => norm(c) === norm(target)) || data.column || cols[0];
      const rows = hs.rows;
      let warn = "";
      if (!rows.length) warn = "Chọn dòng trên sheet Excel để biết ghi vào đâu.";
      else if (target === "__new__" && !prevNew.trim()) warn = "Nhập tên cột mới.";
      else if (sel.length > 1 && sel.length !== rows.length)
        warn = `Đã chọn ${sel.length} kết quả cho ${rows.length} dòng: chọn 1 kết quả (ghi cùng giá trị) hoặc số kết quả bằng số dòng.`;
      form.innerHTML = `
        <label>Cột đích trong Excel
          <select data-target>${headers.map((c) => `<option ${c === target ? "selected" : ""}>${esc(c)}</option>`).join("")}
            <option value="__new__" ${target === "__new__" ? "selected" : ""}>+ Tạo cột mới…</option></select></label>
        <input data-newcol placeholder="Tên cột mới" value="${esc(prevNew)}" ${target === "__new__" ? "" : "hidden"}>
        <label>Lấy giá trị từ trường của kết quả
          <select data-source>${cols.map((c) => `<option ${c === source ? "selected" : ""}>${esc(c)}</option>`).join("")}</select></label>
        <div class="apply-summary">${
          warn
            ? `⚠ ${esc(warn)}`
            : `Ghi <strong>${esc(source)}</strong> của ${sel.length} kết quả vào cột <strong>${esc(target === "__new__" ? `${prevNew} (mới)` : target)}</strong> cho ${rows.length} dòng: ${rows
                .slice(0, 8)
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
      if (e.target.matches("select[data-target], select[data-source]")) {
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
        await host.context().catch(() => {});
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
      const chosen = checked().map((i) => records[i]);
      try {
        const table = await host.readTable();
        let done;
        if (mode === "append") {
          done = await host.appendRows(planAppend(table, chosen));
        } else {
          const target = $("select[data-target]", form).value;
          const source = $("select[data-source]", form).value;
          const isNew = target === "__new__";
          const plan = planSetValues(table, {
            column: isNew ? $("input[data-newcol]", form).value.trim() : target,
            rows: host.selection().rows,
            values: chosen.map((r) => r[source] ?? ""),
            create_column: isNew,
          });
          done = await host.setValues(plan);
        }
        result.className = "apply-result";
        result.innerHTML = `✓ ${esc(done.message)}${done.version ? ` · phiên bản ${done.version}` : ""}`;
        toast(done.message);
        mode = null;
        form.hidden = true;
      } catch (err) {
        result.className = "apply-result err";
        result.textContent = err.message;
      }
      result.hidden = false;
    }

    host.onChange(refresh);
    setTimeout(refresh);
    return card;
  }

  // ---------------------------------------------------------------- khởi động
  async function loadConfig() {
    const badge = $("#mode-badge");
    try {
      state.config = await api("/api/v1/config");
      const offline = state.config.mode !== "openai";
      badge.textContent = offline ? "Offline · chưa có OPENAI_API_KEY" : `Agno · ${state.config.model}`;
      badge.classList.toggle("offline", offline);
    } catch {
      badge.textContent = "Không kết nối được server";
    }
  }

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
  $("#suggestions")?.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-text]");
    if (btn) send(btn.dataset.text);
  });
  $("#new-chat").addEventListener("click", () => {
    state.threadId = newId();
    sessionStorage.setItem(threadKey, state.threadId);
    messages.innerHTML = "";
    if ($("#suggestions")) $("#suggestions").hidden = false;
    addMessage("assistant", markdown("Đã bắt đầu hội thoại mới. Gõ `/help` để xem hướng dẫn."));
  });

  addMessage("assistant", markdown(welcome));
  loadConfig();
  return { send };
}
