"""What someone has heard of the music in the library: per artist, per album and for the whole library.

Jellyfin is asked for the tracks when a page needs them, and the answer is kept for a little while. A track
counts as heard when the user has a counted play of it here, or Jellyfin has it marked as played (so listening
from before the add-on existed counts too). Without a user selected, any counted play by anyone counts, and
Jellyfin's marks are left out because they belong to a single user.

This is the current state, so it does not depend on the selected period.
"""
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

import db
from jellyfin import TICKS_PER_SECOND

CACHE_SECONDS = 600

_cache: Dict[tuple, Tuple[float, object]] = {}


async def _cached(key: tuple, load):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    result = await load()
    _cache[key] = (time.time(), result)
    return result


def forget() -> None:
    """Drop cached answers, e.g. when a new play has been saved."""
    _cache.clear()


def plays_here(user_id: Optional[str]) -> Dict[str, int]:
    """Counted plays per track, for one user or everyone."""
    user_sql, params = ("AND user_id = ?", [user_id]) if user_id else ("", [])
    rows = db.query(f"SELECT item_id, COUNT(*) AS n FROM plays WHERE counted = 1 {user_sql} GROUP BY item_id", params)
    return {r["item_id"]: r["n"] for r in rows}


def is_heard(item: dict, heard_here) -> bool:
    data = item.get("UserData") or {}
    return item["Id"] in heard_here or bool(data.get("Played")) or (data.get("PlayCount") or 0) > 0


def _minutes(item: dict) -> float:
    return (item.get("RunTimeTicks") or 0) / TICKS_PER_SECOND / 60


# --- artist -------------------------------------------------------------------

async def artist_progress(client, name: str, user_id: Optional[str]) -> Optional[dict]:
    async def load():
        items = await client.artist_tracks(name, user_id)
        return summarise(items, plays_here(user_id)) if items else None
    return await _cached(("artist", name, user_id), load)


def summarise(items: list, heard_here) -> dict:
    albums: dict = {}
    unheard_minutes = 0.0
    for it in items:
        heard = is_heard(it, heard_here)
        key = it.get("AlbumId") or "none"
        album = albums.setdefault(key, {
            "id": it.get("AlbumId"), "name": it.get("Album") or "", "year": it.get("ProductionYear"),
            "heard": 0, "total": 0, "next": None,
        })
        album["total"] += 1
        if heard:
            album["heard"] += 1
        else:
            unheard_minutes += _minutes(it)
            if album["next"] is None:  # tracks come in album order, so the first unheard one is next
                album["next"] = {"item_id": it["Id"], "name": it.get("Name"), "album_id": it.get("AlbumId"),
                                 "album": album["name"]}

    # what to discover next: the first unheard track on the album you've come furthest with
    started = sorted((a for a in albums.values() if a["next"]),
                     key=lambda a: (-(a["heard"] / a["total"]), a["year"] or 9999))
    return {
        "total": sum(a["total"] for a in albums.values()),
        "heard": sum(a["heard"] for a in albums.values()),
        "minutes_left": round(unheard_minutes, 1),
        "next": started[0]["next"] if started else None,
        "albums": [{k: v for k, v in a.items() if k != "next"} for a in albums.values()],
    }


def unheard_in_order(items: list, heard_here, limit: int) -> list:
    """Unheard track ids, starting with the albums you've come furthest with (for 'next to discover')."""
    albums: dict = {}
    for it in items:
        a = albums.setdefault(it.get("AlbumId") or "none", {"heard": 0, "total": 0, "unheard": []})
        a["total"] += 1
        if is_heard(it, heard_here):
            a["heard"] += 1
        else:
            a["unheard"].append(it["Id"])
    ordered = sorted((a for a in albums.values() if a["unheard"]), key=lambda a: -(a["heard"] / a["total"]))
    return [i for a in ordered for i in a["unheard"]][:limit]


# --- album --------------------------------------------------------------------

async def album_tracks(client, album_id: str, user_id: Optional[str]) -> Optional[dict]:
    async def load():
        items = await client.album_tracks(album_id, user_id)
        return track_list(items, plays_here(user_id)) if items else None
    return await _cached(("album", album_id, user_id), load)


def track_list(items: list, plays: Dict[str, int]) -> dict:
    discs = {it.get("ParentIndexNumber") or 1 for it in items}
    tracks = [{
        "item_id": it["Id"],
        "name": it.get("Name"),
        "number": it.get("IndexNumber"),
        "disc": (it.get("ParentIndexNumber") or 1) if len(discs) > 1 else None,
        "artist": (it.get("Artists") or [None])[0],
        "duration": round(_minutes(it) * 60),
        "plays": plays.get(it["Id"], 0),
        "heard": is_heard(it, plays),
    } for it in items]
    return {
        "total": len(tracks),
        "heard": sum(t["heard"] for t in tracks),
        "minutes_left": round(sum(t["duration"] for t in tracks if not t["heard"]) / 60, 1),
        "tracks": tracks,
    }


# --- whole library ------------------------------------------------------------

def _added(value: Optional[str]) -> Optional[int]:
    """Jellyfin's DateCreated is UTC with up to 7 fractional digits; the fraction is dropped."""
    try:
        return int(datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
    except (TypeError, ValueError):
        return None


async def never_heard(client, user_id: Optional[str]) -> dict:
    async def load():
        return library_summary(await client.library_tracks(user_id), plays_here(user_id))
    return await _cached(("library", user_id), load)


def library_summary(items: list, heard_here, limit: int = 120) -> dict:
    albums: dict = {}
    for it in items:
        key = it.get("AlbumId") or f"single:{it['Id']}"
        artist = it.get("AlbumArtist") or (it.get("Artists") or [None])[0]
        a = albums.setdefault(key, {
            "id": it.get("AlbumId"), "name": it.get("Album") or it.get("Name"), "artist": artist,
            "year": it.get("ProductionYear"), "added": None, "tracks": 0, "minutes": 0.0, "heard": False,
        })
        a["tracks"] += 1
        a["minutes"] += _minutes(it)
        a["heard"] = a["heard"] or is_heard(it, heard_here)
        added = _added(it.get("DateCreated"))
        if added and (a["added"] is None or added > a["added"]):
            a["added"] = added

    artists: dict = {}
    for a in albums.values():
        if not a["artist"]:
            continue
        s = artists.setdefault(a["artist"], {"name": a["artist"], "albums": 0, "tracks": 0, "heard": False})
        s["albums"] += 1
        s["tracks"] += a["tracks"]
        s["heard"] = s["heard"] or a["heard"]

    never = sorted((a for a in albums.values() if not a["heard"]), key=lambda a: -(a["added"] or 0))
    never_artists = sorted((s for s in artists.values() if not s["heard"]), key=lambda s: -s["tracks"])
    return {
        "albums_total": len(albums),
        "albums_never": len(never),
        "artists_total": len(artists),
        "artists_never": len(never_artists),
        "tracks_total": len(items),
        "tracks_heard": sum(1 for it in items if is_heard(it, heard_here)),
        "minutes_never": round(sum(a["minutes"] for a in never), 1),
        "albums": [{**{k: v for k, v in a.items() if k != "heard"}, "minutes": round(a["minutes"], 1)}
                   for a in never[:limit]],
        "artists": [{k: v for k, v in s.items() if k != "heard"} for s in never_artists[:limit]],
    }
