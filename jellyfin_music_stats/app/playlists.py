"""Smart playlists: playlists in Jellyfin, one set per user, kept up to date from the statistics.

Every few hours each user gets their playlists rebuilt: the top tracks of the last 30 days, forgotten
favourites, the next tracks to discover from the artists they're into, a morning and an evening mix and one
playlist per mood. They're private to the user and show up in every Jellyfin app.

Only playlists the add-on made itself are touched (their ids are kept in the smart_playlists table). A playlist
with too few tracks is removed until there's enough data again. Turning the option off leaves them alone.
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional

import db
import progress
import stats
import texts
from collector import describe_error
from stats import LOCAL

log = logging.getLogger("playlists")

REFRESH_EVERY = 6 * 3600
FIRST_RUN_AFTER = 120  # let the collectors settle after a restart
SIZE = 50
MIN_TRACKS = 5  # fewer than this and the playlist isn't worth having

NAMES = {
    "da": {"top": "Top 50 – seneste 30 dage", "forgotten": "Glemte favoritter", "discover": "Næste at opdage",
           "morning": "Morgen-mix", "evening": "Aften-mix", "mood": "Humør: {mood}"},
    "en": {"top": "Top 50 – last 30 days", "forgotten": "Forgotten favourites", "discover": "Next to discover",
           "morning": "Morning mix", "evening": "Evening mix", "mood": "Mood: {mood}"},
}
PREFIX = "🎧 "

status: dict = {"enabled": False, "last_run": None, "last_error": None, "playlists": 0}


def playlist_name(kind: str, lang: str) -> str:
    names = NAMES[texts.lang_of(lang)]
    if kind.startswith("mood:"):
        return PREFIX + names["mood"].format(mood=texts.mood(lang, kind[5:]).capitalize())
    return PREFIX + names[kind]


# --- what goes in each playlist ---------------------------------------------------

def top_tracks(user_id: str, now: float) -> List[str]:
    return [r["key"] for r in stats.top(stats.Scope(int(now) - 30 * 86400, int(now) + 60, user_id), "tracks", SIZE)]


def forgotten(user_id: str, now: float, min_plays: int = 4, quiet_days: int = 90) -> List[str]:
    """Tracks played a lot once, but not for a good while."""
    rows = db.query(
        """SELECT item_id, COUNT(*) AS n FROM plays WHERE counted = 1 AND user_id = ?
           GROUP BY item_id HAVING n >= ? AND MAX(started_at) < ? ORDER BY n DESC LIMIT ?""",
        [user_id, min_plays, int(now) - quiet_days * 86400, SIZE],
    )
    return [r["item_id"] for r in rows]


def by_hours(user_id: str, hours: range, min_plays: int = 2) -> List[str]:
    """Tracks this user plays most at these hours of the day."""
    marks = ",".join(str(h) for h in hours)
    rows = db.query(
        f"""SELECT item_id, COUNT(*) AS n FROM plays WHERE counted = 1 AND user_id = ?
              AND CAST(strftime('%H', started_at, {LOCAL}) AS INTEGER) IN ({marks})
            GROUP BY item_id HAVING n >= ? ORDER BY n DESC LIMIT ?""",
        [user_id, min_plays, SIZE],
    )
    return [r["item_id"] for r in rows]


def by_mood(user_id: str, mood: str) -> List[str]:
    rows = db.query(
        """SELECT p.item_id, COUNT(*) AS n FROM plays p JOIN tracks t USING(item_id)
           WHERE p.counted = 1 AND p.user_id = ? AND EXISTS (SELECT 1 FROM json_each(t.moods) m WHERE m.value = ?)
           GROUP BY p.item_id ORDER BY n DESC LIMIT ?""",
        [user_id, mood, SIZE],
    )
    return [r["item_id"] for r in rows]


async def to_discover(client, user_id: str, now: float, artists: int = 10, per_artist: int = 5) -> List[str]:
    """Unheard tracks from the artists this user has played most lately, furthest-along albums first."""
    heard = progress.plays_here(user_id)
    scope = stats.Scope(int(now) - 90 * 86400, int(now) + 60, user_id)
    out: List[str] = []
    for a in stats.top(scope, "artists", artists):
        items = await client.artist_tracks(a["name"], user_id)
        out += progress.unheard_in_order(items or [], heard, per_artist)
    return out[:SIZE]


async def wanted(client, user_id: str, now: float) -> Dict[str, List[str]]:
    lists = {
        "top": top_tracks(user_id, now),
        "forgotten": forgotten(user_id, now),
        "discover": await to_discover(client, user_id, now),
        "morning": by_hours(user_id, range(5, 11)),
        "evening": by_hours(user_id, range(18, 24)),
    }
    for mood in stats.MOOD_NAMES:
        lists[f"mood:{mood}"] = by_mood(user_id, mood)
    return lists


# --- keeping Jellyfin in step ----------------------------------------------------

class PlaylistKeeper:
    def __init__(self, client, lang: str):
        self.client = client
        self.lang = lang

    async def run(self) -> None:
        status["enabled"] = True
        await asyncio.sleep(FIRST_RUN_AFTER)
        while True:
            try:
                await self.sync_all()
                status["last_error"] = None
            except Exception as e:
                status["last_error"] = describe_error(e)
                log.warning("smart playlists failed: %s", status["last_error"])
            await asyncio.sleep(REFRESH_EVERY)

    async def sync_all(self, now: Optional[float] = None) -> int:
        now = now or time.time()
        changed = 0
        for user in stats.users():
            lists = await wanted(self.client, user["id"], now)
            for kind, ids in lists.items():
                changed += await self.sync(user["id"], kind, ids)
        status.update(last_run=now, playlists=db.query("SELECT COUNT(*) AS n FROM smart_playlists")[0]["n"])
        if changed:
            log.info("smarte playlister opdateret: %d", changed)
        return changed

    async def sync(self, user_id: str, kind: str, ids: List[str]) -> int:
        """Make one playlist match; returns 1 if Jellyfin was changed."""
        row = db.query("SELECT playlist_id, name FROM smart_playlists WHERE user_id = ? AND kind = ?", [user_id, kind])
        playlist_id = row[0]["playlist_id"] if row else None
        if playlist_id and not await self.client.playlist_exists(playlist_id, user_id):
            playlist_id = None  # deleted by hand in Jellyfin: make it again
            self._forget(user_id, kind)

        if len(ids) < MIN_TRACKS:
            if playlist_id:
                await self.client.delete_item(playlist_id)
                self._forget(user_id, kind)
                return 1
            return 0

        name = playlist_name(kind, self.lang)
        if playlist_id:
            if await self.client.playlist_track_ids(playlist_id, user_id) == ids and row[0]["name"] == name:
                return 0
            if await self.client.update_playlist(playlist_id, name, ids):
                self._remember(user_id, kind, playlist_id, name)
                return 1
            await self.client.delete_item(playlist_id)  # older Jellyfin can't replace contents: start over
        playlist_id = await self.client.create_playlist(name, user_id, ids)
        self._remember(user_id, kind, playlist_id, name)
        return 1

    @staticmethod
    def _remember(user_id: str, kind: str, playlist_id: str, name: str) -> None:
        db.execute(
            """INSERT INTO smart_playlists (user_id, kind, playlist_id, name) VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, kind) DO UPDATE SET playlist_id = excluded.playlist_id, name = excluded.name""",
            (user_id, kind, playlist_id, name),
        )

    @staticmethod
    def _forget(user_id: str, kind: str) -> None:
        db.execute("DELETE FROM smart_playlists WHERE user_id = ? AND kind = ?", (user_id, kind))
