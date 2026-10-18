/* Lộ trình kỹ năng AI — ứng dụng một trang, JavaScript thuần.
 * Dữ liệu: catalog/*.yaml → `python -m aiarch.site build` → nhúng vào index.html (#catalog-data).
 * Tiến độ cá nhân lưu trong localStorage của trình duyệt (có xuất/nhập file).
 */
(function () {
  "use strict";

  // ───────────────────────── dữ liệu ─────────────────────────
  let D = null;
  const LV = ["basic", "intermediate", "advanced"];
  const RANK = { basic: 1, intermediate: 2, advanced: 3 };
  const SYM = { core: "●", needed: "◐", minor: "○" };
  const PROGRESS_KEY = "aiarch-progress-v1";
  const UI_KEY = "aiarch-ui-v1";
  let SK, GR, DOM, CMB, ORDER, STAGES, ALL_STEPS, STEP, PATH_KEY;

  function index() {
    SK = Object.fromEntries(D.skills.map((s) => [s.id, s]));
    GR = Object.fromEntries(D.groups.map((g) => [g.id, g]));
    DOM = Object.fromEntries(D.domains.map((d) => [d.code, d]));
    CMB = Object.fromEntries(D.combinations.map((c) => [c.id, c]));
    ORDER = Object.fromEntries(D.skills.map((s) => [s.id, s.order]));
    STAGES = D.roadmap.stages || [];
    ALL_STEPS = STAGES.flatMap((st) => (st.steps || []).map((step) => ({ ...step, stage: st.id })));
    STEP = Object.fromEntries(ALL_STEPS.map((step) => [step.id, step]));
    PATH_KEY = Object.fromEntries(Object.entries(D.meta.docs).map(([key, d]) => [d.path, key]));
  }

  // ───────────────────────── lưu trữ (an toàn khi bị chặn) ─────────────────────────
  function readJSON(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) {
      return fallback;
    }
  }
  function writeJSON(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      /* chế độ riêng tư / bị chặn: vẫn chạy, chỉ không nhớ */
    }
  }

  let progress = readJSON(PROGRESS_KEY, { v: 1, skills: {} });
  if (!progress || typeof progress.skills !== "object") progress = { v: 1, skills: {} };
  const ui = Object.assign({ track: null, stage: null, open: [], q: "", domain: "", tier: "", group: "", sort: "order", matrixDomain: "" }, readJSON(UI_KEY, {}));
  ui.open = new Set(Array.isArray(ui.open) ? ui.open : []);
  ui.quiz = { i: 0, result: null };
  function saveUI() {
    writeJSON(UI_KEY, { track: ui.track, stage: ui.stage, open: [...ui.open], sort: ui.sort });
  }

  const rank = (id) => progress.skills[id] || 0;
  function setRank(id, r) {
    if (r <= 0) delete progress.skills[id];
    else progress.skills[id] = Math.min(3, r);
    writeJSON(PROGRESS_KEY, progress);
  }
  function toggleLevel(id, level) {
    const r = RANK[level];
    setRank(id, rank(id) >= r ? r - 1 : r);
  }
  const met = (item) => rank(item.id) >= RANK[item.level];

  // ───────────────────────── tiện ích HTML ─────────────────────────
  const esc = (s) =>
    String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const md = (s) =>
    esc(s)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  const fold = (s) =>
    String(s || "")
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toLowerCase();
  const pct = (a, b) => (b ? Math.round((100 * a) / b) : 0);
  const byOrder = (a, b) => ORDER[a] - ORDER[b];
  const stageColor = (id) => `--stage-color: var(--st-${esc(id)})`;
  const groupNo = (gid) => gid.slice(1);

  function lvBadge(level, withPill = true) {
    const r = typeof level === "number" ? level : RANK[level];
    const label = r ? D.levels[LV[r - 1]] : "Chưa đạt";
    return `<span class="lv lv-${r} ${withPill ? "lv-pill" : ""}"><span class="lv-bars" aria-hidden="true"><i></i><i></i><i></i></span>${esc(label)}</span>`;
  }
  function skillLink(id, cls = "") {
    const s = SK[id];
    return `<a class="chip ${cls} ${rank(id) ? "done" : ""}" href="#/ky-nang/${esc(id)}" title="${esc(s.summary)}"><span class="mono">${esc(id)}</span>${esc(s.name)}</a>`;
  }
  function groupLink(gid) {
    const g = GR[gid];
    return `<a class="chip" href="#/nhom/${esc(gid)}"><span class="mono">${esc(groupNo(gid))}</span>${esc(g.name)}</a>`;
  }
  function meter(done, total, label) {
    const p = pct(done, total);
    const text = label != null ? label : `${done}/${total}`;
    return `<div class="meter" role="img" aria-label="Tiến độ ${p}%"><div class="meter-track"><div class="meter-fill ${p === 100 ? "full" : ""}" style="width:${p}%"></div></div><span class="meter-label">${esc(text)}</span></div>`;
  }
  function toggle(id, level, label) {
    const on = rank(id) >= RANK[level];
    const text = label || `Đạt ${D.levels[level]}`;
    return `<button type="button" class="toggle" data-action="lvl" data-id="${esc(id)}" data-level="${level}" aria-pressed="${on}"><span class="box" aria-hidden="true"></span>${esc(text)}</button>`;
  }
  const chev = `<svg class="chev" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`;

  // ───────────────────────── liên kết học: tài liệu ↔ bước ↔ kỹ năng ↔ nhóm (từ catalog/docs.yaml) ─────────────────────────
  const KIND = { guide: "Hướng dẫn", lesson: "Bài học", lab: "Lab", project: "Dự án", report: "Báo cáo", doc: "Tài liệu" };
  const KIND_ORDER = { lesson: 0, lab: 1, guide: 2, project: 3, report: 4, doc: 5 };
  const ICON_BOOK = `<svg class="ico" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M0 1.75A.75.75 0 0 1 .75 1h4.253c1.227 0 2.317.59 3 1.501A3.743 3.743 0 0 1 11.006 1h4.245a.75.75 0 0 1 .75.75v10.5a.75.75 0 0 1-.75.75h-4.507a2.25 2.25 0 0 0-1.591.659l-.622.621a.75.75 0 0 1-1.06 0l-.622-.621A2.25 2.25 0 0 0 5.258 13H.75a.75.75 0 0 1-.75-.75Zm7.251 10.324.004-5.073-.002-2.253A2.25 2.25 0 0 0 5.003 2.5H1.5v9h3.757a3.75 3.75 0 0 1 1.994.574ZM8.755 4.75l-.004 7.322a3.752 3.752 0 0 1 1.992-.572H14.5v-9h-3.495a2.25 2.25 0 0 0-2.25 2.25Z"/></svg>`;
  const encPath = (p) => String(p).split("/").map(encodeURIComponent).join("/");
  const docHref = (path, anchor) => `#/doc/${encPath(path)}${anchor ? `#${encodeURIComponent(anchor)}` : ""}`;
  const docOf = (key) => D.meta.docs[key];
  const kindOf = (key) => (docOf(key) || {}).kind || "doc";
  const byKind = (a, b) => (KIND_ORDER[kindOf(a)] ?? 9) - (KIND_ORDER[kindOf(b)] ?? 9);
  const uniq = (xs) => [...new Set(xs)];
  // Tài liệu gắn với một bước/giai đoạn/nhóm/tổ hợp/mảng/trang — danh sách khóa trong docs.yaml.
  const docsBy = (map, id) => ((D.learn[`by_${map}`] || {})[id] || []).filter((k) => docOf(k));
  function docLink(key, label) {
    const d = docOf(key);
    return d ? `<a href="${esc(docHref(d.path))}">${esc(label || d.title)}</a>` : "";
  }
  function resLink(key) {
    const d = docOf(key);
    if (!d) return "";
    return `<a class="res res-${esc(d.kind)}" href="${esc(docHref(d.path))}" title="${esc(d.desc)}"><span class="res-kind">${esc(KIND[d.kind] || KIND.doc)}</span><span class="res-title">${esc(d.title)}</span></a>`;
  }
  // Nơi học một kỹ năng: {key, level, step} — bài học/lab của bước chứa kỹ năng + tài liệu khai báo kỹ năng.
  function skillResources(id) {
    const seen = new Set();
    return ((D.learn.by_skill || {})[id] || []).filter((r) => docOf(r.key) && !seen.has(r.key) && seen.add(r.key));
  }
  // Tài liệu tốt nhất để học kỹ năng ở một mức: đúng mức trước, rồi bài học trước lab trước tài liệu.
  function bestResource(id, level) {
    const want = RANK[level] || 1;
    const score = (r) => (r.level ? Math.abs(RANK[r.level] - want) : 4) * 10 + (KIND_ORDER[kindOf(r.key)] ?? 9);
    return skillResources(id).sort((a, b) => score(a) - score(b))[0] || null;
  }
  function learnMini(id, level) {
    const r = bestResource(id, level);
    if (!r) return "";
    const d = docOf(r.key);
    return `<a class="learn-mini" href="${esc(docHref(d.path))}" title="${esc(`${KIND[d.kind]}: ${d.title}`)}">${ICON_BOOK}Học ngay${r.step ? ` · ${esc(r.step)}` : ""}</a>`;
  }
  const docsForSkills = (ids) => uniq(ids.flatMap((id) => skillResources(id).map((r) => r.key))).sort(byKind);
  function stageChip(id) {
    const st = STAGES.find((x) => x.id === id);
    return st ? `<a class="chip" href="#/lo-trinh/${esc(id)}"><span class="mono">${esc(id)}</span>${esc(st.name)}</a>` : "";
  }
  const PAGE_NAMES = { "lo-trinh": "Lộ trình", nhom: "Nhóm bài toán", "ky-nang": "Kỹ năng", "ma-tran": "Ma trận", "to-hop": "Tổ hợp", "tien-do": "Tiến độ" };
  function stepChip(id) {
    const step = STEP[id];
    return step ? `<a class="chip" href="#/lo-trinh/${esc(id)}"><span class="mono">${esc(id)}</span>${esc(step.title)}</a>` : "";
  }
  function readMore(page) {
    const keys = docsBy("page", page);
    return keys.length ? `<div class="read-more"><span>Đọc thêm:</span>${keys.map((k) => docLink(k)).join("")}</div>` : "";
  }

  // ───────────────────────── tính toán tiến độ ─────────────────────────
  const stepDone = (step) => step.skills.every(met);
  function stageStats(st) {
    const steps = st.steps || [];
    return { done: steps.filter(stepDone).length, total: steps.length };
  }
  function overall() {
    const total = D.skills.length * 3;
    const got = D.skills.reduce((a, s) => a + rank(s.id), 0);
    return { got, total };
  }

  // Lộ trình của một nhóm: 3 chặng theo quy tắc mức nhóm (01-kien-truc-ky-nang.md#muc-nhom).
  function groupPlan(gid) {
    const core = D.skills.filter((s) => s.used_by[gid] === "core").map((s) => s.id);
    const needed = D.skills.filter((s) => s.used_by[gid] === "needed").map((s) => s.id);
    const rules = [
      { key: "basic", title: "Đạt mức Cơ bản của nhóm", rule: "Mọi kỹ năng Cốt lõi ở mức Cơ bản", set: [[core, 1]] },
      { key: "intermediate", title: "Đạt mức Trung cấp của nhóm", rule: "Cốt lõi ở Trung cấp, Cần ở Cơ bản", set: [[core, 2], [needed, 1]] },
      { key: "advanced", title: "Đạt mức Nâng cao của nhóm", rule: "Cốt lõi ở Nâng cao, Cần ở Trung cấp", set: [[core, 3], [needed, 2]] },
    ];
    const prev = {};
    return rules.map((r) => {
      const target = { ...prev };
      for (const [ids, lv] of r.set) for (const id of ids) target[id] = Math.max(target[id] || 0, lv);
      // tiên quyết chưa nằm trong nhóm: cần ít nhất Cơ bản
      const stack = Object.keys(target);
      while (stack.length) {
        const id = stack.pop();
        for (const p of SK[id].prereqs) {
          if (!target[p]) {
            target[p] = 1;
            stack.push(p);
          }
        }
      }
      const items = Object.keys(target)
        .filter((id) => target[id] > (prev[id] || 0))
        .sort(byOrder)
        .map((id) => ({ id, level: LV[target[id] - 1], prereqOnly: !SK[id].used_by[gid] || SK[id].used_by[gid] === "minor" }));
      Object.assign(prev, target);
      const all = Object.keys(target).map((id) => ({ id, level: LV[target[id] - 1] }));
      return { ...r, items, all, reached: all.every(met) };
    });
  }
  function groupLevel(gid) {
    const plan = groupPlan(gid);
    let lvl = 0;
    for (let i = 0; i < plan.length; i++) {
      if (plan[i].reached) lvl = i + 1;
      else break;
    }
    return lvl;
  }

  // ───────────────────────── khối giao diện dùng chung ─────────────────────────
  function skillRow(item, opts = {}) {
    const s = SK[item.id];
    const done = met(item);
    const now = rank(item.id);
    const extra = item.level === "intermediate" ? `<div class="small" style="margin-top:4px"><strong>Đạt khi:</strong> ${md(s.done_when)}</div>` : "";
    const tag = opts.prereqOnly ? `<span class="badge">tiên quyết</span>` : "";
    return `<div class="skill-row ${done ? "done" : ""}">
      <div class="sr-title"><a href="#/ky-nang/${esc(s.id)}"><span class="mono">${esc(s.id)}</span> ${esc(s.name)}</a> ${lvBadge(item.level)} ${tag}
        ${now && !done ? `<span class="small muted">đang ở ${esc(D.levels[LV[now - 1]])}</span>` : ""}</div>
      <div class="sr-actions">${opts.noLearn ? "" : learnMini(s.id, item.level)}${toggle(s.id, item.level, done ? "Đã đạt" : "Đánh dấu đạt")}</div>
      <div class="sr-desc">${md(s.levels[item.level])}${extra}</div>
    </div>`;
  }

  // ───────────────────────── trang: tổng quan ─────────────────────────
  function pageHome() {
    const o = overall();
    const steps = ALL_STEPS.length;
    const top = [...D.skills].sort((a, b) => b.leverage - a.leverage || a.order - b.order).slice(0, 8);
    const famHtml = D.families
      .map(
        (f) => `<div class="card family"><h3>${esc(f.name)}</h3>
        <div class="row">${f.groups.map(groupLink).join("")}</div></div>`
      )
      .join("");
    const stageCards = STAGES.map((st) => {
      const ss = stageStats(st);
      return `<a class="card stage-card" href="#/lo-trinh/${esc(st.id)}" style="${stageColor(st.id)}">
        <span class="stage-id"><span class="stage-dot" style="background:var(--stage-color)"></span>Giai đoạn ${esc(st.id)} · ${esc(st.period)}</span>
        <h3>${esc(st.name)}</h3>
        <p>${md(st.goal)}</p>
        ${meter(ss.done, ss.total, `${ss.done}/${ss.total} bước`)}
      </a>`;
    }).join("");
    const next = ALL_STEPS.find((step) => !stepDone(step)) || ALL_STEPS[0];
    const nextDocs = next ? docsBy("step", next.id).sort(byKind) : [];
    const continueCard = next
      ? `<div class="card continue-card" style="${stageColor(next.stage)}">
        <div class="spread"><span class="stage-id"><span class="stage-dot" style="background:var(--stage-color)"></span>Tiếp tục học · Bước ${esc(next.id)}${next.week ? ` · tuần ${esc(next.week)}` : ""}</span>
          ${meter(next.skills.filter(met).length, next.skills.length, `${next.skills.filter(met).length}/${next.skills.length} kỹ năng`)}</div>
        <h3>${esc(next.title)}</h3>
        <p class="small muted">${md(next.do)}</p>
        <div class="row">${nextDocs.map(resLink).join("")}<a class="btn btn-sm" href="#/lo-trinh/${esc(next.id)}">Xem bước trong lộ trình →</a></div>
      </div>`
      : "";
    return {
      title: "Tổng quan",
      html: `
      <section class="hero">
        <h1>Lộ trình kỹ năng lập trình AI cho doanh nghiệp</h1>
        <p class="lead">Từ 8 nhóm bài toán AI mà doanh nghiệp cần đến ${D.skills.length} kỹ năng cụ thể — đi từng bước từ
        <strong>cơ bản</strong> đến <strong>nâng cao</strong>, biết kỹ năng nào dùng chung, kỹ năng nào riêng, và cách tiết kiệm token mà vẫn chính xác.</p>
        <div class="row">
          <a class="btn btn-primary" href="#/lo-trinh">Bắt đầu lộ trình</a>
          <a class="btn" href="#/nhom">Nhận diện bài toán trong 30 giây</a>
        </div>
      </section>
      ${continueCard}
      <div class="tiles">
        <div class="tile"><div class="tile-value">${D.groups.length}</div><div class="tile-label">nhóm bài toán</div></div>
        <div class="tile"><div class="tile-value">${D.skills.length}</div><div class="tile-label">kỹ năng · ${D.domains.length} mảng</div></div>
        <div class="tile"><div class="tile-value">${STAGES.length}</div><div class="tile-label">giai đoạn · ${steps} bước</div></div>
        <div class="tile"><div class="tile-value">${D.combinations.length}</div><div class="tile-label">tổ hợp dự án</div></div>
        <div class="tile"><div class="tile-value">${pct(o.got, o.total)}%</div><div class="tile-label">tiến độ của bạn</div></div>
      </div>

      <div class="section-title"><h2>Bốn giai đoạn</h2><a href="#/lo-trinh">Xem từng bước →</a></div>
      <div class="grid grid-4" style="margin-top:12px">${stageCards}</div>

      <div class="section-title"><h2>Hai họ bài toán</h2><a href="#/ma-tran">Mức chia sẻ kỹ năng →</a></div>
      <p class="muted">Nhóm cùng họ dùng chung nhiều kỹ năng; chuyển họ cần đi qua các kỹ năng <em>cầu nối</em>.</p>
      <div class="grid grid-2">${famHtml}</div>

      <div class="grid grid-2" style="margin-top:36px">
        <div class="card">
          <h3>Học gì trước? Kỹ năng đòn bẩy cao nhất</h3>
          <p class="small muted">Điểm = Σ (Cốt lõi 2, Cần 1) trên 8 nhóm — học một lần, dùng nhiều nơi.</p>
          <ul class="clean lev-list">${top
            .map(
              (s, i) =>
                `<li><span class="lev-rank">${i + 1}</span><a href="#/ky-nang/${esc(s.id)}"><span class="mono">${esc(s.id)}</span> ${esc(s.name)}</a><span class="lev-score">${s.leverage}</span></li>`
            )
            .join("")}</ul>
        </div>
        <div class="card">
          <div class="spread"><h3>Tài liệu</h3><a href="#/tai-lieu">Tất cả →</a></div>
          <ul class="list-dots">${D.meta.doc_sections
            .map((sec) => `<li><a href="#/tai-lieu/${esc(sec.id)}">${esc(sec.title)}</a> <span class="muted">· ${sec.items.length} tài liệu</span></li>`)
            .join("")}</ul>
        </div>
      </div>`,
    };
  }

  // ───────────────────────── trang: lộ trình ─────────────────────────
  function defaultStage() {
    const firstOpen = STAGES.find((st) => stageStats(st).done < stageStats(st).total);
    return (firstOpen || STAGES[0]).id;
  }

  function pageRoadmap(param) {
    let stageId = ui.stage || defaultStage();
    let focusStep = null;
    if (param) {
      const step = ALL_STEPS.find((s) => s.id === param);
      if (step) {
        stageId = step.stage;
        focusStep = step.id;
        ui.open.add(step.id);
      } else if (STAGES.some((s) => s.id === param)) {
        stageId = param;
      }
    }
    ui.stage = stageId;
    const st = STAGES.find((s) => s.id === stageId) || STAGES[0];
    const steps = st.steps || [];
    if (!steps.some((s) => ui.open.has(s.id))) {
      const first = steps.find((s) => !stepDone(s)) || steps[0];
      if (first) ui.open.add(first.id);
    }
    saveUI();

    const tabs = STAGES.map((s) => {
      const ss = stageStats(s);
      return `<button type="button" class="stage-tab" role="tab" data-action="stage" data-id="${esc(s.id)}" aria-selected="${s.id === st.id}" style="${stageColor(s.id)}">
        <span class="t1">${esc(s.id)} · ${esc(s.name)}</span>
        <span class="t2">${esc(s.period)}</span>
        ${meter(ss.done, ss.total)}
      </button>`;
    }).join("");

    const ss = stageStats(st);
    const stageGuides = docsBy("stage", st.id).filter((k) => kindOf(k) === "guide");
    const stageProjects = docsBy("stage", st.id).filter((k) => kindOf(k) === "project");
    const stepsHtml = steps
      .map((step) => {
        const open = ui.open.has(step.id);
        const done = step.skills.filter(met).length;
        const finished = done === step.skills.length;
        const week = step.week ? `Tuần ${esc(step.week)}` : "Linh hoạt";
        const stepDocs = docsBy("step", step.id).sort(byKind);
        const hasLesson = stepDocs.some((k) => kindOf(k) === "lesson");
        let learnBar;
        if (stepDocs.length) {
          learnBar = `<div class="learn-bar"><span class="learn-label">${ICON_BOOK}Học ngay</span>${stepDocs.map(resLink).join("")}</div>`;
        } else {
          const rel = docsForSkills(step.skills.map((it) => it.id)).slice(0, 6);
          learnBar = `<div class="learn-bar is-empty"><span class="learn-label">Chưa có bài học riêng</span>${
            rel.length ? `<span class="small muted">Tài liệu liên quan:</span>${rel.map(resLink).join("")}` : `<span class="small muted">Học theo mô tả từng kỹ năng bên dưới.</span>`
          }</div>`;
        }
        return `<li id="step-${esc(step.id)}">
          <span class="step-marker ${finished ? "done" : ""}" aria-hidden="true">${finished ? "✓" : esc(step.id)}</span>
          <div class="card step-card">
            <button type="button" class="step-head" data-action="step" data-id="${esc(step.id)}" aria-expanded="${open}" aria-controls="body-${esc(step.id)}">
              <span><span class="week">${esc(step.id)} · ${week}${hasLesson ? ` <span class="badge badge-lesson">${ICON_BOOK}Có bài học + lab</span>` : ""}</span><h3>${esc(step.title)}</h3></span>
              <span class="row" style="flex-wrap:nowrap">${meter(done, step.skills.length, `${done}/${step.skills.length} kỹ năng`)}${chev}</span>
            </button>
            ${
              open
                ? `<div class="step-body" id="body-${esc(step.id)}">
              ${learnBar}
              <dl class="kv"><dt>Việc cần làm</dt><dd>${md(step.do)}</dd><dt>Sản phẩm nộp</dt><dd>${md(step.deliverable)}</dd></dl>
              <div class="skill-rows">${step.skills.map((it) => skillRow(it, { noLearn: stepDocs.length > 0 })).join("")}</div>
            </div>`
                : ""
            }
          </div>
        </li>`;
      })
      .join("");

    let tracksHtml = "";
    if (st.tracks && st.tracks.length) {
      const sel = st.tracks.find((t) => t.id === ui.track) || null;
      tracksHtml = `
        <div class="section-title"><h2>Hướng chuyên sâu</h2><span class="small muted">Chọn 1–2 hướng sát nhu cầu công ty</span></div>
        <div class="track-picker" role="group" aria-label="Chọn hướng chuyên sâu">${st.tracks
          .map((t) => {
            const d = t.skills.filter(met).length;
            return `<button type="button" class="chip" data-action="track" data-id="${esc(t.id)}" aria-pressed="${sel && sel.id === t.id}">${esc(t.name)} <span class="mono">${d}/${t.skills.length}</span></button>`;
          })
          .join("")}</div>
        ${
          sel
            ? `<div class="card">
          <div class="spread"><h3 style="margin:0">${esc(sel.name)}</h3>${meter(sel.skills.filter(met).length, sel.skills.length)}</div>
          <dl class="kv"><dt>Nhóm</dt><dd class="row">${sel.groups.map(groupLink).join("")}</dd>
          <dt>Tổ hợp tiêu biểu</dt><dd class="row">${sel.combos.map((c) => `<a class="chip" href="#/to-hop/${esc(c)}"><span class="mono">${esc(c)}</span>${esc(CMB[c].name)}</a>`).join("")}</dd></dl>
          <div class="skill-rows">${[...sel.skills].sort((a, b) => byOrder(a.id, b.id)).map((it) => skillRow(it)).join("")}</div>
        </div>`
            : `<p class="muted">Chọn một hướng để xem kỹ năng và mức mục tiêu.</p>`
        }`;
    }

    const tbar = (D.roadmap.t_bar || [])
      .map(
        (r) => `<tr><td>${groupLink(r.group)}</td><td><div class="row">${r.skills.map((id) => skillLink(id)).join("")}</div></td><td class="muted">${esc(r.note)}</td></tr>`
      )
      .join("");
    const ongoing = (D.roadmap.ongoing || []).map((r) => `<li>${skillLink(r.id)} ${md(r.text)}</li>`).join("");

    return {
      title: `Lộ trình · Giai đoạn ${st.id}`,
      focus: focusStep ? `step-${focusStep}` : null,
      html: `
      <div class="page-head">
        <h1>Lộ trình theo bước</h1>
        <p>Mỗi bước có việc cần làm, sản phẩm phải nộp và kỹ năng cần đạt kèm <strong>mức mục tiêu</strong>. Kỹ năng tiên quyết luôn nằm ở bước trước.
        Đánh dấu khi bạn tự làm được trên dữ liệu thật và giải thích được cho người ngoài ngành.</p>
        ${readMore("lo-trinh")}
      </div>
      <div class="stage-tabs" role="tablist" aria-label="Giai đoạn">${tabs}</div>

      <section style="${stageColor(st.id)}">
        <div class="stage-summary">
          <div>
            <h2 style="margin-top:0">Giai đoạn ${esc(st.id)} · ${esc(st.name)} <span class="muted small nowrap">${esc(st.period)}</span></h2>
            <p>${md(st.goal)}</p>
            ${st.note ? `<p class="small muted">${md(st.note)}</p>` : ""}
            <dl class="kv"><dt>Cài đặt</dt><dd><code>${esc(st.setup)}</code> <span class="small">${docLink("setup", "hướng dẫn setup")}</span></dd>
            ${stageGuides.length ? `<dt>Hướng dẫn</dt><dd class="row">${stageGuides.map(resLink).join("")}</dd>` : ""}
            <dt>Đọc</dt><dd>${esc(st.book)}</dd>
            ${st.project ? `<dt>Dự án</dt><dd class="row">${groupLink(st.project)}${stageProjects.map(resLink).join("")}</dd>` : ""}</dl>
          </div>
          <div>
            <div class="milestone"><strong>Mốc cuối giai đoạn</strong>${md(st.milestone)}</div>
            <div style="margin-top:12px">${meter(ss.done, ss.total, `${ss.done}/${ss.total} bước hoàn thành`)}</div>
            <div class="row" style="margin-top:12px">
              <button type="button" class="btn btn-sm" data-action="expand-all">Mở tất cả bước</button>
              <button type="button" class="btn btn-sm btn-ghost" data-action="collapse-all">Thu gọn</button>
            </div>
          </div>
        </div>
        <ol class="timeline">${stepsHtml}</ol>
      </section>
      ${tracksHtml}

      <div class="section-title"><h2>Xuyên suốt mọi giai đoạn</h2></div>
      <div class="card">
        <h3>Thanh ngang chữ T — dựng baseline cho cả 8 nhóm</h3>
        <p class="small muted">Ngoài kỹ năng nền tảng, mỗi nhóm cần thêm các kỹ năng sau ở mức Cơ bản.</p>
        <div class="table-wrap"><table><thead><tr><th>Nhóm</th><th>Kỹ năng</th><th>Gợi ý baseline</th></tr></thead><tbody>${tbar}</tbody></table></div>
        <h3 style="margin-top:20px">Thói quen</h3>
        <ul class="list-dots">${ongoing}</ul>
      </div>`,
    };
  }

  // ───────────────────────── trang: danh sách kỹ năng ─────────────────────────
  function filteredSkills() {
    const q = fold(ui.q.trim());
    let list = D.skills.filter((s) => {
      if (ui.domain && s.domain !== ui.domain) return false;
      if (ui.tier && s.tier !== ui.tier) return false;
      if (ui.group && !["core", "needed"].includes(s.used_by[ui.group])) return false;
      if (q) {
        const hay = fold([s.id, s.name, s.summary, s.tools.join(" "), LV.map((l) => s.levels[l]).join(" ")].join(" "));
        return q.split(/\s+/).every((w) => hay.includes(w));
      }
      return true;
    });
    if (ui.sort === "leverage") list = [...list].sort((a, b) => b.leverage - a.leverage || a.order - b.order);
    else if (ui.sort === "progress") list = [...list].sort((a, b) => rank(a.id) - rank(b.id) || a.order - b.order);
    else list = [...list].sort((a, b) => D.skills.indexOf(a) - D.skills.indexOf(b));
    return list;
  }
  function skillCard(s) {
    const strip = D.groups
      .map((g) => {
        const rel = s.used_by[g.id];
        return `<span class="${rel || ""}" title="Nhóm ${esc(groupNo(g.id))} ${esc(g.name)}: ${esc(rel ? D.relevance[rel] : "không liên quan")}">${esc(groupNo(g.id))}</span>`;
      })
      .join("");
    return `<a class="card skill-card" href="#/ky-nang/${esc(s.id)}">
      <div class="sc-top"><span class="mono">${esc(s.id)}</span>${lvBadge(rank(s.id))}</div>
      <h3>${esc(s.name)}</h3>
      <p>${esc(s.summary)}</p>
      <div class="row"><span class="badge badge-tier">${esc(D.tiers[s.tier].name)}</span><span class="badge">đòn bẩy ${s.leverage}</span></div>
      <div class="use-strip" aria-label="Mức cần ở 8 nhóm">${strip}</div>
    </a>`;
  }
  function renderSkillResults() {
    const box = document.getElementById("skill-results");
    if (!box) return;
    const list = filteredSkills();
    box.innerHTML = `<div class="result-count">${list.length} kỹ năng</div>
      <div class="skill-grid">${list.map(skillCard).join("") || `<p class="muted">Không có kỹ năng phù hợp bộ lọc.</p>`}</div>`;
  }
  function pageSkills() {
    const opt = (v, label, cur) => `<option value="${esc(v)}" ${v === cur ? "selected" : ""}>${esc(label)}</option>`;
    return {
      title: "Kỹ năng",
      after: renderSkillResults,
      html: `
      <div class="page-head"><h1>${D.skills.length} kỹ năng</h1>
        <p>Mỗi kỹ năng có 3 mức Cơ bản → Trung cấp → Nâng cao. Dải số 1–8 ở cuối thẻ cho biết mức cần ở từng nhóm bài toán
        (ô đậm = Cốt lõi, ô nhạt = Cần).</p>${readMore("ky-nang")}</div>
      <div class="filters">
        <input class="search" type="search" placeholder="Tìm theo tên, mã, công cụ… (gõ không dấu cũng được)" value="${esc(ui.q)}" data-filter="q" aria-label="Tìm kỹ năng">
        <select data-filter="domain" aria-label="Mảng">${opt("", "Mọi mảng", ui.domain)}${D.domains.map((d) => opt(d.code, `${d.code} · ${d.name}`, ui.domain)).join("")}</select>
        <select data-filter="tier" aria-label="Tầng">${opt("", "Mọi tầng", ui.tier)}${Object.entries(D.tiers).map(([k, t]) => opt(k, t.name, ui.tier)).join("")}</select>
        <select data-filter="group" aria-label="Nhóm bài toán">${opt("", "Mọi nhóm", ui.group)}${D.groups.map((g) => opt(g.id, `Nhóm ${groupNo(g.id)} · ${g.short}`, ui.group)).join("")}</select>
        <select data-filter="sort" aria-label="Sắp xếp">${opt("order", "Theo mảng", ui.sort)}${opt("leverage", "Đòn bẩy cao trước", ui.sort)}${opt("progress", "Chưa học trước", ui.sort)}</select>
      </div>
      <div id="skill-results"></div>`,
    };
  }

  // ───────────────────────── trang: chi tiết kỹ năng ─────────────────────────
  function pageSkill(id) {
    const s = SK[id];
    if (!s) return pageNotFound();
    const d = DOM[s.domain];
    const now = rank(id);
    const uses = ["core", "needed", "minor"]
      .map((rel) => {
        const gs = D.groups.filter((g) => s.used_by[g.id] === rel);
        return gs.length ? `<dt>${SYM[rel]} ${esc(D.relevance[rel])}</dt><dd class="row">${gs.map((g) => groupLink(g.id)).join("")}</dd>` : "";
      })
      .join("");
    const ladder = LV.map((l, i) => {
      const reached = now >= i + 1;
      return `<div class="rung ${reached ? "reached" : ""}">
        <div class="rung-head">${lvBadge(l)}<span class="small muted">Bước ${i + 1}/3</span></div>
        <p>${md(s.levels[l])}</p>
        ${l === "intermediate" ? `<p class="small"><strong>Đạt khi:</strong> ${md(s.done_when)}</p>` : ""}
        ${toggle(id, l, reached ? `Đã đạt ${D.levels[l]}` : `Đánh dấu đạt ${D.levels[l]}`)}
      </div>`;
    }).join("");
    const combos = D.combinations.filter((c) => c.skills.includes(id) || (c.glue || []).includes(id));
    const learnCard = skillLearnCard(s, now);
    const places = (s.placements || [])
      .map((p) => {
        // where: id bước ("A3"), "<giai đoạn>:<hướng>" ("C:risk"), "T:<nhóm>" hoặc "ongoing"
        const step = ALL_STEPS.find((x) => x.id === p.where);
        const [head, track] = p.where.split(":");
        let href = "#/lo-trinh";
        let attr = "";
        if (step) href = `#/lo-trinh/${esc(step.id)}`;
        else if (track && STAGES.some((st) => st.id === head)) {
          href = `#/lo-trinh/${esc(head)}`;
          attr = ` data-track="${esc(track)}"`;
        }
        return `<li><a href="${href}"${attr}>${esc(p.label)}</a> — ${lvBadge(p.level)}</li>`;
      })
      .join("");
    return {
      title: `${s.id} · ${s.name}`,
      html: `
      <div class="breadcrumb"><a href="#/ky-nang">Kỹ năng</a> / ${esc(d.code)} · ${esc(d.name)}</div>
      <div class="page-head">
        <div class="spread"><h1>${esc(s.name)}</h1>${lvBadge(now)}</div>
        <p>${esc(s.summary)}</p>
        <div class="row">
          <span class="chip"><span class="mono">${esc(s.id)}</span>${esc(d.name)}</span>
          <span class="badge badge-tier" title="${esc(D.tiers[s.tier].desc)}">${esc(D.tiers[s.tier].name)}</span>
          <span class="badge">đòn bẩy ${s.leverage}</span>
        </div>
      </div>

      ${learnCard}

      <h2>Từ cơ bản đến nâng cao</h2>
      <div class="ladder">${ladder}</div>
      ${s.efficiency_note ? `<div class="milestone" style="--stage-color: var(--accent); margin-top:16px"><strong>Token & độ chính xác</strong>${md(s.efficiency_note)}</div>` : ""}

      <div class="grid grid-2" style="margin-top:24px">
        <div class="card">
          <h3>Dùng cho nhóm bài toán</h3>
          <dl class="kv">${uses}</dl>
        </div>
        <div class="card">
          <h3>Trong lộ trình</h3>
          <ul class="list-dots">${places || "<li class='muted'>—</li>"}</ul>
        </div>
        <div class="card">
          <h3>Học trước (tiên quyết)</h3>
          <div class="row">${s.prereqs.map((p) => skillLink(p)).join("") || "<span class='muted'>Không cần — có thể bắt đầu ngay.</span>"}</div>
          <h3 style="margin-top:16px">Mở khóa</h3>
          <div class="row">${s.unlocks.map((p) => skillLink(p)).join("") || "<span class='muted'>—</span>"}</div>
        </div>
        <div class="card">
          <h3>Công cụ tiêu biểu</h3>
          <div class="row">${s.tools.map((t) => `<span class="chip">${esc(t)}</span>`).join("")}</div>
          ${
            combos.length
              ? `<h3 style="margin-top:16px">Có trong tổ hợp</h3><div class="row">${combos
                  .map((c) => `<a class="chip" href="#/to-hop/${esc(c.id)}"><span class="mono">${esc(c.id)}</span>${esc(c.name)}</a>`)
                  .join("")}</div>`
              : ""
          }
        </div>
      </div>`,
    };
  }

  // Thẻ "Học kỹ năng này": bài học/lab/tài liệu theo mức, nút học ngay cho mức kế tiếp, dự án áp dụng.
  function skillLearnCard(s, now) {
    const res = skillResources(s.id).sort((a, b) => (RANK[a.level] || 9) - (RANK[b.level] || 9) || byKind(a.key, b.key));
    const own = new Set(res.map((r) => r.key));
    const stagesOf = uniq((s.placements || []).map((p) => (STEP[p.where] || {}).stage).filter(Boolean));
    const projects = uniq(stagesOf.flatMap((st) => docsBy("stage", st))).filter((k) => kindOf(k) === "project" && !own.has(k));
    const extra = docsBy("domain", s.domain).filter((k) => !own.has(k));
    const target = LV[Math.min(now, 2)];
    const best = bestResource(s.id, target);
    const steps = (s.placements || []).filter((p) => STEP[p.where]).map((p) => stepChip(p.where));
    const list = res.length
      ? `<ul class="res-list">${res
          .map((r) => `<li>${resLink(r.key)}<span class="res-meta">${r.level ? lvBadge(r.level) : `<span class="small muted">liên quan</span>`}${r.step ? `<a class="small" href="#/lo-trinh/${esc(r.step)}">bước ${esc(r.step)}</a>` : ""}</span></li>`)
          .join("")}</ul>`
      : `<p class="muted small">Chưa có bài học riêng cho kỹ năng này — học theo mô tả 3 mức bên dưới ở bước: <span class="row" style="display:inline-flex">${steps.join("") || "—"}</span></p>`;
    return `<div class="card learn-card" id="hoc">
      <div class="spread"><h3 style="margin:0">${ICON_BOOK} Học kỹ năng này</h3>
        ${best ? `<a class="btn btn-primary btn-sm" href="${esc(docHref(docOf(best.key).path))}">${ICON_BOOK}Học ngay: ${esc(docOf(best.key).title)}</a>` : ""}</div>
      ${list}
      ${projects.length ? `<div class="res-row"><span class="small muted">Áp dụng trong dự án</span>${projects.map(resLink).join("")}</div>` : ""}
      ${extra.length ? `<div class="res-row"><span class="small muted">Đọc thêm</span>${extra.map(resLink).join("")}</div>` : ""}
    </div>`;
  }

  // ───────────────────────── trang: nhóm bài toán ─────────────────────────
  function quizHtml() {
    const qs = D.identify.questions || [];
    const qz = ui.quiz;
    const bars = qs.map((_, i) => `<span class="${i < qz.i || qz.result ? "on" : ""}"></span>`).join("");
    if (qz.result) {
      const g = GR[qz.result];
      return `<div class="quiz"><div class="quiz-progress">${bars}</div>
        <div class="quiz-result"><div class="small muted">Bài toán của bạn thuộc</div>
          <h3 style="margin:4px 0">Nhóm ${esc(groupNo(g.id))} · ${esc(g.name)}</h3><p class="small" style="margin:0">“${esc(g.question)}”</p></div>
        <p class="small muted">${esc(D.identify.note || "")}</p>
        <div class="row"><a class="btn btn-primary" href="#/nhom/${esc(g.id)}">Xem lộ trình của nhóm</a><button type="button" class="btn" data-action="quiz-reset">Làm lại</button></div></div>`;
    }
    const q = qs[qz.i];
    return `<div class="quiz"><div class="quiz-progress">${bars}</div>
      <div class="small muted">Câu ${qz.i + 1}/${qs.length} — dừng ở câu trả lời “Có” đầu tiên</div>
      <p class="quiz-q">${esc(q.q)}</p>
      <div class="row"><button type="button" class="btn btn-primary" data-action="quiz" data-answer="yes">Có</button>
      <button type="button" class="btn" data-action="quiz" data-answer="no">Không</button>
      ${qz.i > 0 ? `<button type="button" class="btn btn-ghost" data-action="quiz-reset">Làm lại</button>` : ""}</div></div>`;
  }
  function pageGroups() {
    const blocks = Object.entries(D.blocks)
      .map(([b, name]) => {
        const gs = D.groups.filter((g) => g.block === b);
        return gs
          .map((g) => {
            const lvl = groupLevel(g.id);
            return `<a class="card group-card" href="#/nhom/${esc(g.id)}">
            <span class="group-num">Nhóm ${esc(groupNo(g.id))} · Khối ${esc(b)} ${esc(name)}</span>
            <h3 style="margin:0">${esc(g.name)}</h3>
            <p class="q">“${esc(g.question)}”</p>
            <div class="row" style="margin-top:auto"><span class="small muted">Mức của bạn:</span>${lvBadge(lvl)}${
              groupDocs(g.id).projects.length ? `<span class="badge badge-lesson">${ICON_BOOK}Có dự án</span>` : ""
            }</div>
          </a>`;
          })
          .join("");
      })
      .join("");
    return {
      title: "Nhóm bài toán",
      html: `
      <div class="page-head"><h1>8 nhóm bài toán AI trong doanh nghiệp</h1>
        <p>Phân loại theo <strong>đầu ra mà nghiệp vụ cần</strong>. Mỗi nhóm có lộ trình riêng từ mức Cơ bản đến Nâng cao, tính từ các kỹ năng Cốt lõi và Cần của nhóm.</p>${readMore("nhom")}</div>
      <div class="card" id="quiz">
        <h3>Nhận diện bài toán trong 30 giây</h3>
        <div id="quiz-box">${quizHtml()}</div>
      </div>
      <div class="grid grid-3" style="margin-top:24px">${blocks}</div>`,
    };
  }

  // Dự án và tài liệu của một nhóm: khai báo trực tiếp (groups) hoặc qua tổ hợp có nhóm (combos).
  function groupDocs(gid) {
    const combos = D.combinations.filter((c) => c.groups.includes(gid)).map((c) => c.id);
    const keys = uniq([...docsBy("group", gid), ...combos.flatMap((cid) => docsBy("combo", cid))]);
    return {
      projects: keys.filter((k) => ["project", "report"].includes(kindOf(k))),
      docs: keys.filter((k) => !["project", "report"].includes(kindOf(k))).sort(byKind),
    };
  }
  function groupLearnCard(g) {
    const { projects, docs } = groupDocs(g.id);
    const stages = STAGES.filter((st) => st.project === g.id);
    const stageLine = stages
      .map((st) => {
        const guide = docsBy("stage", st.id).filter((k) => kindOf(k) === "guide");
        return `<p style="margin:0">Giai đoạn <a href="#/lo-trinh/${esc(st.id)}">${esc(st.id)} · ${esc(st.name)}</a> học trọn bằng dự án của nhóm này.</p>${
          guide.length ? `<div class="res-row">${guide.map(resLink).join("")}</div>` : ""
        }`;
      })
      .join("");
    return `<div class="card learn-card" id="hoc">
      <h3 style="margin:0">${ICON_BOOK} Học và thực hành nhóm này</h3>
      ${stageLine}
      ${projects.length ? `<div class="res-row"><span class="small muted">Dự án</span>${projects.map(resLink).join("")}</div>` : `<p class="small muted" style="margin:0">Dự án luyện tập dự kiến: ${md(g.practice_project)}</p>`}
      ${docs.length ? `<div class="res-row"><span class="small muted">Tài liệu và lab</span>${docs.map(resLink).join("")}</div>` : ""}
    </div>`;
  }

  function pageGroup(gid) {
    const g = GR[gid];
    if (!g) return pageNotFound();
    const plan = groupPlan(gid);
    const lvl = groupLevel(gid);
    const flow = [
      ["Đầu vào", g.flow.input],
      ["Kỹ thuật chính", g.flow.technique],
      ["Đầu ra", g.flow.output],
      ["Quyết định kinh doanh", g.flow.decision],
    ]
      .map(([k, v]) => `<div class="flow-step"><strong>${esc(k)}</strong>${md(v)}</div>`)
      .join("");
    const keys = plan.map((p) => `${gid}:${p.key}`);
    if (!keys.some((k) => ui.open.has(k))) {
      const first = plan.find((p) => !p.reached) || plan[0];
      ui.open.add(`${gid}:${first.key}`);
    }
    const planHtml = plan
      .map((p, i) => {
        const done = p.all.filter(met).length;
        const key = `${gid}:${p.key}`;
        const open = ui.open.has(key);
        return `<div class="path-stage">
          <button type="button" class="path-stage-head" data-action="step" data-id="${esc(key)}" aria-expanded="${open}">
            <span><span class="small muted">Chặng ${i + 1}/3 · ${esc(p.rule)} · ${p.items.length} mục tiêu mới</span><h3>${esc(p.title)}</h3></span>
            <span class="row" style="flex-wrap:nowrap"><span style="min-width:180px">${meter(done, p.all.length, p.reached ? "Đã đạt" : `${done}/${p.all.length} mục tiêu`)}</span>${chev}</span>
          </button>
          ${
            open
              ? `<div class="path-stage-body"><div class="skill-rows">${
                  p.items.map((it) => skillRow(it, { prereqOnly: it.prereqOnly })).join("") || "<p class='muted'>Không có mục mới ở chặng này.</p>"
                }</div></div>`
              : ""
          }
        </div>`;
      })
      .join("");
    const combos = D.combinations.filter((c) => c.groups.includes(gid));
    const tracks = STAGES.flatMap((st) => (st.tracks || []).filter((t) => t.groups.includes(gid)));
    return {
      title: `Nhóm ${groupNo(gid)} · ${g.name}`,
      html: `
      <div class="breadcrumb"><a href="#/nhom">Nhóm bài toán</a> / Khối ${esc(g.block)} · ${esc(D.blocks[g.block])}</div>
      <div class="page-head">
        <div class="spread"><h1>Nhóm ${esc(groupNo(gid))} · ${esc(g.name)}</h1><span class="group-level"><span class="small muted">Mức của bạn</span>${lvBadge(lvl)}</span></div>
        <p style="font-size:1.1rem">“${esc(g.question)}”</p>
        <p class="small">Ví dụ: ${esc(g.examples.join(", "))}.</p>
      </div>
      <div class="flow">${flow}</div>
      ${groupLearnCard(g)}

      <div class="grid grid-2" style="margin-top:20px">
        <div class="card"><h3>Mức năng lực của nhóm</h3>
          <dl class="kv">${LV.map((l) => `<dt>${lvBadge(l, false)}</dt><dd>${md(g.levels[l])}</dd>`).join("")}</dl></div>
        <div class="card"><dl class="kv">
          <dt>Metric</dt><dd>${md(g.metrics)}</dd>
          <dt>Công cụ</dt><dd>${esc(g.tools.join(", "))}</dd>
          <dt>Bẫy</dt><dd>${md(g.pitfalls)}</dd>
          <dt>Dự án</dt><dd>${md(g.practice_project)}</dd>
          ${g.principle ? `<dt>Nguyên tắc</dt><dd>${md(g.principle)}</dd>` : ""}
        </dl></div>
      </div>

      <div class="section-title"><h2>Lộ trình của nhóm: Cơ bản → Trung cấp → Nâng cao</h2></div>
      <p class="muted">Mỗi chặng chỉ liệt kê mục tiêu <em>mới</em> so với chặng trước, theo thứ tự đã tôn trọng tiên quyết.
      Kỹ năng gắn nhãn “tiên quyết” không thuộc nhóm nhưng cần học trước.</p>
      ${planHtml}

      ${
        tracks.length || combos.length
          ? `<div class="section-title"><h2>Liên quan</h2></div><div class="card"><dl class="kv">
        ${tracks.length ? `<dt>Hướng chuyên sâu</dt><dd class="row">${tracks.map((t) => `<a class="chip" href="#/lo-trinh/C" data-track="${esc(t.id)}">${esc(t.name)}</a>`).join("")}</dd>` : ""}
        ${combos.length ? `<dt>Tổ hợp</dt><dd class="row">${combos.map((c) => `<a class="chip" href="#/to-hop/${esc(c.id)}"><span class="mono">${esc(c.id)}</span>${esc(c.name)}</a>`).join("")}</dd>` : ""}
      </dl></div>`
          : ""
      }`,
    };
  }

  // ───────────────────────── trang: ma trận ─────────────────────────
  const SEQ = ["--seq-100", "--seq-200", "--seq-300", "--seq-400", "--seq-500", "--seq-600", "--seq-700"];
  function pageMatrix() {
    const gs = D.groups;
    const doms = ui.matrixDomain ? D.domains.filter((d) => d.code === ui.matrixDomain) : D.domains;
    const head = `<tr><th>Kỹ năng</th><th>Tầng</th>${gs.map((g) => `<th class="c" title="${esc(g.name)}">${esc(groupNo(g.id))}<br>${esc(g.short)}</th>`).join("")}</tr>`;
    const body = doms
      .map((d) => {
        const rows = D.skills
          .filter((s) => s.domain === d.code)
          .map(
            (s) => `<tr><td><a href="#/ky-nang/${esc(s.id)}"><span class="mono">${esc(s.id)}</span> ${esc(s.name)}</a></td>
            <td class="small muted nowrap">${esc(D.tiers[s.tier].name)}</td>
            ${gs.map((g) => {
              const rel = s.used_by[g.id];
              return `<td class="c" title="${esc(rel ? D.relevance[rel] : "Không liên quan")}">${rel ? SYM[rel] : ""}</td>`;
            }).join("")}</tr>`
          )
          .join("");
        return `<tr><td class="domain-row" colspan="${gs.length + 2}">${esc(d.code)} · ${esc(d.name)}</td></tr>${rows}`;
      })
      .join("");

    // bản đồ nhiệt mức chia sẻ: ô ngoài đường chéo theo thang tuần tự; đường chéo = tổng của nhóm
    const off = [];
    gs.forEach((a) => gs.forEach((b) => a.id !== b.id && off.push(D.sharing[a.id][b.id])));
    const lo = Math.min(...off);
    const hi = Math.max(...off);
    const heatRows = gs
      .map((a) => {
        const cells = gs
          .map((b) => {
            const v = D.sharing[a.id][b.id];
            if (a.id === b.id) {
              const tip = `Nhóm ${groupNo(a.id)} ${a.name}: tổng ${v} kỹ năng Cốt lõi/Cần`;
              return `<td class="diag" tabindex="0" data-tip="${esc(tip)}" aria-label="${esc(tip)}">${v}</td>`;
            }
            const step = hi === lo ? 3 : Math.round(((v - lo) / (hi - lo)) * (SEQ.length - 1));
            const tip = `Nhóm ${groupNo(a.id)} ${a.name} ↔ Nhóm ${groupNo(b.id)} ${b.name}: ${v} kỹ năng chung`;
            return `<td class="${step >= 3 ? "ink-light" : "ink-dark"}" style="background:var(${SEQ[step]})" tabindex="0" data-tip="${esc(tip)}" aria-label="${esc(tip)}">${v}</td>`;
          })
          .join("");
        return `<tr><th scope="row">${esc(groupNo(a.id))} · ${esc(a.short)}</th>${cells}</tr>`;
      })
      .join("");

    const domainChips = [`<button type="button" class="chip" data-action="matrix-domain" data-id="" aria-pressed="${!ui.matrixDomain}">Tất cả</button>`]
      .concat(D.domains.map((d) => `<button type="button" class="chip" data-action="matrix-domain" data-id="${esc(d.code)}" aria-pressed="${ui.matrixDomain === d.code}">${esc(d.code)}</button>`))
      .join("");
    return {
      title: "Ma trận",
      html: `
      <div class="page-head"><h1>Ma trận kỹ năng × nhóm bài toán</h1>
        <p>Kỹ năng nào cần cho nhóm nào, ở mức nào. Tầng được tính tự động từ mức sử dụng.</p>${readMore("ma-tran")}</div>
      <div class="legend"><span>● Cốt lõi</span><span>◐ Cần</span><span>○ Ít</span><span>ô trống = không liên quan</span></div>
      <div class="row" style="margin-bottom:12px">${domainChips}</div>
      <div class="table-wrap" style="max-height:70vh"><table class="matrix"><thead>${head}</thead><tbody>${body}</tbody></table></div>

      <div class="section-title"><h2>Mức chia sẻ kỹ năng giữa các nhóm</h2></div>
      <p class="muted">Số kỹ năng ở mức Cốt lõi/Cần cho <strong>cả hai</strong> nhóm. Ô càng đậm, chuyển giữa hai nhóm càng tận dụng được nhiều kỹ năng.
      Đường chéo (viền nét đứt) là tổng số kỹ năng Cốt lõi/Cần của chính nhóm đó.</p>
      <div class="table-wrap" style="padding:12px">
        <table class="heat"><thead><tr><th></th>${gs.map((g) => `<th class="c">${esc(groupNo(g.id))}</th>`).join("")}</tr></thead><tbody>${heatRows}</tbody></table>
        <div class="heat-scale"><span>${lo}</span><span class="bar" aria-hidden="true"></span><span>${hi} kỹ năng chung</span></div>
      </div>`,
    };
  }

  // ───────────────────────── trang: tổ hợp ─────────────────────────
  function pageCombos(focus) {
    const cards = D.combinations
      .map((c) => {
        const glue = new Set(c.glue || []);
        const ids = [...new Set([...c.skills, ...(c.glue || [])])];
        return `<article class="card" id="combo-${esc(c.id)}">
          <div class="spread"><div><span class="group-num">${esc(c.id)}</span><h3 style="margin:2px 0 0">${esc(c.name)}</h3></div>
          ${meter(ids.filter((id) => rank(id) > 0).length, ids.length, `${ids.filter((id) => rank(id) > 0).length}/${ids.length} kỹ năng đã học`)}</div>
          <div class="combo-flow" style="margin:12px 0">${c.groups.map(groupLink).join(`<span class="arrow" aria-hidden="true">→</span>`)}</div>
          <p>${md(c.flow)}</p>
          <dl class="kv">
            <dt>Ví dụ</dt><dd>${esc(c.examples.join(", "))}</dd>
            <dt>Kỹ năng</dt><dd class="row">${ids.map((id) => skillLink(id) + (glue.has(id) ? `<span class="badge" title="Kỹ năng keo ở điểm nối">🔗 keo</span>` : "")).join("")}</dd>
            <dt>Bẫy khi ghép</dt><dd><ul class="list-dots">${c.pitfalls.map((p) => `<li>${md(p)}</li>`).join("")}</ul></dd>
            <dt>Metric end-to-end</dt><dd>${md(c.end_to_end_metric)}</dd>
            ${docsBy("combo", c.id).length ? `<dt>Dự án</dt><dd class="row">${docsBy("combo", c.id).map(resLink).join("")}</dd>` : ""}
          </dl>
        </article>`;
      })
      .join("");
    return {
      title: "Tổ hợp",
      focus: focus ? `combo-${focus}` : null,
      html: `
      <div class="page-head"><h1>Tổ hợp — dự án ghép nhiều nhóm</h1>
        <p>Dự án thật hiếm khi thuộc một nhóm. Mỗi tổ hợp nêu luồng giữa các nhóm, kỹ năng cần, kỹ năng <strong>keo</strong> ở điểm nối,
        bẫy khi ghép và metric đo từ đầu đến cuối.</p>${readMore("to-hop")}</div>
      ${cards}`,
    };
  }

  // ───────────────────────── trang: tiến độ ─────────────────────────
  function pageProgress() {
    const o = overall();
    const byDomain = D.domains
      .map((d) => {
        const ss = D.skills.filter((s) => s.domain === d.code);
        const got = ss.reduce((a, s) => a + rank(s.id), 0);
        return `<tr><td>${esc(d.code)} · ${esc(d.name)}</td><td>${meter(got, ss.length * 3, `${got}/${ss.length * 3} mức`)}</td></tr>`;
      })
      .join("");
    const byStage = STAGES.map((st) => {
      const ss = stageStats(st);
      return `<tr><td><a href="#/lo-trinh/${esc(st.id)}">${esc(st.id)} · ${esc(st.name)}</a></td><td>${meter(ss.done, ss.total, `${ss.done}/${ss.total} bước`)}</td></tr>`;
    }).join("");
    const byGroup = D.groups
      .map((g) => `<tr><td><a href="#/nhom/${esc(g.id)}">${esc(groupNo(g.id))} · ${esc(g.name)}</a></td><td>${lvBadge(groupLevel(g.id))}</td></tr>`)
      .join("");
    const learned = D.skills.filter((s) => rank(s.id) > 0).length;
    return {
      title: "Tiến độ",
      html: `
      <div class="page-head"><h1>Tiến độ của bạn</h1>
        <p>Tiến độ lưu trong trình duyệt này. Dùng <strong>Xuất file</strong> để sao lưu, chuyển máy hoặc gửi cho người hướng dẫn.</p>${readMore("tien-do")}</div>
      <div class="tiles" style="margin-top:0">
        <div class="tile"><div class="tile-value">${pct(o.got, o.total)}%</div><div class="tile-label">${o.got}/${o.total} mức kỹ năng</div></div>
        <div class="tile"><div class="tile-value">${learned}</div><div class="tile-label">kỹ năng đã bắt đầu</div></div>
        <div class="tile"><div class="tile-value">${ALL_STEPS.filter(stepDone).length}/${ALL_STEPS.length}</div><div class="tile-label">bước lộ trình xong</div></div>
        <div class="tile"><div class="tile-value">${D.groups.filter((g) => groupLevel(g.id) > 0).length}/${D.groups.length}</div><div class="tile-label">nhóm đạt ≥ Cơ bản</div></div>
      </div>
      <div class="row" style="margin-top:16px">
        <button type="button" class="btn btn-primary" data-action="export">Xuất file tiến độ</button>
        <button type="button" class="btn" data-action="import">Nhập file tiến độ</button>
        <button type="button" class="btn btn-ghost" data-action="reset">Xóa tiến độ</button>
        <input class="file-input" type="file" accept="application/json,.json" id="import-file">
      </div>
      <div class="grid grid-2" style="margin-top:24px">
        <div><h3>Theo giai đoạn</h3><div class="table-wrap"><table class="progress-table"><tbody>${byStage}</tbody></table></div>
          <h3 style="margin-top:20px">Mức theo nhóm bài toán</h3><div class="table-wrap"><table><tbody>${byGroup}</tbody></table></div></div>
        <div><h3>Theo mảng kỹ năng</h3><div class="table-wrap"><table class="progress-table"><tbody>${byDomain}</tbody></table></div></div>
      </div>`,
    };
  }

  // ───────────────────────── trang: tài liệu ─────────────────────────
  function docCard(key) {
    const d = docOf(key);
    const rel = (D.learn.docs || {})[key] || { skills: [], groups: [], combos: [], domains: [], pages: [] };
    const chips = [];
    if (rel.step) chips.push(stepChip(rel.step));
    else if (rel.stage) chips.push(`<a class="chip" href="#/lo-trinh/${esc(rel.stage)}">Giai đoạn ${esc(rel.stage)}</a>`);
    const skills = rel.skills.slice(0, 4).map((x) => `<a class="chip chip-sm ${rank(x.id) ? "done" : ""}" href="#/ky-nang/${esc(x.id)}" title="${esc(SK[x.id].name)}"><span class="mono">${esc(x.id)}</span></a>`);
    if (rel.skills.length > 4) skills.push(`<span class="small muted">+${rel.skills.length - 4}</span>`);
    chips.push(...skills, ...rel.groups.map(groupLink), ...rel.combos.map((cid) => `<a class="chip" href="#/to-hop/${esc(cid)}"><span class="mono">${esc(cid)}</span></a>`));
    chips.push(...(rel.domains || []).map((code) => `<a class="chip" href="#/ky-nang" data-domain="${esc(code)}"><span class="mono">${esc(code)}</span>${esc(DOM[code].name)}</a>`));
    chips.push(...(rel.pages || []).map((pg) => `<a class="chip" href="#/${esc(pg)}">→ ${esc(PAGE_NAMES[pg] || pg)}</a>`));
    return `<article class="card doc-card doc-${esc(d.kind)}">
      <div class="spread"><span class="res-kind">${esc(KIND[d.kind] || KIND.doc)}</span>${d.tag ? `<span class="badge">${esc(d.tag)}</span>` : ""}</div>
      <h3><a class="stretched" href="${esc(docHref(d.path))}">${esc(d.title)}</a></h3>
      <p>${esc(d.desc)}</p>
      ${chips.length ? `<div class="row doc-rel">${chips.join("")}</div>` : ""}
      <span class="mono doc-path">${esc(d.path)}</span>
    </article>`;
  }

  function pageDocs(param) {
    const sections = D.meta.doc_sections;
    const jump = sections
      .map((sec) => `<a class="chip" href="#/tai-lieu/${esc(sec.id)}">${esc(sec.title)} <span class="mono">${sec.items.length}</span></a>`)
      .join("");
    const body = sections
      .map(
        (sec) => `<section class="doc-section" id="docs-${esc(sec.id)}">
          <div class="section-title"><h2>${esc(sec.title)}</h2></div>
          <p class="muted">${esc(sec.desc)}</p>
          <div class="grid grid-2">${sec.items.map(docCard).join("")}</div>
        </section>`
      )
      .join("");
    return {
      title: "Tài liệu",
      focus: param && sections.some((sec) => sec.id === param) ? `docs-${param}` : null,
      html: `<div class="page-head"><h1>Tài liệu</h1>
          <p>Tài liệu viết tay của repo, chia theo chủ đề. Bấm một thẻ để đọc ngay trên trang (định dạng như GitHub: bảng,
          code tô màu, sơ đồ mermaid, công thức); thẻ nhỏ bên dưới dẫn tới bước, kỹ năng, nhóm liên quan.</p>
          <div class="row">${jump}</div></div>
        ${body}`,
    };
  }

  function pageNotFound() {
    return { title: "Không tìm thấy", html: `<div class="page-head"><h1>Không tìm thấy trang</h1><p><a href="#/">Về trang tổng quan</a></p></div>` };
  }

  // ───────────────────────── trình xem tài liệu (#/doc/<đường dẫn trong repo>) ─────────────────────────
  // Nội dung đã render lúc build (src/aiarch/docview.py) thành md/<đường dẫn>.html; ở đây chỉ tải, gắn vào khung xem,
  // vẽ sơ đồ mermaid + công thức KaTeX (thư viện trong assets/vendor, chỉ tải khi tài liệu cần), thêm mục lục và nút
  // sao chép code. Đóng khung xem = quay lại đúng trang và vị trí cuộn trước đó.
  const $ = (id) => document.getElementById(id);
  const viewer = { open: false, path: null, ready: false, depth: 0, token: 0, lastFocus: null, cache: new Map() };
  let lastDepth = null; // mục lịch sử vừa đi qua: 0 = trang thường, n ≥ 1 = tài liệu thứ n liên tiếp, null = mở thẳng vào tài liệu
  const ICON_COPY = `<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 0 1 0 1.5h-1.5a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-1.5a.75.75 0 0 1 1.5 0v1.5A1.75 1.75 0 0 1 9.25 16h-7.5A1.75 1.75 0 0 1 0 14.25Z"/><path fill="currentColor" d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0 1 14.25 11h-7.5A1.75 1.75 0 0 1 5 9.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z"/></svg>`;
  const ICON_CHECK = `<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"/></svg>`;
  const dirOf = (path) => path.split("/").slice(0, -1).join("/");
  const baseName = (path) => path.split("/").pop();

  function splitDocParam(param) {
    const s = param || "";
    const i = s.indexOf("#");
    return i < 0 ? { path: s, anchor: "" } : { path: s.slice(0, i), anchor: s.slice(i + 1) };
  }
  function loadFragment(path) {
    if (!viewer.cache.has(path)) {
      const job = fetch(`md/${encPath(path)}.html`).then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.text();
      });
      job.catch(() => viewer.cache.delete(path));
      viewer.cache.set(path, job);
    }
    return viewer.cache.get(path);
  }
  const loading = new Map();
  function loadScript(src) {
    if (!loading.has(src)) {
      loading.set(
        src,
        new Promise((resolve, reject) => {
          const el = document.createElement("script");
          el.src = src;
          el.async = true;
          el.onload = resolve;
          el.onerror = () => {
            loading.delete(src);
            el.remove();
            reject(new Error(`không tải được ${src}`));
          };
          document.head.appendChild(el);
        })
      );
    }
    return loading.get(src);
  }
  function loadStyle(href) {
    if (document.querySelector(`link[data-vendor="${href}"]`)) return;
    const el = document.createElement("link");
    el.rel = "stylesheet";
    el.href = href;
    el.setAttribute("data-vendor", href);
    document.head.appendChild(el);
  }

  // Ghi độ sâu vào history.state để nút Đóng lùi đúng số bước về trang trước khi mở tài liệu.
  function trackDocDepth() {
    let st = null;
    try {
      st = history.state;
    } catch (e) {
      /* bỏ qua */
    }
    let depth = st && typeof st === "object" && "docDepth" in st ? st.docDepth : undefined;
    if (depth === undefined) {
      depth = lastDepth == null ? null : lastDepth + 1;
      try {
        history.replaceState(Object.assign({}, st, { docDepth: depth }), "");
      } catch (e) {
        /* bỏ qua */
      }
    }
    lastDepth = depth;
    viewer.depth = depth;
  }

  function showViewer() {
    if (viewer.open) return;
    viewer.open = true;
    viewer.lastFocus = document.activeElement;
    $("viewer").hidden = false;
    document.documentElement.classList.add("viewer-open");
    document.querySelectorAll(".site-header, #app, .site-footer").forEach((el) => (el.inert = true));
    hideTip();
    $("viewer").querySelector(".viewer-close").focus({ preventScroll: true });
  }
  function hideViewer() {
    if (!viewer.open) return;
    viewer.open = false;
    viewer.token += 1;
    $("viewer").hidden = true;
    $("viewer").classList.remove("toc-open");
    document.documentElement.classList.remove("viewer-open");
    document.querySelectorAll(".site-header, #app, .site-footer").forEach((el) => (el.inert = false));
    if (viewer.lastFocus && document.contains(viewer.lastFocus)) viewer.lastFocus.focus({ preventScroll: true });
  }
  function closeDoc() {
    if (viewer.depth > 0) history.go(-viewer.depth);
    else location.replace(pageKey || "#/tai-lieu");
  }

  function crumbs(path) {
    const parts = path.split("/");
    const out = [D.meta.pages["README.md"] && path !== "README.md" ? `<a href="${esc(docHref("README.md"))}">${esc(D.meta.repo.split("/").pop())}</a>` : `<span>${esc(D.meta.repo.split("/").pop())}</span>`];
    let acc = "";
    parts.forEach((part, i) => {
      acc = acc ? `${acc}/${part}` : part;
      const readme = `${acc}/README.md`;
      if (i < parts.length - 1 && D.meta.pages[readme] && readme !== path) out.push(`<a href="${esc(docHref(readme))}">${esc(part)}</a>`);
      else out.push(`<span>${esc(part)}</span>`);
    });
    return out.join(`<span class="sep">/</span>`);
  }

  // Tài liệu README gần nhất chứa file này — "thuộc dự án / lab nào" cho file code và tài liệu con.
  function parentDoc(path) {
    let dir = dirOf(path);
    while (dir) {
      const readme = `${dir}/README.md`;
      if (readme !== path && PATH_KEY[readme]) return PATH_KEY[readme];
      dir = dirOf(dir);
    }
    return null;
  }

  function skillChip(id, level) {
    const s = SK[id];
    return `<a class="chip ${rank(id) && (!level || met({ id, level })) ? "done" : ""}" href="#/ky-nang/${esc(id)}" title="${esc(s.summary)}"><span class="mono">${esc(id)}</span>${esc(s.name)}${
      level ? `<span class="chip-lv">${esc(D.levels[level])}</span>` : ""
    }</a>`;
  }

  // Dải "đang đọc gì, thuộc đâu" phía trên tài liệu: loại, nhóm tài liệu, bước, kỹ năng, học cùng, nhóm bài toán.
  function docContext(path) {
    const key = PATH_KEY[path];
    if (!key) {
      const parent = parentDoc(path);
      return parent ? `<div class="ctx-card"><div class="ctx-row"><span class="ctx-label">Thuộc</span><div class="row">${resLink(parent)}</div></div></div>` : "";
    }
    const d = docOf(key);
    const rel = D.learn.docs[key] || { skills: [], groups: [], combos: [] };
    const sec = D.meta.doc_sections.find((x) => x.id === d.section);
    const rows = [];
    if (rel.step) rows.push(["Bước", stepChip(rel.step)]);
    else if (rel.stage) rows.push(["Giai đoạn", stageChip(rel.stage)]);
    if (rel.skills.length) rows.push(["Kỹ năng", rel.skills.map((x) => skillChip(x.id, x.level)).join("")]);
    const mates = rel.step ? docsBy("step", rel.step).filter((k) => k !== key).sort(byKind) : [];
    if (mates.length) rows.push(["Học cùng", mates.map(resLink).join("")]);
    if (rel.groups.length) rows.push(["Nhóm", rel.groups.map(groupLink).join("")]);
    if (rel.combos.length) rows.push(["Tổ hợp", rel.combos.map((cid) => `<a class="chip" href="#/to-hop/${esc(cid)}"><span class="mono">${esc(cid)}</span>${esc(CMB[cid].name)}</a>`).join("")]);
    const head = `<span class="res-kind">${esc(KIND[d.kind] || KIND.doc)}</span>${sec ? `<a href="#/tai-lieu/${esc(sec.id)}">${esc(sec.title)}</a>` : ""}`;
    if (!rows.length) return `<div class="ctx-card"><div class="ctx-head">${head}</div></div>`;
    // Điện thoại: thu gọn để nội dung tài liệu hiện ngay; bấm để xem bước, kỹ năng, tài liệu học cùng.
    const wide = window.matchMedia ? window.matchMedia("(min-width: 720px)").matches : true;
    return `<details class="ctx-card"${wide ? " open" : ""}>
      <summary class="ctx-head">${head}<span class="ctx-more small muted">${esc(rows.map(([label]) => label).join(" · "))}</span></summary>
      ${rows.map(([label, html]) => `<div class="ctx-row"><span class="ctx-label">${esc(label)}</span><div class="row">${html}</div></div>`).join("")}
    </details>`;
  }

  // Các trang cùng thư mục (như cây file của GitHub) + README của thư mục con.
  function folderPages(path) {
    const dir = dirOf(path);
    const inDir = (p) => dirOf(p) === dir;
    const sub = (p) => baseName(p) === "README.md" && dirOf(dirOf(p)) === dir && dirOf(p) !== dir;
    const all = Object.keys(D.meta.pages).filter((p) => inDir(p) || sub(p));
    const rankOf = (p) => (baseName(p) === "README.md" && inDir(p) ? 0 : sub(p) ? 1 : D.meta.pages[p].k === "md" ? 2 : 3);
    return all.sort((a, b) => rankOf(a) - rankOf(b) || a.localeCompare(b));
  }

  // Phần cuối tài liệu: đánh dấu kỹ năng đã đạt, bài trước / bài tiếp, cùng thư mục.
  function docAfter(path) {
    const key = PATH_KEY[path];
    let out = "";
    if (key) {
      const rel = D.learn.docs[key] || { skills: [] };
      const leveled = rel.skills.filter((x) => x.level);
      if (leveled.length) {
        out += `<section class="after-card"><h3>Học xong? Đánh dấu kỹ năng đã đạt</h3><div class="skill-rows">${leveled
          .map((x) => {
            const done = met(x);
            return `<div class="skill-row ${done ? "done" : ""}"><div class="sr-title"><a href="#/ky-nang/${esc(x.id)}"><span class="mono">${esc(x.id)}</span> ${esc(SK[x.id].name)}</a> ${lvBadge(x.level)}</div>
              <div class="sr-actions">${toggle(x.id, x.level, done ? "Đã đạt" : "Đánh dấu đạt")}</div>
              <div class="sr-desc">${md(SK[x.id].levels[x.level])}</div></div>`;
          })
          .join("")}</div></section>`;
      }
      const sec = D.meta.doc_sections.find((x) => x.items.includes(key));
      if (sec) {
        const i = sec.items.indexOf(key);
        const [prev, next] = [sec.items[i - 1], sec.items[i + 1]];
        const cell = (k, dir) =>
          k ? `<a class="pager-${dir}" href="${esc(docHref(docOf(k).path))}"><span class="small muted">${dir === "prev" ? "← Trước" : "Tiếp theo →"}</span><span>${esc(docOf(k).title)}</span></a>` : "<span></span>";
        if (prev || next) out += `<nav class="doc-pager" aria-label="Tài liệu trước và sau">${cell(prev, "prev")}${cell(next, "next")}</nav>`;
      }
    }
    const pages = folderPages(path);
    if (pages.length > 1) {
      const dir = dirOf(path);
      out += `<details class="after-card folder"><summary>Cùng thư mục <span class="mono">${esc(dir || D.meta.repo.split("/").pop())}/</span> · ${pages.length} file</summary><ul class="clean">${pages
        .map((p) => {
          const name = dirOf(p) === dir ? baseName(p) : `${baseName(dirOf(p))}/`;
          const icon = dirOf(p) === dir ? (D.meta.pages[p].k === "md" ? "📄" : "🧾") : "📁";
          return `<li${p === path ? ' aria-current="page"' : ""}><a href="${esc(docHref(p))}"><span aria-hidden="true">${icon}</span><span class="mono">${esc(name)}</span><span class="muted small">${esc(D.meta.pages[p].t)}</span></a></li>`;
        })
        .join("")}</ul></details>`;
    }
    return out;
  }
  function refreshViewerPanels() {
    if (!viewer.open || !viewer.ready) return;
    $("viewer-context").innerHTML = docContext(viewer.path);
    $("viewer-after").innerHTML = docAfter(viewer.path);
  }

  function buildToc(path) {
    const heads = [...$("viewer-body").querySelectorAll("h1[id], h2[id], h3[id]")];
    const items = heads.filter((h, i) => !(i === 0 && h.tagName === "H1"));
    const v = $("viewer");
    v.classList.toggle("has-toc", items.length >= 3);
    $("viewer-toc").innerHTML =
      items.length >= 3
        ? `<div class="toc-title">Mục lục</div><ul class="clean">${items
            .map((h) => `<li class="toc-${h.tagName.toLowerCase()}"><a href="${esc(docHref(path, h.id.slice(3)))}">${esc(h.textContent.trim())}</a></li>`)
            .join("")}</ul>`
        : "";
    viewer.heads = items;
  }
  // Đánh dấu mục đang đọc trong mục lục.
  function spyToc() {
    if (!viewer.open || !viewer.heads || !viewer.heads.length) return;
    const top = $("viewer-scroll").getBoundingClientRect().top + 80;
    let current = null;
    for (const h of viewer.heads) {
      if (h.getBoundingClientRect().top <= top) current = h;
      else break;
    }
    $("viewer-toc").querySelectorAll("a").forEach((a, i) => {
      if (viewer.heads[i] === current) a.setAttribute("aria-current", "true");
      else a.removeAttribute("aria-current");
    });
  }

  function goAnchor(anchor) {
    const scroller = $("viewer-scroll");
    const body = $("viewer-body");
    body.querySelectorAll(".cl.hl").forEach((el) => el.classList.remove("hl"));
    if (!anchor) {
      scroller.scrollTop = 0;
      return;
    }
    let el = null;
    const line = anchor.match(/^L(\d+)(?:-L?(\d+))?$/);
    if (line) {
      const [a, b] = [Number(line[1]), Number(line[2] || line[1])];
      for (let i = a; i <= b; i++) {
        const ln = $(`md-L${i}`);
        if (ln) ln.classList.add("hl");
      }
      el = $(`md-L${a}`);
    }
    if (!el) el = $(`md-${anchor}`);
    if (!el) {
      // liên kết cũ viết anchor hơi khác (gạch dưới, hoa/thường): so khớp lỏng
      const loose = (x) => x.toLowerCase().replace(/[_\s]/g, "");
      el = [...body.querySelectorAll("[id^='md-']")].find((x) => loose(x.id.slice(3)) === loose(anchor)) || null;
    }
    if (el) el.scrollIntoView({ block: "start" });
    else scroller.scrollTop = 0;
  }

  async function renderMermaid(root, token) {
    const blocks = [...root.querySelectorAll("pre.mermaid, .mermaid-diagram")];
    if (!blocks.length) return;
    try {
      await loadScript("assets/vendor/mermaid/mermaid.min.js");
    } catch (e) {
      blocks.forEach((b) => b.classList.add("mermaid-failed"));
      return;
    }
    if (token !== viewer.token) return;
    const mm = window.mermaid;
    mm.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      suppressErrorRendering: true,
      theme: currentTheme() === "dark" ? "dark" : "default",
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif',
    });
    for (const el of blocks) {
      if (token !== viewer.token) return;
      const src = el.getAttribute("data-src") || el.textContent;
      try {
        viewer.mermaidSeq = (viewer.mermaidSeq || 0) + 1;
        const { svg } = await mm.render(`mmd-${viewer.mermaidSeq}`, src);
        if (token !== viewer.token) return;
        const box = document.createElement("div");
        box.className = "mermaid-diagram";
        box.setAttribute("data-src", src);
        box.innerHTML = svg;
        el.replaceWith(box);
      } catch (err) {
        const pre = document.createElement("pre");
        pre.className = "mermaid mermaid-failed";
        pre.setAttribute("data-src", src);
        pre.title = `Sơ đồ lỗi cú pháp: ${(err && err.message) || err}`;
        pre.textContent = src;
        el.replaceWith(pre);
      }
    }
  }
  async function renderMath(root, token) {
    const nodes = [...root.querySelectorAll(".math:not([data-done])")];
    if (!nodes.length) return;
    try {
      loadStyle("assets/vendor/katex/katex.min.css");
      await loadScript("assets/vendor/katex/katex.min.js");
    } catch (e) {
      return;
    }
    if (token !== viewer.token) return;
    nodes.forEach((el) => {
      try {
        window.katex.render(el.textContent, el, { displayMode: el.classList.contains("math-display"), throwOnError: false });
        el.setAttribute("data-done", "1");
      } catch (e) {
        /* để nguyên mã TeX */
      }
    });
  }
  function enhanceDoc(root, token) {
    root.querySelectorAll("div.highlight").forEach((block) => {
      if (!block.querySelector(".copy-btn"))
        block.insertAdjacentHTML("beforeend", `<button type="button" class="copy-btn" data-action="copy-code" aria-label="Sao chép code" title="Sao chép">${ICON_COPY}</button>`);
    });
    return Promise.all([renderMermaid(root, token), renderMath(root, token)]);
  }

  async function openDoc(param) {
    const { path, anchor } = splitDocParam(param);
    showViewer();
    if (viewer.path === path && viewer.ready) {
      goAnchor(anchor);
      return;
    }
    const token = ++viewer.token;
    const meta = D.meta.pages[path];
    const title = meta ? meta.t : baseName(path) || "Tài liệu";
    viewer.path = path;
    viewer.ready = false;
    viewer.heads = [];
    document.title = `${title} · Lộ trình kỹ năng AI`;
    $("viewer-title").textContent = title;
    $("viewer-crumbs").innerHTML = crumbs(path);
    $("viewer-github").href = `${D.meta.repo_url}/blob/main/${encPath(path)}`;
    $("viewer-context").innerHTML = "";
    $("viewer-after").innerHTML = "";
    $("viewer-toc").innerHTML = "";
    $("viewer").classList.remove("has-toc", "toc-open");
    $("viewer").querySelector(".viewer-toc-btn").setAttribute("aria-expanded", "false");
    const body = $("viewer-body");
    body.className = "markdown-body";
    body.removeAttribute("data-ready");
    $("viewer-scroll").scrollTop = 0;
    const gh = `<a href="${esc(`${D.meta.repo_url}/blob/main/${encPath(path)}`)}" target="_blank" rel="noopener">mở trên GitHub ↗</a>`;
    if (!meta) {
      body.innerHTML = `<p class="viewer-note">Trang web không có bản xem của <code>${esc(path)}</code> — ${gh}.</p>`;
      return;
    }
    body.innerHTML = `<p class="viewer-note">Đang tải…</p>`;
    let html;
    try {
      html = await loadFragment(path);
    } catch (err) {
      if (token === viewer.token)
        body.innerHTML = `<p class="viewer-note">Không tải được tài liệu (${esc(err.message)}). Nếu bạn mở thẳng file
          <code>index.html</code>, hãy chạy <code>make site-serve</code> rồi mở http://localhost:8000 — hoặc ${gh}.</p>`;
      return;
    }
    if (token !== viewer.token) return;
    body.innerHTML = html;
    body.classList.toggle("is-code", meta.k === "code");
    viewer.ready = true;
    $("viewer-context").innerHTML = docContext(path);
    $("viewer-after").innerHTML = docAfter(path);
    buildToc(path);
    goAnchor(anchor);
    const scroller = $("viewer-scroll");
    const before = scroller.scrollTop;
    await enhanceDoc(body, token);
    // sơ đồ vẽ xong làm tài liệu dài ra: nhảy lại anchor nếu người đọc chưa tự cuộn
    if (token !== viewer.token) return;
    if (anchor && Math.abs(scroller.scrollTop - before) < 4) goAnchor(anchor);
    spyToc();
    body.setAttribute("data-ready", "1"); // đã vẽ xong sơ đồ, công thức (kiểm thử chờ dấu này)
  }

  // ───────────────────────── điều hướng ─────────────────────────
  const ROUTES = {
    "": pageHome,
    "lo-trinh": pageRoadmap,
    "ky-nang": (p) => (p ? pageSkill(p) : pageSkills()),
    nhom: (p) => (p ? pageGroup(p) : pageGroups()),
    "ma-tran": pageMatrix,
    "to-hop": pageCombos,
    "tai-lieu": pageDocs,
    "tien-do": pageProgress,
    doc: pageDocs, // #/doc/... mở khung xem; trang Tài liệu nằm bên dưới
  };
  const app = () => document.getElementById("app");

  function parseHash(hash = location.hash) {
    let h = hash.replace(/^#\/?/, "");
    try {
      h = decodeURIComponent(h);
    } catch (e) {
      /* hash lỗi mã hoá: dùng nguyên văn */
    }
    const [path, ...rest] = h.split("/");
    return { path: path || "", param: rest.join("/") || null };
  }

  let pageKey = null; // hash của trang đang vẽ trong #app — nằm dưới khung xem tài liệu khi khung đang mở
  let pageTitle = "";
  function render(keepScroll) {
    const key = parseHash().path === "doc" ? pageKey || "#/tai-lieu" : location.hash || "#/";
    const { path, param } = parseHash(key);
    const fn = ROUTES[path] || pageNotFound;
    const y = window.scrollY;
    const page = fn(param);
    pageKey = key;
    app().innerHTML = page.html;
    pageTitle = `${page.title} · Lộ trình kỹ năng AI`;
    if (!viewer.open) document.title = pageTitle;
    document.querySelectorAll("[data-nav]").forEach((a) => {
      if (a.getAttribute("data-nav") === path) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
    // Menu cuộn ngang trên mobile: kéo mục đang mở vào giữa tầm nhìn (chỉ cuộn menu, không cuộn trang).
    const nav = document.querySelector(".site-nav");
    const current = nav && nav.querySelector('[aria-current="page"]');
    if (current && nav.scrollWidth > nav.clientWidth) {
      nav.scrollLeft = current.offsetLeft - nav.offsetLeft - (nav.clientWidth - current.offsetWidth) / 2;
    }
    if (page.after) page.after();
    if (keepScroll) window.scrollTo(0, y);
    else if (page.focus && document.getElementById(page.focus)) document.getElementById(page.focus).scrollIntoView({ block: "start" });
    else window.scrollTo(0, 0);
  }

  function route() {
    const r = parseHash();
    if (r.path === "doc") {
      if (pageKey === null) render(false); // mở thẳng link tài liệu: dựng trang Tài liệu bên dưới
      trackDocDepth();
      openDoc(r.param);
      return;
    }
    lastDepth = 0;
    const wasOpen = viewer.open;
    hideViewer();
    if (wasOpen && (location.hash || "#/") === pageKey) {
      document.title = pageTitle; // chỉ đóng khung xem: giữ nguyên trang và vị trí cuộn
      return;
    }
    render(false);
  }

  // ───────────────────────── tương tác ─────────────────────────
  function toast(msg) {
    const t = document.createElement("div");
    t.className = "toast";
    t.setAttribute("role", "status");
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 2600);
  }

  function currentTheme() {
    const attr = document.documentElement.getAttribute("data-theme");
    if (attr) return attr;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function exportProgress() {
    const data = { app: "aiarch-roadmap", version: 1, exported_at: new Date().toISOString(), skills: progress.skills };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `tien-do-lo-trinh-ai-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      URL.revokeObjectURL(a.href);
      a.remove();
    }, 0);
  }
  function importProgress(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(reader.result);
        const src = data && typeof data.skills === "object" ? data.skills : null;
        if (!src) throw new Error("bad");
        const clean = {};
        for (const [id, r] of Object.entries(src)) {
          const n = Number(r);
          if (SK[id] && n >= 1 && n <= 3) clean[id] = Math.round(n);
        }
        progress = { v: 1, skills: clean };
        writeJSON(PROGRESS_KEY, progress);
        render(true);
        toast(`Đã nhập tiến độ của ${Object.keys(clean).length} kỹ năng`);
      } catch (e) {
        toast("File không đúng định dạng tiến độ");
      }
    };
    reader.readAsText(file);
  }

  function onClick(e) {
    if (e.target.closest && e.target.closest("#viewer-toc a")) $("viewer").classList.remove("toc-open");
    const el = e.target.closest("[data-action]");
    if (!el) {
      const trackLink = e.target.closest("[data-track]");
      if (trackLink) {
        ui.track = trackLink.getAttribute("data-track");
        saveUI();
      }
      const domainLink = e.target.closest("[data-domain]");
      if (domainLink) {
        ui.domain = domainLink.getAttribute("data-domain");
        ui.q = "";
        if (parseHash().path === "ky-nang" && !parseHash().param) render(true); // đang ở trang Kỹ năng: hash không đổi
      }
      return;
    }
    const act = el.getAttribute("data-action");
    const id = el.getAttribute("data-id");
    switch (act) {
      case "lvl":
        toggleLevel(id, el.getAttribute("data-level"));
        render(true);
        refreshViewerPanels();
        break;
      case "doc-close":
        closeDoc();
        break;
      case "doc-toc": {
        const v = $("viewer");
        v.style.setProperty("--bar-h", `${v.querySelector(".viewer-bar").offsetHeight}px`); // thanh trên cao hơn khi xuống dòng
        el.setAttribute("aria-expanded", String(v.classList.toggle("toc-open")));
        break;
      }
      case "copy-code": {
        const pre = el.parentElement.querySelector("pre");
        const done = () => {
          el.innerHTML = ICON_CHECK;
          el.classList.add("copied");
          setTimeout(() => {
            el.innerHTML = ICON_COPY;
            el.classList.remove("copied");
          }, 1600);
        };
        if (navigator.clipboard && pre) navigator.clipboard.writeText(pre.innerText).then(done, () => toast("Không sao chép được — hãy bôi đen để chép"));
        break;
      }
      case "step":
        if (ui.open.has(id)) ui.open.delete(id);
        else ui.open.add(id);
        saveUI();
        render(true);
        break;
      case "stage":
        ui.stage = id;
        saveUI();
        if (parseHash().param) location.hash = `#/lo-trinh/${id}`;
        else render(true);
        break;
      case "expand-all":
      case "collapse-all": {
        const st = STAGES.find((s) => s.id === ui.stage);
        (st.steps || []).forEach((s) => (act === "expand-all" ? ui.open.add(s.id) : ui.open.delete(s.id)));
        saveUI();
        render(true);
        break;
      }
      case "track":
        ui.track = ui.track === id ? null : id;
        saveUI();
        render(true);
        break;
      case "matrix-domain":
        ui.matrixDomain = id;
        render(true);
        break;
      case "quiz": {
        const qs = D.identify.questions;
        if (el.getAttribute("data-answer") === "yes") ui.quiz.result = qs[ui.quiz.i].group;
        else if (ui.quiz.i + 1 >= qs.length) ui.quiz.result = D.identify.fallback;
        else ui.quiz.i += 1;
        document.getElementById("quiz-box").innerHTML = quizHtml();
        break;
      }
      case "quiz-reset":
        ui.quiz = { i: 0, result: null };
        document.getElementById("quiz-box").innerHTML = quizHtml();
        break;
      case "theme": {
        const next = currentTheme() === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        try {
          localStorage.setItem("aiarch-theme", next);
        } catch (err) {
          /* bỏ qua */
        }
        if (viewer.open && viewer.ready) renderMermaid($("viewer-body"), viewer.token); // vẽ lại sơ đồ theo màu mới
        break;
      }
      case "export":
        exportProgress();
        break;
      case "import":
        document.getElementById("import-file").click();
        break;
      case "reset":
        if (window.confirm("Xóa toàn bộ tiến độ đã đánh dấu trên trình duyệt này?")) {
          progress = { v: 1, skills: {} };
          writeJSON(PROGRESS_KEY, progress);
          render(true);
          toast("Đã xóa tiến độ");
        }
        break;
    }
  }

  function onInput(e) {
    const f = e.target.getAttribute && e.target.getAttribute("data-filter");
    if (!f) return;
    ui[f] = e.target.value;
    if (f === "sort") saveUI();
    renderSkillResults();
  }

  function onChange(e) {
    if (e.target.id === "import-file" && e.target.files && e.target.files[0]) importProgress(e.target.files[0]);
  }

  // tooltip cho bản đồ nhiệt (chuột và bàn phím)
  function showTip(el, x, y) {
    const tip = document.getElementById("tooltip");
    tip.textContent = el.getAttribute("data-tip");
    tip.hidden = false;
    const r = tip.getBoundingClientRect();
    tip.style.left = `${Math.max(8, Math.min(window.innerWidth - r.width - 8, x + 12))}px`;
    tip.style.top = `${Math.max(8, y - r.height - 12)}px`;
  }
  function hideTip() {
    document.getElementById("tooltip").hidden = true;
  }
  function onPointer(e) {
    const el = e.target.closest && e.target.closest("[data-tip]");
    if (el) showTip(el, e.clientX, e.clientY);
    else hideTip();
  }
  function onFocus(e) {
    const el = e.target.closest && e.target.closest("[data-tip]");
    if (el) {
      const r = el.getBoundingClientRect();
      showTip(el, r.left + r.width / 2, r.top);
    }
  }

  function footer() {
    const m = D.meta;
    document.getElementById("footer").innerHTML = `
      <span>Dữ liệu sinh từ <a href="${esc(m.repo_url)}/tree/main/catalog" target="_blank" rel="noopener">catalog/*.yaml</a>
      · <a href="${esc(m.repo_url)}" target="_blank" rel="noopener">${esc(m.repo)}</a> · v${esc(m.version)}${m.commit ? ` (${esc(m.commit)})` : ""}</span>
      <span>Tiến độ chỉ lưu trong trình duyệt của bạn.</span>`;
  }

  async function boot() {
    const el = document.getElementById("catalog-data");
    if (el) D = JSON.parse(el.textContent);
    else {
      const res = await fetch("data/catalog.json");
      D = await res.json();
    }
    index();
    footer();
    document.addEventListener("click", onClick);
    document.addEventListener("input", onInput);
    document.addEventListener("change", onChange);
    document.addEventListener("mousemove", onPointer);
    document.addEventListener("focusin", onFocus);
    document.addEventListener("focusout", hideTip);
    window.addEventListener("scroll", hideTip, { passive: true });
    window.addEventListener("hashchange", route);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && viewer.open && !e.defaultPrevented) {
        e.preventDefault();
        closeDoc();
      }
    });
    let spy = 0;
    $("viewer-scroll").addEventListener(
      "scroll",
      () => {
        if (!spy) spy = requestAnimationFrame(() => ((spy = 0), spyToc()));
      },
      { passive: true }
    );
    route();
  }

  boot().catch((err) => {
    app().innerHTML = `<p class="notice">Không tải được dữ liệu: ${esc(err.message)}</p>`;
  });
})();
