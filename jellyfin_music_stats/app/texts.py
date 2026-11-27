"""Texts the server writes itself (insights, listener types, mood names, CSV), in Danish and English.

The page's own texts live in static/i18n.js; these are the ones that are built from the data.
"""
from typing import Dict

LANGS = ("da", "en")

MOODS: Dict[str, Dict[str, str]] = {
    "da": {"energetic": "energisk", "happy": "glad", "chill": "rolig", "melancholic": "melankolsk",
           "dark": "mørk", "romantic": "romantisk", "aggressive": "aggressiv", "party": "festlig"},
    "en": {"energetic": "energetic", "happy": "happy", "chill": "chill", "melancholic": "melancholic",
           "dark": "dark", "romantic": "romantic", "aggressive": "aggressive", "party": "party"},
}

TEXTS: Dict[str, Dict[str, str]] = {
    "da": {
        "insight.peak": "Du lytter mest om {day}en omkring kl. {hour}.",
        "insight.loyal": "{artist} er din mest spillede kunstner: {plays} lytninger fordelt på {days} dage.",
        "insight.new": "Nyopdaget: {artist}. Første lytning var {date}, og du har hørt dem {n} gange siden.",
        "insight.rediscovered": "Genfundet: {artist} efter {days} dages pause.",
        "insight.repeat": "På repeat: \"{track}\" blev spillet {n} gange den {date}.",
        "insight.skip": "Du springer oftest {artist} over ({pct} % af afspilningerne).",
        "insight.weekend": "I weekenden hører du mere {mood} musik ({pct} procentpoint mere).",
        "insight.weekdays": "I hverdagene hører du mere {mood} musik ({pct} procentpoint mere).",
        "insight.night": "Natteravn: {pct} % af din lytning sker mellem kl. 23 og 04.",
        "persona.night.title": "Natteravnen", "persona.night.text": "Dine bedste lytte-timer ligger, når andre sover.",
        "persona.morning.title": "Morgenfuglen", "persona.morning.text": "Du starter dagen med musik i ørerne.",
        "persona.explorer.title": "Opdageren", "persona.explorer.text": "{pct} % af det, du hørte, var nyt for dig.",
        "persona.fan.title": "Den trofaste fan", "persona.fan.text": "Din favoritkunstner stod for {pct} % af alt, du hørte.",
        "persona.party.title": "Festaben", "persona.party.text": "Når du trykker play, skal der danses.",
        "persona.chill.title": "Zen-mesteren", "persona.chill.text": "Rolig musik er dit soundtrack.",
        "persona.moody.title": "Den eftertænksomme", "persona.moody.text": "Du har ikke noget imod lidt tungsind.",
        "persona.energy.title": "Energibomben", "persona.energy.text": "Højt tempo og fuld skrue.",
        "persona.omnivore.title": "Altæderen", "persona.omnivore.text": "{n} forskellige kunstnere – du hører lidt af det hele.",
        "persona.default.title": "Musikelskeren", "persona.default.text": "Musik er en fast del af din hverdag.",
        "csv.header": "tidspunkt;bruger;titel;kunstnere;album;albumkunstner;år;genrer;humør;lyttet_sek;længde_sek;"
                      "talt_som_lytning;klient;enhed;kilde",
        "csv.yes": "ja", "csv.no": "nej",
    },
    "en": {
        "insight.peak": "You listen most on {day}s around {hour}:00.",
        "insight.loyal": "{artist} is your most played artist: {plays} plays over {days} days.",
        "insight.new": "New find: {artist}. First heard on {date}, and you've played them {n} times since.",
        "insight.rediscovered": "Rediscovered: {artist} after a {days} day break.",
        "insight.repeat": "On repeat: \"{track}\" was played {n} times on {date}.",
        "insight.skip": "You skip {artist} the most ({pct} % of plays).",
        "insight.weekend": "At weekends you listen to more {mood} music ({pct} percentage points more).",
        "insight.weekdays": "On weekdays you listen to more {mood} music ({pct} percentage points more).",
        "insight.night": "Night owl: {pct} % of your listening happens between 23:00 and 04:00.",
        "persona.night.title": "The Night Owl", "persona.night.text": "Your best listening hours are while others sleep.",
        "persona.morning.title": "The Early Bird", "persona.morning.text": "You start the day with music in your ears.",
        "persona.explorer.title": "The Explorer", "persona.explorer.text": "{pct} % of what you heard was new to you.",
        "persona.fan.title": "The Loyal Fan", "persona.fan.text": "Your favourite artist made up {pct} % of everything you heard.",
        "persona.party.title": "The Party Animal", "persona.party.text": "When you press play, it's time to dance.",
        "persona.chill.title": "The Zen Master", "persona.chill.text": "Calm music is your soundtrack.",
        "persona.moody.title": "The Thoughtful One", "persona.moody.text": "You don't mind a little melancholy.",
        "persona.energy.title": "The Powerhouse", "persona.energy.text": "High tempo, full volume.",
        "persona.omnivore.title": "The Omnivore", "persona.omnivore.text": "{n} different artists – you listen to a bit of everything.",
        "persona.default.title": "The Music Lover", "persona.default.text": "Music is part of your everyday life.",
        "csv.header": "time;user;title;artists;album;album_artist;year;genres;mood;listened_sec;length_sec;"
                      "counted_as_listen;client;device;source",
        "csv.yes": "yes", "csv.no": "no",
    },
}

WEEKDAYS = {
    "da": ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
}


def lang_of(value) -> str:
    return value if value in LANGS else "da"


def tr(lang: str, key: str, **values) -> str:
    return TEXTS[lang_of(lang)][key].format(**values)


def mood(lang: str, name: str) -> str:
    return MOODS[lang_of(lang)].get(name, name)


def date(lang: str, ts_or_date) -> str:
    """Short day and month: 08.10 in Danish, 8 Oct in English."""
    if lang_of(lang) == "da":
        return ts_or_date.strftime("%d.%m")
    return f"{ts_or_date.day} {ts_or_date.strftime('%b')}"
