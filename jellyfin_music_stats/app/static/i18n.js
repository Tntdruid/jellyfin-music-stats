// Page texts in Danish and English. The language follows the browser (Danish for "da", English otherwise)
// until the viewer picks one with the DA/EN button; that choice is remembered in this browser only.
const LANG = (() => {
  try {
    const saved = localStorage.getItem("lang");
    if (saved === "da" || saved === "en") return saved;
  } catch { /* storage blocked: fall back to the browser language */ }
  return (navigator.language || "da").toLowerCase().startsWith("da") ? "da" : "en";
})();
const LOCALE = LANG === "da" ? "da-DK" : "en-GB";

const STRINGS = {
  da: {
    title: "Musikstatistik",
    "nav.dashboard": "Oversigt", "nav.discover": "Aldrig hørt", "nav.wrapped": "Wrapped", "nav.compare": "Sammenlign",
    "range.7": "7 dage", "range.30": "30 dage", "range.90": "90 dage", "range.year": "I år", "range.all": "Alt",
    "users.all": "Alle brugere", "users.me": " (dig)",
    "export.title": "Hent afspilningerne i perioden som CSV",
    "lang.switch": "EN", "lang.switch.title": "Switch to English",
    back: "← Tilbage",
    nodata: "Ingen data endnu",
    hours: "t", minutes: "min", "unit.hours": "timer",
    other: "Andet", "no.album": "Uden album", unknown: "Ukendt",

    "kpi.plays": "Lytninger", "kpi.time": "Lyttetid", "kpi.artists": "Kunstnere", "kpi.new_artists": "Nye kunstnere",
    "kpi.skip": "Skip-rate", "kpi.streak": "Streak", "kpi.session": "Gns. session",
    "kpi.vs_prev": "{pct} % vs. forrige periode", "kpi.new_tracks": "{pct} % nye sange",
    "kpi.days": "{n} dage", "kpi.record": "rekord: {n} dage", "kpi.sessions": "{n} sessioner",

    "card.timeline": "Lytninger over tid", "bucket.day": "Dag", "bucket.week": "Uge", "bucket.month": "Måned",
    "series.plays": "Lytninger", "series.minutes": "Minutter", "series.hours": "Timer",
    "card.insights": "Indsigt", "insights.empty": "Indsigter dukker op, når der er lyttet lidt mere.",
    "card.top_artists": "Top kunstnere", "card.top_albums": "Top albums", "card.top_tracks": "Top sange",
    "card.genres": "Genrer over tid", "hint.share": "andel af lytninger",
    "card.heatmap": "Hvornår lytter du?", "card.moods": "Musikhumør over tid", "card.mood_hours": "Humør i løbet af døgnet",
    "mood.coverage": "{pct} % af lytningerne har humør-data",
    "card.recent": "Seneste afspilninger", "recent.empty": "Ingen afspilninger endnu",
    "tag.backup": "fundet bagefter", "tag.backup.title": "Appen rapporterede ikke afspilningen live; fundet via Jellyfins afspilningstal",
    "tag.skip": "sprunget over",
    "now.playing": "SPILLER NU", "now.paused": "PAUSE",
    "heatmap.tip": "{day} kl. {hour}: {n} lytninger",
    days: ["Man", "Tir", "Ons", "Tor", "Fre", "Lør", "Søn"],
    weekdays: ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"],

    "status.off": "Opsamling slået fra (mangler Jellyfin URL/API-nøgle)",
    "status.error": "Fejl: {msg}",
    "status.stalled": "Opsamlingen er gået i stå – sidste tjek af Jellyfin for {n} min. siden. Genstart add-on'et.",
    "status.ok": "Forbundet til Jellyfin – sidst tjekket {time}", "status.starting": "Starter…",
    "err.auth": "Jellyfin afviste API-nøglen – tjek api_key i add-on'ets konfiguration",
    "err.connect": "Kan ikke forbinde til Jellyfin – tjek jellyfin_url",
    "err.timeout": "Jellyfin svarer ikke (timeout)", "err.http": "Jellyfin svarede {detail}",

    "detail.empty": "Ingen lytninger i perioden", "detail.empty.hint": "Prøv en længere periode, fx \"Alt\".",
    "detail.rank.artist": "#{n} blandt dine kunstnere i perioden", "detail.rank.album": "#{n} blandt dine albums i perioden",
    "detail.rank.track": "#{n} blandt dine sange i perioden",
    "detail.by": "af {names}", "detail.from": "fra {album}", "detail.first": "Første gang hørt {date}",
    "detail.share": "{pct} % af al lytning", "kpi.tracks": "Sange", "kpi.tracks.albums": "fra {n} albums",
    "kpi.tracks_heard": "Sange hørt", "kpi.length": "Længde", "kpi.days_label": "Dage", "kpi.days_hint": "med mindst én lytning",
    "kpi.fav_day": "Yndlingsdag", "kpi.last": "Sidst hørt",
    "card.per_month": "Lytninger pr. måned", "card.hours": "Hvornår på døgnet?", "card.albums": "Albums",
    "list.artist": "Top sange", "list.album": "Sange på albummet", "list.track": "Ofte hørt lige efter",
    "list.track.hint": "inden for 10 min",

    "progress.title": "Fremdrift", "progress.hint": "uanset periode",
    "progress.hint.marks": " · tæller også numre markeret som hørt i Jellyfin",
    "progress.heard": "{heard} af {total} sange hørt", "progress.left": " · {hours} t tilbage",
    "progress.next": "Næste at opdage:", "progress.done": "Du har hørt alt i biblioteket 🎉",
    "tracks.title": "Sporliste", "tracks.disc": "Disk {n}", "tracks.plays": "{n} ×",
    "tracks.heard.title": "Hørt", "tracks.unheard.title": "Ikke hørt endnu",

    "discover.title": "Aldrig hørt",
    "discover.hint": "uanset periode · nyeste i biblioteket først",
    "discover.albums_never": "Albums aldrig hørt", "discover.of": "af {n}",
    "discover.artists_never": "Kunstnere aldrig hørt", "discover.hours": "Uhørt musik",
    "discover.library": "Biblioteket hørt", "discover.tracks_of": "{heard} af {total} sange",
    "discover.albums": "Albums, du aldrig har hørt", "discover.artists": "Kunstnere, du aldrig har hørt",
    "discover.added": "tilføjet {date}", "discover.tracks": "{n} sange", "discover.albums_n": "{n} albums",
    "discover.track_one": "1 sang", "discover.album_one": "1 album",
    "discover.none": "Du har hørt noget fra hvert eneste album 🎉",
    "discover.nojf": "Kræver forbindelse til Jellyfin.",

    "wr.empty": "Ingen lytninger i {year} endnu.",
    "wr.busiest": "Travleste dag", "wr.busiest.text": "{min} minutter og {n} sange på én dag.",
    "wr.session": "Længste session", "wr.session.text": "{n} sange i træk den {date}.",
    "wr.repeat": "På repeat", "wr.repeat.text": "{artist} – spillet {n} gange den {date}.",
    "wr.first": "Årets første sang", "wr.first.text": "{artist} – {date}.",
    "wr.new": "Nye opdagelser", "wr.new.one": "1 ny kunstner", "wr.new.many": "{n} nye kunstnere",
    "wr.new.text": "{pct} % af de sange, du hørte, var nye for dig.",
    "wr.genre": "Årets genre", "wr.genre.text": "Efterfulgt af {names}.",
    "wr.eyebrow": "Dit {year} i musik",
    "wr.lead": "minutter med musik. Det er {hours} timer, eller {days} døgn, fordelt på {plays} lytninger af {tracks} forskellige sange.",
    "wr.persona": "Din lyttertype", "wr.peak": "Dit yndlingstidspunkt", "wr.peak.value": "{day} kl. {hour}",
    "wr.peak.text": "Her er der størst chance for at finde dig med musik i ørerne.",
    "wr.star": "Årets kunstner", "wr.star.text": "{plays} lytninger og {hours} timer fordelt på {days} dage.",
    "wr.months": "Måned for måned", "wr.moods": "Årets humør",

    "cmp.match": "Musiksmag-match: {a} og {b}", "cmp.shared": "{n} fælles kunstnere",
    "cmp.empty": "Sammenligningen kræver mindst to brugere med lytninger i perioden.",
    "cmp.top_artist": "Top kunstner", "cmp.top_track": "Top sang", "cmp.top_genre": "Top genre", "cmp.mood": "Humør",
    "cmp.peak": "Lytter mest", "cmp.peak.value": "kl. {hour}", "cmp.chart": "Lyttetid over tid",
  },
  en: {
    title: "Music Stats",
    "nav.dashboard": "Overview", "nav.discover": "Never heard", "nav.wrapped": "Wrapped", "nav.compare": "Compare",
    "range.7": "7 days", "range.30": "30 days", "range.90": "90 days", "range.year": "This year", "range.all": "All",
    "users.all": "All users", "users.me": " (you)",
    "export.title": "Download the period's plays as CSV",
    "lang.switch": "DA", "lang.switch.title": "Skift til dansk",
    back: "← Back",
    nodata: "No data yet",
    hours: "h", minutes: "min", "unit.hours": "hours",
    other: "Other", "no.album": "No album", unknown: "Unknown",

    "kpi.plays": "Plays", "kpi.time": "Listening time", "kpi.artists": "Artists", "kpi.new_artists": "New artists",
    "kpi.skip": "Skip rate", "kpi.streak": "Streak", "kpi.session": "Avg. session",
    "kpi.vs_prev": "{pct} % vs. previous period", "kpi.new_tracks": "{pct} % new tracks",
    "kpi.days": "{n} days", "kpi.record": "record: {n} days", "kpi.sessions": "{n} sessions",

    "card.timeline": "Plays over time", "bucket.day": "Day", "bucket.week": "Week", "bucket.month": "Month",
    "series.plays": "Plays", "series.minutes": "Minutes", "series.hours": "Hours",
    "card.insights": "Insights", "insights.empty": "Insights show up once there's a bit more listening.",
    "card.top_artists": "Top artists", "card.top_albums": "Top albums", "card.top_tracks": "Top tracks",
    "card.genres": "Genres over time", "hint.share": "share of plays",
    "card.heatmap": "When do you listen?", "card.moods": "Music mood over time", "card.mood_hours": "Mood through the day",
    "mood.coverage": "{pct} % of plays have mood data",
    "card.recent": "Recent plays", "recent.empty": "No plays yet",
    "tag.backup": "found afterwards", "tag.backup.title": "The app didn't report this play live; found via Jellyfin's play count",
    "tag.skip": "skipped",
    "now.playing": "NOW PLAYING", "now.paused": "PAUSED",
    "heatmap.tip": "{day} at {hour}: {n} plays",
    days: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    weekdays: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],

    "status.off": "Collecting is off (Jellyfin URL/API key missing)",
    "status.error": "Error: {msg}",
    "status.stalled": "Collecting has stalled – Jellyfin was last checked {n} min ago. Restart the add-on.",
    "status.ok": "Connected to Jellyfin – last checked {time}", "status.starting": "Starting…",
    "err.auth": "Jellyfin rejected the API key – check api_key in the add-on's configuration",
    "err.connect": "Can't connect to Jellyfin – check jellyfin_url",
    "err.timeout": "Jellyfin isn't answering (timeout)", "err.http": "Jellyfin answered {detail}",

    "detail.empty": "No plays in this period", "detail.empty.hint": "Try a longer period, e.g. \"All\".",
    "detail.rank.artist": "#{n} of your artists in this period", "detail.rank.album": "#{n} of your albums in this period",
    "detail.rank.track": "#{n} of your tracks in this period",
    "detail.by": "by {names}", "detail.from": "from {album}", "detail.first": "First heard {date}",
    "detail.share": "{pct} % of all listening", "kpi.tracks": "Tracks", "kpi.tracks.albums": "from {n} albums",
    "kpi.tracks_heard": "Tracks heard", "kpi.length": "Length", "kpi.days_label": "Days", "kpi.days_hint": "with at least one play",
    "kpi.fav_day": "Favourite day", "kpi.last": "Last heard",
    "card.per_month": "Plays per month", "card.hours": "What time of day?", "card.albums": "Albums",
    "list.artist": "Top tracks", "list.album": "Tracks on the album", "list.track": "Often played next",
    "list.track.hint": "within 10 min",

    "progress.title": "Progress", "progress.hint": "any period",
    "progress.hint.marks": " · also counts tracks marked as played in Jellyfin",
    "progress.heard": "{heard} of {total} tracks heard", "progress.left": " · {hours} h left",
    "progress.next": "Next to discover:", "progress.done": "You've heard everything in the library 🎉",
    "tracks.title": "Track list", "tracks.disc": "Disc {n}", "tracks.plays": "{n} ×",
    "tracks.heard.title": "Heard", "tracks.unheard.title": "Not heard yet",

    "discover.title": "Never heard",
    "discover.hint": "any period · newest in the library first",
    "discover.albums_never": "Albums never heard", "discover.of": "of {n}",
    "discover.artists_never": "Artists never heard", "discover.hours": "Unheard music",
    "discover.library": "Library heard", "discover.tracks_of": "{heard} of {total} tracks",
    "discover.albums": "Albums you've never heard", "discover.artists": "Artists you've never heard",
    "discover.added": "added {date}", "discover.tracks": "{n} tracks", "discover.albums_n": "{n} albums",
    "discover.track_one": "1 track", "discover.album_one": "1 album",
    "discover.none": "You've heard something from every single album 🎉",
    "discover.nojf": "Needs a connection to Jellyfin.",

    "wr.empty": "No plays in {year} yet.",
    "wr.busiest": "Busiest day", "wr.busiest.text": "{min} minutes and {n} tracks in one day.",
    "wr.session": "Longest session", "wr.session.text": "{n} tracks in a row on {date}.",
    "wr.repeat": "On repeat", "wr.repeat.text": "{artist} – played {n} times on {date}.",
    "wr.first": "First track of the year", "wr.first.text": "{artist} – {date}.",
    "wr.new": "New discoveries", "wr.new.one": "1 new artist", "wr.new.many": "{n} new artists",
    "wr.new.text": "{pct} % of the tracks you heard were new to you.",
    "wr.genre": "Genre of the year", "wr.genre.text": "Followed by {names}.",
    "wr.eyebrow": "Your {year} in music",
    "wr.lead": "minutes of music. That's {hours} hours, or {days} days, over {plays} plays of {tracks} different tracks.",
    "wr.persona": "Your listener type", "wr.peak": "Your favourite time", "wr.peak.value": "{day} at {hour}",
    "wr.peak.text": "This is when you're most likely to have music in your ears.",
    "wr.star": "Artist of the year", "wr.star.text": "{plays} plays and {hours} hours over {days} days.",
    "wr.months": "Month by month", "wr.moods": "Mood of the year",

    "cmp.match": "Music taste match: {a} and {b}", "cmp.shared": "{n} shared artists",
    "cmp.empty": "The comparison needs at least two users with plays in the period.",
    "cmp.top_artist": "Top artist", "cmp.top_track": "Top track", "cmp.top_genre": "Top genre", "cmp.mood": "Mood",
    "cmp.peak": "Listens most", "cmp.peak.value": "at {hour}", "cmp.chart": "Listening time over time",
  },
};

function t(key, vars = {}) {
  const s = STRINGS[LANG][key] ?? STRINGS.da[key] ?? key;
  return typeof s === "string" ? s.replace(/\{(\w+)\}/g, (_, k) => (vars[k] ?? "")) : s;
}

function applyI18n() {
  document.documentElement.lang = LANG;
  document.title = t("title");
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => { el.title = t(el.dataset.i18nTitle); });
}

function switchLanguage() {
  try { localStorage.setItem("lang", LANG === "da" ? "en" : "da"); } catch { /* nothing to remember it in */ }
  location.reload();
}
