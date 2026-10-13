// Host "web": bảng Excel mô phỏng trong trình duyệt, dữ liệu là file .xlsx lưu trên server (/api/v1/workbooks).
// Cùng giao diện với OfficeHost nên chat và công cụ Excel chạy y hệt khi chuyển sang add-in thật.

import { $, api, colLetter, esc, fmt, toast } from "../util.js";

const PAGE = 500;

export class WebGridHost {
  kind = "web";

  constructor() {
    this.workbook = null; // WorkbookInfo
    this.sheet = null;
    this.columns = [];
    this.rows = []; // mảng giá trị theo thứ tự cột; chỉ số 0 = dòng 2 trong Excel
    this.totalRows = 0;
    this.selectedColumn = null;
    this.selectedRows = new Set(); // chỉ số dòng dữ liệu (0 = dòng 2)
    this.lastRow = null;
    this.flash = null; // { rows: Set, column }
    this.listeners = new Set();
    this.bind();
  }

  // ---------------------------------------------------------------- giao diện chung của host
  isOpen() {
    return Boolean(this.workbook);
  }

  label() {
    return this.workbook ? `${this.workbook.name} · sheet ${this.sheet}` : "";
  }

  headers() {
    return this.columns;
  }

  selection() {
    return { column: this.selectedColumn, rows: [...this.selectedRows].sort((a, b) => a - b).map((r) => r + 2) };
  }

  onChange(fn) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  async context({ sampleRows = 0 } = {}) {
    if (!this.workbook) return { host: "web", workbook: null, sheet: null, headers: [], note: "Chưa mở file Excel nào" };
    const sel = this.selection();
    return {
      host: "web",
      workbook: this.workbook.name,
      workbook_id: this.workbook.id,
      sheet: this.sheet,
      headers: this.columns,
      header_row: 1,
      data_rows: this.totalRows,
      first_data_row: 2,
      last_row: this.totalRows + 1,
      selection: { column: sel.column, rows: sel.rows },
      ...(sampleRows ? { sample_rows: this.rows.slice(0, sampleRows).map((r, i) => ({ row: i + 2, values: r })) } : {}),
    };
  }

  async readTable() {
    if (!this.workbook) throw new Error("Chưa mở file Excel nào — tạo file hoặc bấm vào thẻ file trước.");
    while (this.rows.length < this.totalRows) await this.loadPreview(this.sheet, { append: true });
    return {
      sheet: this.sheet,
      headers: this.columns,
      headerRow: 1,
      rows: this.rows.map((values, i) => ({ row: i + 2, values })),
    };
  }

  async select(rows, column = null) {
    this.selectedRows = new Set(rows.map((r) => r - 2).filter((i) => i >= 0 && i < this.rows.length));
    if (column) this.selectedColumn = column;
    this.renderGrid();
    this.scrollTo(Math.min(...this.selectedRows));
  }

  async setValues(plan) {
    const res = await this.apply({
      mode: "set_column",
      sheet: plan.sheet,
      records: plan.changes.map((c) => ({ [plan.column]: c.value })),
      target_column: plan.column,
      source_field: plan.column,
      row_indexes: plan.changes.map((c) => c.row - 2),
      create_column: plan.create,
    });
    if (res.changed_column) this.selectedColumn = res.changed_column;
    this.renderGrid();
    return { changed_rows: res.changed_rows.map((i) => i + 2), message: res.message, version: res.workbook.version };
  }

  async appendRows(plan) {
    const res = await this.apply({ mode: "append_rows", sheet: plan.sheet, records: plan.rows });
    const rows = res.changed_rows.map((i) => i + 2);
    this.scrollTo(res.changed_rows[0]);
    return { first_row: rows[0], last_row: rows.at(-1), message: res.message, version: res.workbook.version };
  }

  fileActions(data) {
    return [{ label: "Xem dữ liệu", primary: true, run: () => this.openWorkbook(data.workbook_id) }];
  }

  // ---------------------------------------------------------------- REST workbook
  async apply(body) {
    const res = await api(`/api/v1/workbooks/${this.workbook.id}/apply`, {
      method: "POST",
      body: JSON.stringify({ ...body, expected_version: this.workbook.version }),
    });
    this.workbook = res.workbook;
    this.flash = { rows: new Set(res.changed_rows), column: res.changed_column };
    await this.loadPreview(this.sheet);
    setTimeout(() => (this.flash = null), 4000);
    return res;
  }

  async openWorkbook(id, sheet = null) {
    try {
      const info = await api(`/api/v1/workbooks/${id}`);
      if (this.workbook?.id !== id) {
        this.selectedColumn = null;
        this.selectedRows.clear();
      }
      this.workbook = info;
      await this.loadPreview(sheet || info.sheets[0]);
      $("#sheet-empty").hidden = true;
      $("#sheet-view").hidden = false;
      this.markActiveCards();
    } catch (err) {
      toast(err.message, true);
    }
  }

  async loadPreview(sheet, { append = false } = {}) {
    const offset = append ? this.rows.length : 0;
    const limit = append ? PAGE : Math.max(200, Math.min(this.rows.length, PAGE));
    const pv = await api(
      `/api/v1/workbooks/${this.workbook.id}/preview?sheet=${encodeURIComponent(sheet)}&offset=${offset}&limit=${limit}`,
    );
    if (this.sheet !== pv.sheet) {
      this.selectedColumn = null;
      this.selectedRows.clear();
    }
    this.sheet = pv.sheet;
    this.columns = pv.columns;
    this.rows = append ? this.rows.concat(pv.rows) : pv.rows;
    this.totalRows = pv.total_rows;
    this.workbook.version = pv.version;
    this.renderSheet(pv);
  }

  async loadRecent() {
    try {
      const list = await api("/api/v1/workbooks?limit=5");
      $("#recent").innerHTML = list.length
        ? `<div class="small muted">File gần đây</div>` +
          list
            .map(
              (w) =>
                `<button type="button" data-open="${esc(w.id)}"><span>📗 ${esc(w.name)}</span><span class="muted small">${w.rows} dòng · v${w.version}</span></button>`,
            )
            .join("")
        : "";
    } catch {
      /* chưa có file nào */
    }
  }

  // ---------------------------------------------------------------- vẽ bảng
  markActiveCards() {
    document.querySelectorAll(".file-card").forEach((c) => c.classList.toggle("active", c.dataset.workbook === this.workbook?.id));
  }

  scrollTo(index) {
    if (!Number.isFinite(index)) return;
    document.querySelector(`#grid tr[data-row="${index}"]`)?.scrollIntoView({ block: "center" });
  }

  renderSheet(pv) {
    const wb = this.workbook;
    $("#wb-name").textContent = wb.name;
    $("#wb-meta").textContent = ` · phiên bản ${pv.version} · ${pv.total_rows} dòng · ${pv.columns.length} cột`;
    $("#btn-download").href = `${wb.download_url}?v=${pv.version}`;
    $("#btn-download").setAttribute("download", wb.name);
    $("#btn-undo").disabled = pv.version <= 1;
    $("#sheet-tabs").innerHTML = pv.sheets
      .map((s) => `<button type="button" role="tab" aria-selected="${s === pv.sheet}" data-sheet="${esc(s)}">${esc(s)}</button>`)
      .join("");
    this.renderGrid();
  }

  renderGrid() {
    const { flash, columns, selectedColumn } = this;
    const head =
      `<thead><tr class="letters"><th class="corner"></th>${columns.map((_, i) => `<th>${colLetter(i)}</th>`).join("")}</tr>` +
      `<tr class="headers"><th class="corner">1</th>${columns
        .map((c) => `<th data-col="${esc(c)}" class="${c === selectedColumn ? "col-sel" : ""}" title="Bấm để chọn cột">${esc(c)}</th>`)
        .join("")}</tr></thead>`;
    const body = this.rows
      .map((row, r) => {
        const cells = columns
          .map((c, i) => {
            const v = row[i];
            const cls = [typeof v === "number" ? "num" : "", c === selectedColumn ? "col-sel" : ""];
            if (flash && flash.rows.has(r) && (!flash.column || flash.column === c)) cls.push("flash");
            return `<td class="${cls.join(" ").trim()}">${esc(fmt(v))}</td>`;
          })
          .join("");
        const sel = this.selectedRows.has(r) ? "row-sel" : "";
        return `<tr class="${sel}" data-row="${r}"><td class="rownum" data-row="${r}" title="Bấm để chọn dòng">${r + 2}</td>${cells}</tr>`;
      })
      .join("");
    $("#grid").innerHTML = head + `<tbody>${body}</tbody>`;
    $("#grid-range").textContent = `Hiển thị ${this.rows.length}/${this.totalRows} dòng dữ liệu (số bên trái là số dòng trong Excel)`;
    $("#btn-more").hidden = this.rows.length >= this.totalRows;
    this.updateSelectionText();
  }

  updateSelectionText() {
    const n = this.selectedRows.size;
    const parts = [];
    if (this.selectedColumn) parts.push(`Cột đang chọn: <strong>${esc(this.selectedColumn)}</strong>`);
    if (n) parts.push(`<strong>${n}</strong> dòng đang chọn`);
    $("#selection-text").innerHTML = parts.length
      ? parts.join(" · ")
      : "Bấm tiêu đề cột để chọn cột · bấm số dòng để chọn dòng (Shift để chọn liên tiếp)";
    $("#btn-clear-selection").hidden = !parts.length;
    this.listeners.forEach((fn) => fn());
  }

  bind() {
    $("#grid").addEventListener("click", (e) => {
      const th = e.target.closest("th[data-col]");
      if (th) {
        this.selectedColumn = this.selectedColumn === th.dataset.col ? null : th.dataset.col;
        this.renderGrid();
        return;
      }
      const rn = e.target.closest("td.rownum");
      if (!rn) return;
      const r = Number(rn.dataset.row);
      if (e.shiftKey && this.lastRow !== null) {
        const [a, b] = [Math.min(this.lastRow, r), Math.max(this.lastRow, r)];
        for (let i = a; i <= b; i++) this.selectedRows.add(i);
      } else if (this.selectedRows.has(r)) this.selectedRows.delete(r);
      else this.selectedRows.add(r);
      this.lastRow = r;
      this.renderGrid();
    });
    $("#sheet-tabs").addEventListener("click", (e) => {
      const tab = e.target.closest("button[data-sheet]");
      if (tab) this.loadPreview(tab.dataset.sheet).catch((err) => toast(err.message, true));
    });
    $("#btn-clear-selection").addEventListener("click", () => {
      this.selectedColumn = null;
      this.selectedRows.clear();
      this.renderGrid();
    });
    $("#btn-refresh").addEventListener("click", () => this.loadPreview(this.sheet).catch((err) => toast(err.message, true)));
    $("#btn-more").addEventListener("click", () => this.loadPreview(this.sheet, { append: true }).catch((err) => toast(err.message, true)));
    $("#btn-undo").addEventListener("click", async () => {
      try {
        this.workbook = await api(`/api/v1/workbooks/${this.workbook.id}/undo`, { method: "POST" });
        await this.loadPreview(this.sheet);
        toast(`Đã hoàn tác về phiên bản ${this.workbook.version}`);
      } catch (err) {
        toast(err.message, true);
      }
    });
    $("#recent").addEventListener("click", (e) => {
      const btn = e.target.closest("[data-open]");
      if (btn) this.openWorkbook(btn.dataset.open);
    });
  }
}
