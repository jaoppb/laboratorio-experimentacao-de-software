import { parquetReadObjects } from "./node_modules/hyparquet/src/index.js";

// Served straight from GitHub (not a local relative path) so the dashboard
// works from any static host without needing dados/ to be reachable on disk.
// Must be a plain git blob, not Git LFS: raw.githubusercontent.com returns
// the LFS pointer text (not the binary) for LFS-tracked paths.
const DATASET_URL = "https://raw.githubusercontent.com/jaoppb/laboratorio-experimentacao-de-software/main/lab01/dados/unified_sample.parquet";

/* ---------------------------------------------------------------
   Theme toggle (light / dark, persisted in localStorage)
   --------------------------------------------------------------- */
(function initTheme() {
  const root = document.documentElement;
  const stored = localStorage.getItem("lab01-dashboard-theme");
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const effective = stored || (systemDark ? "dark" : "light");
  if (stored) root.setAttribute("data-theme", stored);

  function paintToggle(theme) {
    document.getElementById("theme-icon-dark").style.display = theme === "dark" ? "none" : "inline";
    document.getElementById("theme-icon-light").style.display = theme === "dark" ? "inline" : "none";
    document.getElementById("theme-label").textContent = theme === "dark" ? "Claro" : "Escuro";
  }

  document.addEventListener("DOMContentLoaded", () => {
    paintToggle(effective);
    document.getElementById("theme-toggle").addEventListener("click", () => {
      const current = root.getAttribute("data-theme") ||
        (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      const next = current === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      localStorage.setItem("lab01-dashboard-theme", next);
      paintToggle(next);
    });
  });
})();

/* ---------------------------------------------------------------
   Small inline icon set (GitHub-inspired, hand-drawn originals)
   --------------------------------------------------------------- */
const ICONS = {
  clock: '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1Zm0 12.5a5.5 5.5 0 1 1 0-11 5.5 5.5 0 0 1 0 11Z"/><path d="M8.75 4.75a.75.75 0 0 0-1.5 0V8c0 .2.08.39.22.53l2.25 2.25a.75.75 0 1 0 1.06-1.06L8.75 7.69Z"/></svg>',
  pr: '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M5 3.25a1.75 1.75 0 1 0-2.5 1.586v6.328a1.75 1.75 0 1 0 1.5 0V8.06c.55.323 1.188.51 1.87.51h2.318a1.75 1.75 0 1 0 0-1.5H5.87a1.75 1.75 0 0 1-1.75-1.75V4.836A1.75 1.75 0 0 0 5 3.25Zm6.5 5.25a1.75 1.75 0 1 1 0-3.5 1.75 1.75 0 0 1 0 3.5Zm-8-6.5a.25.25 0 1 1 0 .5.25.25 0 0 1 0-.5Zm0 8.5a.25.25 0 1 1 0 .5.25.25 0 0 1 0-.5Z"/></svg>',
  tag: '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M1 7.775V2.75C1 1.784 1.784 1 2.75 1h5.025c.464 0 .91.184 1.238.513l6.25 6.25a1.75 1.75 0 0 1 0 2.474l-5.026 5.026a1.75 1.75 0 0 1-2.474 0l-6.25-6.25A1.752 1.752 0 0 1 1 7.775Zm1.5 0c0 .066.026.13.073.177l6.25 6.25a.25.25 0 0 0 .354 0l5.025-5.025a.25.25 0 0 0 0-.354l-6.25-6.25a.25.25 0 0 0-.177-.073H2.75a.25.25 0 0 0-.25.25ZM6 5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"/></svg>',
  sync: '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M1.705 8.005a.75.75 0 0 1 .834.656 5.5 5.5 0 0 0 9.592 2.97l-1.204-1.204a.25.25 0 0 1 .177-.427h3.646a.25.25 0 0 1 .25.25v3.646a.25.25 0 0 1-.427.177l-1.38-1.38A7 7 0 0 1 1.05 8.84a.75.75 0 0 1 .656-.834ZM8 2.5a5.5 5.5 0 0 0-5.396 4.474l1.204 1.204A.25.25 0 0 1 3.63 8.6H-.017a.25.25 0 0 1-.25-.25V4.705a.25.25 0 0 1 .427-.177l1.38 1.38A7 7 0 0 1 14.95 7.16a.75.75 0 1 1-1.49.168A5.5 5.5 0 0 0 8 2.5Z"/></svg>',
  code: '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M4.72 3.22a.75.75 0 0 1 1.06 1.06L2.06 8l3.72 3.72a.75.75 0 1 1-1.06 1.06L.47 8.53a.75.75 0 0 1 0-1.06Zm6.56 0a.75.75 0 1 0-1.06 1.06L13.94 8l-3.72 3.72a.75.75 0 1 0 1.06 1.06l4.25-4.25a.75.75 0 0 0 0-1.06Z"/></svg>',
  check: '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M8 16A8 8 0 1 1 8 0a8 8 0 0 1 0 16Zm3.78-9.72a.75.75 0 0 0-1.06-1.06L6.75 9.19 5.28 7.72a.75.75 0 0 0-1.06 1.06l2 2a.75.75 0 0 0 1.06 0Z"/></svg>',
  graph: '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M1.75 1a.75.75 0 0 1 .75.75v11.75h11.75a.75.75 0 0 1 0 1.5H2a.75.75 0 0 1-.75-.75V1.75A.75.75 0 0 1 1.75 1Z"/><path d="M14.28 4.28a.75.75 0 0 0-1.06-1.06L9.75 6.69 7.28 4.22a.75.75 0 0 0-1.06 0L3.47 6.97a.75.75 0 1 0 1.06 1.06L7 5.56l2.47 2.47a.75.75 0 0 0 1.06 0Z"/></svg>',
};

/* ---------------------------------------------------------------
   Fixed analysis parameters (bin edges/labels are visualization
   choices, not data - they stay hard-coded regardless of source).
   Every statistic below them is computed live from the Parquet file.
   --------------------------------------------------------------- */
const YEAR_EDGES = Array.from({ length: 20 }, (_, i) => i); // 0..19 -> 19 bins
const YEAR_LABELS = YEAR_EDGES.slice(0, -1).map((e) => `${e}–${e + 1}`);

const DAY_BUCKET_EDGES = [0, 1, 7, 30, 90, 365, Infinity];
const DAY_BUCKET_LABELS = ["<1 dia", "1–7 dias", "7–30 dias", "30–90 dias", "90–365 dias", ">365 dias"];

const RATIO_BUCKET_EDGES = [0, 0.25, 0.5, 0.75, 0.9, 1.0000001];
const RATIO_BUCKET_LABELS = ["0–25%", "25–50%", "50–75%", "75–90%", "90–100%"];

const TOP_LANGUAGES_N = 12;

/* ---------------------------------------------------------------
   Stats helpers (no library - dataset is ~100k rows, trivial for JS)
   --------------------------------------------------------------- */
const mean = (arr) => arr.reduce((a, b) => a + b, 0) / arr.length;

function quantile(sortedArr, p) {
  const idx = p * (sortedArr.length - 1);
  const lo = Math.floor(idx), hi = Math.ceil(idx);
  if (lo === hi) return sortedArr[lo];
  return sortedArr[lo] + (sortedArr[hi] - sortedArr[lo]) * (idx - lo);
}
const sortNums = (arr) => [...arr].sort((a, b) => a - b);
const median = (arr) => quantile(sortNums(arr), 0.5);

function histogramCounts(values, edges) {
  const counts = new Array(edges.length - 1).fill(0);
  for (const v of values) {
    for (let i = 0; i < edges.length - 1; i++) {
      const isLast = i === edges.length - 2;
      if (v >= edges[i] && (isLast ? v <= edges[i + 1] : v < edges[i + 1])) {
        counts[i]++;
        break;
      }
    }
  }
  return counts;
}

/* ---------------------------------------------------------------
   Load the Parquet file and compute every RQ01-RQ07 statistic
   client-side (this is the "dynamic" part - no numbers are baked in).
   --------------------------------------------------------------- */
async function loadRows() {
  const res = await fetch(DATASET_URL);
  if (!res.ok) throw new Error(`HTTP ${res.status} ao buscar ${DATASET_URL}`);
  const buffer = await res.arrayBuffer();
  return parquetReadObjects({ file: buffer });
}

function computeStats(rows) {
  const n_total = rows.length;

  // RQ01 - age
  const ageDays = rows.map((r) => r.age_days);
  const ageDaysSorted = sortNums(ageDays);
  const ageYears = ageDays.map((d) => d / 365.25);
  const rq01 = {
    mean_years: mean(ageDays) / 365.25,
    median_years: quantile(ageDaysSorted, 0.5) / 365.25,
    max_years: ageDaysSorted[ageDaysSorted.length - 1] / 365.25,
    years_labels: YEAR_LABELS,
    years_counts: histogramCounts(ageYears, YEAR_EDGES),
  };

  // RQ02 - merged pull requests
  const prs = rows.map((r) => r.merged_pull_requests);
  const prsSorted = sortNums(prs);
  const rq02 = {
    mean: mean(prs),
    median: quantile(prsSorted, 0.5),
    max: prsSorted[prsSorted.length - 1],
    q_labels: ["P25", "Mediana (P50)", "P75", "P90", "P99"],
    q_values: [0.25, 0.5, 0.75, 0.9, 0.99].map((p) => Math.round(quantile(prsSorted, p))),
  };

  // RQ03 - releases
  const releases = rows.map((r) => r.total_releases);
  const zero_pct = (releases.filter((v) => v === 0).length / n_total) * 100;
  const rq03 = {
    mean: mean(releases),
    median: median(releases),
    zero_pct,
    nonzero_pct: 100 - zero_pct,
  };

  // RQ04 - time since last update
  const upd = rows.map((r) => r.time_since_update_days);
  const updSorted = sortNums(upd);
  const rq04 = {
    mean: mean(upd),
    median: quantile(updSorted, 0.5),
    max: updSorted[updSorted.length - 1],
    labels: DAY_BUCKET_LABELS,
    counts: histogramCounts(upd, DAY_BUCKET_EDGES),
  };

  // RQ05 - primary language
  const langCounts = new Map();
  let missingLang = 0;
  for (const r of rows) {
    const lang = r.primary_language;
    if (lang == null) { missingLang++; continue; }
    langCounts.set(lang, (langCounts.get(lang) || 0) + 1);
  }
  const topLangs = [...langCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, TOP_LANGUAGES_N);
  const rq05 = {
    missing: missingLang,
    missing_pct: (missingLang / n_total) * 100,
    labels: [...topLangs.map(([lang]) => lang), "(sem linguagem)"],
    counts: [...topLangs.map(([, c]) => c), missingLang],
  };

  // RQ06 - closed issues ratio
  const ratios = rows.map((r) => r.closed_issues_ratio).filter((v) => v != null);
  const missingRatio = n_total - ratios.length;
  const rq06 = {
    missing_pct: (missingRatio / n_total) * 100,
    mean: mean(ratios),
    median: median(ratios),
    labels: RATIO_BUCKET_LABELS,
    counts: histogramCounts(ratios, RATIO_BUCKET_EDGES),
  };

  // RQ07 - RQ02/RQ03/RQ04 medians per top language
  const topLangNames = topLangs.map(([lang]) => lang);
  const groups = new Map(topLangNames.map((l) => [l, { prs: [], rel: [], upd: [] }]));
  for (const r of rows) {
    const g = groups.get(r.primary_language);
    if (!g) continue;
    g.prs.push(r.merged_pull_requests);
    g.rel.push(r.total_releases);
    g.upd.push(r.time_since_update_days);
  }
  const rq07 = {
    labels: topLangNames,
    median_prs: topLangNames.map((l) => median(groups.get(l).prs)),
    median_releases: topLangNames.map((l) => median(groups.get(l).rel)),
    median_update_days: topLangNames.map((l) => median(groups.get(l).upd)),
  };

  return { n_total, rq01, rq02, rq03, rq04, rq05, rq06, rq07 };
}

const fmt = (n) => n.toLocaleString("pt-BR");
const fmtDec = (n, d = 2) => n.toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d });

function kpi(icon, label, value, sub) {
  const el = document.createElement("div");
  el.className = "kpi-tile";
  el.innerHTML = `<div class="label">${icon}${label}</div><div class="value">${value}</div><div class="sub">${sub || ""}</div>`;
  return el;
}

const tooltip = document.getElementById("tooltip");
function positionTooltip(evt) {
  tooltip.style.left = evt.pageX + "px";
  tooltip.style.top = (evt.pageY - 14) + "px";
}
function hideTooltip() { tooltip.style.opacity = 0; }

/* Vertical bar chart. opts: {scale, colorFor(i), showValueLabels, valueFmt, height, labelEvery} */
function renderVBarChart(svg, labels, values, opts = {}) {
  const W = 600, H = opts.height || 220;
  const padL = 34, padR = 8, padT = 14, padB = 30;
  const plotW = W - padL - padR, plotH = H - padT - padB;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("class", "chart");

  const scale = opts.scale || "linear";
  const valueFmt = opts.valueFmt || ((v) => fmt(v));
  const maxV = Math.max(...values);
  const domainMax = scale === "log" ? Math.log10(maxV + 1) : maxV;
  const y = (v) => scale === "log" ? (Math.log10(v + 1) / domainMax) * plotH : (v / domainMax) * plotH;

  let svgContent = "";
  const gridCount = 4;
  for (let i = 0; i <= gridCount; i++) {
    const gy = padT + plotH - (plotH * i / gridCount);
    svgContent += `<line class="grid-line" x1="${padL}" x2="${W - padR}" y1="${gy}" y2="${gy}" />`;
  }
  svgContent += `<line class="axis-line" x1="${padL}" x2="${W - padR}" y1="${padT + plotH}" y2="${padT + plotH}" />`;

  const n = values.length;
  const gap = 3;
  const barW = (plotW / n) - gap;
  const labelEvery = opts.labelEvery || 1;

  values.forEach((v, i) => {
    const bh = y(v);
    const bx = padL + i * (plotW / n) + gap / 2;
    const by = padT + plotH - bh;
    const bw = Math.max(barW, 1);
    const r = Math.min(4, bw / 2, bh);
    const color = opts.colorFor ? opts.colorFor(i) : "var(--accent-emphasis)";
    const path = bh > 0
      ? `M${bx},${by + bh} L${bx},${by + r} Q${bx},${by} ${bx + r},${by} L${bx + bw - r},${by} Q${bx + bw},${by} ${bx + bw},${by + r} L${bx + bw},${by + bh} Z`
      : "";
    svgContent += `<path class="bar" d="${path}" fill="${color}" data-label="${labels[i]}" data-value="${valueFmt(v)}" style="cursor:pointer"/>`;
    if (opts.showValueLabels && bh > 12) {
      svgContent += `<text class="value-label" x="${bx + bw / 2}" y="${by - 4}" text-anchor="middle">${valueFmt(v)}</text>`;
    }
    if (i % labelEvery === 0) {
      svgContent += `<text class="axis-label" x="${bx + bw / 2}" y="${H - 10}" text-anchor="middle">${labels[i]}</text>`;
    }
  });

  svg.innerHTML = svgContent;
  svg.querySelectorAll(".bar").forEach((bar) => {
    bar.addEventListener("mousemove", (evt) => {
      positionTooltip(evt);
      tooltip.innerHTML = `<b>${bar.dataset.label}</b>: ${bar.dataset.value}`;
      tooltip.style.opacity = 1;
    });
    bar.addEventListener("mouseleave", hideTooltip);
  });
}

/* Horizontal bar chart (language distribution) */
function renderHBarChart(svg, labels, values, opts = {}) {
  const n = labels.length;
  const rowH = 24, padL = 110, padR = 46, padT = 6, padB = 6;
  const W = 600, H = n * rowH + padT + padB;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("class", "chart");
  const plotW = W - padL - padR;
  const maxV = Math.max(...values);
  const valueFmt = opts.valueFmt || ((v) => fmt(v));

  let content = "";
  values.forEach((v, i) => {
    const bw = (v / maxV) * plotW;
    const by = padT + i * rowH + 4;
    const bh = rowH - 8;
    const r = Math.min(4, bh / 2, bw);
    const color = opts.colorFor ? opts.colorFor(i) : "var(--accent-emphasis)";
    const path = bw > 0
      ? `M${padL},${by} L${padL + bw - r},${by} Q${padL + bw},${by} ${padL + bw},${by + r} L${padL + bw},${by + bh - r} Q${padL + bw},${by + bh} ${padL + bw - r},${by + bh} L${padL},${by + bh} Z`
      : "";
    content += `<text class="axis-label" x="${padL - 8}" y="${by + bh / 2 + 3}" text-anchor="end">${labels[i]}</text>`;
    content += `<path class="bar" d="${path}" fill="${color}" data-label="${labels[i]}" data-value="${valueFmt(v)}" style="cursor:pointer"/>`;
    content += `<text class="value-label" x="${padL + bw + 6}" y="${by + bh / 2 + 3}">${valueFmt(v)}</text>`;
  });
  svg.innerHTML = content;
  svg.querySelectorAll(".bar").forEach((bar) => {
    bar.addEventListener("mousemove", (evt) => {
      positionTooltip(evt);
      tooltip.innerHTML = `<b>${bar.dataset.label}</b>: ${bar.dataset.value}`;
      tooltip.style.opacity = 1;
    });
    bar.addEventListener("mouseleave", hideTooltip);
  });
}

/* Picks a step from the 7-stop sequential blue ramp (--blue-1 lightest/low magnitude
   in light mode, --blue-7 darkest/high magnitude - inverted consistently in dark mode). */
function blueRamp(i, n) {
  const steps = 7;
  const idx = 1 + Math.round((i / Math.max(1, n - 1)) * (steps - 1));
  return `var(--blue-${idx})`;
}

function buildTable(container, headers, rows) {
  const table = document.createElement("table");
  table.className = "data-table";
  table.innerHTML = `<thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
    <tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody>`;
  container.appendChild(table);
  return table;
}

function addToggle(card, table) {
  const btn = document.createElement("button");
  btn.className = "toggle-btn";
  btn.textContent = "Ver tabela";
  btn.addEventListener("click", () => {
    const showing = table.style.display === "table";
    table.style.display = showing ? "none" : "table";
    btn.textContent = showing ? "Ver tabela" : "Ocultar tabela";
  });
  card.querySelector(".card-body").appendChild(btn);
}

function makeCard(icon, tag, title, metricNote) {
  const card = document.createElement("div");
  card.className = "card";
  card.innerHTML = `
    <div class="card-header">
      ${icon}
      <span class="rq-tag">${tag}</span>
      <h2>${title}</h2>
    </div>
    <div class="card-body">
      <p class="metric-note">${metricNote}</p>
    </div>`;
  return card;
}
function body(card) { return card.querySelector(".card-body"); }

/* ---------------------------------------------------------------
   Build dashboard
   --------------------------------------------------------------- */
function renderDashboard(DATA) {
  const kpiGrid = document.getElementById("kpi-grid");
  kpiGrid.innerHTML = "";
  kpiGrid.append(
    kpi(ICONS.graph, "Repositórios analisados", fmt(DATA.n_total), "topo de estrelas no GitHub"),
    kpi(ICONS.clock, "Idade mediana", fmtDec(DATA.rq01.median_years, 1) + " anos", "RQ01"),
    kpi(ICONS.pr, "PRs aceitas (mediana)", fmt(DATA.rq02.median), "RQ02 · média " + fmt(Math.round(DATA.rq02.mean))),
    kpi(ICONS.tag, "Sem releases", fmtDec(DATA.rq03.zero_pct, 1) + "%", "RQ03"),
    kpi(ICONS.sync, "Atualização (mediana)", fmt(Math.round(DATA.rq04.median)) + " dias", "RQ04"),
    kpi(ICONS.check, "Issues fechadas (mediana)", fmtDec(DATA.rq06.median * 100, 0) + "%", "RQ06")
  );

  const rqGrid = document.getElementById("rq-grid");
  rqGrid.innerHTML = "";

  // ---- RQ01: age ----
  {
    const card = makeCard(ICONS.clock, "RQ01", "Sistemas populares são maduros/antigos?", "Métrica: idade do repositório (anos desde a criação)");
    const b = body(card);
    const stat = document.createElement("div");
    stat.className = "stat-line";
    stat.innerHTML = `<span class="stat">Mediana: <b>${fmtDec(DATA.rq01.median_years, 1)} anos</b></span>
      <span class="stat">Média: <b>${fmtDec(DATA.rq01.mean_years, 1)} anos</b></span>
      <span class="stat">Máx.: <b>${fmtDec(DATA.rq01.max_years, 1)} anos</b></span>`;
    b.appendChild(stat);
    const wrap = document.createElement("div");
    wrap.className = "chart-wrap";
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    wrap.appendChild(svg);
    b.appendChild(wrap);
    renderVBarChart(svg, DATA.rq01.years_labels, DATA.rq01.years_counts, { labelEvery: 2, valueFmt: (v) => fmt(v) + " repos" });
    buildTable(b, ["Idade (anos)", "Repositórios"],
      DATA.rq01.years_labels.map((l, i) => [l, fmt(DATA.rq01.years_counts[i])]));
    addToggle(card, card.querySelector(".data-table"));
    b.insertAdjacentHTML("beforeend", `<p class="hypothesis"><b>Hipótese informal:</b> a popularidade não está fortemente ligada à idade — a distribuição é relativamente homogênea entre 0 e 19 anos, sem concentração atípica em repositórios muito antigos ou muito novos. Nenhum outlier identificado em amostra de validação (IQR).</p>`);
    rqGrid.appendChild(card);
  }

  // ---- RQ02: merged PRs ----
  {
    const card = makeCard(ICONS.pr, "RQ02", "Sistemas populares recebem muita contribuição externa?", "Métrica: total de pull requests aceitas (escala log — distribuição muito assimétrica)");
    const b = body(card);
    const stat = document.createElement("div");
    stat.className = "stat-line";
    stat.innerHTML = `<span class="stat">Mediana: <b>${fmt(DATA.rq02.median)}</b></span>
      <span class="stat">Média: <b>${fmt(Math.round(DATA.rq02.mean))}</b></span>
      <span class="stat">Máx.: <b>${fmt(DATA.rq02.max)}</b></span>`;
    b.appendChild(stat);
    const wrap = document.createElement("div");
    wrap.className = "chart-wrap";
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    wrap.appendChild(svg);
    b.appendChild(wrap);
    renderVBarChart(svg, DATA.rq02.q_labels, DATA.rq02.q_values, { scale: "log", showValueLabels: true });
    buildTable(b, ["Percentil", "PRs aceitas"],
      DATA.rq02.q_labels.map((l, i) => [l, fmt(DATA.rq02.q_values[i])]));
    addToggle(card, card.querySelector(".data-table"));
    b.insertAdjacentHTML("beforeend", `<p class="hypothesis"><b>Hipótese informal:</b> a contribuição externa é distribuída de forma desigual — a mediana é baixa frente à média, puxada por uma minoria de frameworks/bibliotecas muito utilizadas que concentram milhares de PRs aceitas, enquanto a maioria recebe um volume mais modesto.</p>`);
    rqGrid.appendChild(card);
  }

  // ---- RQ03: releases ----
  {
    const card = makeCard(ICONS.tag, "RQ03", "Sistemas populares lançam releases com frequência?", "Métrica: total de releases publicadas");
    const b = body(card);
    const stat = document.createElement("div");
    stat.className = "stat-line";
    stat.innerHTML = `<span class="stat">Mediana: <b>${fmt(DATA.rq03.median)}</b></span>
      <span class="stat">Média: <b>${fmtDec(DATA.rq03.mean, 1)}</b></span>
      <span class="stat">Sem releases: <b>${fmtDec(DATA.rq03.zero_pct, 1)}%</b></span>`;
    b.appendChild(stat);
    const wrap = document.createElement("div");
    wrap.className = "chart-wrap";
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    wrap.appendChild(svg);
    b.appendChild(wrap);
    renderVBarChart(svg, ["Sem releases (0)", "Com ao menos 1 release"], [DATA.rq03.zero_pct, DATA.rq03.nonzero_pct], {
      showValueLabels: true, valueFmt: (v) => fmtDec(v, 1) + "%", height: 180,
      colorFor: (i) => i === 0 ? "var(--fg-subtle)" : "var(--success-fg)",
    });
    buildTable(b, ["Grupo", "% dos repositórios"], [
      ["Sem releases (0)", fmtDec(DATA.rq03.zero_pct, 1) + "%"],
      ["Com ao menos 1 release", fmtDec(DATA.rq03.nonzero_pct, 1) + "%"],
    ]);
    addToggle(card, card.querySelector(".data-table"));
    b.insertAdjacentHTML("beforeend", `<p class="hypothesis"><b>Observação:</b> quase metade (${fmtDec(DATA.rq03.zero_pct, 1)}%) dos repositórios populares nunca publicou uma release formal — popularidade (estrelas) não implica necessariamente um processo de release estruturado; muitos projetos entregam via commits diretos na branch principal.</p>`);
    rqGrid.appendChild(card);
  }

  // ---- RQ04: update recency ----
  {
    const card = makeCard(ICONS.sync, "RQ04", "Sistemas populares são atualizados com frequência?", "Métrica: tempo desde a última atualização (dias)");
    const b = body(card);
    const stat = document.createElement("div");
    stat.className = "stat-line";
    stat.innerHTML = `<span class="stat">Mediana: <b>${fmt(Math.round(DATA.rq04.median))} dias</b></span>
      <span class="stat">Média: <b>${fmtDec(DATA.rq04.mean, 1)} dias</b></span>
      <span class="stat">Máx.: <b>${fmt(DATA.rq04.max)} dias</b></span>`;
    b.appendChild(stat);
    const wrap = document.createElement("div");
    wrap.className = "chart-wrap";
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    wrap.appendChild(svg);
    b.appendChild(wrap);
    renderVBarChart(svg, DATA.rq04.labels, DATA.rq04.counts, {
      showValueLabels: true, colorFor: (i) => blueRamp(i, DATA.rq04.labels.length),
    });
    buildTable(b, ["Faixa desde a última atualização", "Repositórios"],
      DATA.rq04.labels.map((l, i) => [l, fmt(DATA.rq04.counts[i])]));
    addToggle(card, card.querySelector(".data-table"));
    b.insertAdjacentHTML("beforeend", `<p class="hypothesis"><b>Hipótese informal:</b> repositórios com grande base de usuários recebem manutenção ativa constante — ${fmtDec((DATA.rq04.counts[0] + DATA.rq04.counts[1]) / DATA.n_total * 100, 0)}% foram atualizados há menos de 7 dias, e praticamente nenhum passou mais de um ano sem atividade.</p>`);
    rqGrid.appendChild(card);
  }

  // ---- RQ05: primary language ----
  {
    const card = makeCard(ICONS.code, "RQ05", "Sistemas populares são escritos nas linguagens mais populares?", "Métrica: linguagem primária de cada repositório · referência de comparação externa (ex.: GitHub Octoverse) a incorporar no relatório final");
    const b = body(card);
    const stat = document.createElement("div");
    stat.className = "stat-line";
    stat.innerHTML = `<span class="stat">Sem linguagem definida: <b>${fmtDec(DATA.rq05.missing_pct, 1)}%</b></span>
      <span class="stat">Linguagem líder: <b>${DATA.rq05.labels[0]}</b></span>`;
    b.appendChild(stat);
    const wrap = document.createElement("div");
    wrap.className = "chart-wrap";
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    wrap.appendChild(svg);
    b.appendChild(wrap);
    const realN = DATA.rq05.labels.length - 1;
    renderHBarChart(svg, DATA.rq05.labels, DATA.rq05.counts, {
      colorFor: (i) => i === DATA.rq05.labels.length - 1 ? "var(--fg-subtle)" : blueRamp(i, realN),
    });
    buildTable(b, ["Linguagem", "Repositórios"],
      DATA.rq05.labels.map((l, i) => [l, fmt(DATA.rq05.counts[i])]));
    addToggle(card, card.querySelector(".data-table"));
    b.insertAdjacentHTML("beforeend", `<p class="hypothesis"><b>Hipótese informal:</b> a popularidade continua concentrada em poucas linguagens dominantes, mas ${fmtDec(DATA.rq05.missing_pct, 1)}% dos repositórios não têm linguagem primária identificada (coleções, documentação, etc.), exigindo tratamento explícito como categoria própria.</p>`);
    rqGrid.appendChild(card);
  }

  // ---- RQ06: closed issues ratio ----
  {
    const card = makeCard(ICONS.check, "RQ06", "Sistemas populares possuem alto percentual de issues fechadas?", "Métrica: razão entre issues fechadas e total de issues");
    const b = body(card);
    const stat = document.createElement("div");
    stat.className = "stat-line";
    stat.innerHTML = `<span class="stat">Mediana: <b>${fmtDec(DATA.rq06.median * 100, 0)}%</b></span>
      <span class="stat">Média: <b>${fmtDec(DATA.rq06.mean * 100, 1)}%</b></span>
      <span class="stat">Sem issues (excluído): <b>${fmtDec(DATA.rq06.missing_pct, 1)}%</b></span>`;
    b.appendChild(stat);
    const wrap = document.createElement("div");
    wrap.className = "chart-wrap";
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    wrap.appendChild(svg);
    b.appendChild(wrap);
    renderVBarChart(svg, DATA.rq06.labels, DATA.rq06.counts, {
      showValueLabels: true, colorFor: (i) => blueRamp(i, DATA.rq06.labels.length),
    });
    buildTable(b, ["Faixa de issues fechadas", "Repositórios"],
      DATA.rq06.labels.map((l, i) => [l, fmt(DATA.rq06.counts[i])]));
    addToggle(card, card.querySelector(".data-table"));
    b.insertAdjacentHTML("beforeend", `<p class="hypothesis"><b>Hipótese informal:</b> a maioria dos repositórios fecha uma fração substancial das issues, indicando manutenção ativa; ${fmtDec(DATA.rq06.missing_pct, 1)}% não têm nenhuma issue registrada (razão indefinida, excluídos do cálculo).</p>`);
    rqGrid.appendChild(card);
  }

  // ---- RQ07: cross by language ----
  {
    const card = makeCard(ICONS.graph, "RQ07", "Linguagens mais populares recebem mais contribuição, mais releases e são atualizadas com mais frequência?", "Métrica: RQ02, RQ03 e RQ04 (medianas) por linguagem primária — mesma ordem de linguagens nos 3 gráficos");
    card.classList.add("full");
    const b = body(card);
    const grid = document.createElement("div");
    grid.className = "mini-grid";
    b.appendChild(grid);

    const metrics = [
      { title: "PRs aceitas (mediana) por linguagem", values: DATA.rq07.median_prs, fmtv: (v) => fmt(v) },
      { title: "Releases (mediana) por linguagem", values: DATA.rq07.median_releases, fmtv: (v) => fmt(v) },
      { title: "Dias desde atualização (mediana) por linguagem", values: DATA.rq07.median_update_days, fmtv: (v) => fmt(v) + "d" },
    ];
    metrics.forEach((m) => {
      const box = document.createElement("div");
      box.innerHTML = `<div class="mini-title">${m.title}</div>`;
      const wrap = document.createElement("div");
      wrap.className = "chart-wrap";
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      wrap.appendChild(svg);
      box.appendChild(wrap);
      grid.appendChild(box);
      renderVBarChart(svg, DATA.rq07.labels, m.values, { height: 200, labelEvery: 1, valueFmt: m.fmtv });
    });

    buildTable(b, ["Linguagem", "PRs (mediana)", "Releases (mediana)", "Dias p/ atualização (mediana)"],
      DATA.rq07.labels.map((l, i) => [l, fmt(DATA.rq07.median_prs[i]), fmt(DATA.rq07.median_releases[i]), fmt(DATA.rq07.median_update_days[i]) + "d"]));
    addToggle(card, card.querySelector(".data-table"));
    b.insertAdjacentHTML("beforeend", `<p class="hypothesis"><b>Leitura dos dados:</b> não há um padrão único entre as linguagens mais populares e o volume de contribuição, releases ou frequência de atualização — cada linguagem tem seu próprio ecossistema de ferramentas e convenções de release.</p>`);
    rqGrid.appendChild(card);
  }
}

function renderLoading() {
  const kpiGrid = document.getElementById("kpi-grid");
  kpiGrid.innerHTML = `<div class="kpi-tile" style="grid-column:1/-1"><div class="label">Carregando dataset</div><div class="sub">Baixando unified_sample.parquet do GitHub (~6 MB, 99.984 linhas) e decodificando no navegador…</div></div>`;
}

function renderError(err) {
  const kpiGrid = document.getElementById("kpi-grid");
  kpiGrid.innerHTML = `<div class="kpi-tile" style="grid-column:1/-1; border-color:var(--danger-fg)">
    <div class="label" style="color:var(--danger-fg)">Falha ao carregar o dataset</div>
    <div class="sub">${err.message}. Verifique: (1) conexão com a internet — o arquivo é buscado em <code>${DATASET_URL}</code>; (2) que a página está sendo servida por HTTP, não aberta com <code>file://</code> (o import do hyparquet via <code>node_modules/</code> exige isso) — rode <code>npm install</code> uma vez e depois <code>python3 -m http.server 8000</code> dentro de <code>lab01/dashboard</code>.</div>
  </div>`;
}

document.addEventListener("DOMContentLoaded", async () => {
  renderLoading();
  try {
    const rows = await loadRows();
    const stats = computeStats(rows);
    renderDashboard(stats);
  } catch (err) {
    renderError(err);
  }
});
