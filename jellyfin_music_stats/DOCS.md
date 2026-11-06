# Jellyfin Music Stats

Add-on'et følger med i, hvad der bliver spillet på din Jellyfin-server, og viser statistik over din musiklytning.

## Opsætning

1. Opret en API-nøgle i Jellyfin under **Kontrolpanel → API-nøgler → +**.
2. Sæt `jellyfin_url` og `api_key` under add-on'ets **Konfiguration** og start add-on'et.
3. Åbn **Musikstatistik** i sidemenuen.

Prikken ved titlen viser forbindelsen: grøn betyder forbundet, rød betyder fejl (hold musen over den for at se detaljer), og grå betyder, at opsamlingen ikke er sat op.

### Jellyfin URL

Jellyfin-add-on'et kører på samme maskine, så det er nok at bruge Home Assistants IP-adresse med port 8096, fx `http://192.168.1.10:8096`. Du kan også bruge add-on'ets interne værtsnavn, som står på Jellyfin-add-on'ets infoside under *Hostname*, fx `http://2937404c-jellyfin:8096` for det officielle Jellyfin-add-on.

## Indstillinger

| Indstilling | Betydning |
|---|---|
| `poll_interval` | Antal sekunder mellem hvert tjek af, hvad der spilles (3–60). |
| `min_play_percent` | Hvor stor en del af et nummer der skal høres, før det tæller som en lytning. Fire minutter tæller altid, som hos Last.fm. Kortere afspilninger registreres som skips. |
| `lastfm_api_key` | Valgfri. Henter humør-tags fra Last.fm for numre, der ikke har nogen. Du kan få en gratis nøgle på https://www.last.fm/api/account/create |
| `user_map` | Valgfri. Kobler Home Assistant-brugere til Jellyfin-brugere, når navnene er forskellige. Én linje pr. bruger, fx `christian=Tntdruid`. |

## Flere brugere

Når du åbner Musikstatistik, viser siden automatisk **din egen** statistik. Det sker, hvis dit brugernavn eller visningsnavn i Home Assistant er det samme som dit brugernavn i Jellyfin (store og små bogstaver er ligegyldige). I brugermenuen står der "(dig)" ved dig, og du kan altid skifte til "Alle brugere", en anden bruger eller fanen Sammenlign.

Hvis navnene er forskellige, kobler du dem under `user_map`. Den del, der står før `=`, er HA-brugernavnet, og den del, der står efter, er Jellyfin-brugernavnet.

En Jellyfin-bruger kommer først med i statistikken efter sin første afspilning.

## Humør

Hvert nummer får op til tre humørkategorier: energisk, glad, rolig, melankolsk, mørk, romantisk, aggressiv eller festlig. Kilderne bruges i denne rækkefølge:

1. Tags på nummeret i Jellyfin, fx mood-tags skrevet med MusicBrainz Picard
2. Last.fm-tags for nummeret, og derefter for kunstneren (kræver `lastfm_api_key`)
3. Et groft gæt ud fra genren

## Bemærk

- Jellyfin gemmer ikke selv en lyttehistorik, så statistikken starter først, når add-on'et kører.
- Data gemmes i SQLite-filen `music_stats.db` i add-on'ets offentlige config-mappe. Via Samba ligger den under `app_configs/<id>_jellyfin_music_stats/` (`addon_configs` på ældre Home Assistant), så du kan kopiere den eller åbne den i fx DB Browser for SQLite. Filen kommer med i Home Assistants backups.
- Opdaterer du fra en version før 0.4.0, flyttes din eksisterende database automatisk dertil første gang add-on'et starter.
