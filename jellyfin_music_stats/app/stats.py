"""Read-side queries for the dashboard. All times are bucketed in the container's local time zone."""
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

import db

LOCAL = "'unixepoch','localtime'"
BUCKETS = {
    "day": f"date(started_at,{LOCAL})",
    "week": f"date(started_at,{LOCAL},'weekday 0','-6 days')",
    "month": f"strftime('%Y-%m-01',started_at,{LOCAL})",
}
SESSION_GAP = 30 * 60
WEEKDAYS = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
MOOD_DA = {
    "energetic": "energisk", "happy": "glad", "chill": "rolig", "melancholic": "melankolsk",
    "dark": "mørk", "romantic": "romantisk", "aggressive": "aggressiv", "party": "festlig",
}


@dataclass
class Scope:
    start: int
    end: int
    user: Optional[str] = None

    def where(self, counted: Optional[bool] = True, alias: str = "plays"):
        sql = f"{alias}.started_at >= ? AND {alias}.started_at < ?"
        params = [self.start, self.end]
        if self.user:
            sql += f" AND {alias}.user_id = ?"
            params.append(self.user)
        if counted is not None:
            sql += f" AND {alias}.counted = {int(counted)}"
        return sql, params

    def previous(self) -> "Scope":
        length = self.end - self.start
        return Scope(self.start - length, self.start, self.user)


def _plays_cte(scope: Scope, counted: Optional[bool] = True):
    where, params = scope.where(counted)
    return (
        f"""WITH p AS (
              SELECT plays.*, t.name, t.album, t.album_id, t.album_artist,
                     COALESCE(t.artists,'[]') AS artists, COALESCE(t.genres,'[]') AS genres,
                     COALESCE(t.moods,'[]') AS moods
              FROM plays LEFT JOIN tracks t USING(item_id)
              WHERE {where})""",
        params,
    )


# --- meta -----------------------------------------------------------------

def users() -> list:
    return db.query(
        """SELECT user_id AS id, MAX(user_name) AS name, COUNT(*) AS plays
           FROM plays WHERE user_id IS NOT NULL GROUP BY user_id ORDER BY plays DESC"""
    )


def first_play() -> Optional[int]:
    rows = db.query("SELECT MIN(started_at) AS t FROM plays")
    return rows[0]["t"] if rows else None


# --- summary --------------------------------------------------------------

def _totals(scope: Scope) -> dict:
    cte, params = _plays_cte(scope)
    row = db.query(
        f"""{cte} SELECT COUNT(*) AS plays, COALESCE(SUM(listened),0)/60.0 AS minutes,
                  COUNT(DISTINCT item_id) AS tracks, COUNT(DISTINCT album_id) AS albums,
                  (SELECT COUNT(DISTINCT a.value) FROM p, json_each(p.artists) a) AS artists
            FROM p""",
        params,
    )[0]
    where, params = scope.where(counted=None)
    all_row = db.query(f"SELECT COUNT(*) AS n, SUM(counted) AS c FROM plays WHERE {where}", params)[0]
    row["skip_rate"] = 1 - (all_row["c"] or 0) / all_row["n"] if all_row["n"] else 0
    return row


def summary(scope: Scope) -> dict:
    current = _totals(scope)
    previous = _totals(scope.previous())

    # discovery: tracks/artists whose first-ever listen falls inside the range
    user_sql, user_params = ("AND user_id = ?", [scope.user]) if scope.user else ("", [])
    firsts = db.query(
        f"""SELECT item_id, MIN(started_at) AS first FROM plays
            WHERE counted = 1 {user_sql} GROUP BY item_id""",
        user_params,
    )
    new_tracks = sum(1 for r in firsts if scope.start <= r["first"] < scope.end)
    new_artists = len(_new_artists(scope))

    sessions = _sessions(scope)
    lengths = [(s[-1]["ended_at"] - s[0]["started_at"]) / 60 for s in sessions]
    streak_now, streak_best = _streaks(scope.user)

    return {
        **current,
        "previous": previous,
        "new_tracks": new_tracks,
        "new_artists": new_artists,
        "discovery_rate": new_tracks / current["tracks"] if current["tracks"] else 0,
        "sessions": len(sessions),
        "avg_session_minutes": sum(lengths) / len(lengths) if lengths else 0,
        "longest_session_minutes": max(lengths) if lengths else 0,
        "streak_current": streak_now,
        "streak_best": streak_best,
    }


def _new_artists(scope: Scope) -> dict:
    user_sql, user_params = ("AND p.user_id = ?", [scope.user]) if scope.user else ("", [])
    rows = db.query(
        f"""SELECT a.value AS artist, MIN(p.started_at) AS first,
                   SUM(CASE WHEN p.started_at >= ? AND p.started_at < ? THEN 1 ELSE 0 END) AS in_range
            FROM plays p JOIN tracks t USING(item_id), json_each(t.artists) a
            WHERE p.counted = 1 {user_sql} GROUP BY a.value""",
        [scope.start, scope.end, *user_params],
    )
    return {r["artist"]: r for r in rows if scope.start <= r["first"] < scope.end}


def _sessions(scope: Scope) -> list:
    where, params = scope.where(counted=None)
    rows = db.query(
        f"SELECT user_id, started_at, ended_at FROM plays WHERE {where} ORDER BY user_id, started_at", params
    )
    sessions, current = [], []
    for r in rows:
        if current and (r["user_id"] != current[-1]["user_id"] or r["started_at"] - current[-1]["ended_at"] > SESSION_GAP):
            sessions.append(current)
            current = []
        current.append(r)
    if current:
        sessions.append(current)
    return sessions


def _streaks(user: Optional[str]):
    user_sql, params = ("AND user_id = ?", [user]) if user else ("", [])
    days = [
        date.fromisoformat(r["d"])
        for r in db.query(
            f"SELECT DISTINCT date(started_at,{LOCAL}) AS d FROM plays WHERE counted = 1 {user_sql} ORDER BY d",
            params,
        )
    ]
    best = run = 0
    prev = None
    for d in days:
        run = run + 1 if prev and d - prev == timedelta(days=1) else 1
        best = max(best, run)
        prev = d
    today = date.today()
    current = run if prev and (today - prev).days <= 1 else 0
    return current, best


# --- charts ---------------------------------------------------------------

def _bucket_range(scope: Scope, bucket: str) -> list:
    first = first_play() or scope.start
    start = datetime.fromtimestamp(max(scope.start, first)).date()
    end = datetime.fromtimestamp(min(scope.end, datetime.now().timestamp())).date()
    if bucket == "week":
        start -= timedelta(days=start.weekday())
    elif bucket == "month":
        start = start.replace(day=1)
    out, d = [], start
    while d <= end:
        out.append(d.isoformat())
        if bucket == "day":
            d += timedelta(days=1)
        elif bucket == "week":
            d += timedelta(days=7)
        else:
            d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return out


def timeline(scope: Scope, bucket: str) -> dict:
    cte, params = _plays_cte(scope)
    rows = db.query(
        f"""{cte} SELECT {BUCKETS[bucket]} AS b, COUNT(*) AS plays, SUM(listened)/60.0 AS minutes
            FROM p GROUP BY b""",
        params,
    )
    by_bucket = {r["b"]: r for r in rows}
    labels = _bucket_range(scope, bucket)
    return {
        "labels": labels,
        "plays": [by_bucket.get(l, {}).get("plays", 0) for l in labels],
        "minutes": [round(by_bucket.get(l, {}).get("minutes") or 0, 1) for l in labels],
    }


def top(scope: Scope, kind: str, limit: int) -> list:
    cte, params = _plays_cte(scope)
    if kind == "artists":
        sql = f"""{cte} SELECT a.value AS key, a.value AS name, NULL AS sub, COUNT(*) AS plays, SUM(listened)/60.0 AS minutes,
                         MAX(p.album_id) AS image_id, COUNT(DISTINCT date(started_at,{LOCAL})) AS days
                  FROM p, json_each(p.artists) a GROUP BY a.value"""
    elif kind == "albums":
        sql = f"""{cte} SELECT album_id AS key, MAX(album) AS name, MAX(album_artist) AS sub, COUNT(*) AS plays,
                         SUM(listened)/60.0 AS minutes, album_id AS image_id,
                         COUNT(DISTINCT date(started_at,{LOCAL})) AS days
                  FROM p WHERE album_id IS NOT NULL GROUP BY album_id"""
    else:
        sql = f"""{cte} SELECT item_id AS key, MAX(name) AS name, MAX(json_extract(artists,'$[0]')) AS sub, COUNT(*) AS plays,
                         SUM(listened)/60.0 AS minutes, COALESCE(MAX(album_id), item_id) AS image_id,
                         COUNT(DISTINCT date(started_at,{LOCAL})) AS days
                  FROM p GROUP BY item_id"""
    return db.query(sql + " ORDER BY plays DESC, minutes DESC LIMIT ?", [*params, limit])


def _series_over_time(scope: Scope, bucket: str, field: str, limit: int) -> dict:
    cte, params = _plays_cte(scope)
    rows = db.query(
        f"""{cte} SELECT {BUCKETS[bucket]} AS b, TRIM(g.value) AS k, COUNT(*) AS n
            FROM p, json_each(p.{field}) g GROUP BY b, k""",
        params,
    )
    totals = Counter()
    for r in rows:
        totals[r["k"]] += r["n"]
    keys = [k for k, _ in totals.most_common(limit)]
    labels = _bucket_range(scope, bucket)
    grid = defaultdict(lambda: defaultdict(int))
    for r in rows:
        key = r["k"] if r["k"] in keys else "Andet"
        grid[key][r["b"]] += r["n"]
    if "Andet" in grid:
        keys.append("Andet")
    return {
        "labels": labels,
        "totals": {k: totals.get(k, sum(grid[k].values())) for k in keys},
        "series": [{"name": k, "data": [grid[k].get(l, 0) for l in labels]} for k in keys],
    }


def genres(scope: Scope, bucket: str) -> dict:
    return _series_over_time(scope, bucket, "genres", 8)


def moods(scope: Scope, bucket: str) -> dict:
    data = _series_over_time(scope, bucket, "moods", len(MOOD_DA))
    cte, params = _plays_cte(scope)
    by_hour = db.query(
        f"""{cte} SELECT CAST(strftime('%H',started_at,{LOCAL}) AS INTEGER) AS h, m.value AS mood, COUNT(*) AS n
            FROM p, json_each(p.moods) m GROUP BY h, mood""",
        params,
    )
    data["by_hour"] = by_hour
    coverage = db.query(
        f"""{cte} SELECT COUNT(*) AS total,
                  SUM(CASE WHEN json_array_length(moods) > 0 THEN 1 ELSE 0 END) AS tagged FROM p""",
        params,
    )[0]
    data["coverage"] = (coverage["tagged"] or 0) / coverage["total"] if coverage["total"] else 0
    return data


def heatmap(scope: Scope) -> list:
    cte, params = _plays_cte(scope)
    rows = db.query(
        f"""{cte} SELECT (CAST(strftime('%w',started_at,{LOCAL}) AS INTEGER) + 6) % 7 AS wd,
                  CAST(strftime('%H',started_at,{LOCAL}) AS INTEGER) AS h, COUNT(*) AS n
            FROM p GROUP BY wd, h""",
        params,
    )
    return [[r["h"], r["wd"], r["n"]] for r in rows]


def recent(scope: Scope, limit: int = 15) -> list:
    cte, params = _plays_cte(scope, counted=None)
    return db.query(
        f"""{cte} SELECT item_id, name, json_extract(artists,'$[0]') AS artist, album_id, user_name,
                  started_at, listened, duration, counted, source
            FROM p ORDER BY started_at DESC LIMIT ?""",
        [*params, limit],
    )


# --- insights -------------------------------------------------------------

def insights(scope: Scope) -> list:
    """Short observations in Danish, most interesting first."""
    out = []
    cte, params = _plays_cte(scope)
    if not db.query(f"{cte} SELECT 1 FROM p LIMIT 1", params):
        return out

    peak = heatmap(scope)
    if peak:
        h, wd, _ = max(peak, key=lambda x: x[2])
        out.append({"icon": "clock", "text": f"Du lytter mest om {WEEKDAYS[wd]}en omkring kl. {h:02d}."})

    loyal = top(scope, "artists", 1)
    if loyal:
        a = loyal[0]
        out.append({"icon": "star", "text": f"{a['name']} er din mest spillede kunstner: {a['plays']} lytninger fordelt på {a['days']} dage."})

    # everything is "new" when the range reaches back to the very first play
    new = _new_artists(scope) if scope.start > (first_play() or 0) + 14 * 86400 else {}
    if new:
        best = max(new.values(), key=lambda r: r["in_range"])
        if best["in_range"] >= 3:
            when = datetime.fromtimestamp(best["first"]).strftime("%d.%m")
            out.append({"icon": "sparkle", "text": f"Nyopdaget: {best['artist']}. Første lytning var {when}, og du har hørt dem {best['in_range']} gange siden."})

    redisc = _rediscovered(scope)
    if redisc:
        out.append({"icon": "rewind", "text": f"Genfundet: {redisc['artist']} efter {redisc['gap']} dages pause."})

    rep = db.query(
        f"""{cte} SELECT MAX(name) AS name, date(started_at,{LOCAL}) AS d, COUNT(*) AS n
            FROM p GROUP BY item_id, d ORDER BY n DESC LIMIT 1""",
        params,
    )
    if rep and rep[0]["n"] >= 4:
        d = date.fromisoformat(rep[0]["d"]).strftime("%d.%m")
        out.append({"icon": "repeat", "text": f"På repeat: \"{rep[0]['name']}\" blev spillet {rep[0]['n']} gange den {d}."})

    skip = _most_skipped(scope)
    if skip:
        out.append({"icon": "skip", "text": f"Du springer oftest {skip['artist']} over ({round(skip['rate'] * 100)} % af afspilningerne)."})

    mood_shift = _weekend_mood(scope)
    if mood_shift:
        out.append({"icon": "mood", "text": mood_shift})

    night = db.query(
        f"""{cte} SELECT AVG(CASE WHEN CAST(strftime('%H',started_at,{LOCAL}) AS INTEGER) >= 23
                   OR CAST(strftime('%H',started_at,{LOCAL}) AS INTEGER) < 4 THEN 1.0 ELSE 0 END) AS r FROM p""",
        params,
    )[0]["r"]
    if night and night > 0.15:
        out.append({"icon": "moon", "text": f"Natteravn: {round(night * 100)} % af din lytning sker mellem kl. 23 og 04."})
    return out


def _rediscovered(scope: Scope, min_gap_days: int = 90) -> Optional[dict]:
    user_sql, user_params = ("AND p.user_id = ?", [scope.user]) if scope.user else ("", [])
    rows = db.query(
        f"""SELECT a.value AS artist, p.started_at AS t FROM plays p JOIN tracks t USING(item_id), json_each(t.artists) a
            WHERE p.counted = 1 AND p.started_at < ? {user_sql} ORDER BY a.value, p.started_at""",
        [scope.end, *user_params],
    )
    best = None
    prev_artist, prev_t = None, None
    for r in rows:
        if r["artist"] == prev_artist and r["t"] >= scope.start:
            gap = (r["t"] - prev_t) / 86400
            if gap >= min_gap_days and (not best or gap > best["gap"]):
                best = {"artist": r["artist"], "gap": int(gap)}
        prev_artist, prev_t = r["artist"], r["t"]
    return best


def _most_skipped(scope: Scope) -> Optional[dict]:
    where, params = scope.where(counted=None, alias="p")
    rows = db.query(
        f"""SELECT a.value AS artist, COUNT(*) AS n, 1.0 - AVG(p.counted) AS rate
            FROM plays p JOIN tracks t USING(item_id), json_each(t.artists) a
            WHERE {where} GROUP BY a.value HAVING n >= 8 ORDER BY rate DESC LIMIT 1""",
        params,
    )
    return rows[0] if rows and rows[0]["rate"] >= 0.3 else None


def _weekend_mood(scope: Scope) -> Optional[str]:
    cte, params = _plays_cte(scope)
    rows = db.query(
        f"""{cte} SELECT CAST(strftime('%w',started_at,{LOCAL}) AS INTEGER) IN (0,6) AS weekend,
                  m.value AS mood, COUNT(*) AS n
            FROM p, json_each(p.moods) m GROUP BY weekend, mood""",
        params,
    )
    share = {0: Counter(), 1: Counter()}
    for r in rows:
        share[r["weekend"]][r["mood"]] += r["n"]
    tot = {k: sum(v.values()) for k, v in share.items()}
    if tot[0] < 20 or tot[1] < 20:
        return None
    diffs = {m: share[1][m] / tot[1] - share[0][m] / tot[0] for m in MOOD_DA}
    mood, diff = max(diffs.items(), key=lambda kv: abs(kv[1]))
    if abs(diff) < 0.05:
        return None
    side = "weekenden" if diff > 0 else "hverdagene"
    return f"I {side} hører du mere {MOOD_DA[mood]} musik ({round(abs(diff) * 100)} procentpoint mere)."


def mood_labels() -> dict:
    return MOOD_DA
