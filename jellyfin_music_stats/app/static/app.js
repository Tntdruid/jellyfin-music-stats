const MOOD_COLORS = {
  energetic: "#f97316", happy: "#eab308", chill: "#14b8a6", melancholic: "#3b82f6",
  dark: "#6b5b95", romantic: "#ec4899", aggressive: "#ef4444", party: "#a855f7",
};
const PALETTE = ["#7c5cff", "#14b8a6", "#f97316", "#3b82f6", "#ec4899", "#eab308", "#22c55e", "#ef4444", "#94a3b8"];
const ICONS = { clock: "🕒", star: "⭐", sparkle: "✨", rewind: "⏪", repeat: "🔁", skip: "⏭️", mood: "🎭", moon: "🌙" };
const OTHER = "__other__";  // the server's name for the "everything else" series

const state = { range: "30", user: "", bucket: null, meta: null };
const charts = {};

const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const fmt = (n, d = 0) => Number(n || 0).toLocaleString(LOCALE, { maximumFractionDigits: d });
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const pad = (h) => String(h).padStart(2, "0");
const seriesName = (name) => (name === OTHER ? t("other") : name);

function rangeParams() {
  const now = Math.floor(Date.now() / 1000);
  let start = 0;
  if (state.range === "year") start = Math.floor(new Date(new Date().getFullYear(), 0, 1) / 1000);
  else if (state.range !== "all") start = now - Number(state.range) * 86400;
  const p = new URLSearchParams({ start, end: now + 60, lang: LANG });
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

// for the pages that show the current state, not a period: just the user (and language)
async function apiNow(path, extra = {}) {
  const p = new URLSearchParams({ lang: LANG, ...extra });
  if (state.user) p.set("user", state.user);
  const r = await fetch(`api/${path}?${p}`);
  return r.ok ? r.json() : null;
}

function chart(id) {
  const el = document.getElementById(id);
  if (charts[id] && charts[id].getDom() !== el) charts[id].dispose();  // container was re-rendered
  if (!charts[id] || charts[id].isDisposed()) charts[id] = echarts.init(el, null, { renderer: "canvas" });
  return charts[id];
}

function baseOption() {
  const text = css("--muted"), line = css("--line");
  return {
    animation: !state.quiet,  // no replayed animations on background refreshes
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
  if (bucket === "month") return d.toLocaleDateString(LOCALE, { month: "short", year: "2-digit" });
  return d.toLocaleDateString(LOCALE, { day: "numeric", month: "short" });
}

const longDate = (ts) => new Date(ts * 1000).toLocaleDateString(LOCALE, { day: "numeric", month: "long", year: "numeric" });
const shortDate = (ts) => new Date(ts * 1000).toLocaleDateString(LOCALE, { day: "numeric", month: "short" });
const capital = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const mmss = (sec) => `${Math.floor(sec / 60)}:${pad(Math.round(sec % 60))}`;

// --- renderers ---------------------------------------------------------------

function renderKpis(s) {
  const delta = (cur, prev, invert = false) => {
    if (!prev) return `<div class="delta">&nbsp;</div>`;
    const pct = ((cur - prev) / prev) * 100;
    const good = invert ? pct < 0 : pct > 0;
    return `<div class="delta ${Math.abs(pct) < 1 ? "" : good ? "up" : "down"}">${pct > 0 ? "▲" : "▼"} ${t("kpi.vs_prev", { pct: fmt(Math.abs(pct)) })}</div>`;
  };
  const items = [
    [t("kpi.plays"), fmt(s.plays), delta(s.plays, s.previous.plays)],
    [t("kpi.time"), `${fmt(s.minutes / 60, 1)} ${t("hours")}`, delta(s.minutes, s.previous.minutes)],
    [t("kpi.artists"), fmt(s.artists), delta(s.artists, s.previous.artists)],
    [t("kpi.new_artists"), fmt(s.new_artists), `<div class="delta">${t("kpi.new_tracks", { pct: fmt(s.discovery_rate * 100) })}</div>`],
    [t("kpi.skip"), `${fmt(s.skip_rate * 100)} %`, delta(s.skip_rate, s.previous.skip_rate, true)],
    [t("kpi.streak"), t("kpi.days", { n: s.streak_current }), `<div class="delta">${t("kpi.record", { n: s.streak_best })}</div>`],
    [t("kpi.session"), `${fmt(s.avg_session_minutes)} ${t("minutes")}`, `<div class="delta">${t("kpi.sessions", { n: fmt(s.sessions) })}</div>`],
  ];
  $("#kpis").innerHTML = items
    .map(([l, v, d]) => `<div class="kpi"><div class="label">${l}</div><div class="value">${v}</div>${d}</div>`)
    .join("");
}

function renderTimeline(tl, bucket) {
  const opt = baseOption();
  opt.legend.data = [t("series.plays"), t("series.minutes")];
  opt.xAxis.data = tl.labels.map((l) => fmtLabel(l, bucket));
  opt.yAxis = [
    { type: "value", splitLine: { lineStyle: { color: css("--line") } } },
    { type: "value", splitLine: { show: false } },
  ];
  opt.grid.right = 40;
  opt.series = [
    { name: t("series.plays"), type: "bar", data: tl.plays, itemStyle: { color: css("--accent"), borderRadius: [3, 3, 0, 0] } },
    { name: t("series.minutes"), type: "line", yAxisIndex: 1, data: tl.minutes, smooth: 0.3, smoothMonotone: "x", symbol: "none",
      lineStyle: { color: "#14b8a6", width: 2 }, itemStyle: { color: "#14b8a6" } },
  ];
  chart("timeline").setOption(opt, true);
}

function cover(imageId, name, cls = "img") {
  const letter = esc((name || "?")[0]).replace(/'/g, "");
  return imageId
    ? `<img class="${cls}" loading="lazy" src="api/image/${esc(imageId)}" alt="" onerror="this.outerHTML='<div class=${cls}>${letter}</div>'">`
    : `<div class="${cls}">${letter}</div>`;
}

const artistLink = (name) => `#/artist/${encodeURIComponent(name)}`;
const albumLink = (id) => `#/album/${encodeURIComponent(id)}`;
const trackLink = (id) => `#/track/${encodeURIComponent(id)}`;

// rows: {name, sub, image_id, plays, minutes} or {..., count} where count replaces the plays/minutes column
function renderTop(id, rows, linkFor = null) {
  const el = document.getElementById(id);
  if (!rows.length) { el.innerHTML = `<div class="empty">${t("nodata")}</div>`; return; }
  const max = Math.max(1, ...rows.map((r) => r.plays ?? 0));
  el.innerHTML = rows.map((r) => {
    const link = linkFor && linkFor(r);
    const tag = link ? `a class="row" href="${esc(link)}"` : `div class="row"`;
    const count = r.count ?? `${fmt(r.plays)}${r.minutes != null ? `<br>${fmt(r.minutes)} ${t("minutes")}` : " ×"}`;
    return `
    <li>
      <${tag}>
        ${cover(r.image_id, r.name)}
        <div class="meta">
          <div class="name" title="${esc(r.name)}">${esc(r.name)}</div>
          ${r.sub ? `<div class="sub">${esc(r.sub)}</div>` : ""}
          ${r.plays != null ? `<div class="bar" style="width:${(r.plays / max) * 100}%"></div>` : ""}
        </div>
        <div class="count">${count}</div>
      </${link ? "a" : "div"}>
    </li>`;
  }).join("");
}

function renderShareArea(id, data, bucket, colorFor) {
  const opt = baseOption();
  const totals = data.labels.map((_, i) => data.series.reduce((s, x) => s + x.data[i], 0));
  // an area needs at least two points to have any width; with fewer buckets draw stacked bars
  const bars = data.labels.length < 3;
  opt.xAxis.data = data.labels.map((l) => fmtLabel(l, bucket));
  opt.xAxis.boundaryGap = bars;
  opt.yAxis.max = 100;
  opt.yAxis.axisLabel = { formatter: "{value} %" };
  opt.tooltip.valueFormatter = (v) => `${fmt(v)} %`;
  opt.series = data.series.map((s, i) => ({
    name: s.label || seriesName(s.name),
    stack: "share",
    ...(bars
      ? { type: "bar", barMaxWidth: 120 }
      : { type: "line", areaStyle: { opacity: 0.85 }, symbol: "none", smooth: 0.3, lineStyle: { width: 0 } }),
    itemStyle: { color: colorFor(s.name, i) },
    data: s.data.map((v, j) => (totals[j] ? (v / totals[j]) * 100 : 0)),
  }));
  if (!data.series.length) opt.title = { text: t("nodata"), left: "center", top: "middle", textStyle: { color: css("--muted"), fontSize: 13 } };
  chart(id).setOption(opt, true);
}

function renderHeatmap(cells) {
  const max = Math.max(1, ...cells.map((c) => c[2]));
  const days = t("days");
  chart("heatmap").setOption({
    animation: !state.quiet,
    textStyle: { color: css("--muted") },
    tooltip: { formatter: (p) => t("heatmap.tip", { day: days[p.value[1]], hour: pad(p.value[0]), n: p.value[2] }),
               backgroundColor: css("--card"), borderColor: css("--line"), textStyle: { color: css("--text") } },
    grid: { left: 40, right: 12, top: 10, bottom: 50 },
    xAxis: { type: "category", data: [...Array(24).keys()].map(pad), splitArea: { show: false },
             axisLine: { lineStyle: { color: css("--line") } }, axisTick: { show: false } },
    yAxis: { type: "category", data: days, inverse: true, axisLine: { show: false }, axisTick: { show: false } },
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
  opt.xAxis.data = [...Array(24).keys()].map(pad);
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
    : `<li class="empty">${t("insights.empty")}</li>`;
}

function renderRecent(rows) {
  $("#recent").innerHTML = rows.length ? rows.map((r) => {
    const at = new Date(r.started_at * 1000);
    const pct = r.duration ? Math.round((r.listened / r.duration) * 100) : null;
    return `<tr>
      <td class="muted">${at.toLocaleDateString(LOCALE, { day: "numeric", month: "short" })} ${at.toLocaleTimeString(LOCALE, { hour: "2-digit", minute: "2-digit" })}</td>
      <td><a class="plain" href="${esc(trackLink(r.item_id))}"><strong>${esc(r.name || t("unknown"))}</strong></a>
        ${r.artist ? `<span class="muted">· <a class="plain" href="${esc(artistLink(r.artist))}">${esc(r.artist)}</a></span>` : ""}</td>
      <td>${r.source === "backup"
        ? `<span class="tag" title="${esc(t("tag.backup.title"))}">${t("tag.backup")}</span>`
        : r.counted ? "" : `<span class="tag">${t("tag.skip")}</span>`}</td>
      <td class="muted">${pct != null && r.source !== "backup" ? pct + " %" : ""}</td>
      <td class="muted">${esc(r.user_name || "")}</td>
    </tr>`;
  }).join("") : `<tr><td class="empty">${t("recent.empty")}</td></tr>`;
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
          <div class="live">${n.paused ? t("now.paused") : t("now.playing")} · ${esc(n.user_name || "")}</div>
          <div><strong>${esc(n.name)}</strong> <span class="muted">· ${esc((n.artists || [])[0] || "")}</span></div>
          ${n.duration ? `<progress max="${n.duration}" value="${n.position}"></progress>` : ""}
        </div>
      </div>`).join("");
  } catch { /* ignore */ }
}

function renderStatus(meta) {
  const el = $("#status");
  const c = meta.collector;
  if (!c.enabled) { el.className = "status"; el.title = t("status.off"); return; }
  if (c.last_error) {
    const msg = c.last_error.code === "other" ? c.last_error.detail : t(`err.${c.last_error.code}`, { detail: c.last_error.detail });
    el.className = "status err";
    el.title = t("status.error", { msg });
    return;
  }
  const age = c.last_poll ? Date.now() / 1000 - c.last_poll : 0;
  if (age > Math.max(60, c.poll_interval * 3)) {
    el.className = "status err";
    el.title = t("status.stalled", { n: Math.round(age / 60) });
    return;
  }
  el.className = "status ok";
  el.title = c.last_poll ? t("status.ok", { time: new Date(c.last_poll * 1000).toLocaleTimeString(LOCALE) }) : t("status.starting");
}

// --- main -----------------------------------------------------------------

async function loadMeta() {
  state.meta = await (await fetch(`api/meta?lang=${LANG}`)).json();
  renderStatus(state.meta);
  const me = state.meta.me?.jellyfin_user;
  // first load: start on the viewer's own stats when their HA user matches a Jellyfin user
  if (state.user === "" && me && !state.userChosen) state.user = me;
  const sel = $("#user");
  sel.innerHTML = `<option value="">${t("users.all")}</option>` +
    state.meta.users.map((u) => `<option value="${esc(u.id)}">${esc(u.name || u.id)}${u.id === me ? t("users.me") : ""}</option>`).join("");
  sel.value = state.user;
}

async function loadDashboard() {
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
  renderTop("top-artists", artists, (r) => artistLink(r.name));
  renderTop("top-albums", albums, (r) => albumLink(r.key));
  renderTop("top-tracks", tracks, (r) => trackLink(r.key));
  renderShareArea("genres", genres, trend, (_, i) => PALETTE[i % PALETTE.length]);
  moods.series.forEach((s) => (s.label = labels[s.name] || seriesName(s.name)));
  renderShareArea("moods", moods, trend, (name) => MOOD_COLORS[name] || "#94a3b8");
  $("#mood-coverage").textContent = t("mood.coverage", { pct: fmt(moods.coverage * 100) });
  renderMoodHours(moods.by_hour, labels);
  renderHeatmap(heat);
  renderInsights(insights);
  renderRecent(recent);
}

// --- artist / album / track pages ------------------------------------------------

async function loadDetail(kind, key) {
  let a;
  try {
    a = await api("detail", { kind, key });
  } catch {
    $("#artist-hero").innerHTML = `<div><h2>${t("detail.empty")}</h2><div class="sub">${t("detail.empty.hint")}</div></div>`;
    for (const id of ["artist-kpis", "artist-tracks", "artist-albums"]) document.getElementById(id).innerHTML = "";
    chart("artist-months").clear();
    chart("artist-hours").clear();
    loadExtra(kind, key);  // an album's track list doesn't depend on the period
    return;
  }
  const labels = state.meta.moods;
  const favDay = a.weekdays.indexOf(Math.max(...a.weekdays));
  const by = [
    a.artists.length ? t("detail.by", { names: a.artists.map((n) => `<a href="${esc(artistLink(n))}">${esc(n)}</a>`).join(", ") }) : "",
    a.album ? t("detail.from", { album: `<a href="${esc(albumLink(a.album.id))}">${esc(a.album.name)}</a>` }) : "",
    a.year ? `(${a.year})` : "",
  ].filter(Boolean).join(" ");
  $("#artist-hero").innerHTML = `
    ${cover(a.image_id, a.name, "cover")}
    <div style="min-width:0">
      ${a.rank ? `<div class="sub">${t(`detail.rank.${kind}`, { n: a.rank })}</div>` : ""}
      <h2>${esc(a.name)}</h2>
      ${by ? `<div class="sub links">${by}</div>` : ""}
      ${a.first ? `<div class="sub">${t("detail.first", { date: longDate(a.first) })}</div>` : ""}
      <div class="chips">
        ${a.genres.map((g) => `<span class="chip">${esc(g.name)}</span>`).join("")}
        ${a.moods.map((m) => `<span class="chip"><span class="dot" style="background:${MOOD_COLORS[m.name] || "#94a3b8"}"></span>${esc(labels[m.name] || m.name)}</span>`).join("")}
      </div>
    </div>`;
  const kpi = (l, v, d = "&nbsp;") => `<div class="kpi"><div class="label">${l}</div><div class="value">${v}</div><div class="delta">${d}</div></div>`;
  $("#artist-kpis").innerHTML = [
    kpi(t("kpi.plays"), fmt(a.plays), t("detail.share", { pct: fmt(a.share * 100, 1) })),
    kpi(t("kpi.time"), `${fmt(a.minutes / 60, 1)} ${t("hours")}`),
    kind === "artist" && kpi(t("kpi.tracks"), fmt(a.tracks), t("kpi.tracks.albums", { n: fmt(a.albums) })),
    kind === "album" && kpi(t("kpi.tracks_heard"), fmt(a.tracks)),
    kind === "track" && a.duration && kpi(t("kpi.length"), mmss(a.duration)),
    kpi(t("kpi.days_label"), fmt(a.days), t("kpi.days_hint")),
    kpi(t("kpi.fav_day"), capital(t("weekdays")[favDay])),
    kpi(t("kpi.skip"), `${fmt(a.skip_rate * 100)} %`),
    kpi(t("kpi.last"), shortDate(a.last)),
  ].filter(Boolean).join("");

  const months = baseOption();
  months.legend.show = false;
  months.xAxis.data = a.months.labels.map((l) => fmtLabel(l, "month"));
  months.series = [{ type: "bar", name: t("series.plays"), data: a.months.plays, itemStyle: { color: css("--accent"), borderRadius: [3, 3, 0, 0] } }];
  chart("artist-months").setOption(months, true);

  const hours = baseOption();
  hours.legend.show = false;
  hours.xAxis.data = [...Array(24).keys()].map(pad);
  hours.series = [{ type: "bar", name: t("series.plays"), data: a.hours, itemStyle: { color: "#14b8a6", borderRadius: [3, 3, 0, 0] } }];
  chart("artist-hours").setOption(hours, true);

  $("#artist-tracks-title").textContent = t(`list.${kind}`);
  $("#artist-tracks-hint").textContent = kind === "track" ? t("list.track.hint") : "";
  renderTop("artist-tracks", a.top_tracks, (r) => trackLink(r.key));
  $("#artist-albums-card").hidden = kind !== "artist";
  renderTop("artist-albums", a.top_albums, (r) => albumLink(r.key));
  loadExtra(kind, key);
}

// the card under the numbers: progress per album for an artist, the full track list for an album
function loadExtra(kind, key) {
  if (kind === "artist") loadArtistProgress(key);
  else if (kind === "album") loadAlbumTracks(key);
  else $("#artist-progress").hidden = true;
}

const pbar = (heard, total) => `<div class="pbar"><div style="width:${total ? (heard / total) * 100 : 0}%"></div></div>`;

function progressHead(d, extra = "") {
  const pct = Math.round((d.heard / d.total) * 100);
  return `
    <div class="progress-head">
      <div class="progress-pct">${pct} %</div>
      <div style="flex:1;min-width:0">
        <div>${t("progress.heard", { heard: fmt(d.heard), total: fmt(d.total) })}${d.minutes_left ? t("progress.left", { hours: fmt(d.minutes_left / 60, 1) }) : ""}</div>
        ${pbar(d.heard, d.total)}
        ${extra}
      </div>
    </div>`;
}

// the user may have moved on to another page while Jellyfin answered
const stillOn = (kind, key) => { const { view, arg } = currentRoute(); return view === kind && arg === key; };

// How much of the artist's music in the library has been heard, per album (current state, not the period)
async function loadArtistProgress(name) {
  const el = $("#artist-progress");
  const d = await apiNow("artist-progress", { name }).catch(() => null);
  if (!stillOn("artist", name)) return;
  el.hidden = !d || !d.total;
  if (el.hidden) return;
  const next = d.next
    ? `<div class="sub">${t("progress.next")} <a class="plain" href="${esc(trackLink(d.next.item_id))}"><strong>${esc(d.next.name)}</strong></a>
        · <a class="plain" href="${esc(albumLink(d.next.album_id))}">${esc(d.next.album || t("no.album"))}</a></div>`
    : `<div class="sub">${t("progress.done")}</div>`;
  el.innerHTML = `
    <div class="card-head"><h2>${t("progress.title")}</h2>
      <span class="hint">${t("progress.hint")}${state.user ? t("progress.hint.marks") : ""}</span></div>
    ${progressHead(d, next)}
    <div class="progress-albums">${d.albums.map((a) => `
      <div class="palbum">
        ${a.id ? `<a class="plain name" href="${esc(albumLink(a.id))}" title="${esc(a.name)}">${esc(a.name || t("no.album"))}</a>`
               : `<span class="name">${esc(a.name || t("no.album"))}</span>`}
        ${pbar(a.heard, a.total)}
        <span class="count">${a.heard}/${a.total}</span>
      </div>`).join("")}</div>`;
}

// Every track on the album, with a mark for heard and the number of plays (current state, not the period)
async function loadAlbumTracks(albumId) {
  const el = $("#artist-progress");
  const d = await apiNow("album-tracks", { id: albumId }).catch(() => null);
  if (!stillOn("album", albumId)) return;
  el.hidden = !d || !d.total;
  if (el.hidden) return;
  let disc = null;
  const rows = d.tracks.map((tr) => {
    const head = tr.disc && tr.disc !== disc ? `<tr class="disc"><td colspan="4">${t("tracks.disc", { n: tr.disc })}</td></tr>` : "";
    disc = tr.disc;
    const name = tr.plays ? `<a class="plain" href="${esc(trackLink(tr.item_id))}">${esc(tr.name)}</a>` : esc(tr.name);
    return `${head}<tr class="${tr.heard ? "" : "unheard"}">
      <td class="num">${tr.number ?? ""}</td>
      <td><span class="mark" title="${esc(t(tr.heard ? "tracks.heard.title" : "tracks.unheard.title"))}">${tr.heard ? "✓" : "○"}</span> ${name}</td>
      <td class="muted">${tr.plays ? t("tracks.plays", { n: fmt(tr.plays) }) : ""}</td>
      <td class="muted num">${tr.duration ? mmss(tr.duration) : ""}</td>
    </tr>`;
  }).join("");
  el.innerHTML = `
    <div class="card-head"><h2>${t("tracks.title")}</h2>
      <span class="hint">${t("progress.hint")}${state.user ? t("progress.hint.marks") : ""}</span></div>
    ${progressHead(d)}
    <table class="tracklist"><tbody>${rows}</tbody></table>`;
}

// --- never heard ------------------------------------------------------------------

const nTracks = (n) => (n === 1 ? t("discover.track_one") : t("discover.tracks", { n: fmt(n) }));
const nAlbums = (n) => (n === 1 ? t("discover.album_one") : t("discover.albums_n", { n: fmt(n) }));

async function loadDiscover() {
  const d = await apiNow("never-heard");
  if (currentRoute().view !== "discover") return;
  if (!d) {
    $("#discover-kpis").innerHTML = `<div class="card empty">${t("discover.nojf")}</div>`;
    $("#discover-albums").innerHTML = $("#discover-artists").innerHTML = "";
    return;
  }
  const kpi = (l, v, sub) => `<div class="kpi"><div class="label">${l}</div><div class="value">${v}</div><div class="delta">${sub}</div></div>`;
  const heardPct = d.tracks_total ? Math.round((d.tracks_heard / d.tracks_total) * 100) : 0;
  $("#discover-kpis").innerHTML = [
    kpi(t("discover.library"), `${heardPct} %`, t("discover.tracks_of", { heard: fmt(d.tracks_heard), total: fmt(d.tracks_total) })),
    kpi(t("discover.albums_never"), fmt(d.albums_never), t("discover.of", { n: fmt(d.albums_total) })),
    kpi(t("discover.artists_never"), fmt(d.artists_never), t("discover.of", { n: fmt(d.artists_total) })),
    kpi(t("discover.hours"), `${fmt(d.minutes_never / 60, 1)} ${t("hours")}`, "&nbsp;"),
  ].join("");
  if (!d.albums.length) {
    $("#discover-albums").innerHTML = `<div class="empty">${t("discover.none")}</div>`;
  } else {
    renderTop("discover-albums", d.albums.map((a) => ({
      name: a.name, image_id: a.id,
      sub: [a.artist, a.year].filter(Boolean).join(" · "),
      count: `${nTracks(a.tracks)}${a.added ? `<br>${t("discover.added", { date: shortDate(a.added) })}` : ""}`,
    })));
  }
  renderTop("discover-artists", d.artists.map((s) => ({
    name: s.name, count: `${nAlbums(s.albums)}<br>${nTracks(s.tracks)}`,
  })));
}

// --- wrapped ------------------------------------------------------------------

async function loadWrapped() {
  const p = new URLSearchParams({ lang: LANG });
  if (state.year) p.set("year", state.year);
  if (state.user) p.set("user", state.user);
  const w = await (await fetch(`api/wrapped?${p}`)).json();
  $("#wrapped-year").innerHTML = (w.years.length ? w.years : [w.year])
    .map((y) => `<option value="${y}" ${y === w.year ? "selected" : ""}>${y}</option>`).join("");

  const el = $("#view-wrapped");
  if (!w.plays) {
    el.innerHTML = `<section class="wr-hero"><div class="eyebrow">Wrapped ${w.year}</div><div class="lead" style="margin-top:12px">${t("wr.empty", { year: w.year })}</div></section>`;
    return;
  }
  const day = (iso) => new Date(iso + "T00:00:00").toLocaleDateString(LOCALE, { day: "numeric", month: "long" });
  const list = (rows, linkFor) => `<ol class="wr-list">${rows.map((r, i) => `
    <li><span class="n">${i + 1}</span>
      <span>${linkFor ? `<a href="${esc(linkFor(r))}" style="color:inherit">${esc(r.name)}</a>` : esc(r.name)}${r.sub ? ` <span class="muted">· ${esc(r.sub)}</span>` : ""}</span>
      <span class="s">${fmt(r.plays)} ×</span></li>`).join("")}</ol>`;
  const fact = (eyebrow, headline, text) =>
    `<section class="wr-card"><div class="eyebrow">${eyebrow}</div><div class="headline">${headline}</div><div class="text">${text}</div></section>`;

  const star = w.top_artists[0];
  const runnersUp = w.genres.slice(1, 4).map((g) => esc(g.name)).join(", ");
  const facts = [
    fact(t("wr.busiest"), day(w.busiest_day.d), t("wr.busiest.text", { min: fmt(w.busiest_day.minutes), n: fmt(w.busiest_day.n) })),
    w.longest_session && fact(t("wr.session"), `${fmt(w.longest_session.minutes)} ${t("minutes")}`,
      t("wr.session.text", { n: fmt(w.longest_session.tracks), date: longDate(w.longest_session.start) })),
    w.on_repeat && fact(t("wr.repeat"), esc(w.on_repeat.name),
      t("wr.repeat.text", { artist: esc(w.on_repeat.artist || ""), n: w.on_repeat.n, date: day(w.on_repeat.d) })),
    fact(t("wr.first"), esc(w.first_track.name), t("wr.first.text", { artist: esc(w.first_track.artist || ""), date: longDate(w.first_track.started_at) })),
    fact(t("wr.new"), w.new_artists === 1 ? t("wr.new.one") : t("wr.new.many", { n: fmt(w.new_artists) }),
      t("wr.new.text", { pct: fmt(w.discovery_rate * 100) })),
    w.genres[0] && fact(t("wr.genre"), esc(w.genres[0].name), runnersUp ? t("wr.genre.text", { names: runnersUp }) : ""),
  ].filter(Boolean).join("");

  el.innerHTML = `
    <section class="wr-hero">
      <div class="eyebrow">${t("wr.eyebrow", { year: w.year })}</div>
      <div class="big">${fmt(w.minutes)}</div>
      <div class="lead">${t("wr.lead", { hours: fmt(w.minutes / 60), days: fmt(w.minutes / 1440, 1), plays: fmt(w.plays), tracks: fmt(w.tracks) })}</div>
    </section>
    <div class="wr-row">
      <section class="wr-card wr-persona"><div class="eyebrow">${t("wr.persona")}</div><div class="headline">${esc(w.persona.title)}</div><div class="text">${esc(w.persona.text)}</div></section>
      ${fact(t("wr.peak"), t("wr.peak.value", { day: capital(t("weekdays")[w.peak.weekday]), hour: pad(w.peak.hour) }), t("wr.peak.text"))}
    </div>
    ${star ? `<section class="wr-card wr-star">${cover(star.image_id, star.name, "ph")}
      <div><div class="eyebrow">${t("wr.star")}</div>
        <div class="headline"><a href="${esc(artistLink(star.name))}" style="color:inherit;text-decoration:none">${esc(star.name)}</a></div>
        <div class="text">${t("wr.star.text", { plays: fmt(star.plays), hours: fmt(star.minutes / 60, 1), days: fmt(star.days) })}</div></div>
    </section>` : ""}
    <div class="wr-row">
      <section class="wr-card"><div class="eyebrow">${t("card.top_artists")}</div>${list(w.top_artists, (r) => artistLink(r.name))}</section>
      <section class="wr-card"><div class="eyebrow">${t("card.top_tracks")}</div>${list(w.top_tracks, (r) => trackLink(r.key))}</section>
      <section class="wr-card"><div class="eyebrow">${t("card.top_albums")}</div>${list(w.top_albums, (r) => albumLink(r.key))}</section>
    </div>
    <div class="wr-row">${facts}</div>
    <div class="grid two">
      <section class="card"><div class="card-head"><h2>${t("wr.months")}</h2><span class="hint">${t("unit.hours")}</span></div><div id="wr-months" class="chart"></div></section>
      <section class="card"><div class="card-head"><h2>${t("wr.moods")}</h2></div><div id="wr-moods" class="chart"></div></section>
    </div>`;

  const months = baseOption();
  months.legend.show = false;
  months.xAxis.data = w.months.labels.map((l) => fmtLabel(l, "month"));
  months.tooltip.valueFormatter = (v) => `${fmt(v, 1)} ${t("hours")}`;
  months.series = [{
    type: "bar", name: t("series.hours"), data: w.months.minutes.map((m) => +(m / 60).toFixed(1)),
    itemStyle: { borderRadius: [4, 4, 0, 0], color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: "#ec4899" }, { offset: 1, color: "#7c5cff" }]) },
  }];
  chart("wr-months").setOption(months, true);

  chart("wr-moods").setOption({
    animation: !state.quiet,
    tooltip: { trigger: "item", backgroundColor: css("--card"), borderColor: css("--line"), textStyle: { color: css("--text") } },
    legend: { bottom: 0, textStyle: { color: css("--muted") }, itemWidth: 10, itemHeight: 10 },
    series: [{
      type: "pie", radius: ["45%", "72%"], center: ["50%", "45%"], itemStyle: { borderColor: css("--card"), borderWidth: 2 },
      label: { color: css("--text"), formatter: "{d} %" },
      data: w.moods.map((m) => ({ name: m.label, value: m.n, itemStyle: { color: MOOD_COLORS[m.name] } })),
    }],
  }, true);
}

// --- compare ------------------------------------------------------------------

async function loadCompare() {
  const c = await api("compare");
  $("#compare-pairs").innerHTML = c.pairs.length ? c.pairs.map((p) => `
    <section class="card match" style="margin-bottom:16px">
      <div class="pct">${fmt(p.match * 100)} %</div>
      <div style="flex:1;min-width:220px">
        <h2>${t("cmp.match", { a: esc(p.a), b: esc(p.b) })}</h2>
        <div class="meter"><div style="width:${p.match * 100}%"></div></div>
        <div class="hint" style="margin-top:6px">${t("cmp.shared", { n: fmt(p.shared_count) })}</div>
        <div class="chips">${p.shared.map((s) => `<a class="chip" href="${esc(artistLink(s))}" style="color:inherit;text-decoration:none">${esc(s)}</a>`).join("")}</div>
      </div>
    </section>`).join("")
    : `<section class="card empty">${t("cmp.empty")}</section>`;

  const row = (dt, dd) => `<dt>${dt}</dt><dd>${dd}</dd>`;
  $("#compare-people").innerHTML = c.people.map((p) => `
    <section class="card person">
      <h3>${esc(p.name)}</h3>
      <dl>
        ${row(t("kpi.plays"), fmt(p.plays))}
        ${row(t("kpi.time"), `${fmt(p.minutes / 60, 1)} ${t("hours")}`)}
        ${row(t("kpi.artists"), fmt(p.artists))}
        ${row(t("cmp.top_artist"), p.top_artist ? `<a href="${esc(artistLink(p.top_artist.name))}" style="color:inherit">${esc(p.top_artist.name)}</a>` : "–")}
        ${row(t("cmp.top_track"), p.top_track ? esc(p.top_track.name) : "–")}
        ${row(t("cmp.top_genre"), esc(p.top_genre || "–"))}
        ${row(t("cmp.mood"), esc(p.top_mood || "–"))}
        ${row(t("cmp.peak"), p.peak_hour != null ? t("cmp.peak.value", { hour: pad(p.peak_hour) }) : "–")}
        ${row(t("kpi.skip"), `${fmt(p.skip_rate * 100)} %`)}
      </dl>
    </section>`).join("");

  const bucket = state.range === "7" || state.range === "30" ? "week" : "month";
  const series = await Promise.all(c.people.map((p) => api("timeline", { bucket, user: p.id })));
  const opt = baseOption();
  opt.xAxis.data = (series[0]?.labels || []).map((l) => fmtLabel(l, bucket));
  opt.tooltip.valueFormatter = (v) => `${fmt(v, 1)} ${t("hours")}`;
  opt.series = c.people.map((p, i) => ({
    name: p.name, type: "bar", data: series[i].minutes.map((m) => +(m / 60).toFixed(1)),
    itemStyle: { color: PALETTE[i % PALETTE.length], borderRadius: [3, 3, 0, 0] },
  }));
  chart("compare-chart").setOption(opt, true);
}

// --- routing ------------------------------------------------------------------

const DETAIL_VIEWS = ["artist", "album", "track"];  // all rendered into #view-artist
const PAGES = ["dashboard", "artist", "discover", "wrapped", "compare"];  // the #view-* elements
const VIEWS = ["dashboard", ...DETAIL_VIEWS, "discover", "wrapped", "compare"];

function currentRoute() {
  const [view, arg] = location.hash.replace(/^#\/?/, "").split("/");
  return { view: VIEWS.includes(view) ? view : "dashboard", arg: arg ? decodeURIComponent(arg) : null };
}

function updateControls(view) {
  const multiUser = (state.meta?.users.length || 0) > 1;
  const now = view === "discover";  // shows the library as it is, so the period doesn't apply
  $("#range").hidden = view === "wrapped" || now;
  $("#wrapped-year").hidden = view !== "wrapped";
  $("#user").hidden = view === "compare" || !multiUser;
  $("#export").hidden = now;
  document.querySelector('#nav a[data-view="compare"]').hidden = !multiUser;
  document.querySelector('#nav a[data-view="discover"]').hidden = !state.meta?.collector.enabled;
  $("#export").href = `api/export.csv?${rangeParams()}`;
  document.querySelectorAll("#nav a").forEach((a) =>
    a.classList.toggle("on", a.dataset.view === view || (DETAIL_VIEWS.includes(view) && a.dataset.view === "dashboard")));
}

async function refresh() {
  const { view, arg } = currentRoute();
  const shown = DETAIL_VIEWS.includes(view) ? "artist" : view;
  PAGES.forEach((v) => ($(`#view-${v}`).hidden = v !== shown));
  updateControls(view);
  try {
    if (DETAIL_VIEWS.includes(view)) await loadDetail(view, arg);
    else if (view === "discover") await loadDiscover();
    else if (view === "wrapped") await loadWrapped();
    else if (view === "compare") await loadCompare();
    else await loadDashboard();
  } catch (e) {
    console.error(e);
  }
  Object.values(charts).forEach((c) => c.resize());
}

applyI18n();
document.querySelectorAll("#range button").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll("#range button").forEach((x) => x.classList.toggle("on", x === b));
  state.range = b.dataset.range;
  state.bucket = null;
  refresh();
}));
document.querySelectorAll("#bucket button").forEach((b) => b.addEventListener("click", () => {
  state.bucket = b.dataset.bucket;
  api("timeline", { bucket: state.bucket }).then((tl) => {
    document.querySelectorAll("#bucket button").forEach((x) => x.classList.toggle("on", x === b));
    renderTimeline(tl, state.bucket);
  });
}));
$("#user").addEventListener("change", (e) => { state.user = e.target.value; state.userChosen = true; refresh(); });
$("#wrapped-year").addEventListener("change", (e) => { state.year = e.target.value; refresh(); });
$("#lang").addEventListener("click", switchLanguage);
window.addEventListener("hashchange", () => { window.scrollTo(0, 0); refresh(); });
window.addEventListener("resize", () => Object.values(charts).forEach((c) => c.resize()));
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", refresh);

// Reload the visible view when a play has been recorded (or moods were tagged) since last look.
// While the tab is hidden the marker is left alone, so it catches up as soon as it is shown again.
async function checkForNewData() {
  try {
    const { marker } = await (await fetch("api/latest")).json();
    if (document.hidden || marker === state.marker) return;
    const first = state.marker === undefined;
    state.marker = marker;
    if (first) return;
    state.quiet = true;
    await loadMeta();
    await refresh();
  } catch { /* try again next tick */ } finally {
    state.quiet = false;
  }
}

document.addEventListener("visibilitychange", () => { if (!document.hidden) { renderNow(); checkForNewData(); } });

(async () => {
  await loadMeta();
  await refresh();
  renderNow();
  checkForNewData();
  setInterval(() => { renderNow(); checkForNewData(); }, 10000);
  setInterval(async () => { await loadMeta(); updateControls(currentRoute().view); }, 60000);
})();
