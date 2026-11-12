<p align="center"><img src="assets/logo.png" width="160" alt="Jellyfin Music Stats logo"></p>

<h1 align="center">Jellyfin Music Stats</h1>

<p align="center"><a href="https://github.com/Tntdruid/jellyfin-music-stats/actions/workflows/ci.yaml"><img src="https://github.com/Tntdruid/jellyfin-music-stats/actions/workflows/ci.yaml/badge.svg" alt="CI"></a></p>

🇬🇧 [English](#english) · 🇩🇰 [Dansk](#dansk)

---

## English

A Home Assistant add-on with listening statistics for music in Jellyfin, a music take on Jellystat. It is the music sibling of [Jellyfin Video Stats](https://github.com/Tntdruid/jellyfin-video-stats). The add-on's own pages are in Danish.

- Listens and listening time per day, week and month, compared with the previous period
- Top artists, albums and tracks with covers, which are stored locally and survive the album being deleted
- Genres and moods over time, and mood by time of day
- A heatmap of when you listen
- Smarter numbers: skip rate, listening sessions, streaks, new artists, tracks on repeat and automatic insights
- Live "now playing", plus a backup collector that catches plays from apps that don't report it (such as Jellyfin Media Player)
- Pages for artists, albums and tracks, with "often played next" on track pages
- Wrapped: a yearly summary with listener type, artist of the year, top 5 lists and fun facts
- User comparison with a taste match and shared artists
- Each Home Assistant user sees their own stats by default
- CSV export of plays (opens directly in Danish Excel)

See [jellyfin_music_stats/DOCS.md](jellyfin_music_stats/DOCS.md) for setup (in Danish).

### Installation in Home Assistant

1. Go to **Settings → Apps → App store → ⋮ → Repositories**.
2. Add `https://github.com/Tntdruid/jellyfin-music-stats`.
3. Find **Jellyfin Music Stats** in the store and install it.
4. Under **Configuration**, set `jellyfin_url` and `api_key` (create the key in Jellyfin under **Dashboard → API Keys**), then start the add-on.
5. Open **Musikstatistik** in the sidebar.

Home Assistant builds the add-on on your machine, so the first installation takes a few minutes.

**Updates:** raise `version` in `jellyfin_music_stats/config.yaml` and push. Home Assistant then shows the update in the store.

### Local development with demo data

```bash
python -m venv .venv
.venv/Scripts/pip install -r jellyfin_music_stats/app/requirements.txt
curl -L -o jellyfin_music_stats/app/static/echarts.min.js https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js
.venv/Scripts/python dev/seed_demo.py
.venv/Scripts/python dev/run_demo.py
```

Then open http://localhost:8099. If you set `JELLYFIN_URL` and `API_KEY` as environment variables, the local copy also collects real data.

Run the tests with:

```bash
.venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest tests
```

On every push, GitHub Actions runs the tests and checks the add-on configuration. The image is built and started for both amd64 and aarch64, so a broken version is caught before Home Assistant tries to install it.

---

## Dansk

Home Assistant-add-on med lyttestatistik for musik i Jellyfin, en musikudgave af Jellystat. Det er musik-søsteren til [Jellyfin Video Stats](https://github.com/Tntdruid/jellyfin-video-stats).

- Lytninger og lyttetid pr. dag, uge og måned, sammenlignet med forrige periode
- Top kunstnere, albums og sange med covers, der gemmes lokalt og overlever, at albummet slettes
- Genrer og musikhumør over tid samt humør i løbet af døgnet
- Heatmap over, hvornår du lytter
- Smartere tal: skip-rate, lyttesessioner, streaks, nye kunstnere, gentagelser og automatiske indsigter
- Live "spiller nu" plus en backup-opsamler, der fanger lytninger fra apps, som ikke rapporterer det (fx Jellyfin Media Player)
- Sider for kunstnere, albums og sange med "Ofte hørt lige efter" på sangsiderne
- Wrapped: årsoversigt med lyttertype, årets kunstner, top 5-lister og sjove fakta
- Sammenligning af brugere med musiksmag-match og fælles kunstnere
- Hver Home Assistant-bruger ser automatisk sin egen statistik
- Eksport af afspilninger til CSV (åbner direkte i dansk Excel)

Se [jellyfin_music_stats/DOCS.md](jellyfin_music_stats/DOCS.md) for opsætning.

### Installation i Home Assistant

1. Gå til **Indstillinger → Apps → Apps butik → ⋮ → Repositories**.
2. Tilføj `https://github.com/Tntdruid/jellyfin-music-stats`.
3. Find **Jellyfin Music Stats** i butikken og installér det.
4. Sæt `jellyfin_url` og `api_key` under **Konfiguration** (opret nøglen i Jellyfin under **Kontrolpanel → API-nøgler**), og start add-on'et.
5. Åbn **Musikstatistik** i sidemenuen.

Home Assistant bygger add-on'et på din maskine, så den første installation tager et par minutter.

**Opdateringer:** Hæv `version` i `jellyfin_music_stats/config.yaml` og push. Home Assistant viser så opdateringen i butikken.

### Lokal udvikling med demodata

```bash
python -m venv .venv
.venv/Scripts/pip install -r jellyfin_music_stats/app/requirements.txt
curl -L -o jellyfin_music_stats/app/static/echarts.min.js https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js
.venv/Scripts/python dev/seed_demo.py
.venv/Scripts/python dev/run_demo.py
```

Åbn derefter http://localhost:8099. Hvis du sætter `JELLYFIN_URL` og `API_KEY` som miljøvariabler, opsamler den lokale udgave også rigtige data.

Tests køres med:

```bash
.venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest tests
```

Ved hvert push kører GitHub Actions tests og tjekker add-on-konfigurationen. Imaget bygges og startes for både amd64 og aarch64, så en version, der ikke virker, bliver opdaget, før Home Assistant prøver at installere den.

---

<!-- jellyfin-projects:start -->
## More Jellyfin projects / Flere Jellyfin-projekter

| | 🇬🇧 | 🇩🇰 |
|---|---|---|
| [Jellyfin Video Stats](https://github.com/Tntdruid/jellyfin-video-stats) | Home Assistant add-on with viewing stats for movies, series and YouTube videos: progress, binges, transcoding, Wrapped | Home Assistant-add-on med seerstatistik for film, serier og YouTube-videoer: fremdrift, binge, transcoding, Wrapped |
| [Episode Title Fixer](https://github.com/Tntdruid/jellyfin-plugin-episode-title-fixer) | Jellyfin plugin that replaces placeholder episode titles like "Episode 11" with the original title | Jellyfin-plugin, der erstatter pladsholdere som "Afsnit 11" med afsnittets originale titel |
| [Auto Artist Playlists](https://github.com/Tntdruid/jellyfin-plugin-auto-artist-playlists) | Jellyfin plugin that hearts the songs you listen to and adds them to a playlist per artist | Jellyfin-plugin, der giver hjerte til de sange, du hører, og samler dem i en playliste pr. kunstner |
<!-- jellyfin-projects:end -->
