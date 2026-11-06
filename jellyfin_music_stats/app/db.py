import json
import sqlite3
import threading
from typing import Optional

from config import DATA_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks (
    item_id      TEXT PRIMARY KEY,
    name         TEXT,
    album        TEXT,
    album_id     TEXT,
    album_artist TEXT,
    artists      TEXT NOT NULL DEFAULT '[]',  -- JSON list
    genres       TEXT NOT NULL DEFAULT '[]',  -- JSON list
    tags         TEXT NOT NULL DEFAULT '[]',  -- JSON list
    moods        TEXT,                        -- JSON list, NULL = not enriched yet
    mood_source  TEXT,
    year         INTEGER,
    duration     REAL,
    fetched_at   INTEGER
);

CREATE TABLE IF NOT EXISTS plays (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id    TEXT NOT NULL,
    user_id    TEXT,
    user_name  TEXT,
    client     TEXT,
    device     TEXT,
    started_at INTEGER NOT NULL,  -- unix seconds, UTC
    ended_at   INTEGER NOT NULL,
    listened   REAL NOT NULL,     -- seconds actually played (pauses excluded)
    duration   REAL,              -- track length in seconds
    counted    INTEGER NOT NULL   -- 1 = real listen, 0 = skip
);

CREATE INDEX IF NOT EXISTS idx_plays_started ON plays(started_at);
CREATE INDEX IF NOT EXISTS idx_plays_item ON plays(item_id);
CREATE INDEX IF NOT EXISTS idx_plays_user ON plays(user_id);
"""

_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


def connect() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(DATA_DIR / "music_stats.db", check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.executescript(SCHEMA)
    return _conn


def query(sql: str, params=()) -> list:
    with _lock:
        return [dict(r) for r in connect().execute(sql, params).fetchall()]


def execute(sql: str, params=()) -> None:
    with _lock:
        conn = connect()
        conn.execute(sql, params)
        conn.commit()


def upsert_track(t: dict) -> None:
    execute(
        """INSERT INTO tracks (item_id, name, album, album_id, album_artist, artists, genres, tags,
                               year, duration, fetched_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(item_id) DO UPDATE SET
               name=excluded.name, album=excluded.album, album_id=excluded.album_id,
               album_artist=excluded.album_artist, artists=excluded.artists, genres=excluded.genres,
               tags=excluded.tags, year=excluded.year, duration=excluded.duration,
               fetched_at=excluded.fetched_at""",
        (
            t["item_id"], t["name"], t["album"], t["album_id"], t["album_artist"],
            json.dumps(t["artists"]), json.dumps(t["genres"]), json.dumps(t["tags"]),
            t["year"], t["duration"], t["fetched_at"],
        ),
    )


def set_moods(item_id: str, moods: list, source: str) -> None:
    execute("UPDATE tracks SET moods=?, mood_source=? WHERE item_id=?", (json.dumps(moods), source, item_id))


def insert_play(p: dict) -> None:
    execute(
        """INSERT INTO plays (item_id, user_id, user_name, client, device, started_at, ended_at,
                              listened, duration, counted)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            p["item_id"], p["user_id"], p["user_name"], p["client"], p["device"],
            p["started_at"], p["ended_at"], p["listened"], p["duration"], p["counted"],
        ),
    )
