// Office.js GIẢ LẬP cho test task pane (không có Excel thật trong CI). Chỉ mô phỏng phần API mà
// web/js/hosts/office-host.js dùng, theo đúng hành vi của Excel ở những điểm quan trọng:
// - thao tác thực hiện ngay, `load()` không làm gì, `context.sync()` là Promise;
// - chuỗi bắt đầu bằng ' được lưu dạng chữ (bỏ dấu '), chuỗi số khác được đổi thành số;
// - Table mở rộng khi rows.add / columns.add; used range = vùng bao các ô có dữ liệu.
// Test đặt dữ liệu ban đầu qua window.__FAKE_EXCEL_INIT__ = { sheets: [{ name, rows, table }] } trước khi trang chạy.
(() => {
  const init = window.__FAKE_EXCEL_INIT__ || { sheets: [{ name: "Sheet1", rows: [] }] };
  const handlers = [];
  const calls = [];
  const sheets = init.sheets.map((s, i) => ({
    id: `ws-${i}`,
    name: s.name,
    cells: s.rows.map((r) => r.slice()),
    tables: s.table ? [{ name: s.table, startRow: 0, startCol: 0, rowCount: s.rows.length, colCount: s.rows[0].length }] : [],
  }));
  let active = sheets[0];
  let selection = { sheet: active, row: 0, col: 0, rows: 1, cols: 1 };

  const colName = (c) => {
    let s = "";
    for (let n = c + 1; n > 0; n = Math.floor((n - 1) / 26)) s = String.fromCharCode(65 + ((n - 1) % 26)) + s;
    return s;
  };
  const get = (sh, r, c) => (sh.cells[r] && sh.cells[r][c] !== undefined ? sh.cells[r][c] : "");
  const put = (sh, r, c, v) => {
    while (sh.cells.length <= r) sh.cells.push([]);
    if (typeof v === "string" && v.startsWith("'")) v = v.slice(1);
    else if (typeof v === "string" && v.trim() !== "" && !Number.isNaN(Number(v))) v = Number(v);
    sh.cells[r][c] = v;
  };
  const usedBox = (sh) => {
    let r0 = Infinity, c0 = Infinity, r1 = -1, c1 = -1;
    sh.cells.forEach((row, r) => row.forEach((v, c) => {
      if (v !== "" && v !== undefined && v !== null) {
        r0 = Math.min(r0, r); c0 = Math.min(c0, c); r1 = Math.max(r1, r); c1 = Math.max(c1, c);
      }
    }));
    return r1 < 0 ? null : { r: r0, c: c0, rows: r1 - r0 + 1, cols: c1 - c0 + 1 };
  };

  function range(sh, r, c, rows, cols, isNull = false) {
    return {
      isNullObject: isNull,
      rowIndex: r, columnIndex: c, rowCount: rows, columnCount: cols,
      get address() { return `${sh.name}!${colName(c)}${r + 1}:${colName(c + cols - 1)}${r + rows}`; },
      get values() { return Array.from({ length: rows }, (_, i) => Array.from({ length: cols }, (_, j) => get(sh, r + i, c + j))); },
      set values(m) { m.forEach((row, i) => row.forEach((v, j) => put(sh, r + i, c + j, v))); },
      get text() { return this.values.map((row) => row.map((v) => String(v ?? ""))); },
      load() {},
      getRow(i) { return range(sh, r + i, c, 1, cols); },
      select() { active = sh; selection = { sheet: sh, row: r, col: c, rows, cols }; calls.push(["select", this.address]); },
    };
  }

  function table(sh, t) {
    return {
      name: t.name,
      getRange: () => range(sh, t.startRow, t.startCol, t.rowCount, t.colCount),
      rows: {
        add(_index, values) {
          values.forEach((row, i) => row.forEach((v, j) => put(sh, t.startRow + t.rowCount + i, t.startCol + j, v)));
          t.rowCount += values.length;
          calls.push(["table.rows.add", values.length]);
        },
      },
      columns: {
        add(_index, _values, name) {
          put(sh, t.startRow, t.startCol + t.colCount, name);
          t.colCount += 1;
          calls.push(["table.columns.add", name]);
        },
      },
    };
  }

  function worksheet(sh) {
    return {
      get name() { return sh.name; },
      load() {},
      activate() { active = sh; },
      tables: { get items() { return sh.tables.map((t) => table(sh, t)); }, load() {} },
      getUsedRangeOrNullObject() {
        const b = usedBox(sh);
        return b ? range(sh, b.r, b.c, b.rows, b.cols) : range(sh, 0, 0, 0, 0, true);
      },
      getRangeByIndexes: (r, c, rows, cols) => range(sh, r, c, rows, cols),
    };
  }

  const workbook = {
    name: init.workbook || "Book1.xlsx",
    load() {},
    worksheets: {
      getActiveWorksheet: () => worksheet(active),
      getItem(name) {
        const sh = sheets.find((s) => s.name === name || s.id === name);
        if (!sh) throw new Error(`ItemNotFound: ${name}`);
        return worksheet(sh);
      },
    },
    getSelectedRange: () => range(selection.sheet, selection.row, selection.col, selection.rows, selection.cols),
    insertWorksheetsFromBase64(base64) {
      const sh = { id: `ws-${sheets.length}`, name: `Imported ${sheets.length}`, cells: [["Dữ liệu chèn"]], tables: [] };
      sheets.push(sh);
      calls.push(["insertWorksheetsFromBase64", base64.slice(0, 8), base64.length]);
      return { value: [sh.id] };
    },
  };

  window.Excel = {
    run: async (fn) => fn({ workbook, sync: async () => {} }),
    createWorkbook: async (base64) => calls.push(["createWorkbook", base64.length]),
    WorksheetPositionType: { end: "End" },
  };
  window.Office = {
    HostType: { Excel: "Excel" },
    EventType: { DocumentSelectionChanged: "documentSelectionChanged" },
    context: {
      requirements: { isSetSupported: () => true },
      document: { addHandlerAsync: (_type, handler) => handlers.push(handler) },
    },
    onReady(cb) {
      const info = { host: "Excel", platform: "OfficeOnline" };
      setTimeout(() => cb && cb(info));
      return Promise.resolve(info);
    },
  };
  // Điều khiển từ test: chọn vùng như người dùng bấm chuột, xem dữ liệu sheet, xem các lệnh đã gọi
  window.__fakeExcel = {
    select(sheetName, row, col, rows = 1, cols = 1) {
      const sh = sheets.find((s) => s.name === sheetName);
      active = sh;
      selection = { sheet: sh, row, col, rows, cols };
      handlers.forEach((h) => h({ type: "documentSelectionChanged" }));
    },
    setCell(sheetName, row, col, value) {
      put(sheets.find((s) => s.name === sheetName), row, col, value);
    },
    dump: (sheetName) => sheets.find((s) => s.name === sheetName).cells.map((r) => r.slice()),
    calls,
  };
})();
