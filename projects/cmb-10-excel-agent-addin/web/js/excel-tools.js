// Công cụ Excel chạy ở client (frontend tools của AG-UI).
//
// Mỗi lượt chat, giao diện gửi EXCEL_TOOLS trong `RunAgentInput.tools`. AgentOS (Agno) biến chúng thành tool
// `external_execution`: khi model gọi, run TẠM DỪNG và trả TOOL_CALL_START/ARGS/END (không có RESULT). Giao diện
// chạy tool trên "host" (bảng web mô phỏng, hoặc Excel thật qua Office.js), rồi gửi kết quả bằng tin nhắn
// `role: "tool"` để run CHẠY TIẾP. Tool ghi (excel_set_values, excel_append_rows) luôn hiện xem trước và chờ người
// dùng bấm xác nhận — agent không tự ghi được.
//
// Host cần có: kind, context(), readTable(), select(rows, column), setValues(plan), appendRows(plan).
// Bảng (table) mà readTable() trả về: { sheet, headers: [..], headerRow, rows: [{ row, values: [..] }] }
// với `row` là số dòng thật trong Excel và `values` là chữ hiển thị của từng ô theo thứ tự headers.

import { norm } from "./util.js";

export const MAX_WRITE_ROWS = 200;

export const EXCEL_TOOLS = [
  {
    name: "excel_get_context",
    description:
      "Đọc trạng thái Excel hiện tại: workbook, sheet đang mở, tiêu đề cột, số dòng dữ liệu, vùng đang chọn và 3 dòng đầu.",
    parameters: { type: "object", properties: {} },
  },
  {
    name: "excel_find_rows",
    description:
      "Tìm các dòng trong SHEET ĐANG MỞ có ô chứa từ khóa (không phân biệt dấu, hoa thường). Trả về số dòng Excel và " +
      "giá trị từng cột của dòng tìm được, đồng thời chọn các dòng đó trên sheet.",
    parameters: {
      type: "object",
      properties: {
        query: { type: "string", description: "Từ khóa cần tìm" },
        column: { type: ["string", "null"], description: "Tên cột (tiêu đề) để chỉ tìm trong cột đó; null = mọi cột" },
        match: { type: "string", enum: ["contains", "exact"], description: "contains (mặc định) hoặc exact" },
        limit: { type: "integer", description: "Số dòng tối đa trả về, mặc định 20, tối đa 50" },
      },
      required: ["query"],
    },
  },
  {
    name: "excel_read_rows",
    description: "Đọc giá trị các dòng của sheet đang mở theo số dòng Excel.",
    parameters: {
      type: "object",
      properties: {
        rows: { type: "array", items: { type: "integer" }, description: "Số dòng Excel, ví dụ [5, 6]" },
        columns: { type: ["array", "null"], items: { type: "string" }, description: "Chỉ lấy các cột này; null = mọi cột" },
      },
      required: ["rows"],
    },
  },
  {
    name: "excel_set_values",
    description:
      "Ghi giá trị vào MỘT cột cho các dòng chỉ định của sheet đang mở. `values` có 1 phần tử → ghi cùng giá trị cho mọi " +
      "dòng; hoặc có đúng bằng số dòng → ghi lần lượt. Người dùng xem trước và phải bấm xác nhận. Kết quả có " +
      "status: applied | rejected (người dùng hủy) | error.",
    parameters: {
      type: "object",
      properties: {
        column: { type: "string", description: "Tên cột đích (tiêu đề)" },
        rows: { type: "array", items: { type: "integer" }, description: "Số dòng Excel cần ghi" },
        values: { type: "array", items: { type: ["string", "number", "null"] }, description: "Giá trị cần ghi" },
        create_column: { type: "boolean", description: "true nếu cột chưa có và cần tạo mới ở cuối bảng" },
      },
      required: ["column", "rows", "values"],
    },
  },
  {
    name: "excel_append_rows",
    description:
      "Thêm dòng mới vào cuối bảng của sheet đang mở. Mỗi phần tử của `rows` là object {tên cột: giá trị}; cột không có " +
      "trong object để trống. Người dùng xem trước và phải bấm xác nhận. Kết quả có status: applied | rejected | error.",
    parameters: {
      type: "object",
      properties: {
        rows: { type: "array", items: { type: "object", additionalProperties: true }, description: "Các dòng cần thêm" },
      },
      required: ["rows"],
    },
  },
];

export const TOOL_LABELS = {
  excel_get_context: "Đọc trạng thái Excel",
  excel_find_rows: "Tìm trong sheet",
  excel_read_rows: "Đọc dòng trong sheet",
  excel_set_values: "Ghi vào cột",
  excel_append_rows: "Thêm dòng vào sheet",
  export_excel: "Gọi API xuất Excel",
  search_data: "Tìm trong hệ thống",
  list_datasets: "Lấy danh mục dữ liệu",
};

const isWrite = (name) => name === "excel_set_values" || name === "excel_append_rows";

// ------------------------------------------------------------------ logic thuần (dùng chung cho mọi host)
export function columnIndex(headers, name) {
  const key = norm(name);
  return headers.findIndex((h) => norm(h) === key);
}

function asObject(headers, values) {
  return Object.fromEntries(headers.map((h, i) => [h, values[i] ?? ""]));
}

export function findRows(table, { query, column = null, match = "contains", limit = 20 }) {
  const q = norm(query);
  if (!q) throw new Error("Thiếu từ khóa cần tìm.");
  let col = -1;
  if (column) {
    col = columnIndex(table.headers, column);
    if (col < 0) throw new Error(`Sheet ${table.sheet} không có cột "${column}". Các cột: ${table.headers.join(", ")}`);
  }
  const hit = (v) => (match === "exact" ? norm(v) === q : norm(v).includes(q));
  const found = table.rows.filter((r) => (col >= 0 ? hit(r.values[col]) : r.values.some(hit)));
  const max = Math.min(Math.max(Number(limit) || 20, 1), 50);
  return {
    status: "ok",
    sheet: table.sheet,
    column: col >= 0 ? table.headers[col] : null,
    query,
    total: found.length,
    matches: found.slice(0, max).map((r) => ({ row: r.row, values: asObject(table.headers, r.values) })),
  };
}

export function readRows(table, { rows, columns = null }) {
  const wanted = columns?.length ? columns.map((c) => [c, columnIndex(table.headers, c)]) : table.headers.map((h, i) => [h, i]);
  const missing = wanted.filter(([, i]) => i < 0).map(([c]) => c);
  if (missing.length) throw new Error(`Không có cột: ${missing.join(", ")}`);
  const byRow = new Map(table.rows.map((r) => [r.row, r]));
  return {
    status: "ok",
    sheet: table.sheet,
    rows: rows.map((n) => {
      const r = byRow.get(Number(n));
      return r ? { row: r.row, values: Object.fromEntries(wanted.map(([c, i]) => [c, r.values[i] ?? ""])) } : { row: n, missing: true };
    }),
  };
}

export function planSetValues(table, { column, rows, values, create_column = false }) {
  if (!column) throw new Error("Thiếu tên cột đích.");
  if (!rows?.length) throw new Error("Chưa có dòng nào để ghi (chọn dòng trên sheet hoặc nêu số dòng).");
  if (rows.length > MAX_WRITE_ROWS) throw new Error(`Tối đa ${MAX_WRITE_ROWS} dòng mỗi lần ghi.`);
  if (!values?.length || (values.length !== 1 && values.length !== rows.length)) {
    throw new Error(`Có ${values?.length || 0} giá trị cho ${rows.length} dòng: cần 1 giá trị hoặc đúng ${rows.length} giá trị.`);
  }
  let col = columnIndex(table.headers, column);
  const create = col < 0 && Boolean(create_column);
  if (col < 0 && !create) throw new Error(`Sheet ${table.sheet} không có cột "${column}". Các cột: ${table.headers.join(", ")}`);
  if (create) col = table.headers.length;
  const byRow = new Map(table.rows.map((r) => [r.row, r]));
  const bad = rows.filter((n) => !byRow.has(Number(n)));
  if (bad.length) {
    const first = table.rows[0]?.row ?? table.headerRow + 1;
    const last = table.rows.at(-1)?.row ?? first;
    throw new Error(`Dòng ${bad.join(", ")} không nằm trong vùng dữ liệu (dòng ${first}–${last}).`);
  }
  return {
    kind: "set",
    sheet: table.sheet,
    column: create ? column : table.headers[col],
    columnIndex: col,
    create,
    changes: rows.map((n, i) => ({
      row: Number(n),
      old: create ? "" : byRow.get(Number(n)).values[col] ?? "",
      value: values.length === 1 ? values[0] : values[i],
    })),
    warnings: [],
  };
}

function isKeyColumn(header) {
  const n = norm(header);
  return n === "ma" || n.startsWith("ma ") || n === "id" || n.endsWith(" id");
}

export function planAppend(table, rows) {
  if (!Array.isArray(rows) || !rows.length) throw new Error("Không có dòng nào để thêm.");
  if (rows.length > MAX_WRITE_ROWS) throw new Error(`Tối đa ${MAX_WRITE_ROWS} dòng mỗi lần thêm.`);
  if (!table.headers.length) throw new Error("Sheet đang mở chưa có dòng tiêu đề.");
  const unknown = new Set();
  const records = rows.map((obj) => {
    if (!obj || typeof obj !== "object") throw new Error("Mỗi dòng phải là object {tên cột: giá trị}.");
    const out = Object.fromEntries(table.headers.map((h) => [h, ""]));
    let matched = 0;
    for (const [key, value] of Object.entries(obj)) {
      const i = columnIndex(table.headers, key);
      if (i < 0) unknown.add(key);
      else {
        out[table.headers[i]] = value ?? "";
        matched += 1;
      }
    }
    if (!matched) throw new Error(`Dòng không có trường nào trùng tên cột của sheet (${table.headers.join(", ")}).`);
    return out;
  });
  const key = table.headers[0];
  if (isKeyColumn(key)) {
    const existing = new Map(table.rows.map((r) => [norm(r.values[0]), r.row]));
    const dup = records.filter((r) => r[key] !== "" && existing.has(norm(r[key])));
    if (dup.length) {
      throw new Error(dup.map((r) => `${key} ${r[key]} đã có ở dòng ${existing.get(norm(r[key]))}`).join("; ") + " — không thêm trùng.");
    }
  }
  const lastRow = table.rows.at(-1)?.row ?? table.headerRow;
  return {
    kind: "append",
    sheet: table.sheet,
    headers: table.headers,
    rows: records,
    matrix: records.map((r) => table.headers.map((h) => r[h])),
    firstRow: lastRow + 1,
    warnings: unknown.size ? [`Bỏ qua trường không có cột tương ứng: ${[...unknown].join(", ")}`] : [],
  };
}

// ------------------------------------------------------------------ chạy tool
// confirm(plan) → Promise<boolean>: giao diện hiện xem trước và chờ người dùng bấm.
export function createExcelTools({ host, confirm }) {
  async function run(name, args) {
    switch (name) {
      case "excel_get_context":
        return { status: "ok", ...(await host.context({ sampleRows: 3 })) };
      case "excel_find_rows": {
        const result = findRows(await host.readTable(), args);
        if (result.matches.length) await host.select(result.matches.map((m) => m.row), result.column);
        return result;
      }
      case "excel_read_rows":
        return readRows(await host.readTable(), args);
      case "excel_set_values": {
        const plan = planSetValues(await host.readTable(), args);
        if (!(await confirm(plan))) return { status: "rejected", message: "Người dùng đã hủy, chưa ghi gì." };
        const done = await host.setValues(plan);
        return { status: "applied", sheet: plan.sheet, column: plan.column, changed_rows: done.changed_rows, message: done.message };
      }
      case "excel_append_rows": {
        const plan = planAppend(await host.readTable(), args.rows);
        if (!(await confirm(plan))) return { status: "rejected", message: "Người dùng đã hủy, chưa thêm dòng nào." };
        const done = await host.appendRows(plan);
        return { status: "applied", sheet: plan.sheet, rows_added: plan.rows.length, ...done, warnings: plan.warnings };
      }
      default:
        return { status: "error", message: `Giao diện không có công cụ ${name}` };
    }
  }

  return {
    definitions: EXCEL_TOOLS,
    has: (name) => EXCEL_TOOLS.some((t) => t.name === name),
    isWrite,
    async execute(name, args) {
      try {
        return await run(name, args || {});
      } catch (err) {
        return { status: "error", message: err?.message || String(err) };
      }
    },
  };
}
