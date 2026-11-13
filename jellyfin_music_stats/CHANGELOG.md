# Changelog

🇬🇧 English first, 🇩🇰 dansk nedenunder i hver version.

## 0.7.0

🇬🇧
- Genres spelled differently are merged: spellings that only differ in case, spaces, hyphens, slashes or underscores (e.g. "Singer/Songwriter" and "Singer-Songwriter") automatically become one genre, under the spelling your library uses most
- New option `genre_map` to merge other genres, e.g. `Alternative=Alternativ`
- The log suggests genres that look alike when the add-on starts
- Jellyfin's original genres are kept, and a changed `genre_map` is applied to all existing statistics on the next start

🇩🇰
- Genrer, der er stavet forskelligt, slås sammen: navne, der kun adskiller sig ved store og små bogstaver, mellemrum, bindestreger, skråstreger eller understreger (fx "Singer/Songwriter" og "Singer-Songwriter"), bliver automatisk til én genre under den stavemåde, dit bibliotek bruger mest
- Ny indstilling `genre_map` til at slå andre genrer sammen, fx `Alternative=Alternativ`
- Loggen foreslår genrer, der ligner hinanden, når add-on'et starter
- Jellyfins oprindelige genrer bliver gemt, og en ændret `genre_map` bliver brugt på al eksisterende statistik ved næste start

## 0.6.1

🇬🇧
- Album covers are stored locally next to the database, so they still show if an album is deleted from Jellyfin. They are included in backups too.
- Logo and icon in the add-on store
- Tests, a check of the add-on configuration and an image build for amd64 and aarch64 now run automatically on GitHub on every push

🇩🇰
- Albumcovers gemmes lokalt ved siden af databasen, så de stadig vises, hvis et album slettes fra Jellyfin. De kommer også med i backups.
- Logo og ikon i add-on-butikken
- Tests, tjek af add-on-konfigurationen og byg af imaget for amd64 og aarch64 kører nu automatisk på GitHub ved hvert push

## 0.6.0

🇬🇧
- Backup collector: catches plays from apps that don't report "now playing" (such as Jellyfin Media Player), using Jellyfin's play counts
- Such plays are shown with the label "fundet bagefter" (found afterwards) under recent plays
- No double counting when a play was already seen live

🇩🇰
- Backup-opsamler: fanger lytninger fra apps, der ikke rapporterer "spiller nu" (fx Jellyfin Media Player), via Jellyfins afspilningstal
- Sådanne lytninger vises med mærket "fundet bagefter" under Seneste afspilninger
- Der opstår ingen dobbelttællinger, når en afspilning allerede er set live

## 0.5.2

🇬🇧
- The log now shows what Jellyfin reports (app, device, user and what is playing) whenever it changes, and every saved play
- The status dot turns red if collecting has stalled, instead of staying green

🇩🇰
- Loggen viser nu, hvad Jellyfin rapporterer (app, enhed, bruger og hvad der spilles), hver gang det ændrer sig, og hver gemt afspilning
- Statusprikken bliver rød, hvis opsamlingen er gået i stå, i stedet for at forblive grøn

## 0.5.1

🇬🇧
- "Genres over time" and "Music mood over time" were empty when all data fell into one or two periods; they are now shown as stacked bars until there is enough data for a curve
- Spaces before and after genre names are removed (e.g. " Stage & Screen")

🇩🇰
- "Genrer over tid" og "Musikhumør over tid" var tomme, når al data lå i én eller to perioder; de vises nu som stablede søjler, indtil der er nok data til en kurve
- Mellemrum før og efter genrenavne fjernes (fx " Stage & Screen")

## 0.5.0

🇬🇧
- Each user automatically sees their own stats: the Home Assistant user is matched with the Jellyfin user of the same name
- New option `user_map` to link users whose names differ, e.g. `christian=Tntdruid`
- The user menu shows "(dig)" (you) next to your own user
- The options now have Danish and English descriptions in Home Assistant

🇩🇰
- Hver bruger ser automatisk sin egen statistik: HA-brugeren matches med Jellyfin-brugeren med samme navn
- Ny indstilling `user_map` til at koble brugere, hvis navnene er forskellige, fx `christian=Tntdruid`
- Brugermenuen viser "(dig)" ved din egen bruger
- Indstillingerne har nu danske og engelske beskrivelser i Home Assistant

## 0.4.0

🇬🇧
- The database now lives in the add-on's public config folder (`app_configs/…_jellyfin_music_stats/music_stats.db`), so you can see and copy it over Samba
- An existing database is moved there automatically the first time, so your history is kept
- The default Jellyfin URL is now the Jellyfin add-on's internal hostname

🇩🇰
- Databasen ligger nu i add-on'ets offentlige config-mappe (`app_configs/…_jellyfin_music_stats/music_stats.db`), så du kan se og kopiere den via Samba
- En eksisterende database flyttes automatisk første gang, så din historik bliver bevaret
- Standard-URL'en til Jellyfin er nu Jellyfin-add-on'ets interne værtsnavn

## 0.3.1

🇬🇧
- The page updates itself when a new play has been saved; reloading is no longer needed
- The update happens in the background, without jumping to the top or replaying the chart animations

🇩🇰
- Siden opdaterer sig selv, når en ny afspilning er gemt; det er ikke længere nødvendigt at genindlæse
- Opdateringen sker i baggrunden uden at hoppe til toppen eller afspille grafernes animationer igen

## 0.3.0

🇬🇧
- Albums and tracks now have their own pages, like artists
- Track pages show "often played next": the tracks you usually play after it
- Links from top lists, recent plays and Wrapped, and between artist, album and track pages
- "Back" goes to the previous page instead of always to the overview

🇩🇰
- Albums og sange har nu deres egne sider, ligesom kunstnere
- Sangsider viser "Ofte hørt lige efter": de numre du typisk spiller efter sangen
- Links fra top-lister, seneste afspilninger, Wrapped og mellem kunstner-, album- og sangsider
- "Tilbage" går til den forrige side i stedet for altid til oversigten

## 0.2.0

🇬🇧
- Artist pages: click an artist to see their history, top tracks, albums, genres, moods and when in the day you listen to them
- Wrapped: a yearly summary with listener type, artist of the year, top 5 lists and fun facts
- Compare: stats per user and a music taste match with shared artists
- CSV export of plays

🇩🇰
- Kunstnersider: klik på en kunstner for at se historik, top-sange, albums, genrer, humør og hvornår på døgnet du hører dem
- Wrapped: årsoversigt med lyttertype, årets kunstner, top 5-lister og sjove fakta
- Sammenlign: statistik pr. bruger og musiksmag-match med fælles kunstnere
- Eksport af afspilninger til CSV

## 0.1.3

🇬🇧
- Album cover shown under "now playing"

🇩🇰
- Albumcover vises under "Spiller nu"

## 0.1.2

🇬🇧
- The log no longer writes a line for every check of Jellyfin

🇩🇰
- Loggen skriver ikke længere en linje for hvert tjek af Jellyfin

## 0.1.1

🇬🇧
- The API key is sent with Jellyfin's standard header (fixes 401 errors)
- Spaces around API keys are removed automatically
- Connection errors are shown with a clear Danish explanation

🇩🇰
- API-nøglen sendes med Jellyfins standard-header (retter 401-fejl)
- Mellemrum omkring API-nøgler fjernes automatisk
- Forbindelsesfejl vises med en forståelig dansk forklaring

## 0.1.0

🇬🇧
- First version: collects plays from Jellyfin, dashboard with top lists, genres, moods, heatmap and insights

🇩🇰
- Første version: opsamling af afspilninger fra Jellyfin, dashboard med top-lister, genrer, humør, heatmap og indsigter
