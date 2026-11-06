# Changelog

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
