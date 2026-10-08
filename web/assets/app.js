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
  let SK, GR, DOM, CMB, ORDER, STAGES, ALL_STEPS;

  function index() {
    SK = Object.fromEntries(D.skills.map((s) => [s.id, s]));
    GR = Object.fromEntries(D.groups.map((g) => [g.id, g]));
    DOM = Object.fromEntries(D.domains.map((d) => [d.code, d]));
    CMB = Object.fromEntries(D.combinations.map((c) => [c.id, c]));
    ORDER = Object.fromEntries(D.skills.map((s) => [s.id, s.order]));
    STAGES = D.roadmap.stages || [];
    ALL_STEPS = STAGES.flatMap((st) => (st.steps || []).map((step) => ({ ...step, stage: st.id })));
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
  const docLink = (key) => {
    const d = D.meta.docs[key];
    return d ? `<a href="${esc(d.url)}" target="_blank" rel="noopener">${esc(d.title)}</a>` : "";
  };

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
      <div class="sr-actions">${toggle(s.id, item.level, done ? "Đã đạt" : "Đánh dấu đạt")}</div>
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
          <h3>Tài liệu chi tiết trên GitHub</h3>
          <ul class="list-dots">${["setup", "problem_map", "skill_map", "architecture", "combining", "tokens", "checklist", "history"]
            .map((k) => `<li>${docLink(k)}</li>`)
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
    const stepsHtml = steps
      .map((step) => {
        const open = ui.open.has(step.id);
        const done = step.skills.filter(met).length;
        const finished = done === step.skills.length;
        const week = step.week ? `Tuần ${esc(step.week)}` : "Linh hoạt";
        return `<li id="step-${esc(step.id)}">
          <span class="step-marker ${finished ? "done" : ""}" aria-hidden="true">${finished ? "✓" : esc(step.id)}</span>
          <div class="card step-card">
            <button type="button" class="step-head" data-action="step" data-id="${esc(step.id)}" aria-expanded="${open}" aria-controls="body-${esc(step.id)}">
              <span><span class="week">${esc(step.id)} · ${week}</span><h3>${esc(step.title)}</h3></span>
              <span class="row" style="flex-wrap:nowrap">${meter(done, step.skills.length, `${done}/${step.skills.length} kỹ năng`)}${chev}</span>
            </button>
            ${
              open
                ? `<div class="step-body" id="body-${esc(step.id)}">
              <dl class="kv"><dt>Việc cần làm</dt><dd>${md(step.do)}</dd><dt>Sản phẩm nộp</dt><dd>${md(step.deliverable)}</dd></dl>
              <div class="skill-rows">${step.skills.map((it) => skillRow(it)).join("")}</div>
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
      </div>
      <div class="stage-tabs" role="tablist" aria-label="Giai đoạn">${tabs}</div>

      <section style="${stageColor(st.id)}">
        <div class="stage-summary">
          <div>
            <h2 style="margin-top:0">Giai đoạn ${esc(st.id)} · ${esc(st.name)} <span class="muted small nowrap">${esc(st.period)}</span></h2>
            <p>${md(st.goal)}</p>
            ${st.note ? `<p class="small muted">${md(st.note)}</p>` : ""}
            <dl class="kv"><dt>Cài đặt</dt><dd><code>${esc(st.setup)}</code></dd><dt>Đọc</dt><dd>${esc(st.book)}</dd>
            ${st.project ? `<dt>Dự án</dt><dd>${groupLink(st.project)}</dd>` : ""}</dl>
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
        (ô đậm = Cốt lõi, ô nhạt = Cần).</p></div>
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
            <div class="row" style="margin-top:auto"><span class="small muted">Mức của bạn:</span>${lvBadge(lvl)}</div>
          </a>`;
          })
          .join("");
      })
      .join("");
    return {
      title: "Nhóm bài toán",
      html: `
      <div class="page-head"><h1>8 nhóm bài toán AI trong doanh nghiệp</h1>
        <p>Phân loại theo <strong>đầu ra mà nghiệp vụ cần</strong>. Mỗi nhóm có lộ trình riêng từ mức Cơ bản đến Nâng cao, tính từ các kỹ năng Cốt lõi và Cần của nhóm.</p></div>
      <div class="card" id="quiz">
        <h3>Nhận diện bài toán trong 30 giây</h3>
        <div id="quiz-box">${quizHtml()}</div>
      </div>
      <div class="grid grid-3" style="margin-top:24px">${blocks}</div>`,
    };
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
        <p>Kỹ năng nào cần cho nhóm nào, ở mức nào. Tầng được tính tự động từ mức sử dụng.</p></div>
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
        bẫy khi ghép và metric đo từ đầu đến cuối. Nguyên tắc ghép: ${docLink("combining")}.</p></div>
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
        <p>Tiến độ lưu trong trình duyệt này. Dùng <strong>Xuất file</strong> để sao lưu, chuyển máy hoặc gửi cho người hướng dẫn.</p></div>
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

  function pageNotFound() {
    return { title: "Không tìm thấy", html: `<div class="page-head"><h1>Không tìm thấy trang</h1><p><a href="#/">Về trang tổng quan</a></p></div>` };
  }

  // ───────────────────────── điều hướng ─────────────────────────
  const ROUTES = {
    "": pageHome,
    "lo-trinh": pageRoadmap,
    "ky-nang": (p) => (p ? pageSkill(p) : pageSkills()),
    nhom: (p) => (p ? pageGroup(p) : pageGroups()),
    "ma-tran": pageMatrix,
    "to-hop": pageCombos,
    "tien-do": pageProgress,
  };
  const app = () => document.getElementById("app");

  function parseHash() {
    const h = decodeURIComponent(location.hash.replace(/^#\/?/, ""));
    const [path, ...rest] = h.split("/");
    return { path: path || "", param: rest.join("/") || null };
  }

  function render(keepScroll) {
    const { path, param } = parseHash();
    const fn = ROUTES[path] || pageNotFound;
    const y = window.scrollY;
    const page = fn(param);
    app().innerHTML = page.html;
    document.title = `${page.title} · Lộ trình kỹ năng AI`;
    document.querySelectorAll("[data-nav]").forEach((a) => {
      if (a.getAttribute("data-nav") === path) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
    if (page.after) page.after();
    if (keepScroll) window.scrollTo(0, y);
    else if (page.focus && document.getElementById(page.focus)) document.getElementById(page.focus).scrollIntoView({ block: "start" });
    else window.scrollTo(0, 0);
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
    const el = e.target.closest("[data-action]");
    if (!el) {
      const trackLink = e.target.closest("[data-track]");
      if (trackLink) {
        ui.track = trackLink.getAttribute("data-track");
        saveUI();
      }
      return;
    }
    const act = el.getAttribute("data-action");
    const id = el.getAttribute("data-id");
    switch (act) {
      case "lvl":
        toggleLevel(id, el.getAttribute("data-level"));
        render(true);
        break;
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
    window.addEventListener("hashchange", () => render(false));
    render(false);
  }

  boot().catch((err) => {
    app().innerHTML = `<p class="notice">Không tải được dữ liệu: ${esc(err.message)}</p>`;
  });
})();
