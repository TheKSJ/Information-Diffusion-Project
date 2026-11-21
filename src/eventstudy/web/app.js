"use strict";

const $ = (selector, context = document) => context.querySelector(selector);
const $$ = (selector, context = document) => [...context.querySelectorAll(selector)];
const paths = {
  overview: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  events: '<path d="M4 6h16M4 12h16M4 18h10"/><circle cx="19" cy="18" r="2"/>',
  evidence: '<path d="M12 3 4 7v6c0 4 8 8 8 8s8-4 8-8V7l-8-4Z"/><path d="m8 12 3 3 5-6"/>',
  runs: '<path d="M8 4 20 12 8 20V4Z"/>',
  arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>',
  external: '<path d="M14 3h7v7M21 3 10 14"/><path d="M10 3H4a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1v-6"/>',
  search: '<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/>',
  download: '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  book: '<path d="M12 5v16M12 5C9 3 5 3 2 4v15c3-1 7-1 10 2 3-3 7-3 10-2V4c-3-1-7-1-10 1Z"/>',
  refresh: '<path d="M20 8a9 9 0 0 0-15-3L2 8m0-5v5h5m-3 8a9 9 0 0 0 15 3l3-3m0 5v-5h-5"/>',
};
const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.info}</svg>`;
const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
const finite = value => typeof value === "number" && Number.isFinite(value);
const number = (value, digits = 0) => finite(value) ? value.toLocaleString("en-US", {minimumFractionDigits: digits, maximumFractionDigits: digits}) : "—";
const signed = (value, digits = 2) => finite(value) ? `${value > 0 ? "+" : value < 0 ? "−" : ""}${number(Math.abs(value), digits)}` : "—";
const percent = (value, digits = 2) => finite(value) ? `${signed(value * 100, digits)}%` : "—";
const pp = (value, digits = 3) => finite(value) ? `${signed(value, digits)}` : "—";
const signClass = value => finite(value) ? (value >= 0 ? "positive" : "negative") : "";
const pvalue = value => finite(value) ? (value < .0001 ? "< 0.0001" : value.toFixed(5)) : "unavailable";
function date(value, short = false) {
  if (!value) return "—";
  const stamp = new Date(value.length === 10 ? value + "T12:00:00" : value);
  return Number.isNaN(stamp.valueOf()) ? esc(value) : stamp.toLocaleDateString("en-GB", {day: "2-digit", month: "short", ...(short ? {} : {year: "numeric"})});
}
function link(url, label, className = "source-link") {
  try {
    const target = new URL(url);
    if (!["http:", "https:"].includes(target.protocol)) return esc(label);
    return `<a class="${className}" href="${esc(target.href)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`;
  } catch { return esc(label); }
}
const statusLabel = status => ({matched: "Matched", unmatched: "Unmatched", excluded: "Excluded", passed: "Passed", running: "Running", queued: "Queued", failed: "Failed", interrupted: "Interrupted"}[status] || status);
const badge = status => `<span class="tag ${["unmatched", "running", "queued", "interrupted"].includes(status) ? "warn" : status === "excluded" ? "neutral" : status === "failed" ? "danger" : ""}">${esc(statusLabel(status))}</span>`;
const reviewTicker = eventId => state.overview.universe.find(company => eventId?.startsWith(String(company.cik).padStart(10, "0")))?.ticker || "—";
const timingLabel = timing => ({before_open: "Before open", intraday: "During session", after_close: "After close", non_session: "Non-trading day"}[timing] || "Unresolved");
const reasonLabel = reason => ({below_initial_threshold: "Below the 2% initial-response threshold", outside_research_sessions: "Outside the 2021–2025 research sessions", duplicate_ticker_session: "Additional filing on an existing ticker-session", historical_identity_unverified: "Historical security identity unresolved", timestamp_unverified: "Acceptance time unverified", missing_stock_or_market_prices: "Stock or market price data unavailable"}[reason] || (reason ? reason.replaceAll("_", " ") : ""));
const state = {overview: null, evidence: null, view: "overview", chart: "aar", jobs: [], activeJob: null, selectedJob: null,
  events: [], totalEvents: 0, selectedEvent: null, detail: null, request: 0, polling: false,
  connected: false, starting: false, instance: null, dataRevision: null, eventsLoading: false, documentRequest: 0,
  filters: {q: "", year: "all", sector: "all", status: "qualified", sign: "all", timing: "all", sort: "recent", page: 1, limit: 12}};

async function api(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(path, {cache: "no-store", ...options, signal: controller.signal});
    const body = await response.json();
    if (!response.ok) {
      const error = new Error(body.error || `Request failed (${response.status})`);
      error.status = response.status;
      throw error;
    }
    return body;
  } catch (error) {
    if (error.name === "AbortError" || error.name === "TypeError") {
      setConnection(false);
      throw new Error("The local desk is unavailable. Open Research Desk.cmd to start it again, then reconnect.");
    }
    throw error;
  } finally { clearTimeout(timeout); }
}
function setConnection(connected) {
  state.connected = connected;
  $("#connection-banner").hidden = connected;
  $("#connection-pill").classList.toggle("offline", !connected);
  $("#connection-label").textContent = connected ? "Connected" : "Disconnected";
  renderJobs();
}
function toast(message, error = false) {
  const element = $("#toast");
  element.textContent = message;
  element.className = `visible${error ? " error" : ""}`;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { element.className = ""; }, 6000);
}
function pageHead(kicker, title, description, actions = "") {
  return `<div class="page-head"><div><div class="page-kicker"><span class="kicker-line"></span>${esc(kicker)}</div><h1>${title}</h1><p>${description}</p></div>${actions ? `<div class="page-head-actions">${actions}</div>` : ""}</div>`;
}
function empty(title, text) { return `<div class="empty-state">${icon("info")}<h2>${esc(title)}</h2><p>${esc(text)}</p></div>`; }

function lineChart(rows, options = {}) {
  if (!rows.length || !rows.some(row => finite(row[options.value || "aar_percent"]))) return empty("No return window", "This observation does not have a valid analytical return window.");
  const available = options.small ? window.innerWidth - 70 : ($("#trajectory-chart")?.clientWidth || window.innerWidth - 70);
  const width = Math.max(320, Math.min(options.small ? 620 : 720, available)), height = options.small ? 260 : 310;
  const margin = {left: 57, right: 24, top: 27, bottom: 45};
  const field = options.value || "aar_percent";
  const low = options.low, high = options.high;
  const all = rows.flatMap(row => [row[field], row.control, low ? row[low] : null, high ? row[high] : null]).filter(finite);
  let min = Math.min(0, ...all), max = Math.max(0, ...all);
  const span = Math.max(max - min, .15);
  min -= span * .16; max += span * .16;
  const x = offset => margin.left + (offset + 5) / 15 * (width - margin.left - margin.right);
  const y = value => height - margin.bottom - (value - min) / (max - min) * (height - margin.top - margin.bottom);
  const points = (items, fieldName) => items.map(row => `${x(row.offset).toFixed(2)},${y(row[fieldName]).toFixed(2)}`).join(" ");
  const segments = fields => {
    const result = []; let current = [];
    for (const row of rows) {
      if (fields.every(key => finite(row[key]))) current.push(row);
      else if (current.length) { result.push(current); current = []; }
    }
    if (current.length) result.push(current);
    return result;
  };
  let markup = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(options.title || "Abnormal returns by trading-session offset")}"><title>${esc(options.title || "Event-time returns")}</title>`;
  markup += `<rect x="${x(1)}" y="${margin.top}" width="${x(5)-x(1)}" height="${height-margin.top-margin.bottom}" fill="#f2efdf"/><text x="${x(3)}" y="${margin.top - 9}" text-anchor="middle" class="svg-note">PRIMARY POST WINDOW</text>`;
  for (let i = 0; i <= 4; i++) {
    const value = min + (max-min)*i/4;
    markup += `<line x1="${margin.left}" y1="${y(value)}" x2="${width-margin.right}" y2="${y(value)}" stroke="#e6e9de" stroke-width=".8"/><text class="svg-axis" x="${margin.left-12}" y="${y(value)+3}" text-anchor="end">${value.toFixed(Math.max(Math.abs(min),Math.abs(max)) < 1 ? 2 : 1)}%</text>`;
  }
  for (const offset of [-5, -3, 0, 1, 3, 5, 7, 10]) {
    markup += `<text class="svg-axis" x="${x(offset)}" y="${height-margin.bottom+23}" text-anchor="middle">${offset > 0 ? "+" : ""}${offset}</text>`;
  }
  markup += `<line x1="${margin.left}" y1="${y(0)}" x2="${width-margin.right}" y2="${y(0)}" stroke="#b8c2ac" stroke-width=".9"/><line x1="${x(0)}" y1="${margin.top}" x2="${x(0)}" y2="${height-margin.bottom}" stroke="#a18b62" stroke-dasharray="3 4"/>`;
  if (low && high) for (const group of segments([low,high])) markup += `<polygon points="${points(group,high)} ${points([...group].reverse(),low)}" fill="#dfe8d7" opacity=".8"/>`;
  for (const group of segments(["control"])) markup += `<polyline class="chart-line control" points="${points(group,"control")}"/>`;
  for (const group of segments([field])) markup += `<polyline class="chart-line" points="${points(group,field)}"/>`;
  for (const row of rows) {
    if (finite(row[field])) {
      const tip = `${row.offset > 0 ? "+" : ""}${row.offset} session${row.offset === 1 ? "" : "s"} · ${signed(row[field], 3)}%`;
      markup += `<circle class="chart-point" cx="${x(row.offset)}" cy="${y(row[field])}" r="3.2" tabindex="0" aria-label="${esc(tip)}" data-tip="${esc(tip)}"><title>${esc(tip)}</title></circle>`;
    }
  }
  markup += `<text class="svg-note" x="${(width+margin.left-margin.right)/2}" y="${height-4}" text-anchor="middle">TRADING SESSIONS RELATIVE TO VERIFIED FILING ALIGNMENT</text></svg>`;
  return markup;
}
function forest(primary) {
  const issuer = primary.issuer_cluster?.ci95_pp, quarter = primary.quarter_cluster_sensitivity?.ci95_pp;
  if (!issuer || !quarter || !finite(primary.estimate_pp)) return `<p class="small-note">Clustered uncertainty is unavailable for this sample.</p>`;
  const min = Math.min(0, issuer[0], quarter[0]) - .14, max = Math.max(issuer[1], quarter[1]) + .12;
  const x = value => 60+(value-min)/(max-min)*260;
  return `<svg viewBox="0 0 370 164" role="img" aria-label="Issuer and quarter confidence intervals in percentage points">
    <line x1="${x(0)}" x2="${x(0)}" y1="13" y2="123" stroke="#aab89c" stroke-dasharray="3 3"/>
    <text class="forest-label" x="${x(0)}" y="145" text-anchor="middle">0</text>
    ${[[issuer,"Issuer clustered",42,"#54744c"],[quarter,"Quarter sensitivity",96,"#b09765"]].map(([interval,label,y,color])=>`<text class="forest-label" x="20" y="${y-15}">${label}</text><line x1="${x(interval[0])}" x2="${x(interval[1])}" y1="${y}" y2="${y}" stroke="${color}" stroke-width="3"/><circle cx="${x(primary.estimate_pp)}" cy="${y}" r="4" fill="${color}"/><text class="forest-label" x="${x(interval[0])}" y="${y+17}" text-anchor="middle">${signed(interval[0],2)}</text><text class="forest-label" x="${x(interval[1])}" y="${y+17}" text-anchor="middle">${signed(interval[1],2)}</text>`).join("")}
    <text class="svg-note" x="255" y="145" text-anchor="middle">95% CI · PERCENTAGE POINTS</text></svg>`;
}

function renderOverview() {
  const data = state.overview, summary = data.summary, primary = data.primary;
  if (!data.ready) {
    $("#main").innerHTML = pageHead("RESEARCH WORKSPACE", "Your research desk.", "Start with a validated research snapshot.") + empty("No saved study yet", "Use the command-line collection workflow to obtain genuine source data, or run the isolated offline demonstration from Run Center.");
    return;
  }
  const interval = primary.issuer_cluster?.ci95_pp || [];
  const verification = state.jobs.find(job => job.action === "tests" && job.status === "passed" && job.tests)?.tests || data.verification.tests;
  const funnel = [
    ["Candidates", summary.candidate_events, "original Item 2.02 filings", "all"],
    ["In research window", summary.verified_candidates_in_research_sessions, "2021–2025 sessions", "in_window"],
    ["Valid observations", summary.analytical_events, "unique ticker-sessions", "valid"],
    ["Large initial moves", summary.included_large_move_events, "|AR₀| ≥ 2%", "qualified"],
    ["Matched pairs", summary.matched_controls, "primary estimator", "matched"],
  ];
  const sectors = data.secondary.filter(row => row.dimension === "sector");
  const sectorMax = Math.max(1, ...sectors.map(row => Math.abs(row.mean_signed_post_car_percent)));
  $("#main").innerHTML = `<div class="fade-in">${pageHead("US EQUITIES / 2021—2025", "The next five sessions.", "A filing-timed event study of large price movements across 30 US companies.", `<button class="button" data-document="report">${icon("book")} Read full report</button><button class="button primary" data-task="tests">${icon("runs")} Run verification</button>`)}
    <div class="snapshot-caption"><span class="data-kind"><span></span> Genuine SEC filings & adjusted daily prices</span><span>Snapshot ${date(data.snapshot.retrieved_at)} <span class="mobile-hide">&nbsp; / &nbsp; ${verification ? `${number(verification.tests)} tests in last saved check` : "Verification available in Run Center"}</span></span></div>
    <section class="metrics" aria-label="Primary study results">
      <div class="metric"><div class="metric-label">Primary paired difference</div><div class="metric-number">${pp(primary.estimate_pp)}<small>pp</small></div><div class="metric-caption">Signed post CAR · filing minus control</div></div>
      <div class="metric"><div class="metric-label">95% confidence interval</div><div class="metric-number interval">${pp(interval[0])}<span>to</span>${pp(interval[1])}</div><div class="metric-caption">Percentage points · issuer clustered</div></div>
      <div class="metric"><div class="metric-label">Matched sample</div><div class="metric-number">${number(primary.n_pairs)}<span class="divider">/</span>${number(primary.n_issuers)}</div><div class="metric-caption">Pairs / issuers · ${number(primary.n_calendar_quarters)} calendar quarters</div></div>
      <div class="metric"><div class="metric-label">Unmatched events</div><div class="metric-number">${number(summary.unmatched_events)}</div><div class="metric-caption">Retained in descriptive analysis</div></div>
    </section>
    <section class="chart-grid">
      <div class="panel"><div class="panel-head"><div><span class="eyebrow">THE RESPONSE OVER TIME</span><h2>Abnormal returns, session by session</h2></div><div class="segmented" role="group" aria-label="Chart measure"><button data-chart="aar" class="${state.chart === "aar" ? "active" : ""}" aria-pressed="${state.chart === "aar"}">AVERAGE</button><button data-chart="caar" class="${state.chart === "caar" ? "active" : ""}" aria-pressed="${state.chart === "caar"}">CUMULATIVE</button></div></div><p class="panel-subtitle" id="trajectory-subtitle"></p><div class="chart" id="trajectory-chart"></div><div class="chart-legend"><span class="legend-group"><span class="legend-item"><i class="legend-dash"></i> <span id="trajectory-measure">${state.chart === "aar" ? "Average AR" : "Additive CAAR"}</span></span><span class="legend-item"><i class="legend-square"></i> Pointwise 95% CI</span></span><span>n = ${number(summary.included_large_move_events)} · descriptive</span></div></div>
      <div class="panel inference-panel"><div class="panel-head"><div><span class="eyebrow">ESTIMATE & UNCERTAINTY</span><h2>Two views of dependence</h2></div></div><div class="primary-value"><strong>${pvalue(primary.issuer_cluster?.p_one_sided)}</strong><span>one-sided p</span></div><p class="inference-sub">Primary continuation hypothesis · issuer clustered</p><div class="forest-chart">${forest(primary)}</div><div class="inference-bottom">${icon("info")}<span>${primary.quarter_cluster_sensitivity?.ci95_pp?.[0] <= 0 && primary.quarter_cluster_sensitivity?.ci95_pp?.[1] >= 0 ? "The quarter-based interval crosses zero. " : ""}Dependence assumptions matter.</span></div></div>
    </section>
    <section class="panel funnel-panel"><div class="section-title"><div><h2>From source to sample</h2><p>Every exclusion remains visible in the event ledger.</p></div><a class="text-link" href="#/events">Explore the ledger <span>↗</span></a></div><div class="funnel">${funnel.map(([label,count,caption,status])=>`<${status ? "button" : "div"} class="funnel-step" ${status ? `data-explore="${status}"` : ""}><span class="funnel-label">${label}</span><span class="funnel-number">${number(count)}</span><span class="funnel-meta">${caption}</span><span class="funnel-bar"><span style="width:${Math.max(1,count/summary.candidate_events*100)}%"></span></span></${status ? "button" : "div"}>`).join("")}</div></section>
    <section class="bottom-grid"><div class="panel"><div class="panel-head"><div><span class="eyebrow">DESCRIPTIVE COMPARISON</span><h2>Initial direction, carried forward</h2></div><span class="tag neutral">BY SECTOR</span></div><p class="panel-subtitle">Mean signed CAR[+1,+5] among qualifying filing events. These are not paired estimates.</p><div class="sector-list">${sectors.map(row=>`<div class="sector-row"><span class="sector-name">${esc(row.group)}</span><span class="sector-track"><span class="${row.mean_signed_post_car_percent < 0 ? "negative" : ""}" style="width:${Math.abs(row.mean_signed_post_car_percent)/sectorMax*100}%"></span></span><span class="sector-value ${signClass(row.mean_signed_post_car_percent)}">${signed(row.mean_signed_post_car_percent,2)}%</span></div>`).join("")}</div></div>
      <div class="panel guardrails"><span class="eyebrow">BEFORE INTERPRETING THE RESULT</span><div class="guardrail"><span class="guardrail-icon">${icon("clock")}</span><div><strong>Filing time is not first-release time.</strong><p>No independently verified first-public release clocks. The clean-timing sensitivity is unavailable.</p><a class="text-link" href="#/evidence">Inspect timing evidence ↗</a></div></div><div class="guardrail"><span class="guardrail-icon">${icon("events")}</span><div><strong>Matching needs judgment.</strong><p>Median initial-move gap ${number(data.matching.magnitude_gap_median_pp,2)} pp; maximum ${number(data.matching.magnitude_gap_max_pp,2)} pp. ${number(data.matching.year_fallback_count)} controls come from another year.</p><button class="text-link" data-explore="matched" data-sort="gap">Inspect the widest gaps ↗</button></div></div></div></section>
    ${robustnessTable(data.results)}
    <p class="research-note"><strong>Read this as a retrospective conditional comparison.</strong> Selection uses a realized day-zero movement. Daily data and this selected surviving-stock universe do not establish causality, intraday diffusion speed, or a profitable strategy.</p></div>`;
  drawTrajectory();
}

function drawTrajectory() {
  const cumulative = state.chart === "caar";
  $("#trajectory-measure").textContent = cumulative ? "Additive CAAR" : "Average AR";
  $("#trajectory-subtitle").textContent = cumulative ? "Additive cumulative average AR from session −5; no compounding or smoothing." : `Average market-model AR; ${number(state.overview.summary.included_large_move_events)} qualifying filing events, including unmatched observations.`;
  $("#trajectory-chart").innerHTML = lineChart(state.overview.trajectory, {value: cumulative ? "caar_percent" : "aar_percent", low: cumulative ? "caar_ci_low" : "aar_ci_low", high: cumulative ? "caar_ci_high" : "aar_ci_high", title: cumulative ? "Cumulative average abnormal returns from session minus five" : "Average abnormal returns by session"});
  $$('[data-chart]').forEach(button => { button.classList.toggle("active", button.dataset.chart === state.chart); button.setAttribute("aria-pressed", button.dataset.chart === state.chart); });
}
function robustnessTable(rows) {
  const labels = {primary: "Primary · 2% threshold", threshold_0_015: "1.5% threshold", threshold_0_025: "2.5% threshold", nonoverlap_no_other_economic_items: "Non-overlap, no other economic items", simple_market_adjusted: "Simple market-adjusted returns", independently_verified_first_release_same_session: "Verified first-release timing"};
  return `<section class="panel results-panel"><div class="panel-head"><div><span class="eyebrow">FIXED SPECIFICATION & SENSITIVITIES</span><h2>Keep the full picture in view</h2></div><a href="/download/results.csv" class="text-link">Export table ↓</a></div><div class="table-wrap"><table class="data-table"><thead><tr><th>Specification</th><th class="numeric">Pairs</th><th class="numeric">Difference · pp</th><th class="numeric">95% CI · pp</th><th class="numeric">One-sided p</th></tr></thead><tbody>${rows.map(row=>`<tr><td>${esc(labels[row.specification.replaceAll(".","_")] || labels[row.specification] || row.specification)}</td><td class="numeric">${row.n_pairs ? number(row.n_pairs) : "—"}</td><td class="numeric">${pp(row.estimate_pp)}</td><td class="numeric">${finite(row.ci95_low_pp) ? `${pp(row.ci95_low_pp,2)} to ${pp(row.ci95_high_pp,2)}` : "Unavailable"}</td><td class="numeric">${finite(row.p_one_sided) ? pvalue(row.p_one_sided) : "—"}</td></tr>`).join("")}</tbody></table></div><p class="small-note">Sensitivities are prespecified and exploratory. Multiple comparisons must not replace the primary hypothesis. The verified first-release subset has insufficient evidence.</p></section>`;
}

function options(values, selected, allLabel) { return `<option value="all">${allLabel}</option>` + values.map(value => `<option value="${esc(value)}" ${String(selected) === String(value) ? "selected" : ""}>${esc(value)}</option>`).join(""); }
function renderExplorer() {
  const facets = state.overview.facets, filter = state.filters;
  $("#main").innerHTML = `<div class="fade-in">${pageHead("SOURCE-LEVEL INSPECTION", "Every event has a trail.", "Filter observations, inspect the return window, and compare each event with its actual control. The primary estimate stays fixed.", `<a class="button" id="export-events" href="/api/events?format=csv">${icon("download")} Export filtered events</a>`)}
    <div class="filter-bar"><label class="search-box">${icon("search")}<input id="event-search" aria-label="Search ticker, company or accession" placeholder="Find a ticker, company or accession…" value="${esc(filter.q)}"></label><select data-filter="sector" aria-label="Filter by sector">${options(facets.sectors,filter.sector,"All sectors")}</select><select data-filter="year" aria-label="Filter by year">${options(facets.years,filter.year,"All years")}</select><select data-filter="status" aria-label="Filter by sample status">${[["qualified","Qualifying events"],["in_window","In research window"],["valid","Valid observations"],["matched","Matched"],["unmatched","Unmatched"],["excluded","Excluded"],["all","All candidates"]].map(([value,label])=>`<option value="${value}" ${filter.status === value ? "selected" : ""}>${label}</option>`).join("")}</select><select data-filter="sign" aria-label="Filter by initial response">${[["all","Either direction"],["positive","Positive initial AR"],["negative","Negative initial AR"]].map(([value,label])=>`<option value="${value}" ${filter.sign === value ? "selected" : ""}>${label}</option>`).join("")}</select><select data-filter="sort" aria-label="Sort events">${[["recent","Most recent"],["magnitude","Largest initial move"],["gap","Widest matching gap"]].map(([value,label])=>`<option value="${value}" ${filter.sort === value ? "selected" : ""}>${label}</option>`).join("")}</select></div>
    <div class="explorer-layout"><section class="panel"><div class="table-topline"><span id="event-count">Loading observations…</span><span>RETURNS IN %</span></div><div class="table-wrap"><table class="data-table"><thead><tr><th>Company</th><th>Session 0</th><th class="numeric">AR₀</th><th class="numeric">Signed CAR</th><th>Status</th></tr></thead><tbody id="events-body"><tr><td colspan="5" class="loading-row">Loading the ledger…</td></tr></tbody></table></div><div class="pagination"><span id="page-label"></span><div class="pagination-controls"><button id="previous-page" aria-label="Previous page">←</button><button id="next-page" aria-label="Next page">→</button></div></div></section><aside class="panel detail-panel" id="event-detail" aria-live="polite">${empty("Select an observation", "Choose any event to inspect its timing, abnormal returns, source evidence and matched control.")}</aside></div><p class="research-note">Filter results are descriptive subsets. They do not refit the model, change matching, or recalculate the primary hypothesis.</p></div>`;
  $("#event-search").addEventListener("input", event => { clearTimeout(renderExplorer.searchTimer); state.filters.q = event.target.value; state.filters.page = 1; state.request++; setEventsBusy(true); renderExplorer.searchTimer = setTimeout(loadEvents, 220); });
  $$('[data-filter]').forEach(select => select.addEventListener("change", () => { clearTimeout(renderExplorer.searchTimer); state.filters[select.dataset.filter] = select.value; state.filters.page = 1; loadEvents(); }));
  $("#previous-page").onclick = () => { state.filters.page--; loadEvents(); };
  $("#next-page").onclick = () => { state.filters.page++; loadEvents(); };
  loadEvents();
}
function setEventsBusy(busy) {
  state.eventsLoading = busy;
  $("#events-body")?.closest("table")?.setAttribute("aria-busy", String(busy));
  $("#events-body")?.closest("section")?.classList.toggle("table-busy", busy);
  if (busy) { $("#previous-page").disabled = true; $("#next-page").disabled = true; }
  renderJobs();
}
async function loadEvents() {
  if (state.view !== "events" || !$("#export-events")) return;
  const request = ++state.request;
  setEventsBusy(true);
  const query = new URLSearchParams(state.filters);
  $("#export-events").href = `/api/events?${query}&format=csv`;
  try {
    const data = await api(`/api/events?${query}`);
    if (request !== state.request || state.view !== "events") return;
    state.events = data.items; state.totalEvents = data.total; state.filters.page = data.page;
    setEventsBusy(false);
    $("#event-count").innerHTML = `<strong>${number(data.total)}</strong> observations <span class="mobile-hide">/ matching your filters</span>`;
    $("#events-body").innerHTML = data.items.length ? data.items.map(row=>`<tr class="event-row ${row.event_id === state.selectedEvent ? "selected" : ""}" data-event="${esc(row.event_id)}" tabindex="0" aria-label="Inspect ${esc(row.ticker)} on ${esc(row.event_session)}"><td><div class="ticker-cell"><span class="ticker-mark">${esc(row.ticker.slice(0,2))}</span><span><span class="ticker-name">${esc(row.ticker)}</span><span class="company-name">${esc(row.company)}</span></span></div></td><td>${date(row.event_session)}</td><td class="numeric ${signClass(row.ar0)}">${percent(row.ar0)}</td><td class="numeric ${signClass(row.signed_post_car)}">${percent(row.signed_post_car)}</td><td>${badge(row.sample_status)}</td></tr>`).join("") : '<tr><td colspan="5" class="loading-row">No observations match these filters. Try a broader search.</td></tr>';
    $("#page-label").textContent = data.total ? `PAGE ${data.page} OF ${Math.ceil(data.total/data.limit)}` : "NO MATCHES";
    $("#previous-page").disabled = data.page <= 1;
    $("#next-page").disabled = data.page * data.limit >= data.total;
    if (!state.selectedEvent || !data.items.some(row => row.event_id === state.selectedEvent)) state.selectedEvent = data.items[0]?.event_id || null;
    if (state.selectedEvent) await selectEvent(state.selectedEvent);
    else $("#event-detail").innerHTML = empty("No matching event", "Adjust your filters to return to the research ledger.");
  } catch (error) {
    if (request !== state.request || state.view !== "events") return;
    state.eventsLoading = false;
    $("#events-body").innerHTML = `<tr><td colspan="5" class="loading-row">${esc(error.message)}<br><button class="button" data-retry-events>Retry loading events</button></td></tr>`;
    $("#event-detail").innerHTML = empty("Events could not load", "Reconnect and retry. Previously selected values are not shown as a new result.");
    $("#event-count").textContent = "Events unavailable";
    state.events = []; state.selectedEvent = null;
    renderJobs();
  }
}
async function selectEvent(id, reveal = false) {
  state.selectedEvent = id;
  const request = state.request;
  $("#event-detail").innerHTML = '<div class="initial-loading"><div class="spinner"></div><p>Loading the observation…</p></div>';
  $$("[data-event]").forEach(row => row.classList.toggle("selected", row.dataset.event === id));
  try {
    const detail = await api(`/api/event/${encodeURIComponent(id)}`);
    if (state.view !== "events" || state.selectedEvent !== id || request !== state.request) return;
    state.detail = detail;
    drawDetail(detail);
    if (reveal && window.matchMedia("(max-width:1300px)").matches) $("#event-detail").scrollIntoView({behavior: window.matchMedia("(prefers-reduced-motion:reduce)").matches ? "auto" : "smooth", block:"start"});
  } catch (error) {
    if (state.view === "events" && state.selectedEvent === id && request === state.request) $("#event-detail").innerHTML = empty("Observation unavailable", error.message);
  }
}
function drawDetail(detail) {
  const event = detail.event, pair = detail.pair;
  let eventSum = 0, controlSum = 0;
  const control = new Map(detail.control_returns.map(row => [row.offset, row]));
  const rows = detail.returns.map(row => { eventSum = finite(eventSum) && finite(row.abnormal_return) ? eventSum + row.abnormal_return * 100 : null; const item = control.get(row.offset); controlSum = finite(controlSum) && finite(item?.abnormal_return) ? controlSum + item.abnormal_return * 100 : null; return {offset: row.offset, cumulative: eventSum, control: item ? controlSum : null}; });
  $("#event-detail").innerHTML = `<div class="detail-head"><button class="text-link back-to-ledger" data-return-ledger>← Back to event list</button><span class="eyebrow">OBSERVATION INSPECTOR</span><div class="detail-title"><h2>${esc(event.ticker)}</h2>${badge(event.sample_status)}</div><div class="detail-company">${esc(event.company)} · ${esc(event.sector)}</div><div class="detail-meta">${icon("clock")} ${date(event.event_session)} <span>·</span> ${esc(timingLabel(event.timing_class))}</div></div>
    <div class="detail-summary"><div><small>DAY-ZERO ABNORMAL RETURN</small><strong class="${signClass(event.ar0)}">${percent(event.ar0)}</strong></div><div><small>SIGNED CAR · +1 TO +5</small><strong class="${signClass(event.signed_post_car)}">${percent(event.signed_post_car)}</strong></div></div>
    <div class="chart-mini-label">ADDITIVE CAR FROM SESSION −5 · %</div><div class="chart">${lineChart(rows,{value:"cumulative",small:true,title:"Event and matched-control additive cumulative abnormal returns"})}</div><div class="chart-legend"><span class="legend-item"><i class="legend-dash"></i> Filing event</span>${pair ? '<span class="legend-item"><i class="legend-dash control"></i> Matched control</span>' : '<span>No matched control</span>'}</div>
    ${event.primary_reason ? `<div class="detail-section"><div class="audit-callout">${esc(reasonLabel(event.primary_reason))}. Preserved in the ledger; outside the primary large-move sample.</div></div>` : ""}
    ${pair ? `<div class="detail-section"><h3>THE ACTUAL MATCHED PAIR</h3><table class="comparison"><thead><tr><th></th><th>Filing</th><th>Control</th></tr></thead><tbody><tr><td>Session 0</td><td>${esc(pair.event_session)}</td><td>${esc(pair.control_session)}</td></tr><tr><td>Initial AR</td><td>${percent(pair.event_ar0)}</td><td>${percent(pair.control_ar0)}</td></tr><tr><td>Signed post CAR</td><td>${percent(pair.event_signed_post_car)}</td><td>${percent(pair.control_signed_post_car)}</td></tr><tr><td>Pair difference</td><td colspan="2">${pp(pair.difference*100)} pp</td></tr></tbody></table><div class="audit-callout">Initial-magnitude gap: ${number(pair.magnitude_gap*100,2)} pp. ${pair.year_fallback ? "Control selected from another study year." : "Same-year control."} No magnitude caliper was imposed.</div></div>` : !event.primary_reason ? `<div class="detail-section"><h3>NO ELIGIBLE MATCH</h3><p class="event-help">This qualifying event is retained for descriptive analysis. It does not enter the paired primary estimator.</p></div>` : ""}
    <div class="detail-section"><h3>ACCEPTANCE TIME & SESSION ALIGNMENT</h3><div class="timing-list"><div class="timing-item"><label>RAW SUBMISSIONS API VALUE</label><span>${esc(event.raw_acceptance_timestamp || "Unavailable")}</span></div><div class="timing-item verified"><label>VERIFIED ACCEPTANCE · US EASTERN</label><span>${esc(event.verified_acceptance_timestamp || "Unavailable")}</span></div><div class="timing-item verified"><label>ALIGNED TRADING SESSION</label><span>${esc(event.event_session)} · ${esc(timingLabel(event.timing_class))}</span></div></div>${event.discrepancy_changes_session ? `<div class="audit-callout">The raw API value implies ${esc(event.raw_api_session)}. Verification changes the session to ${esc(event.event_session)}.</div>` : ""}${event.intraday_prefiling_activity ? '<div class="audit-callout">Intraday filing: the daily return also contains trading before acceptance.</div>' : ""}<div class="source-actions">${link(event.source_url,"SEC filing index","button small")}${link(event.primary_document_url,"Original filing","button small")}</div><p class="accession">${esc(event.accessionNumber)}</p></div>
    ${event.release_review_notes || event.other_economic_items ? `<div class="detail-section"><h3>DISCLOSURE REVIEW</h3><p class="event-help">${esc(event.release_review_notes || `Other disclosed economic items: ${event.other_economic_items}`)}</p>${event.nonstandard_disclosure_flag ? '<div class="audit-callout">Flagged as a nonstandard Item 2.02 disclosure. Retained under the locked inclusion rule.</div>' : ""}${event.release_evidence_url ? `<div class="source-actions">${link(event.release_evidence_url,"Associated exhibit","button small")}</div>` : ""}</div>` : ""}
    <details class="model-details"><summary>Inspect the model and arithmetic</summary><div class="model-grid"><div><label>DAILY ALPHA</label><span>${percent(event.alpha,4)}</span></div><div><label>BETA</label><span>${number(event.beta,4)}</span></div><div><label>ESTIMATION R²</label><span>${number(event.r_squared,4)}</span></div><div><label>PAIRED OBSERVATIONS</label><span>${number(event.estimation_valid)}</span></div><div><label>PRE-CAR · −5 TO −1</label><span>${percent(event.car_pre_5_1)}</span></div><div><label>POST-CAR · +1 TO +10</label><span>${percent(event.car_post_1_10)}</span></div></div><p class="model-formula">AR = R(stock) − α − β × R(SPY)<br>Signed post CAR = sign(AR₀) × Σ AR[+1,+5]<br>Estimation: ${esc(event.estimation_first || "—")} to ${esc(event.estimation_last || "—")}</p><button class="text-link" data-document="arithmetic">See worked calculations ↗</button></details>`;
}

async function renderEvidence() {
  $("#main").innerHTML = '<div class="initial-loading"><div class="spinner"></div><p>Opening the source evidence…</p></div>';
  try {
    state.evidence ||= await api("/api/evidence");
    if (state.view !== "evidence") return;
    const evidence = state.evidence, data = state.overview;
    $("#main").innerHTML = `<div class="fade-in">${pageHead("PROVENANCE & QUALITY", "Keep the evidence in view.", "The filing clock, the information clock, and the audit trail behind every observation.", `<button class="button" data-document="audit">${icon("book")} Read source audit</button><a class="button primary" href="/download/timestamps.csv">${icon("download")} Export timestamps</a>`)}
      <div class="evidence-stats"><div class="evidence-stat"><span class="eyebrow">TIMESTAMP DISCREPANCIES</span><strong>${number(evidence.discrepancy_count)}<small> / ${number(data.summary.candidate_events)}</small></strong><p>Raw API time differs from the authoritative filing index.</p></div><div class="evidence-stat"><span class="eyebrow">CHANGES TO SESSION 0</span><strong>${number(evidence.session_change_count)}</strong><p>Verification changes the trading day used in the study.</p></div><div class="evidence-stat warn"><span class="eyebrow">VERIFIED FIRST-RELEASE CLOCKS</span><strong>${number(data.summary.release_timing_verified)}</strong><p>Clean-timing sensitivity unavailable. No release times are invented.</p></div></div>
      <section class="panel section-panel"><div class="panel-head"><div><span class="eyebrow">WHEN A TIMESTAMP CHANGES THE TRADING DAY</span><h2>Friday or Monday makes a difference.</h2></div><span class="tag warn">${number(evidence.session_change_count)} VERIFIED CASES</span></div><div class="table-wrap"><table class="data-table evidence-table"><thead><tr><th>Issuer</th><th>Raw API timestamp / implied session</th><th>Verified Eastern timestamp / session</th><th>Evidence</th></tr></thead><tbody>${evidence.session_changes.map(row=>`<tr><td><span class="review-ticker">${esc(row.ticker)}</span></td><td><code class="warn-code">${esc(row.raw_acceptance_timestamp)}</code><small>Implied session ${esc(row.raw_api_session)}</small></td><td><code>${esc(row.verified_acceptance_timestamp)}</code><small>Verified session ${esc(row.event_session)}</small></td><td>${link(row.timestamp_source,"SEC index")}</td></tr>`).join("") || '<tr><td colspan="4">No session-changing discrepancies in this snapshot.</td></tr>'}</tbody></table></div><p class="small-note" style="padding:0 23px 12px">Eastern daylight-saving rules and actual NYSE closing times are applied separately to each filing. No blanket four- or five-hour correction is used.</p></section>
      <div class="provenance-grid section-panel"><section class="panel provenance-card"><span class="eyebrow">HISTORICAL SECURITY IDENTITY</span><div class="identity-strip"><span class="identity-icon">${icon("evidence")}</span><div><strong>${number(evidence.identity_verified)} / ${number(evidence.identity_total)}</strong><small>Annual identity sources corroborated</small></div></div><p class="small-note">Five years of annual-cover evidence, including explicitly incorporated securities exhibits. This is bounded identity evidence, not a complete corporate-action lineage audit.</p><div class="source-actions"><a class="button small" href="/download/universe.csv">${icon("download")} Export verified universe</a></div><div class="hash-row"><label>ADDITIONAL DISCOVERY LEDGERS</label><span class="small-note">${number(evidence.amendments)} amendments recorded separately · ${number(evidence.unresolved_items)} unresolved item records · ${number(evidence.failures.length)} source-operation failures</span></div></section>
      <section class="panel provenance-card"><span class="eyebrow">PINNED RESEARCH SNAPSHOT</span><div class="identity-strip"><span class="identity-icon">${icon("book")}</span><div><strong>${number(data.snapshot.source_count)}</strong><small>Source snapshots in the saved run manifest</small></div></div>${[["Configuration",data.snapshot.config_sha256],["Design lock",data.snapshot.design_sha256],["Fixed universe",data.snapshot.universe_sha256]].map(([label,hash])=>`<div class="hash-row"><label>${label.toUpperCase()} · SHA-256</label><code>${esc(hash || "Unavailable")}</code></div>`).join("")}<div class="source-actions"><a class="button small" href="/download/run-manifest.json">${icon("download")} Download run manifest</a></div></section></div>
      <section class="panel section-panel"><div class="panel-head"><div><span class="eyebrow">FILING VERSUS RELEASE AUDIT</span><h2>${number(evidence.reviews.length)} disclosures, inspected individually.</h2></div><span class="tag warn">DATE ≠ FIRST-PUBLIC TIME</span></div><div class="table-wrap"><table class="data-table review-table"><thead><tr><th>Issuer / release date recorded</th><th>Source inspection</th><th>Evidence</th></tr></thead><tbody>${evidence.reviews.map(row=>`<tr><td><span class="review-ticker">${esc(reviewTicker(row.event_id))}</span><small>${date(row.release_date)}</small>${row.nonstandard_disclosure_flag ? '<br><span class="tag warn">NONSTANDARD</span>' : ""}</td><td><div class="review-note">${esc(row.notes)}</div></td><td>${link(row.evidence_url,"Original exhibit")}</td></tr>`).join("")}</tbody></table></div><p class="small-note" style="padding:0 23px 13px">Builder source reviews are preserved. Karol's independent review remains pending. A date or a conference-call time is never promoted to a first-public release timestamp.</p></section>
      <section class="panel provenance-card section-panel"><span class="eyebrow">VENDOR PRICE QUALITY</span><h2 class="quality-heading">${number(evidence.price_issues.length)} recorded action flags</h2><p class="small-note">${evidence.price_issues.length ? evidence.price_issues.map(row => `${esc(row.ticker)} · ${esc(row.session)} · ${esc(row.issue.replaceAll("_", " "))}`).join("<br>") : "No price-quality flags recorded."}</p><p class="small-note">Vendor-reported actions are disclosed separately from missing-price or estimation failures. Adjusted prices remain the return input.</p></section><section class="panel provenance-card section-panel"><span class="eyebrow">THE RESEARCH LIBRARY</span><div class="library-links">${[["design","Locked research design"],["methods","Reproducible methods"],["limitations","Validity limitations"],["arithmetic","Numerical walkthrough"],["dictionary","Data dictionary"],["handoff","Build handoff"]].map(([key,label])=>`<button data-document="${key}">${label}<span>↗</span></button>`).join("")}</div></section></div>`;
  } catch (error) { $("#main").innerHTML = empty("Evidence unavailable", error.message); }
}

function renderRuns() {
  const cards = [
    ["tests","evidence","Verify installation and tests","Validate the fixed study configuration and execute the automated tests. Read the actual pass/fail output here.","LOCAL CHECKS"],
    ["demo","runs","Run the offline demonstration","Exercise the full workflow on clearly labelled synthetic fixtures, isolated from the genuine research snapshot.","SYNTHETIC FIXTURES"],
    ["reproduce","refresh","Reproduce the cached study","Rebuild the 30-company analysis from the pinned inputs and compare every processed output. Allow several minutes.","GENUINE CACHED DATA"],
    ["report","book","Refresh the research report","Regenerate the evidence tables and five figures using the saved calculations. View or download the result.","SAVED CALCULATIONS"],
  ];
  $("#main").innerHTML = `<div class="fade-in">${pageHead("EXECUTION & REPRODUCIBILITY", "Put the workflow to the test.", "Run a check, follow the output, and keep the evidence. One research task runs at a time.", `<button class="button" data-document="report">${icon("book")} Open full report</button>`)}
    <div class="run-notice"><span class="status-dot"></span><p><strong>Your study specification stays locked.</strong> These tasks use the existing Python pipeline. The offline demonstration stays separate; the real study uses its pinned source snapshot.</p></div>
    <section class="task-grid">${cards.map(([action,graphic,title,description,type])=>`<article class="task-card"><span class="task-icon">${icon(graphic)}</span><div><h2>${title}</h2><p>${description}</p><button class="button ${action === "tests" ? "primary" : ""}" data-task="${action}">${icon("runs")} Run ${action === "tests" ? "verification" : action === "reproduce" ? "reproduction" : action === "demo" ? "demo" : "report"}</button><span class="task-type">${type}</span></div></article>`).join("")}</section>
    <section class="run-layout"><div class="panel run-console"><div class="console-head"><span><span class="console-dots">● ● ●</span><span id="console-title">Execution output</span></span><small id="console-status">NO TASK SELECTED</small></div><pre id="job-log" aria-live="polite">Choose a task above. Actual execution output will appear here.</pre></div><div class="panel run-history"><div class="panel-head"><div><span class="eyebrow">PERSISTED LOCALLY</span><h2>Run history</h2></div><span class="status-caption" id="history-count"></span></div><div class="run-history-list" id="run-history"></div></div></section><p class="research-note">No new vendor data is downloaded here. The primary threshold, universe, controls and hypothesis are unchanged. Test execution confirms software behavior; it does not remove the study's validity limitations.</p></div>`;
  renderJobs();
}
function renderJobs() {
  $$('[data-task]').forEach(button => { button.disabled = Boolean(state.activeJob || state.starting || !state.connected); });
  $$('a[href^="/download/"],a[href^="/api/"]').forEach(anchor => anchor.setAttribute("aria-disabled", String(!state.connected || (anchor.id === "export-events" && (state.eventsLoading || !state.events.length)))));
  const top = $("#top-job");
  top.innerHTML = state.activeJob ? `<span class="global-job"><span class="spinner mini-spinner"></span><button data-go-runs>Task running</button></span>` : "";
  if (state.view !== "runs" || !$("#run-history")) return;
  $("#history-count").textContent = `${state.jobs.length} RUN${state.jobs.length === 1 ? "" : "S"}`;
  $("#run-history").innerHTML = state.jobs.length ? state.jobs.map(job=>`<button class="history-row ${job.id === state.selectedJob ? "active" : ""}" data-job="${esc(job.id)}"><span class="history-title">${esc(job.title)}${badge(job.status)}</span><span class="history-date">${date(job.started_at)} · ${new Date(job.started_at).toLocaleTimeString("en-GB",{hour:"2-digit",minute:"2-digit"})}${job.tests ? ` · ${number(job.tests.tests)} tests` : ""}</span></button>`).join("") : '<p class="small-note" style="padding:20px 8px">No tasks have been launched from this desk yet. Your command-line verification records remain in the research folder.</p>';
  const selected = state.jobs.find(job => job.id === state.selectedJob) || state.jobs.find(job => job.id === state.activeJob) || state.jobs[0];
  if (selected) {
    state.selectedJob = selected.id;
    $("#console-title").textContent = selected.title;
    $("#console-status").textContent = selected.status.toUpperCase() + (selected.exit_code !== null ? ` · EXIT ${selected.exit_code}` : "");
    const log = $("#job-log"), nearEnd = log.scrollHeight-log.clientHeight-log.scrollTop < 60;
    log.textContent = selected.lines.length ? selected.lines.join("\n") : (selected.status === "running" ? "Task started. Waiting for execution output…" : "No execution output was recorded.");
    if (nearEnd) log.scrollTop = log.scrollHeight;
  }
}
async function pollJobs() {
  if (state.polling) return;
  state.polling = true;
  try {
    const previous = state.activeJob;
    const result = await api("/api/jobs");
    const refresh = !state.overview || result.instance_id !== state.instance || result.data_revision !== state.dataRevision;
    if (refresh) {
      state.overview = await api("/api/overview"); state.evidence = null;
      state.instance = result.instance_id; state.dataRevision = result.data_revision;
    }
    if (result.session_token) $('meta[name="research-token"]').content = result.session_token;
    state.jobs = result.jobs; state.activeJob = result.active_id;
    if (state.activeJob && state.activeJob !== previous) state.selectedJob = state.activeJob;
    if (!state.selectedJob && state.jobs.length) state.selectedJob = state.jobs[0].id;
    setConnection(true);
    if (refresh) await route();
    if (previous && !state.activeJob) {
      const completed = state.jobs.find(job => job.id === previous);
      if (completed) toast(completed.status === "passed" ? `${completed.title} completed successfully.` : "Task did not pass. Inspect the execution output.", completed.status !== "passed");
      if (!refresh && state.view === "overview") renderOverview();
    }
    renderJobs();
  } catch {
    setConnection(false);
    if (!state.overview) $("#main").innerHTML = empty("Start the local research desk", "Double-click Open Research Desk.cmd in the project folder. This page will reconnect automatically.") + '<div style="text-align:center"><button class="button" data-reconnect>Try connecting again</button></div>';
  } finally { state.polling = false; }
}
async function startTask(action) {
  if (state.activeJob || state.starting) return toast("A task is already running. Follow its output in Run Center.");
  if (!state.connected) { await pollJobs(); if (!state.connected) return; }
  state.starting = true; renderJobs();
  try {
    // Read the current session immediately before submission; a restarted server rotates its token.
    const session = await api("/api/session");
    $('meta[name="research-token"]').content = session.token;
    const job = await api("/api/jobs", {method:"POST", headers:{"Content-Type":"application/json","X-Research-Token":session.token}, body:JSON.stringify({action})});
    state.activeJob = job.id; state.selectedJob = job.id; state.jobs.unshift(job);
    if (state.view !== "runs") location.hash = "/runs";
    else renderJobs();
    toast(`${job.title} started.`);
  } catch (error) {
    toast(error.message, true);
    // Never retry a task POST: it may have started even if the response was lost.
  } finally { state.starting = false; renderJobs(); }
}

function inlineMarkdown(value) {
  return esc(value).replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>").replace(/`([^`]+)`/g,"<code>$1</code>").replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,(_,text,url)=>`<a href="${url}" target="_blank" rel="noopener noreferrer">${text}</a>`);
}
function markdown(value) {
  const lines = value.split(/\r?\n/); let html="", code=false, buffer=[], table=false, list=false;
  const closeList = () => { if (list) { html += "</ul>"; list = false; } };
  const closeTable = () => { if (table) { html += "</tbody></table>"; table = false; } };
  for (const line of lines) {
    if (line.startsWith("```")) { closeList(); closeTable(); if (code) { html += `<pre>${esc(buffer.join("\n"))}</pre>`; buffer=[]; } code=!code; continue; }
    if (code) { buffer.push(line); continue; }
    if (line.startsWith("|")) {
      closeList(); const cells=line.replace(/^\||\|$/g,"").split("|").map(cell=>cell.trim());
      if (cells.every(cell=>/^:?-+:?$/.test(cell))) continue;
      if (!table) { html += `<table><thead><tr>${cells.map(cell=>`<th>${inlineMarkdown(cell)}</th>`).join("")}</tr></thead><tbody>`; table=true; }
      else html += `<tr>${cells.map(cell=>`<td>${inlineMarkdown(cell)}</td>`).join("")}</tr>`;
      continue;
    }
    closeTable();
    const heading=/^(#{1,3}) (.+)$/.exec(line);
    if (heading) { closeList(); html += `<h${heading[1].length}>${inlineMarkdown(heading[2])}</h${heading[1].length}>`; }
    else if (/^[-*] /.test(line)) { if (!list) {html+="<ul>";list=true;} html+=`<li>${inlineMarkdown(line.slice(2))}</li>`; }
    else if (/^!\[/.test(line)) { closeList(); const image=/^!\[([^\]]*)\]\(figures\/([a-z_]+\.png)\)$/.exec(line); if (image) html+=`<img src="/figures/${image[2]}" alt="${esc(image[1])}" loading="lazy">`; }
    else { closeList(); if (line.trim()) html+=`<p>${inlineMarkdown(line)}</p>`; }
  }
  closeList();closeTable();if(code)html+=`<pre>${esc(buffer.join("\n"))}</pre>`;
  return html;
}
async function showDocument(key) {
  const dialog=$("#document-dialog"), request = ++state.documentRequest;
  const titles={report:"Technical research report",design:"Locked research design",methods:"Reproducible methods",limitations:"Validity limitations",audit:"Source and timing audit",arithmetic:"Numerical walkthrough",dictionary:"Data dictionary",handoff:"Build handoff"};
  $("#document-title").textContent=titles[key] || "Research document";
  $("#document-body").innerHTML='<div class="initial-loading"><div class="spinner"></div></div>';
  if(!dialog.open)dialog.showModal();
  try { const result=await api(`/api/document/${encodeURIComponent(key)}`); if(request !== state.documentRequest || !dialog.open)return; $("#document-body").innerHTML=markdown(result.text); $("#document-body").scrollTop=0; }
  catch(error){$("#document-body").textContent=error.message;}
}

async function route() {
  if (!state.overview || location.hash === "#main") return;
  clearTimeout(renderExplorer.searchTimer); state.request++; state.eventsLoading = false;
  let view=location.hash.replace(/^#\/?/,"").split("/")[0] || "overview";
  if(!["overview","events","evidence","runs"].includes(view))view="overview";
  state.view=view;
  $$("[data-nav]").forEach(item=>{const active=item.dataset.nav===view;item.classList.toggle("active",active);if(active)item.setAttribute("aria-current","page");else item.removeAttribute("aria-current");});
  $("#current-section").textContent={overview:"STUDY OVERVIEW",events:"EVENT EXPLORER",evidence:"EVIDENCE & TIMING",runs:"RUN CENTER"}[view];
  document.title=`${{overview:"Study overview",events:"Event explorer",evidence:"Evidence & timing",runs:"Run center"}[view]} — Diffusion`;
  if(view==="overview")renderOverview();
  if(view==="events")renderExplorer();
  if(view==="evidence")await renderEvidence();
  if(view==="runs")renderRuns();
  if(state.view!==view)return;
  $("#main").insertAdjacentHTML("afterbegin", `<div class="desk-masthead"><button class="desk-home" data-view="overview" aria-label="Diffusion research desk home"><img src="/static/mark.svg" width="36" height="36" alt=""><span><strong>diffusion<span class="wordmark-period">.</span></strong><small>RESEARCH DESK</small></span></button><span class="desk-owner">Karol John<span>Local research workspace</span></span></div><nav class="view-navigation" aria-label="Research views">${[["overview","Overview"],["events","Event explorer"],["evidence","Evidence & timing"],["runs","Run center"]].map(([key,label])=>`<button type="button" data-view="${key}" ${key===view?'aria-current="page"':''}>${label}</button>`).join("")}</nav>`);
  renderJobs();
  window.scrollTo({top:0});
}
document.addEventListener("click",event=>{
  const navigation=event.target.closest("[data-view]");if(navigation){location.hash="/"+navigation.dataset.view;return;}
  if(event.target.closest("[data-reconnect]") || event.target.closest("#reconnect")){pollJobs();return;}
  if(event.target.closest("[data-retry-events]")){loadEvents();return;}
  if(event.target.closest("[data-return-ledger]")){$("#events-body")?.closest("section").scrollIntoView({block:"start"});return;}
  const disabledLink=event.target.closest('a[aria-disabled="true"]');if(disabledLink){event.preventDefault();return;}
  const skip=event.target.closest(".skip-link");if(skip){event.preventDefault();$("#main").focus();$("#main").scrollIntoView({block:"start"});return;}
  const documentButton=event.target.closest("[data-document]");if(documentButton){showDocument(documentButton.dataset.document);return;}
  const taskButton=event.target.closest("[data-task]");if(taskButton){startTask(taskButton.dataset.task);return;}
  const explore=event.target.closest("[data-explore]");if(explore){state.filters={...state.filters,q:"",year:"all",sector:"all",status:explore.dataset.explore,sign:"all",page:1,sort:explore.dataset.sort || "recent"};state.selectedEvent=null;if(state.view==="events")renderExplorer();else location.hash="/events";return;}
  const chart=event.target.closest("[data-chart]");if(chart){state.chart=chart.dataset.chart;drawTrajectory();return;}
  const row=event.target.closest("[data-event]");if(row){selectEvent(row.dataset.event,true);return;}
  const job=event.target.closest("[data-job]");if(job){state.selectedJob=job.dataset.job;renderJobs();return;}
  if(event.target.closest("[data-go-runs]"))location.hash="/runs";
});
document.addEventListener("keydown",event=>{const row=event.target.closest("[data-event]");if(row&&(event.key==="Enter"||event.key===" ")){event.preventDefault();selectEvent(row.dataset.event,true);}});
$("#close-document").onclick=()=>$("#document-dialog").close();
$("#document-dialog").addEventListener("click",event=>{if(event.target===$("#document-dialog")){const rect=event.target.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)event.target.close();}});
document.addEventListener("pointerover",event=>{const point=event.target.closest("[data-tip]");if(!point)return;const parent=point.closest(".chart"),tip=document.createElement("div");tip.className="chart-tooltip";tip.textContent=point.dataset.tip;parent.querySelector(".chart-tooltip")?.remove();parent.append(tip);tip.style.left=`${Math.min(Math.max(event.clientX-parent.getBoundingClientRect().left-50,10),parent.clientWidth-185)}px`;});
document.addEventListener("pointerout",event=>{if(event.target.closest("[data-tip]"))event.target.closest(".chart")?.querySelector(".chart-tooltip")?.remove();});
window.addEventListener("hashchange",route);
window.addEventListener("resize",()=>{
  clearTimeout(state.resizeTimer);
  state.resizeTimer=setTimeout(()=>{
    if(state.view==="overview" && $("#trajectory-chart"))drawTrajectory();
    if(state.view==="events" && !state.eventsLoading && state.detail?.event.event_id===state.selectedEvent){
      const expanded=$(".model-details")?.open;
      drawDetail(state.detail);
      if(expanded)$(".model-details").open=true;
    }
  },150);
});
async function boot(){
  setInterval(pollJobs,3000);
  await pollJobs();
}
boot();
