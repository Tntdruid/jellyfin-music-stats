const MOOD_COLORS = {
  energetic: "#f97316", happy: "#eab308", chill: "#14b8a6", melancholic: "#3b82f6",
  dark: "#6b5b95", romantic: "#ec4899", aggressive: "#ef4444", party: "#a855f7",
};
const PALETTE = ["#7c5cff", "#14b8a6", "#f97316", "#3b82f6", "#ec4899", "#eab308", "#22c55e", "#ef4444", "#94a3b8"];
const DAYS = ["Man", "Tir", "Ons", "Tor", "Fre", "Lør", "Søn"];
const ICONS = { clock: "🕒", star: "⭐", sparkle: "✨", rewind: "⏪", repeat: "🔁", skip: "⏭️", mood: "🎭", moon: "🌙" };

const state = { range: "30", user: "", bucket: null, meta: null };
const charts = {};

const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const fmt = (n, d = 0) => Number(n || 0).toLocaleString("da-DK", { maximumFractionDigits: d });
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

function rangeParams() {
  const now = Math.floor(Date.now() / 1000);
  let start = 0;
  if (state.range === "year") start = Math.floor(new Date(new Date().getFullYear(), 0, 1) / 1000);
  else if (state.range !== "all") start = now - Number(state.range) * 86400;
  const p = new URLSearchParams({ start, end: now + 60 });
  if (state.user) p.set("user", state.user);
  return p;
}

function autoBucket() {
  if (state.range === "7" || state.range === "30") return "day";
  if (state.range === "90") return "week";
  return "month";
}

async function api(path, extra = {}) {
  const p = rangeParams();
  for (const [k, v] of Object.entries(extra)) p.set(k, v);
  const r = await fetch(`api/${path}?${p}`);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

function chart(id) {
  if (!charts[id]) charts[id] = echarts.init(document.getElementById(id), null, { renderer: "canvas" });
  return charts[id];
}

function baseOption() {
  const text = css("--muted"), line = css("--line");
  return {
    textStyle: { color: text, fontFamily: "inherit" },
    grid: { left: 40, right: 12, top: 30, bottom: 30, containLabel: false },
    tooltip: { trigger: "axis", backgroundColor: css("--card"), borderColor: line, textStyle: { color: css("--text") } },
    legend: { top: 0, textStyle: { color: text }, type: "scroll", itemWidth: 10, itemHeight: 10 },
    xAxis: { type: "category", axisLine: { lineStyle: { color: line } }, axisTick: { show: false } },
    yAxis: { type: "value", splitLine: { lineStyle: { color: line } } },
  };
}

function fmtLabel(iso, bucket) {
  const d = new Date(iso + "T00:00:00");
  if (bucket === "month") return d.toLocaleDateString("da-DK", { month: "short", year: "2-digit" });
  return d.toLocaleDateString("da-DK", { day: "numeric", month: "short" });
}

// --- renderers ---------------------------------------------------------------

function renderKpis(s) {
  const delta = (cur, prev, invert = false) => {
    if (!prev) return `<div class="delta">&nbsp;</div>`;
    const pct = ((cur - prev) / prev) * 100;
    const good = invert ? pct < 0 : pct > 0;
    return `<div class="delta ${Math.abs(pct) < 1 ? "" : good ? "up" : "down"}">${pct > 0 ? "▲" : "▼"} ${fmt(Math.abs(pct))} % vs. forrige periode</div>`;
  };
  const items = [
    ["Lytninger", fmt(s.plays), delta(s.plays, s.previous.plays)],
    ["Lyttetid", `${fmt(s.minutes / 60, 1)} t`, delta(s.minutes, s.previous.minutes)],
    ["Kunstnere", fmt(s.artists), delta(s.artists, s.previous.artists)],
    ["Nye kunstnere", fmt(s.new_artists), `<div class="delta">${fmt(s.discovery_rate * 100)} % nye sange</div>`],
    ["Skip-rate", `${fmt(s.skip_rate * 100)} %`, delta(s.skip_rate, s.previous.skip_rate, true)],
    ["Streak", `${s.streak_current} dage`, `<div class="delta">rekord: ${s.streak_best} dage</div>`],
    ["Gns. session", `${fmt(s.avg_session_minutes)} min`, `<div class="delta">${fmt(s.sessions)} sessioner</div>`],
  ];
  $("#kpis").innerHTML = items
    .map(([l, v, d]) => `<div class="kpi"><div class="label">${l}</div><div class="value">${v}</div>${d}</div>`)
    .join("");
}

function renderTimeline(t, bucket) {
  const opt = baseOption();
  opt.legend.data = ["Lytninger", "Minutter"];
  opt.xAxis.data = t.labels.map((l) => fmtLabel(l, bucket));
  opt.yAxis = [
    { type: "value", splitLine: { lineStyle: { color: css("--line") } } },
    { type: "value", splitLine: { show: false } },
  ];
  opt.grid.right = 40;
  opt.series = [
    { name: "Lytninger", type: "bar", data: t.plays, itemStyle: { color: css("--accent"), borderRadius: [3, 3, 0, 0] } },
    { name: "Minutter", type: "line", yAxisIndex: 1, data: t.minutes, smooth: 0.3, smoothMonotone: "x", symbol: "none",
      lineStyle: { color: "#14b8a6", width: 2 }, itemStyle: { color: "#14b8a6" } },
  ];
  chart("timeline").setOption(opt, true);
}

function renderTop(id, rows) {
  const el = document.getElementById(id);
  if (!rows.length) { el.innerHTML = `<div class="empty">Ingen data endnu</div>`; return; }
  const max = rows[0].plays;
  el.innerHTML = rows.map((r) => `
    <li>
      ${r.image_id
        ? `<img class="img" loading="lazy" src="api/image/${esc(r.image_id)}" alt="" onerror="this.outerHTML='<div class=img>${esc((r.name || "?")[0]).replace(/'/g, "")}</div>'">`
        : `<div class="img">${esc((r.name || "?")[0])}</div>`}
      <div class="meta">
        <div class="name" title="${esc(r.name)}">${esc(r.name)}</div>
        ${r.sub ? `<div class="sub">${esc(r.sub)}</div>` : ""}
        <div class="bar" style="width:${(r.plays / max) * 100}%"></div>
      </div>
      <div class="count">${fmt(r.plays)}<br>${fmt(r.minutes)} min</div>
    </li>`).join("");
}

function renderShareArea(id, data, bucket, colorFor) {
  const opt = baseOption();
  const totals = data.labels.map((_, i) => data.series.reduce((s, x) => s + x.data[i], 0));
  opt.xAxis.data = data.labels.map((l) => fmtLabel(l, bucket));
  opt.xAxis.boundaryGap = false;
  opt.yAxis.max = 100;
  opt.yAxis.axisLabel = { formatter: "{value} %" };
  opt.tooltip.valueFormatter = (v) => `${fmt(v)} %`;
  opt.series = data.series.map((s, i) => ({
    name: s.label || s.name,
    type: "line", stack: "share", areaStyle: { opacity: 0.85 }, symbol: "none", smooth: 0.3,
    lineStyle: { width: 0 },
    itemStyle: { color: colorFor(s.name, i) },
    data: s.data.map((v, j) => (totals[j] ? (v / totals[j]) * 100 : 0)),
  }));
  if (!data.series.length) opt.title = { text: "Ingen data endnu", left: "center", top: "middle", textStyle: { color: css("--muted"), fontSize: 13 } };
  chart(id).setOption(opt, true);
}

function renderHeatmap(cells) {
  const max = Math.max(1, ...cells.map((c) => c[2]));
  chart("heatmap").setOption({
    textStyle: { color: css("--muted") },
    tooltip: { formatter: (p) => `${DAYS[p.value[1]]} kl. ${String(p.value[0]).padStart(2, "0")}: ${p.value[2]} lytninger`,
               backgroundColor: css("--card"), borderColor: css("--line"), textStyle: { color: css("--text") } },
    grid: { left: 40, right: 12, top: 10, bottom: 50 },
    xAxis: { type: "category", data: [...Array(24).keys()].map((h) => String(h).padStart(2, "0")), splitArea: { show: false },
             axisLine: { lineStyle: { color: css("--line") } }, axisTick: { show: false } },
    yAxis: { type: "category", data: DAYS, inverse: true, axisLine: { show: false }, axisTick: { show: false } },
    visualMap: { min: 0, max, calculable: false, orient: "horizontal", left: "center", bottom: 0, itemHeight: 120,
                 inRange: { color: [css("--line"), css("--accent")] }, textStyle: { color: css("--muted") } },
    series: [{ type: "heatmap", data: cells, itemStyle: { borderColor: css("--card"), borderWidth: 2, borderRadius: 3 } }],
  }, true);
}

function renderMoodHours(rows, labels) {
  const moods = Object.keys(labels);
  const perHour = Array.from({ length: 24 }, () => ({}));
  for (const r of rows) perHour[r.h][r.mood] = r.n;
  const totals = perHour.map((h) => Object.values(h).reduce((a, b) => a + b, 0));
  const opt = baseOption();
  opt.xAxis.data = [...Array(24).keys()].map((h) => String(h).padStart(2, "0"));
  opt.yAxis.max = 100;
  opt.yAxis.axisLabel = { formatter: "{value} %" };
  opt.tooltip.valueFormatter = (v) => `${fmt(v)} %`;
  opt.series = moods.map((m) => ({
    name: labels[m], type: "bar", stack: "h", barCategoryGap: "15%",
    itemStyle: { color: MOOD_COLORS[m] },
    data: perHour.map((h, i) => (totals[i] ? ((h[m] || 0) / totals[i]) * 100 : 0)),
  }));
  chart("mood-hours").setOption(opt, true);
}

function renderInsights(items) {
  $("#insights").innerHTML = items.length
    ? items.map((i) => `<li><span class="ico">${ICONS[i.icon] || "•"}</span><span>${esc(i.text)}</span></li>`).join("")
    : `<li class="empty">Indsigter dukker op, når der er lyttet lidt mere.</li>`;
}

function renderRecent(rows) {
  $("#recent").innerHTML = rows.length ? rows.map((r) => {
    const t = new Date(r.started_at * 1000);
    const pct = r.duration ? Math.round((r.listened / r.duration) * 100) : null;
    return `<tr>
      <td class="muted">${t.toLocaleDateString("da-DK", { day: "numeric", month: "short" })} ${t.toLocaleTimeString("da-DK", { hour: "2-digit", minute: "2-digit" })}</td>
      <td><strong>${esc(r.name || "Ukendt")}</strong> <span class="muted">· ${esc(r.artist || "")}</span></td>
      <td>${r.counted ? "" : `<span class="tag">sprunget over</span>`}</td>
      <td class="muted">${pct != null ? pct + " %" : ""}</td>
      <td class="muted">${esc(r.user_name || "")}</td>
    </tr>`;
  }).join("") : `<tr><td class="empty">Ingen afspilninger endnu</td></tr>`;
}

async function renderNow() {
  try {
    const now = await (await fetch("api/now")).json();
    const el = $("#now");
    el.hidden = !now.length;
    el.innerHTML = now.map((n) => `
      <div class="item">
        ${n.album_id ? `<img class="img" src="api/image/${esc(n.album_id)}" alt="" onerror="this.outerHTML='<div class=img>♪</div>'">` : `<div class="img">♪</div>`}
        <div style="flex:1;min-width:0">
          <div class="live">${n.paused ? "PAUSE" : "SPILLER NU"} · ${esc(n.user_name || "")}</div>
          <div><strong>${esc(n.name)}</strong> <span class="muted">· ${esc((n.artists || [])[0] || "")}</span></div>
          ${n.duration ? `<progress max="${n.duration}" value="${n.position}"></progress>` : ""}
        </div>
      </div>`).join("");
  } catch { /* ignore */ }
}

function renderStatus(meta) {
  const el = $("#status");
  const c = meta.collector;
  if (!c.enabled) { el.className = "status"; el.title = "Opsamling slået fra (mangler Jellyfin URL/API-nøgle)"; return; }
  if (c.last_error) { el.className = "status err"; el.title = `Fejl: ${c.last_error}`; return; }
  el.className = "status ok";
  el.title = c.last_poll ? `Forbundet til Jellyfin – sidst tjekket ${new Date(c.last_poll * 1000).toLocaleTimeString("da-DK")}` : "Starter…";
}

// --- main -----------------------------------------------------------------

async function loadMeta() {
  state.meta = await (await fetch("api/meta")).json();
  renderStatus(state.meta);
  const sel = $("#user");
  const current = sel.value;
  sel.innerHTML = `<option value="">Alle brugere</option>` +
    state.meta.users.map((u) => `<option value="${esc(u.id)}">${esc(u.name || u.id)}</option>`).join("");
  sel.value = current;
  sel.hidden = state.meta.users.length < 2;
}

async function load() {
  const bucket = state.bucket || autoBucket();
  const trend = autoBucket() === "day" && state.range === "30" ? "week" : autoBucket();
  document.querySelectorAll("#bucket button").forEach((b) => b.classList.toggle("on", b.dataset.bucket === bucket));

  const [summary, timeline, artists, albums, tracks, genres, moods, heat, insights, recent] = await Promise.all([
    api("summary"), api("timeline", { bucket }),
    api("top", { kind: "artists" }), api("top", { kind: "albums" }), api("top", { kind: "tracks" }),
    api("genres", { bucket: trend }), api("moods", { bucket: trend }), api("heatmap"), api("insights"), api("recent"),
  ]);
  const labels = state.meta.moods;
  renderKpis(summary);
  renderTimeline(timeline, bucket);
  renderTop("top-artists", artists);
  renderTop("top-albums", albums);
  renderTop("top-tracks", tracks);
  renderShareArea("genres", genres, trend, (_, i) => PALETTE[i % PALETTE.length]);
  moods.series.forEach((s) => (s.label = labels[s.name] || s.name));
  renderShareArea("moods", moods, trend, (name) => MOOD_COLORS[name] || "#94a3b8");
  $("#mood-coverage").textContent = `${fmt(moods.coverage * 100)} % af lytningerne har humør-data`;
  renderMoodHours(moods.by_hour, labels);
  renderHeatmap(heat);
  renderInsights(insights);
  renderRecent(recent);
}

document.querySelectorAll("#range button").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll("#range button").forEach((x) => x.classList.toggle("on", x === b));
  state.range = b.dataset.range;
  state.bucket = null;
  load();
}));
document.querySelectorAll("#bucket button").forEach((b) => b.addEventListener("click", () => {
  state.bucket = b.dataset.bucket;
  api("timeline", { bucket: state.bucket }).then((t) => {
    document.querySelectorAll("#bucket button").forEach((x) => x.classList.toggle("on", x === b));
    renderTimeline(t, state.bucket);
  });
}));
$("#user").addEventListener("change", (e) => { state.user = e.target.value; load(); });
window.addEventListener("resize", () => Object.values(charts).forEach((c) => c.resize()));
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", load);

(async () => {
  await loadMeta();
  await load();
  renderNow();
  setInterval(renderNow, 10000);
  setInterval(async () => { await loadMeta(); }, 60000);
})();
