"""One name per genre, however the files spell it.

Tags are messy: "Hip-Hop", "Hip Hop" and "hip hop" are the same genre, and so are "Alternativ" and
"Alternative" in a library tagged in two languages. Spellings that only differ in case, spaces, slashes,
hyphens or underscores are merged automatically under the spelling the library uses most; anything
else is merged with the genre_map option ("Alternative=Alternativ").

Jellyfin's own genres are kept in tracks.genres_raw, and tracks.genres holds the merged ones, so
every query sees clean genres and a changed genre_map is applied to all old data on the next start.
"""
import json
import logging
import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Dict, List

import db

log = logging.getLogger("genres")

SIMILAR = 0.85  # how alike two names must be to be suggested as the same genre

_map: Dict[str, str] = {}  # normalised spelling -> name to use, from genre_map
_display: Dict[str, str] = {}  # normalised spelling -> the library's most common spelling


def key(name: str) -> str:
    return re.sub(r"[\s\-_/]+", " ", name.lower()).strip()


def parse_map(entries) -> Dict[str, str]:
    """Entries look like "from=to"; the target keeps its spelling, the source is matched loosely."""
    out = {}
    for entry in entries or []:
        src, sep, dst = str(entry).partition("=")
        if sep and src.strip() and dst.strip():
            out[key(src)] = dst.strip()
    return out


def configure(entries) -> None:
    _map.clear()
    _map.update(parse_map(entries))


def canonical(raw: List[str]) -> List[str]:
    out = []
    for name in raw or []:
        name = name.strip()
        if not name:
            continue
        k = key(name)
        merged = _map.get(k) or _display.setdefault(k, name)
        if merged not in out:
            out.append(merged)
    return out


def rebuild() -> int:
    """Recompute every track's genres from Jellyfin's; returns how many tracks changed."""
    rows = db.query("SELECT item_id, genres, genres_raw FROM tracks")
    raw = {r["item_id"]: json.loads(r["genres_raw"] or r["genres"] or "[]") for r in rows}

    spellings = Counter(name.strip() for names in raw.values() for name in names if name.strip())
    _display.clear()
    for name, _ in spellings.most_common():  # most used first, so it wins its key
        _display.setdefault(key(name), name)

    changed = 0
    for r in rows:
        genres = json.dumps(canonical(raw[r["item_id"]]))
        source = json.dumps(raw[r["item_id"]])
        if genres != r["genres"] or source != r["genres_raw"]:
            db.execute("UPDATE tracks SET genres = ?, genres_raw = ? WHERE item_id = ?", (genres, source, r["item_id"]))
            changed += 1
    if changed:
        log.info("genrer opdateret for %d numre", changed)
    for a, b in suggestions():
        log.info("mulig dublet: '%s' og '%s' – tilføj fx '%s=%s' under genre_map", a, b, a, b)
    return changed


def suggestions() -> List[tuple]:
    """Pairs of merged genres that still look alike, most used one second (the suggested target)."""
    counts = Counter()
    for r in db.query("SELECT genres FROM tracks"):
        counts.update(json.loads(r["genres"] or "[]"))
    names = [n for n, _ in counts.most_common()]
    pairs = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if SequenceMatcher(None, key(a), key(b)).ratio() >= SIMILAR:
                pairs.append((b, a))  # b is used less, so suggest merging it into a
    return pairs
