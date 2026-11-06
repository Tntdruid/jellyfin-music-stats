# Jellyfin Music Stats

Home Assistant-add-on med lyttestatistik for musik i Jellyfin. Det er tænkt som en musikudgave af Jellystat.

- Lytninger og lyttetid pr. dag, uge og måned, sammenlignet med forrige periode
- Top kunstnere, albums og sange med covers
- Genrer og musikhumør over tid samt humør i løbet af døgnet
- Heatmap over, hvornår du lytter
- Smartere tal: skip-rate, lyttesessioner, streaks, nye kunstnere, gentagelser og automatiske indsigter
- Live "spiller nu"
- Kunstnersider med historik, top-sange, albums og tidspunkter på døgnet
- Wrapped: årsoversigt med lyttertype, årets kunstner, top 5-lister og sjove fakta
- Sammenligning af brugere med musiksmag-match og fælles kunstnere
- Eksport af afspilninger til CSV (åbner direkte i dansk Excel)
- Understøtter flere brugere

Se [jellyfin_music_stats/DOCS.md](jellyfin_music_stats/DOCS.md) for opsætning.

## Installation i Home Assistant

1. Gå til **Indstillinger → Apps → Apps butik → ⋮ → Repositories**.
2. Tilføj `https://github.com/Tntdruid/jellyfin-music-stats`.
3. Find **Jellyfin Music Stats** i butikken og installér det.

Home Assistant bygger add-on'et på din maskine, så den første installation tager et par minutter.

**Opdateringer:** Hæv `version` i `jellyfin_music_stats/config.yaml` og push. Home Assistant viser så opdateringen i butikken.

## Lokal udvikling med demodata

```bash
python -m venv .venv
.venv/Scripts/pip install -r jellyfin_music_stats/app/requirements.txt
curl -L -o jellyfin_music_stats/app/static/echarts.min.js https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js
.venv/Scripts/python dev/seed_demo.py
cd jellyfin_music_stats/app && DATA_DIR=../../dev/data ../../.venv/Scripts/python -m uvicorn main:app --port 8099
```

Hvis du sætter `JELLYFIN_URL` og `API_KEY` som miljøvariabler, opsamler den lokale udgave også rigtige data.
