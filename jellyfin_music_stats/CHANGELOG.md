# Changelog

## 0.6.0

- Backup-opsamler: fanger lytninger fra apps, der ikke rapporterer "spiller nu" (fx Jellyfin Media Player), via Jellyfins afspilningstal
- Sådanne lytninger vises med mærket "fundet bagefter" under Seneste afspilninger
- Der opstår ingen dobbelttællinger, når en afspilning allerede er set live

## 0.5.2

- Loggen viser nu, hvad Jellyfin rapporterer (app, enhed, bruger og hvad der spilles), hver gang det ændrer sig, og hver gemt afspilning
- Statusprikken bliver rød, hvis opsamlingen er gået i stå, i stedet for at forblive grøn

## 0.5.1

- "Genrer over tid" og "Musikhumør over tid" var tomme, når al data lå i én eller to perioder; de vises nu som stablede søjler, indtil der er nok data til en kurve
- Mellemrum før og efter genrenavne fjernes (fx " Stage & Screen")

## 0.5.0

- Hver bruger ser automatisk sin egen statistik: HA-brugeren matches med Jellyfin-brugeren med samme navn
- Ny indstilling `user_map` til at koble brugere, hvis navnene er forskellige, fx `christian=Tntdruid`
- Brugermenuen viser "(dig)" ved din egen bruger
- Indstillingerne har nu danske og engelske beskrivelser i Home Assistant

## 0.4.0

- Databasen ligger nu i add-on'ets offentlige config-mappe (`addon_configs/…_jellyfin_music_stats/music_stats.db`), så du kan se og kopiere den via Samba
- En eksisterende database flyttes automatisk første gang, så din historik bliver bevaret
- Standard-URL'en til Jellyfin er nu Jellyfin-add-on'ets interne værtsnavn

## 0.3.1

- Siden opdaterer sig selv, når en ny afspilning er gemt; det er ikke længere nødvendigt at genindlæse
- Opdateringen sker i baggrunden uden at hoppe til toppen eller afspille grafernes animationer igen

## 0.3.0

- Albums og sange har nu deres egne sider, ligesom kunstnere
- Sangsider viser "Ofte hørt lige efter": de numre du typisk spiller efter sangen
- Links fra top-lister, seneste afspilninger, Wrapped og mellem kunstner-, album- og sangsider
- "Tilbage" går til den forrige side i stedet for altid til oversigten

## 0.2.0

- Kunstnersider: klik på en kunstner for at se historik, top-sange, albums, genrer, humør og hvornår på døgnet du hører dem
- Wrapped: årsoversigt med lyttertype, årets kunstner, top 5-lister og sjove fakta
- Sammenlign: statistik pr. bruger og musiksmag-match med fælles kunstnere
- Eksport af afspilninger til CSV

## 0.1.3

- Albumcover vises under "Spiller nu"

## 0.1.2

- Loggen skriver ikke længere en linje for hvert tjek af Jellyfin

## 0.1.1

- API-nøglen sendes med Jellyfins standard-header (retter 401-fejl)
- Mellemrum omkring API-nøgler fjernes automatisk
- Forbindelsesfejl vises med en forståelig dansk forklaring

## 0.1.0

- Første version: opsamling af afspilninger fra Jellyfin, dashboard med top-lister, genrer, humør, heatmap og indsigter
