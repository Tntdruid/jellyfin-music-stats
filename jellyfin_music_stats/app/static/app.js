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

function cover(imageId, name, cls = "img") {
  const letter = esc((name || "?")[0]).replace(/'/g, "");
  return imageId
    ? `<img class="${cls}" loading="lazy" src="api/image/${esc(imageId)}" alt="" onerror="this.outerHTML='<div class=${cls}>${letter}</div>'">`
    : `<div class="${cls}">${letter}</div>`;
}

const artistLink = (name) => `#/artist/${encodeURIComponent(name)}`;
const albumLink = (id) => `#/album/${encodeURIComponent(id)}`;
const trackLink = (id) => `#/track/${encodeURIComponent(id)}`;

function renderTop(id, rows, linkFor = null) {
  const el = document.getElementById(id);
  if (!rows.length) { el.innerHTML = `<div class="empty">Ingen data endnu</div>`; return; }
  const max = rows[0].plays;
  el.innerHTML = rows.map((r) => {
    const tag = linkFor ? `a class="row" href="${esc(linkFor(r))}"` : `div class="row"`;
    return `
    <li>
      <${tag}>
        ${cover(r.image_id, r.name)}
        <div class="meta">
          <div class="name" title="${esc(r.name)}">${esc(r.name)}</div>
          ${r.sub ? `<div class="sub">${esc(r.sub)}</div>` : ""}
          <div class="bar" style="width:${(r.plays / max) * 100}%"></div>
        </div>
        <div class="count">${fmt(r.plays)}${r.minutes != null ? `<br>${fmt(r.minutes)} min` : " ×"}</div>
      </${linkFor ? "a" : "div"}>
    </li>`;
  }).join("");
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
    animation: !state.quiet,
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
      <td><a class="plain" href="${esc(trackLink(r.item_id))}"><strong>${esc(r.name || "Ukendt")}</strong></a>
        ${r.artist ? `<span class="muted">· <a class="plain" href="${esc(artistLink(r.artist))}">${esc(r.artist)}</a></span>` : ""}</td>
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
  moods.series.forEach((s) => (s.label = labels[s.name] || s.name));
  renderShareArea("moods", moods, trend, (name) => MOOD_COLORS[name] || "#94a3b8");
  $("#mood-coverage").textContent = `${fmt(moods.coverage * 100)} % af lytningerne har humør-data`;
  renderMoodHours(moods.by_hour, labels);
  renderHeatmap(heat);
  renderInsights(insights);
  renderRecent(recent);
}

// --- artist page --------------------------------------------------------------

const longDate = (t) => new Date(t * 1000).toLocaleDateString("da-DK", { day: "numeric", month: "long", year: "numeric" });
const capital = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const WEEKDAY_NAMES = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"];

const KIND_TEXT = {
  artist: { rank: "kunstnere", list: "Top sange" },
  album: { rank: "albums", list: "Sange på albummet" },
  track: { rank: "sange", list: "Ofte hørt lige efter" },
};

async function loadDetail(kind, key) {
  let a;
  try {
    a = await api("detail", { kind, key });
  } catch {
    $("#artist-hero").innerHTML = `<div><h2>Ingen lytninger i perioden</h2><div class="sub">Prøv en længere periode, fx "Alt".</div></div>`;
    for (const id of ["artist-kpis", "artist-tracks", "artist-albums"]) document.getElementById(id).innerHTML = "";
    chart("artist-months").clear();
    chart("artist-hours").clear();
    return;
  }
  const labels = state.meta.moods;
  const favDay = a.weekdays.indexOf(Math.max(...a.weekdays));
  const by = [
    a.artists.length ? `af ${a.artists.map((n) => `<a href="${esc(artistLink(n))}">${esc(n)}</a>`).join(", ")}` : "",
    a.album ? `fra <a href="${esc(albumLink(a.album.id))}">${esc(a.album.name)}</a>` : "",
    a.year ? `(${a.year})` : "",
  ].filter(Boolean).join(" ");
  $("#artist-hero").innerHTML = `
    ${cover(a.image_id, a.name, "cover")}
    <div style="min-width:0">
      ${a.rank ? `<div class="sub">#${a.rank} blandt dine ${KIND_TEXT[kind].rank} i perioden</div>` : ""}
      <h2>${esc(a.name)}</h2>
      ${by ? `<div class="sub links">${by}</div>` : ""}
      ${a.first ? `<div class="sub">Første gang hørt ${longDate(a.first)}</div>` : ""}
      <div class="chips">
        ${a.genres.map((g) => `<span class="chip">${esc(g.name)}</span>`).join("")}
        ${a.moods.map((m) => `<span class="chip"><span class="dot" style="background:${MOOD_COLORS[m.name] || "#94a3b8"}"></span>${esc(labels[m.name] || m.name)}</span>`).join("")}
      </div>
    </div>`;
  const kpi = (l, v, d = "&nbsp;") => `<div class="kpi"><div class="label">${l}</div><div class="value">${v}</div><div class="delta">${d}</div></div>`;
  $("#artist-kpis").innerHTML = [
    kpi("Lytninger", fmt(a.plays), `${fmt(a.share * 100, 1)} % af al lytning`),
    kpi("Lyttetid", `${fmt(a.minutes / 60, 1)} t`),
    kind === "artist" && kpi("Sange", fmt(a.tracks), `fra ${fmt(a.albums)} albums`),
    kind === "album" && kpi("Sange hørt", fmt(a.tracks)),
    kind === "track" && a.duration && kpi("Længde", `${Math.floor(a.duration / 60)}:${String(Math.round(a.duration % 60)).padStart(2, "0")}`),
    kpi("Dage", fmt(a.days), "med mindst én lytning"),
    kpi("Yndlingsdag", capital(WEEKDAY_NAMES[favDay])),
    kpi("Skip-rate", `${fmt(a.skip_rate * 100)} %`),
    kpi("Sidst hørt", new Date(a.last * 1000).toLocaleDateString("da-DK", { day: "numeric", month: "short" })),
  ].filter(Boolean).join("");

  const months = baseOption();
  months.legend.show = false;
  months.xAxis.data = a.months.labels.map((l) => fmtLabel(l, "month"));
  months.series = [{ type: "bar", name: "Lytninger", data: a.months.plays, itemStyle: { color: css("--accent"), borderRadius: [3, 3, 0, 0] } }];
  chart("artist-months").setOption(months, true);

  const hours = baseOption();
  hours.legend.show = false;
  hours.xAxis.data = [...Array(24).keys()].map((h) => String(h).padStart(2, "0"));
  hours.series = [{ type: "bar", name: "Lytninger", data: a.hours, itemStyle: { color: "#14b8a6", borderRadius: [3, 3, 0, 0] } }];
  chart("artist-hours").setOption(hours, true);

  $("#artist-tracks-title").textContent = KIND_TEXT[kind].list;
  $("#artist-tracks-hint").textContent = kind === "track" ? "inden for 10 min" : "";
  renderTop("artist-tracks", a.top_tracks, (r) => trackLink(r.key));
  $("#artist-albums-card").hidden = kind !== "artist";
  renderTop("artist-albums", a.top_albums, (r) => albumLink(r.key));
}

// --- wrapped ------------------------------------------------------------------

async function loadWrapped() {
  const p = new URLSearchParams();
  if (state.year) p.set("year", state.year);
  if (state.user) p.set("user", state.user);
  const w = await (await fetch(`api/wrapped?${p}`)).json();
  $("#wrapped-year").innerHTML = (w.years.length ? w.years : [w.year])
    .map((y) => `<option value="${y}" ${y === w.year ? "selected" : ""}>${y}</option>`).join("");

  const el = $("#view-wrapped");
  if (!w.plays) {
    el.innerHTML = `<section class="wr-hero"><div class="eyebrow">Wrapped ${w.year}</div><div class="lead" style="margin-top:12px">Ingen lytninger i ${w.year} endnu.</div></section>`;
    return;
  }
  const day = (iso) => new Date(iso + "T00:00:00").toLocaleDateString("da-DK", { day: "numeric", month: "long" });
  const list = (rows, linkFor) => `<ol class="wr-list">${rows.map((r, i) => `
    <li><span class="n">${i + 1}</span>
      <span>${linkFor ? `<a href="${esc(linkFor(r))}" style="color:inherit">${esc(r.name)}</a>` : esc(r.name)}${r.sub ? ` <span class="muted">· ${esc(r.sub)}</span>` : ""}</span>
      <span class="s">${fmt(r.plays)} ×</span></li>`).join("")}</ol>`;
  const fact = (eyebrow, headline, text) =>
    `<section class="wr-card"><div class="eyebrow">${eyebrow}</div><div class="headline">${headline}</div><div class="text">${text}</div></section>`;

  const star = w.top_artists[0];
  const runnersUp = w.genres.slice(1, 4).map((g) => esc(g.name)).join(", ");
  const facts = [
    fact("Travleste dag", day(w.busiest_day.d), `${fmt(w.busiest_day.minutes)} minutter og ${fmt(w.busiest_day.n)} sange på én dag.`),
    w.longest_session && fact("Længste session", `${fmt(w.longest_session.minutes)} min`,
      `${fmt(w.longest_session.tracks)} sange i træk den ${longDate(w.longest_session.start)}.`),
    w.on_repeat && fact("På repeat", esc(w.on_repeat.name), `${esc(w.on_repeat.artist || "")} – spillet ${w.on_repeat.n} gange den ${day(w.on_repeat.d)}.`),
    fact("Årets første sang", esc(w.first_track.name), `${esc(w.first_track.artist || "")} – ${longDate(w.first_track.started_at)}.`),
    fact("Nye opdagelser", w.new_artists === 1 ? "1 ny kunstner" : `${fmt(w.new_artists)} nye kunstnere`, `${fmt(w.discovery_rate * 100)} % af de sange, du hørte, var nye for dig.`),
    w.genres[0] && fact("Årets genre", esc(w.genres[0].name), runnersUp ? `Efterfulgt af ${runnersUp}.` : ""),
  ].filter(Boolean).join("");

  el.innerHTML = `
    <section class="wr-hero">
      <div class="eyebrow">Dit ${w.year} i musik</div>
      <div class="big">${fmt(w.minutes)}</div>
      <div class="lead">minutter med musik. Det er ${fmt(w.minutes / 60)} timer, eller ${fmt(w.minutes / 1440, 1)} døgn, fordelt på ${fmt(w.plays)} lytninger af ${fmt(w.tracks)} forskellige sange.</div>
    </section>
    <div class="wr-row">
      <section class="wr-card wr-persona"><div class="eyebrow">Din lyttertype</div><div class="headline">${esc(w.persona.title)}</div><div class="text">${esc(w.persona.text)}</div></section>
      ${fact("Dit yndlingstidspunkt", `${capital(w.peak.weekday)} kl. ${String(w.peak.hour).padStart(2, "0")}`, "Her er der størst chance for at finde dig med musik i ørerne.")}
    </div>
    ${star ? `<section class="wr-card wr-star">${cover(star.image_id, star.name, "ph")}
      <div><div class="eyebrow">Årets kunstner</div>
        <div class="headline"><a href="${esc(artistLink(star.name))}" style="color:inherit;text-decoration:none">${esc(star.name)}</a></div>
        <div class="text">${fmt(star.plays)} lytninger og ${fmt(star.minutes / 60, 1)} timer fordelt på ${fmt(star.days)} dage.</div></div>
    </section>` : ""}
    <div class="wr-row">
      <section class="wr-card"><div class="eyebrow">Top kunstnere</div>${list(w.top_artists, (r) => artistLink(r.name))}</section>
      <section class="wr-card"><div class="eyebrow">Top sange</div>${list(w.top_tracks, (r) => trackLink(r.key))}</section>
      <section class="wr-card"><div class="eyebrow">Top albums</div>${list(w.top_albums, (r) => albumLink(r.key))}</section>
    </div>
    <div class="wr-row">${facts}</div>
    <div class="grid two">
      <section class="card"><div class="card-head"><h2>Måned for måned</h2><span class="hint">timer</span></div><div id="wr-months" class="chart"></div></section>
      <section class="card"><div class="card-head"><h2>Årets humør</h2></div><div id="wr-moods" class="chart"></div></section>
    </div>`;

  const months = baseOption();
  months.legend.show = false;
  months.xAxis.data = w.months.labels.map((l) => fmtLabel(l, "month"));
  months.tooltip.valueFormatter = (v) => `${fmt(v, 1)} t`;
  months.series = [{
    type: "bar", name: "Timer", data: w.months.minutes.map((m) => +(m / 60).toFixed(1)),
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
        <h2>Musiksmag-match: ${esc(p.a)} og ${esc(p.b)}</h2>
        <div class="meter"><div style="width:${p.match * 100}%"></div></div>
        <div class="hint" style="margin-top:6px">${fmt(p.shared_count)} fælles kunstnere</div>
        <div class="chips">${p.shared.map((s) => `<a class="chip" href="${esc(artistLink(s))}" style="color:inherit;text-decoration:none">${esc(s)}</a>`).join("")}</div>
      </div>
    </section>`).join("")
    : `<section class="card empty">Sammenligningen kræver mindst to brugere med lytninger i perioden.</section>`;

  const row = (dt, dd) => `<dt>${dt}</dt><dd>${dd}</dd>`;
  $("#compare-people").innerHTML = c.people.map((p) => `
    <section class="card person">
      <h3>${esc(p.name)}</h3>
      <dl>
        ${row("Lytninger", fmt(p.plays))}
        ${row("Lyttetid", `${fmt(p.minutes / 60, 1)} t`)}
        ${row("Kunstnere", fmt(p.artists))}
        ${row("Top kunstner", p.top_artist ? `<a href="${esc(artistLink(p.top_artist.name))}" style="color:inherit">${esc(p.top_artist.name)}</a>` : "–")}
        ${row("Top sang", p.top_track ? esc(p.top_track.name) : "–")}
        ${row("Top genre", esc(p.top_genre || "–"))}
        ${row("Humør", esc(p.top_mood || "–"))}
        ${row("Lytter mest", p.peak_hour != null ? `kl. ${String(p.peak_hour).padStart(2, "0")}` : "–")}
        ${row("Skip-rate", `${fmt(p.skip_rate * 100)} %`)}
      </dl>
    </section>`).join("");

  const bucket = state.range === "7" || state.range === "30" ? "week" : "month";
  const series = await Promise.all(c.people.map((p) => api("timeline", { bucket, user: p.id })));
  const opt = baseOption();
  opt.xAxis.data = (series[0]?.labels || []).map((l) => fmtLabel(l, bucket));
  opt.tooltip.valueFormatter = (v) => `${fmt(v, 1)} t`;
  opt.series = c.people.map((p, i) => ({
    name: p.name, type: "bar", data: series[i].minutes.map((m) => +(m / 60).toFixed(1)),
    itemStyle: { color: PALETTE[i % PALETTE.length], borderRadius: [3, 3, 0, 0] },
  }));
  chart("compare-chart").setOption(opt, true);
}

// --- routing ------------------------------------------------------------------

const DETAIL_VIEWS = ["artist", "album", "track"];  // all rendered into #view-artist
const VIEWS = ["dashboard", ...DETAIL_VIEWS, "wrapped", "compare"];

function currentRoute() {
  const [view, arg] = location.hash.replace(/^#\/?/, "").split("/");
  return { view: VIEWS.includes(view) ? view : "dashboard", arg: arg ? decodeURIComponent(arg) : null };
}

function updateControls(view) {
  const multiUser = (state.meta?.users.length || 0) > 1;
  $("#range").hidden = view === "wrapped";
  $("#wrapped-year").hidden = view !== "wrapped";
  $("#user").hidden = view === "compare" || !multiUser;
  document.querySelector('#nav a[data-view="compare"]').hidden = !multiUser;
  $("#export").href = `api/export.csv?${rangeParams()}`;
  document.querySelectorAll("#nav a").forEach((a) =>
    a.classList.toggle("on", a.dataset.view === view || (DETAIL_VIEWS.includes(view) && a.dataset.view === "dashboard")));
}

async function refresh() {
  const { view, arg } = currentRoute();
  const shown = DETAIL_VIEWS.includes(view) ? "artist" : view;
  ["dashboard", "artist", "wrapped", "compare"].forEach((v) => ($(`#view-${v}`).hidden = v !== shown));
  updateControls(view);
  try {
    if (DETAIL_VIEWS.includes(view)) await loadDetail(view, arg);
    else if (view === "wrapped") await loadWrapped();
    else if (view === "compare") await loadCompare();
    else await loadDashboard();
  } catch (e) {
    console.error(e);
  }
  Object.values(charts).forEach((c) => c.resize());
}

document.querySelectorAll("#range button").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll("#range button").forEach((x) => x.classList.toggle("on", x === b));
  state.range = b.dataset.range;
  state.bucket = null;
  refresh();
}));
document.querySelectorAll("#bucket button").forEach((b) => b.addEventListener("click", () => {
  state.bucket = b.dataset.bucket;
  api("timeline", { bucket: state.bucket }).then((t) => {
    document.querySelectorAll("#bucket button").forEach((x) => x.classList.toggle("on", x === b));
    renderTimeline(t, state.bucket);
  });
}));
$("#user").addEventListener("change", (e) => { state.user = e.target.value; refresh(); });
$("#wrapped-year").addEventListener("change", (e) => { state.year = e.target.value; refresh(); });
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

