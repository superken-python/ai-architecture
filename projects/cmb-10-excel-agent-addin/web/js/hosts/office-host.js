// Host "office": chạy trong task pane của Excel thật, thao tác workbook đang mở bằng Office.js.
//
// Vùng dữ liệu của sheet: Excel Table đầu tiên của sheet nếu có, không thì vùng đã dùng (used range); dòng đầu
// là tiêu đề cột. Số dòng trả cho agent là số dòng thật trong Excel. API dùng: ExcelApi 1.7 (getRangeByIndexes,
// workbook.name), 1.4 (getUsedRangeOrNullObject, tên cột khi thêm cột vào Table), 1.13 (insertWorksheetsFromBase64,
// không có thì mở file thành workbook mới bằng Excel.createWorkbook — 1.8). Mỗi lần ghi kiểm tra lại dữ liệu so với
// lúc xem trước; người dùng hoàn tác bằng Ctrl+Z như thao tác tay.

import { columnIndex } from "../excel-tools.js";

const MAX_READ_ROWS = 5000; // tránh đọc cả sheet rất lớn mỗi lần tìm (giới hạn Office: 5 triệu ô mỗi lần đọc)
const MAX_SELECTION_ROWS = 500;

function toCell(value) {
  if (value === null || value === undefined) return "";
  // Chuỗi toàn số có số 0 đầu (điện thoại, mã) hoặc dài hơn 15 chữ số: giữ dạng chữ, không để Excel đổi thành số
  if (typeof value === "string" && (/^0\d+$/.test(value) || /^\d{16,}$/.test(value))) return `'${value}`;
  return value;
}

function toBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(binary);
}

export class OfficeHost {
  kind = "office";

  constructor() {
    this.cache = { workbook: null, sheet: null, headers: [], selection: { column: null, rows: [], address: null } };
    this.listeners = new Set();
  }

  // ---------------------------------------------------------------- giao diện chung của host
  isOpen() {
    return Boolean(this.cache.sheet);
  }

  label() {
    return this.cache.sheet ? `${this.cache.workbook || "Workbook"} · sheet ${this.cache.sheet}` : "";
  }

  headers() {
    return this.cache.headers;
  }

  selection() {
    return this.cache.selection;
  }

  onChange(fn) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  // Theo dõi vùng chọn để khung chat luôn biết người dùng đang chọn cột/dòng nào.
  watchSelection() {
    let timer;
    const refresh = () => {
      clearTimeout(timer);
      timer = setTimeout(() => this.context().catch(() => {}), 150);
    };
    Office.context.document.addHandlerAsync(Office.EventType.DocumentSelectionChanged, refresh);
    return this.context().catch(() => {});
  }

  async context({ sampleRows = 0 } = {}) {
    const ctx = await Excel.run(async (context) => {
      context.workbook.load("name");
      const area = await this.dataArea(context, null, { withData: sampleRows > 0 });
      const selection = await this.readSelection(context, area);
      const headers = area.headers;
      const out = {
        host: "office",
        workbook: context.workbook.name,
        sheet: area.sheet,
        table: area.table,
        headers,
        header_row: area.headerRow,
        data_rows: Math.max(area.lastRow - area.headerRow, 0),
        first_data_row: area.headerRow + 1,
        last_row: area.lastRow,
        selection,
      };
      if (sampleRows > 0) {
        out.sample_rows = area.rows.slice(0, sampleRows).map((r) => ({ row: r.row, values: r.values }));
      }
      return out;
    });
    this.cache = { workbook: ctx.workbook, sheet: ctx.sheet, headers: ctx.headers, selection: ctx.selection };
    this.listeners.forEach((fn) => fn());
    return ctx;
  }

  async readTable() {
    return Excel.run(async (context) => {
      const area = await this.dataArea(context, null, { withData: true });
      if (!area.headers.length) throw new Error(`Sheet ${area.sheet} chưa có dữ liệu (cần một dòng tiêu đề cột).`);
      return { sheet: area.sheet, headers: area.headers, headerRow: area.headerRow, table: area.table, rows: area.rows };
    });
  }

  async select(rows, column = null) {
    if (!rows.length) return;
    await Excel.run(async (context) => {
      const area = await this.dataArea(context, null, { withData: false });
      const col = column ? columnIndex(area.headers, column) : -1;
      const target =
        col >= 0
          ? area.ws.getRangeByIndexes(rows[0] - 1, area.firstColumn + col, 1, 1)
          : area.ws.getRangeByIndexes(rows[0] - 1, area.firstColumn, 1, area.headers.length);
      target.select();
      await context.sync();
    });
  }

  async setValues(plan) {
    return Excel.run(async (context) => {
      const area = await this.dataArea(context, plan.sheet, { withData: true });
      const byRow = new Map(area.rows.map((r) => [r.row, r]));
      if (!plan.create) {
        const changed = plan.changes.filter((c) => (byRow.get(c.row)?.values[plan.columnIndex] ?? "") !== c.old);
        if (changed.length) {
          throw new Error(`Ô ở dòng ${changed.map((c) => c.row).join(", ")} đã đổi từ lúc xem trước — chạy lại yêu cầu.`);
        }
      } else if (columnIndex(area.headers, plan.column) >= 0) {
        throw new Error(`Cột "${plan.column}" đã có — không tạo trùng.`);
      }
      const col = area.firstColumn + (plan.create ? area.headers.length : plan.columnIndex);
      if (plan.create) {
        if (area.tableObj) area.tableObj.columns.add(null, null, plan.column);
        else area.ws.getRangeByIndexes(area.headerRow - 1, col, 1, 1).values = [[plan.column]];
      }
      for (const c of plan.changes) area.ws.getRangeByIndexes(c.row - 1, col, 1, 1).values = [[toCell(c.value)]];
      await context.sync();
      // chọn lại đúng vùng vừa ghi nếu các dòng liền nhau (giữ nguyên vùng người dùng đang chọn trong trường hợp thường gặp)
      const rows = plan.changes.map((c) => c.row).sort((a, b) => a - b);
      if (rows.at(-1) - rows[0] + 1 === rows.length) {
        area.ws.getRangeByIndexes(rows[0] - 1, col, rows.length, 1).select();
        await context.sync();
      }
      return { changed_rows: plan.changes.map((c) => c.row), message: `Đã ghi ${plan.changes.length} ô vào cột ${plan.column}` };
    });
  }

  async appendRows(plan) {
    return Excel.run(async (context) => {
      const area = await this.dataArea(context, plan.sheet, { withData: false });
      if (area.headers.join("\u0001") !== plan.headers.join("\u0001")) {
        throw new Error("Tiêu đề cột của sheet đã đổi từ lúc xem trước — chạy lại yêu cầu.");
      }
      if (area.lastRow + 1 !== plan.firstRow) {
        throw new Error(`Sheet đã thêm/bớt dòng từ lúc xem trước (dòng cuối giờ là ${area.lastRow}) — chạy lại yêu cầu.`);
      }
      const matrix = plan.matrix.map((r) => r.map(toCell));
      if (area.tableObj) area.tableObj.rows.add(null, matrix);
      else area.ws.getRangeByIndexes(area.lastRow, area.firstColumn, matrix.length, area.headers.length).values = matrix;
      await context.sync();
      area.ws.getRangeByIndexes(area.lastRow, area.firstColumn, matrix.length, area.headers.length).select();
      await context.sync();
      return {
        first_row: area.lastRow + 1,
        last_row: area.lastRow + matrix.length,
        message: `Đã thêm ${matrix.length} dòng vào sheet ${area.sheet}`,
      };
    });
  }

  fileActions(data) {
    return [{ label: "Chèn vào workbook", primary: true, run: () => this.insertFile(data.download_url) }];
  }

  // File .xlsx do agent xuất (export_excel) → chèn các sheet vào workbook đang mở, hoặc mở thành workbook mới.
  async insertFile(url) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`Không tải được file (HTTP ${resp.status})`);
    const base64 = toBase64(await resp.arrayBuffer());
    if (!Office.context.requirements.isSetSupported("ExcelApi", "1.13")) {
      await Excel.createWorkbook(base64);
      return "Đã mở file thành workbook mới.";
    }
    await Excel.run(async (context) => {
      const ids = context.workbook.insertWorksheetsFromBase64(base64, { positionType: Excel.WorksheetPositionType.end });
      await context.sync();
      context.workbook.worksheets.getItem(ids.value[0]).activate();
      await context.sync();
    });
    await this.context().catch(() => {});
    return "Đã chèn dữ liệu thành sheet mới ở cuối workbook.";
  }

  // ---------------------------------------------------------------- đọc vùng dữ liệu
  async dataArea(context, sheetName, { withData }) {
    const ws = sheetName ? context.workbook.worksheets.getItem(sheetName) : context.workbook.worksheets.getActiveWorksheet();
    ws.load("name");
    ws.tables.load("items/name");
    await context.sync();
    const tableObj = ws.tables.items[0] || null;
    const range = tableObj ? tableObj.getRange() : ws.getUsedRangeOrNullObject(true);
    range.load(["rowIndex", "columnIndex", "rowCount", "columnCount", "address"]);
    await context.sync();
    const empty = { ws, tableObj: null, table: null, sheet: ws.name, headers: [], headerRow: 1, lastRow: 0, firstColumn: 0, rows: [] };
    if (range.isNullObject) return empty;
    const header = range.getRow(0);
    header.load("text");
    let body = null;
    const bodyRows = Math.min(range.rowCount - 1, MAX_READ_ROWS);
    if (withData && bodyRows > 0) {
      body = ws.getRangeByIndexes(range.rowIndex + 1, range.columnIndex, bodyRows, range.columnCount);
      body.load("text");
    }
    await context.sync();
    let headers = header.text[0].map((h) => String(h).trim());
    while (headers.length && !headers.at(-1)) headers.pop(); // bỏ cột trống cuối vùng
    if (!headers.some(Boolean)) return { ...empty, tableObj };
    headers = headers.map((h, i) => h || `Cột ${i + 1}`);
    return {
      ws,
      tableObj,
      table: tableObj ? tableObj.name : null,
      sheet: ws.name,
      headers,
      headerRow: range.rowIndex + 1,
      lastRow: range.rowIndex + range.rowCount,
      firstColumn: range.columnIndex,
      rows: body
        ? body.text.map((vals, i) => ({ row: range.rowIndex + 2 + i, values: vals.slice(0, headers.length) }))
        : [],
    };
  }

  async readSelection(context, area) {
    try {
      const sel = context.workbook.getSelectedRange();
      sel.load(["address", "rowIndex", "columnIndex", "rowCount", "columnCount"]);
      await context.sync();
      const colOffset = sel.columnIndex - area.firstColumn;
      const column = sel.columnCount === 1 && colOffset >= 0 && colOffset < area.headers.length ? area.headers[colOffset] : null;
      const rows = [];
      for (let r = sel.rowIndex + 1; r <= sel.rowIndex + sel.rowCount && rows.length < MAX_SELECTION_ROWS; r++) {
        if (r > area.headerRow && r <= area.lastRow) rows.push(r);
      }
      return { address: sel.address, column, rows };
    } catch {
      return { address: null, column: null, rows: [] }; // đang chọn biểu đồ/hình hoặc nhiều vùng
    }
  }
}
