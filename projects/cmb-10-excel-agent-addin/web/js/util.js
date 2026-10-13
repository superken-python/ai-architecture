// Tiện ích dùng chung cho web POC và task pane trong Excel.

export const $ = (sel, root = document) => root.querySelector(sel);

export function newId() {
  return globalThis.crypto?.randomUUID ? crypto.randomUUID() : `id-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function esc(text) {
  return String(text ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function inline(text) {
  return esc(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[\s(])\*([^*\n]+)\*/g, "$1<em>$2</em>")
    .replace(/(^|[\s(])_([^_\n]+)_/g, "$1<em>$2</em>");
}

// Markdown tối giản đủ cho câu trả lời của agent: đoạn, danh sách gạch đầu dòng, **đậm**, *nghiêng*, `code`.
export function markdown(text) {
  const out = [];
  let list = [];
  const flush = () => {
    if (list.length) out.push(`<ul>${list.map((li) => `<li>${inline(li)}</li>`).join("")}</ul>`);
    list = [];
  };
  for (const line of String(text).split("\n")) {
    const m = line.match(/^\s*(?:[-*]|\d+\.)\s+(.*)$/);
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

export function fmt(value) {
  if (typeof value === "number") return value.toLocaleString("vi-VN");
  return value ?? "";
}

export function colLetter(index) {
  let s = "";
  for (let n = index + 1; n > 0; n = Math.floor((n - 1) / 26)) s = String.fromCharCode(65 + ((n - 1) % 26)) + s;
  return s;
}

// Chuẩn hóa để so khớp tiếng Việt: bỏ dấu, đ → d, chữ thường, gộp khoảng trắng (giống core/text.py).
export function norm(text) {
  return String(text ?? "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/đ/gi, "d")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

export async function api(path, options = {}) {
  const resp = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const detail = data.detail ? (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)) : `HTTP ${resp.status}`;
    throw new Error(detail);
  }
  return data;
}

let toastTimer;
export function toast(text, isError = false) {
  const el = $("#toast");
  if (!el) return;
  el.textContent = text;
  el.classList.toggle("err", isError);
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 3500);
}
