"""Mood tagging for tracks.

Sources, best first:
  1. tags on the track in Jellyfin (e.g. written by MusicBrainz Picard)
  2. Last.fm community tags for the track, then the artist (needs lastfm_api_key)
  3. a rough guess from the track's genres
"""
import asyncio
import json
import logging
from typing import Optional

import httpx

import db

log = logging.getLogger("enrich")

MOODS = {
    "energetic": ["energetic", "energy", "upbeat", "workout", "driving", "power", "uptempo", "pumped"],
    "happy": ["happy", "feel good", "feelgood", "cheerful", "fun", "uplifting", "joyful", "sunny", "summer", "positive"],
    "chill": ["chill", "relax", "calm", "mellow", "peaceful", "lounge", "downtempo", "soothing", "sleep", "easy listening"],
    "melancholic": ["sad", "melanchol", "depress", "heartbreak", "lonely", "bittersweet", "emotional", "nostalg", "longing"],
    "dark": ["dark", "gloomy", "haunting", "eerie", "sinister", "brooding", "ominous"],
    "romantic": ["romantic", "love", "sensual", "sexy", "tender"],
    "aggressive": ["aggressive", "angry", "brutal", "rage", "intense", "furious"],
    "party": ["party", "dance", "club", "danceable", "groovy", "funky", "banger"],
}

GENRE_MOODS = [
    ("metal", "aggressive"), ("hardcore", "aggressive"), ("punk", "energetic"),
    ("ambient", "chill"), ("lo-fi", "chill"), ("lofi", "chill"), ("classical", "chill"),
    ("jazz", "chill"), ("acoustic", "chill"), ("folk", "melancholic"), ("blues", "melancholic"),
    ("soul", "romantic"), ("r&b", "romantic"), ("rnb", "romantic"),
    ("house", "party"), ("techno", "party"), ("edm", "party"), ("dance", "party"), ("disco", "party"),
    ("pop", "happy"), ("reggae", "happy"), ("rock", "energetic"), ("hip hop", "energetic"),
    ("hip-hop", "energetic"), ("rap", "energetic"), ("drum and bass", "energetic"),
    ("goth", "dark"), ("darkwave", "dark"), ("industrial", "dark"),
]

_queue: Optional["asyncio.Queue[str]"] = None


def _get_queue() -> "asyncio.Queue[str]":
    # created lazily so it binds to the server's event loop
    global _queue
    if _queue is None:
        _queue = asyncio.Queue()
    return _queue


def queue(item_id: str) -> None:
    _get_queue().put_nowait(item_id)


def moods_from_tags(tags: list) -> list:
    found = []
    for tag in tags:
        t = tag.lower()
        for mood, words in MOODS.items():
            if mood not in found and any(w in t for w in words):
                found.append(mood)
    return found


def moods_from_genres(genres: list) -> list:
    found = []
    for genre in genres:
        g = genre.lower()
        for needle, mood in GENRE_MOODS:
            if needle in g and mood not in found:
                found.append(mood)
                break
    return found


class Enricher:
    def __init__(self, lastfm_api_key: str):
        self.lastfm_key = lastfm_api_key
        self.http = httpx.AsyncClient(timeout=10)

    async def run(self) -> None:
        for row in db.query("SELECT item_id FROM tracks WHERE moods IS NULL"):
            queue(row["item_id"])
        while True:
            item_id = await _get_queue().get()
            try:
                await self.enrich(item_id)
            except Exception as e:
                log.warning("enrich %s failed: %s", item_id, e)
            await asyncio.sleep(0.25)  # stay well under Last.fm's rate limit

    async def enrich(self, item_id: str) -> None:
        rows = db.query("SELECT * FROM tracks WHERE item_id=?", (item_id,))
        if not rows:
            return
        t = rows[0]
        artists = json.loads(t["artists"])

        moods = moods_from_tags(json.loads(t["tags"]))
        source = "tags"
        if not moods and self.lastfm_key and artists:
            moods = moods_from_tags(await self._lastfm_tags(artists[0], t["name"]))
            source = "lastfm"
        if not moods:
            moods = moods_from_genres(json.loads(t["genres"]))
            source = "genre"
        db.set_moods(item_id, moods[:3], source if moods else "none")

    async def _lastfm_tags(self, artist: str, track: Optional[str]) -> list:
        tags = []
        if track:
            tags = await self._lastfm("track.gettoptags", artist=artist, track=track)
        if not tags:
            tags = await self._lastfm("artist.gettoptags", artist=artist)
        return tags

    async def _lastfm(self, method: str, **params) -> list:
        r = await self.http.get(
            "https://ws.audioscrobbler.com/2.0/",
            params={"method": method, "api_key": self.lastfm_key, "format": "json", "autocorrect": 1, **params},
        )
        if r.status_code != 200:
            return []
        tags = (r.json().get("toptags") or {}).get("tag") or []
        # Last.fm counts are relative (100 = most used); ignore the long tail
        return [tag["name"] for tag in tags if int(tag.get("count", 0)) >= 10][:15]
