"""Queries behind the artist page, Wrapped, user comparison and CSV export."""
import csv
import io
import json
import math
from collections import Counter
from datetime import datetime
from typing import Optional

import db
import stats
from stats import LOCAL, MOOD_DA, WEEKDAYS, Scope

# {t} is the alias that carries the track columns (artists, album_id, item_id)
FILTERS = {
    "artist": "EXISTS (SELECT 1 FROM json_each({t}.artists) a WHERE a.value = ?)",
    "album": "{t}.album_id = ?",
    "track": "{t}.item_id = ?",
}


# --- artist / album / track pages -----------------------------------------

def detail(scope: Scope, kind: str, key: str) -> Optional[dict]:
    cte, params = stats._plays_cte(scope)
    base = f"{cte}, ap AS (SELECT * FROM p WHERE {FILTERS[kind].format(t='p')})"
    params = [*params, key]

    totals = db.query(
        f"""{base} SELECT COUNT(*) AS plays, COALESCE(SUM(listened),0)/60.0 AS minutes,
                  COUNT(DISTINCT item_id) AS tracks, COUNT(DISTINCT album_id) AS albums,
                  COUNT(DISTINCT date(started_at,{LOCAL})) AS days, MAX(started_at) AS last
            FROM ap""",
        params,
    )[0]
    if not totals["plays"]:
        return None

    user_sql, user_params = ("AND p.user_id = ?", [scope.user]) if scope.user else ("", [])
    first = db.query(
        f"""SELECT MIN(p.started_at) AS t FROM plays p JOIN tracks t USING(item_id)
            WHERE p.counted = 1 {user_sql} AND {FILTERS[kind].format(t='t')}""",
        [*user_params, key],
    )[0]["t"]

    ranking = stats.top(scope, kind + "s", 1000)
    rank = next((i + 1 for i, r in enumerate(ranking) if r["key"] == key), None)
    all_plays = stats._totals(scope)["plays"] or 1

    where, wparams = scope.where(counted=None, alias="p")
    skip = db.query(
        f"""SELECT 1.0 - AVG(p.counted) AS rate FROM plays p JOIN tracks t USING(item_id)
            WHERE {where} AND {FILTERS[kind].format(t='t')}""",
        [*wparams, key],
    )[0]["rate"] or 0

    top_tracks = db.query(
        f"""{base} SELECT item_id AS key, MAX(name) AS name, MAX(album) AS sub, COUNT(*) AS plays,
                  SUM(listened)/60.0 AS minutes, COALESCE(MAX(album_id), item_id) AS image_id
            FROM ap GROUP BY item_id ORDER BY plays DESC LIMIT 15""",
        params,
    )
    top_albums = db.query(
        f"""{base} SELECT ap.album_id AS key, MAX(ap.album) AS name, MAX(t.year) AS sub, COUNT(*) AS plays,
                  SUM(ap.listened)/60.0 AS minutes, ap.album_id AS image_id
            FROM ap JOIN tracks t ON t.item_id = ap.item_id WHERE ap.album_id IS NOT NULL
            GROUP BY ap.album_id ORDER BY plays DESC LIMIT 10""",
        params,
    )
    months = db.query(
        f"""{base} SELECT strftime('%Y-%m-01',started_at,{LOCAL}) AS b, COUNT(*) AS n FROM ap GROUP BY b""", params
    )
    hours = db.query(
        f"""{base} SELECT CAST(strftime('%H',started_at,{LOCAL}) AS INTEGER) AS h, COUNT(*) AS n FROM ap GROUP BY h""",
        params,
    )
    weekdays = db.query(
        f"""{base} SELECT (CAST(strftime('%w',started_at,{LOCAL}) AS INTEGER) + 6) % 7 AS d, COUNT(*) AS n
            FROM ap GROUP BY d""",
        params,
    )
    tags = db.query(
        f"""{base} SELECT 'genre' AS kind, g.value AS k, COUNT(*) AS n FROM ap, json_each(ap.genres) g GROUP BY k
            UNION ALL
            SELECT 'mood', m.value, COUNT(*) FROM ap, json_each(ap.moods) m GROUP BY m.value""",
        params,
    )

    month_map = {r["b"]: r["n"] for r in months}
    labels = stats._bucket_range(Scope(max(scope.start, first or scope.start), scope.end, scope.user), "month")
    hour_counts = {r["h"]: r["n"] for r in hours}
    day_counts = {r["d"]: r["n"] for r in weekdays}
    return {
        "kind": kind,
        "key": key,
        **_header(kind, key),
        **totals,
        "first": first,
        "rank": rank,
        "share": totals["plays"] / all_plays,
        "skip_rate": skip,
        "top_tracks": top_tracks if kind != "track" else _played_next(scope, key),
        "top_albums": top_albums if kind == "artist" else [],
        "months": {"labels": labels, "plays": [month_map.get(l, 0) for l in labels]},
        "hours": [hour_counts.get(h, 0) for h in range(24)],
        "weekdays": [day_counts.get(d, 0) for d in range(7)],
        "genres": sorted(({"name": t["k"], "n": t["n"]} for t in tags if t["kind"] == "genre"), key=lambda x: -x["n"])[:6],
        "moods": sorted(({"name": t["k"], "n": t["n"]} for t in tags if t["kind"] == "mood"), key=lambda x: -x["n"]),
    }


def _header(kind: str, key: str) -> dict:
    """Title, cover and links shown at the top of the page."""
    if kind == "artist":
        row = db.query(
            """SELECT t.album_id FROM plays p JOIN tracks t USING(item_id)
               WHERE EXISTS (SELECT 1 FROM json_each(t.artists) a WHERE a.value = ?)
               GROUP BY t.album_id ORDER BY COUNT(*) DESC LIMIT 1""",
            [key],
        )
        return {"name": key, "image_id": row[0]["album_id"] if row else None, "artists": [], "album": None}
    col = "album_id" if kind == "album" else "item_id"
    rows = db.query(f"SELECT * FROM tracks WHERE {col} = ? LIMIT 1", [key])
    if not rows:
        return {"name": key, "image_id": None, "artists": [], "album": None}
    t = rows[0]
    artists = [t["album_artist"]] if kind == "album" and t["album_artist"] else json.loads(t["artists"])
    return {
        "name": t["album"] if kind == "album" else t["name"],
        "image_id": t["album_id"] or t["item_id"],
        "artists": artists,
        "album": {"id": t["album_id"], "name": t["album"]} if kind == "track" and t["album_id"] else None,
        "year": t["year"],
        "duration": t["duration"],
    }


def _played_next(scope: Scope, item_id: str, max_gap: int = 600) -> list:
    """Tracks most often played right after this one, within the same listening session."""
    where, params = scope.where(counted=True, alias="plays")
    return db.query(
        f"""WITH seq AS (
              SELECT item_id, ended_at,
                     LEAD(item_id) OVER w AS next_id, LEAD(started_at) OVER w AS next_start
              FROM plays WHERE {where}
              WINDOW w AS (PARTITION BY user_id ORDER BY started_at))
            SELECT s.next_id AS key, t.name, json_extract(t.artists,'$[0]') AS sub, COUNT(*) AS plays,
                   NULL AS minutes, COALESCE(t.album_id, s.next_id) AS image_id
            FROM seq s JOIN tracks t ON t.item_id = s.next_id
            WHERE s.item_id = ? AND s.next_id <> s.item_id AND s.next_start - s.ended_at < ?
            GROUP BY s.next_id ORDER BY plays DESC LIMIT 10""",
        [*params, item_id, max_gap],
    )


# --- wrapped ---------------------------------------------------------------

def wrapped_years() -> list:
    rows = db.query(f"SELECT DISTINCT strftime('%Y',started_at,{LOCAL}) AS y FROM plays ORDER BY y DESC")
    return [int(r["y"]) for r in rows]


def wrapped(year: int, user: Optional[str]) -> dict:
    start = int(datetime(year, 1, 1).timestamp())
    end = int(datetime(year + 1, 1, 1).timestamp())
    scope = Scope(start, end, user)
    s = stats.summary(scope)
    if not s["plays"]:
        return {"year": year, "plays": 0}

    cte, params = stats._plays_cte(scope)
    busiest = db.query(
        f"""{cte} SELECT date(started_at,{LOCAL}) AS d, COUNT(*) AS n, SUM(listened)/60.0 AS minutes
            FROM p GROUP BY d ORDER BY minutes DESC LIMIT 1""",
        params,
    )[0]
    first_track = db.query(
        f"""{cte} SELECT name, json_extract(artists,'$[0]') AS artist, album_id, started_at
            FROM p ORDER BY started_at LIMIT 1""",
        params,
    )[0]
    on_repeat = db.query(
        f"""{cte} SELECT MAX(name) AS name, MAX(json_extract(artists,'$[0]')) AS artist, date(started_at,{LOCAL}) AS d,
                  COUNT(*) AS n
            FROM p GROUP BY item_id, d ORDER BY n DESC LIMIT 1""",
        params,
    )[0]
    sessions = stats._sessions(scope)
    longest = max(sessions, key=lambda x: x[-1]["ended_at"] - x[0]["started_at"]) if sessions else None

    genres = stats.genres(scope, "month")["totals"]
    genres.pop("Andet", None)
    moods = stats.moods(scope, "month")["totals"]
    moods.pop("Andet", None)
    months = stats.timeline(Scope(start, end, user), "month")
    peak = max(stats.heatmap(scope), key=lambda c: c[2])

    top_artists = stats.top(scope, "artists", 5)
    top_share = top_artists[0]["plays"] / s["plays"] if top_artists else 0
    mood_total = sum(moods.values()) or 1
    persona = _persona(s, peak[0], top_share, {k: v / mood_total for k, v in moods.items()})

    return {
        "year": year,
        **s,
        "top_artists": top_artists,
        "top_tracks": stats.top(scope, "tracks", 5),
        "top_albums": stats.top(scope, "albums", 5),
        "genres": [{"name": k, "n": v} for k, v in list(genres.items())[:5]],
        "moods": [{"name": k, "label": MOOD_DA.get(k, k), "n": v} for k, v in sorted(moods.items(), key=lambda kv: -kv[1])],
        "months": months,
        "peak": {"hour": peak[0], "weekday": WEEKDAYS[peak[1]]},
        "busiest_day": busiest,
        "first_track": first_track,
        "on_repeat": on_repeat if on_repeat["n"] >= 3 else None,
        "longest_session": {
            "minutes": (longest[-1]["ended_at"] - longest[0]["started_at"]) / 60,
            "start": longest[0]["started_at"],
            "tracks": len(longest),
        } if longest else None,
        "persona": persona,
    }


def _persona(s: dict, peak_hour: int, top_share: float, mood_share: dict) -> dict:
    top_mood = max(mood_share, key=mood_share.get) if mood_share else None
    rules = [
        (peak_hour >= 22 or peak_hour < 4, "Natteravnen", "Dine bedste lytte-timer ligger, når andre sover."),
        (peak_hour < 9, "Morgenfuglen", "Du starter dagen med musik i ørerne."),
        (s["discovery_rate"] > 0.4, "Opdageren", f"{round(s['discovery_rate'] * 100)} % af det, du hørte, var nyt for dig."),
        (top_share > 0.2, "Den trofaste fan", f"Din favoritkunstner stod for {round(top_share * 100)} % af alt, du hørte."),
        (top_mood == "party", "Festaben", "Når du trykker play, skal der danses."),
        (top_mood == "chill", "Zen-mesteren", "Rolig musik er dit soundtrack."),
        (top_mood in ("melancholic", "dark"), "Den eftertænksomme", "Du har ikke noget imod lidt tungsind."),
        (top_mood in ("energetic", "aggressive"), "Energibomben", "Højt tempo og fuld skrue."),
        (s["artists"] > 100, "Altæderen", f"{s['artists']} forskellige kunstnere – du hører lidt af det hele."),
    ]
    for ok, title, text in rules:
        if ok:
            return {"title": title, "text": text}
    return {"title": "Musikelskeren", "text": "Musik er en fast del af din hverdag."}


# --- compare ---------------------------------------------------------------

def compare(scope: Scope) -> dict:
    users = [u for u in stats.users() if u["id"]]
    people = []
    vectors = {}
    for u in users:
        us = Scope(scope.start, scope.end, u["id"])
        t = stats._totals(us)
        if not t["plays"]:
            continue
        artists = stats.top(us, "artists", 200)
        vectors[u["id"]] = {a["name"]: a["plays"] for a in artists}
        genres = stats.genres(us, "month")["totals"]
        genres.pop("Andet", None)
        moods = stats.moods(us, "month")["totals"]
        moods.pop("Andet", None)
        heat = stats.heatmap(us)
        hours = Counter()
        for h, _, n in heat:
            hours[h] += n
        people.append({
            "id": u["id"],
            "name": u["name"] or u["id"],
            **t,
            "top_artist": artists[0] if artists else None,
            "top_track": (stats.top(us, "tracks", 1) or [None])[0],
            "top_genre": next(iter(genres), None),
            "top_mood": MOOD_DA.get(max(moods, key=moods.get)) if moods else None,
            "peak_hour": hours.most_common(1)[0][0] if hours else None,
        })

    pairs = []
    for i, a in enumerate(people):
        for b in people[i + 1:]:
            va, vb = vectors[a["id"]], vectors[b["id"]]
            shared = sorted(set(va) & set(vb), key=lambda k: -(va[k] + vb[k]))
            pairs.append({
                "a": a["name"], "b": b["name"],
                "match": _cosine(va, vb),
                "shared": shared[:12],
                "shared_count": len(shared),
            })
    return {"people": people, "pairs": pairs}


def _cosine(a: dict, b: dict) -> float:
    # log-damped so one heavily played artist doesn't dominate the match
    la = {k: math.log1p(v) for k, v in a.items()}
    lb = {k: math.log1p(v) for k, v in b.items()}
    dot = sum(la[k] * lb[k] for k in set(la) & set(lb))
    norm = math.sqrt(sum(v * v for v in la.values())) * math.sqrt(sum(v * v for v in lb.values()))
    return dot / norm if norm else 0


# --- export ----------------------------------------------------------------

def export_csv(scope: Scope) -> str:
    where, params = scope.where(counted=None, alias="p")
    rows = db.query(
        f"""SELECT datetime(p.started_at,{LOCAL}) AS tidspunkt, p.user_name AS bruger, t.name AS titel,
                   t.artists, t.album, t.album_artist, t.year, t.genres, t.moods,
                   ROUND(p.listened) AS lyttet_sek, ROUND(p.duration) AS laengde_sek, p.counted,
                   p.client AS klient, p.device AS enhed
            FROM plays p LEFT JOIN tracks t USING(item_id)
            WHERE {where} ORDER BY p.started_at""",
        params,
    )
    out = io.StringIO()
    w = csv.writer(out, delimiter=";")  # semicolon so Danish Excel opens it directly
    w.writerow(["tidspunkt", "bruger", "titel", "kunstnere", "album", "albumkunstner", "år", "genrer", "humør",
                "lyttet_sek", "længde_sek", "talt_som_lytning", "klient", "enhed"])
    for r in rows:
        w.writerow([
            r["tidspunkt"], r["bruger"], r["titel"], _join(r["artists"]), r["album"], r["album_artist"], r["year"],
            _join(r["genres"]), ", ".join(MOOD_DA.get(m, m) for m in json.loads(r["moods"] or "[]")),
            r["lyttet_sek"], r["laengde_sek"], "ja" if r["counted"] else "nej", r["klient"], r["enhed"],
        ])
    return "﻿" + out.getvalue()  # BOM so Excel picks UTF-8 for æøå


def _join(value: Optional[str]) -> str:
    return ", ".join(json.loads(value)) if value else ""
