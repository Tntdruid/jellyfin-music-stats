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
| `genre_map` | Valgfri. Slår genrer med forskellige navne sammen. Én linje pr. genre, fx `Alternative=Alternativ`. Se [Genrer](#genrer). |
| `smart_playlists` | Laver og opdaterer playlister i Jellyfin for hver bruger. Slået fra som standard. Se [Smarte playlister](#smarte-playlister). |
| `playlist_language` | Sproget for playlisternes navne: `da` eller `en`. |

## Sprog

Siderne vises på dansk eller engelsk efter browserens sprog. Knappen **EN**/**DA** øverst skifter sprog, og valget huskes i den browser.

## Fremdrift på kunstnersider

På en kunstners side viser kortet **Fremdrift**, hvor mange af kunstnerens numre i dit Jellyfin-bibliotek du har hørt, med en bjælke pr. album og det næste nummer, du kan opdage. Et nummer tæller som hørt, hvis add-on'et har en lytning af det, eller hvis Jellyfin har det markeret som spillet for dig. Med "Alle brugere" valgt tæller alles lytninger, men ikke Jellyfins markeringer, da de hører til én bruger. Kortet viser altid status nu, uanset den valgte periode.

På en albumside viser **Sporliste** alle albummets numre med ✓ for hørt og antal lytninger.

## Aldrig hørt

Fanen **Aldrig hørt** viser, hvor stor en del af biblioteket du har hørt, og hvilke albums og kunstnere du aldrig har spillet. De nyeste i biblioteket står først. Fanen kræver forbindelse til Jellyfin.

## Smarte playlister

Med `smart_playlists` slået til får hver Jellyfin-bruger disse playlister, som opdateres hver 6. time:

- **🎧 Top 50 – seneste 30 dage**
- **🎧 Glemte favoritter:** numre, du har hørt mindst 4 gange, men ikke i 90 dage
- **🎧 Næste at opdage:** uhørte numre fra de kunstnere, du har hørt mest de seneste 90 dage, startende med de albums, du er længst med
- **🎧 Morgen-mix** (kl. 5–11) og **🎧 Aften-mix** (kl. 18–24): det, du typisk hører på de tidspunkter
- **🎧 Humør: …** for hvert humør, du har lyttet til

Playlisterne er private for brugeren og kan bruges i alle Jellyfin-apps. Add-on'et ændrer kun de playlister, det selv har lavet. En playliste med færre end 5 numre bliver fjernet, indtil der er data nok. Sletter du en i Jellyfin, bliver den lavet igen ved næste opdatering. Slår du indstillingen fra, bliver playlisterne liggende, og du kan slette dem i Jellyfin.

## Genrer

Genrer kommer fra taggene i dine musikfiler, og de er ofte stavet forskelligt. Add-on'et rydder op i to trin:

1. **Automatisk:** Navne, der kun adskiller sig ved store og små bogstaver, mellemrum, bindestreger, skråstreger eller understreger, fx "Hip-Hop", "Hip Hop" og "hip hop" eller "Singer/Songwriter" og "Singer-Songwriter", bliver til én genre. Den stavemåde, der bruges mest i dit bibliotek, vinder.
2. **Med `genre_map`:** Andre navne kobler du selv. Den del, der står før `=`, er den genre, der skal forsvinde, og den del, der står efter, er den, den skal tælle som. Fx `Alternative=Alternativ`.

Når add-on'et starter, skriver det **forslag** i loggen, hvis nogle genrer ligner hinanden, fx:

```
mulig dublet: 'Alternative' og 'Alternativ' – tilføj fx 'Alternative=Alternativ' under genre_map
```

Taggene i dine filer bliver ikke ændret, og den oprindelige genre fra Jellyfin bliver gemt. Hvis du ændrer `genre_map`, bliver al eksisterende statistik omregnet ved næste start.

## Flere brugere

Når du åbner Musikstatistik, viser siden automatisk **din egen** statistik. Det sker, hvis dit brugernavn eller visningsnavn i Home Assistant er det samme som dit brugernavn i Jellyfin (store og små bogstaver er ligegyldige). I brugermenuen står der "(dig)" ved dig, og du kan altid skifte til "Alle brugere", en anden bruger eller fanen Sammenlign.

Hvis navnene er forskellige, kobler du dem under `user_map`. Den del, der står før `=`, er HA-brugernavnet, og den del, der står efter, er Jellyfin-brugernavnet.

En Jellyfin-bruger kommer først med i statistikken efter sin første afspilning.

## Humør

Hvert nummer får op til tre humørkategorier: energisk, glad, rolig, melankolsk, mørk, romantisk, aggressiv eller festlig. Kilderne bruges i denne rækkefølge:

1. Tags på nummeret i Jellyfin, fx mood-tags skrevet med MusicBrainz Picard
2. Last.fm-tags for nummeret, og derefter for kunstneren (kræver `lastfm_api_key`)
3. Et groft gæt ud fra genren

## Apps der ikke rapporterer afspilning

Lytninger bliver normalt registreret live via Jellyfins "spiller nu". Nogle apps, fx Jellyfin Media Player, sender ikke altid den besked. De giver dog stadig Jellyfin besked, når et nummer er hørt færdigt.

Add-on'et har derfor en **backup-opsamler**, som hvert halvandet minut tjekker, om Jellyfins afspilningstal er steget for nogle numre. Lytninger, der ikke blev set live, gemmes alligevel og markeres som **"fundet bagefter"** under Seneste afspilninger. Den kan ikke se, hvor meget af et nummer du hørte, så de tæller altid som hele lytninger. Skips fra sådanne apps kommer ikke med.

Første gang backup-opsamleren ser en bruger, noterer den bare de nuværende tal, så gammel historik ikke bliver lagt ind som nye lytninger.

## Bemærk

- Jellyfin gemmer ikke selv en lyttehistorik, så statistikken starter først, når add-on'et kører.
- Data gemmes i SQLite-filen `music_stats.db` i add-on'ets offentlige config-mappe. Via Samba ligger den under `app_configs/<id>_jellyfin_music_stats/` (`addon_configs` på ældre Home Assistant), så du kan kopiere den eller åbne den i fx DB Browser for SQLite. Filen kommer med i Home Assistants backups.
- Opdaterer du fra en version før 0.4.0, flyttes din eksisterende database automatisk dertil første gang add-on'et starter.
