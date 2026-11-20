"""How much of an artist's music in the library someone has heard: tracks heard out of all tracks, per album.

Jellyfin is asked for every track the artist appears on when the artist page is opened, and the answer is
kept for a little while. A track counts as heard when the user has a counted play of it here, or Jellyfin has
it marked as played (so listening from before the add-on existed counts too). Without a user selected, any
counted play by anyone counts, and Jellyfin's marks are left out because they belong to a single user.

Progress is the current state, so it does not depend on the selected period.
"""
import time
from typing import Dict, Optional, Tuple

import db
from jellyfin import TICKS_PER_SECOND

CACHE_SECONDS = 600

_cache: Dict[Tuple[str, Optional[str]], Tuple[float, Optional[dict]]] = {}


async def artist_progress(client, name: str, user_id: Optional[str]) -> Optional[dict]:
    hit = _cache.get((name, user_id))
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    items = await client.artist_tracks(name, user_id)
    result = summarise(items, _heard_here(user_id)) if items else None
    _cache[(name, user_id)] = (time.time(), result)
    return result


def forget() -> None:
    """Drop cached answers, e.g. when a new play has been saved."""
    _cache.clear()


def _heard_here(user_id: Optional[str]) -> set:
    user_sql, params = ("AND user_id = ?", [user_id]) if user_id else ("", [])
    return {r["item_id"] for r in db.query(f"SELECT DISTINCT item_id FROM plays WHERE counted = 1 {user_sql}", params)}


def summarise(items: list, heard_here: set) -> dict:
    albums: dict = {}
    for it in items:
        data = it.get("UserData") or {}
        heard = it["Id"] in heard_here or bool(data.get("Played")) or (data.get("PlayCount") or 0) > 0
        key = it.get("AlbumId") or "none"
        album = albums.setdefault(key, {
            "id": it.get("AlbumId"), "name": it.get("Album") or "Uden album", "year": it.get("ProductionYear"),
            "heard": 0, "total": 0, "next": None,
        })
        album["total"] += 1
        if heard:
            album["heard"] += 1
        elif album["next"] is None:  # tracks come in album order, so the first unheard one is next
            album["next"] = {"item_id": it["Id"], "name": it.get("Name"), "album_id": it.get("AlbumId"),
                             "album": album["name"]}
        it["_heard"] = heard

    total = sum(a["total"] for a in albums.values())
    heard = sum(a["heard"] for a in albums.values())
    left = sum((it.get("RunTimeTicks") or 0) / TICKS_PER_SECOND for it in items if not it["_heard"]) / 60
    # what to discover next: the first unheard track on the album you've come furthest with
    started = [a for a in albums.values() if a["next"]]
    started.sort(key=lambda a: (-(a["heard"] / a["total"]), a["year"] or 9999))
    return {
        "total": total,
        "heard": heard,
        "minutes_left": round(left, 1),
        "next": started[0]["next"] if started else None,
        "albums": [{k: v for k, v in a.items() if k != "next"} for a in albums.values()],
    }
