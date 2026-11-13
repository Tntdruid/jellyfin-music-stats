"""Checks that run on every push, so a broken version never reaches Home Assistant's store.

Jellyfin is replaced by small fakes that answer like the real API.
"""
import asyncio
import json
import sqlite3
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import backup
import collector
import db
import genres
import images
import main
from config import Settings, parse_user_map

T = 10_000_000


@pytest.fixture(scope="module")
def client():
    with TestClient(main.app) as c:
        yield c


ENDPOINTS = [
    "meta", "now", "latest", "summary", "timeline?bucket=day", "timeline?bucket=week", "timeline?bucket=month",
    "top?kind=artists", "top?kind=albums", "top?kind=tracks", "genres", "moods", "heatmap", "recent", "insights",
    "compare", "wrapped", "wrapped?year=2025&user=u2", "export.csv",
    "detail?kind=artist&key=Nordlys&start=0", "detail?kind=album&key=alb0x1&start=0",
    "detail?kind=track&key=trk0x1x1&start=0",
]


@pytest.mark.parametrize("path", ENDPOINTS)
def test_endpoint_answers(client, path):
    r = client.get(f"/api/{path}")
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("rng", [0, 7, 30, 365])
def test_every_range_works_for_every_user(client, rng):
    start = 0 if not rng else int(datetime.now().timestamp()) - rng * 86400
    for user in ("", "u1", "u2"):
        for path in ("summary", "insights", "top?kind=artists", "moods?bucket=week"):
            sep = "&" if "?" in path else "?"
            assert client.get(f"/api/{path}{sep}start={start}&user={user}").status_code == 200


def test_page_and_assets(client):
    assert "Musikstatistik" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200


def test_unknown_detail_is_404(client):
    assert client.get("/api/detail?kind=track&key=nope&start=0").status_code == 404


def test_track_page_lists_tracks_played_next(client):
    d = client.get("/api/detail?kind=track&key=trk0x1x1&start=0").json()
    assert d["album"]["id"] == "alb0x1" and d["top_tracks"] and not d["top_albums"]


def test_csv_export_opens_in_danish_excel(client):
    text = client.get("/api/export.csv?start=0").text
    assert text.startswith("﻿tidspunkt;bruger;titel")


# --- who is looking ---------------------------------------------------------

@pytest.mark.parametrize("headers, expected", [
    ({}, None),
    ({"X-Remote-User-Name": "christian"}, "u1"),
    ({"X-Remote-User-Name": "chris"}, "u2"),  # via USER_MAP in conftest
    ({"X-Remote-User-Name": "nobody"}, None),
])
def test_ha_user_is_matched_to_jellyfin_user(client, headers, expected):
    assert client.get("/api/meta", headers=headers).json()["me"]["jellyfin_user"] == expected


def test_user_map_parsing():
    assert parse_user_map(["Chris = Tntdruid", "broken", "=x", ""]) == {"chris": "tntdruid"}


# --- live collector ---------------------------------------------------------

def session(item_id, pos, paused=False):
    return [{"Id": "s1", "UserId": "tu", "UserName": "Test", "Client": "Finamp", "DeviceName": "Telefon",
             "NowPlayingItem": {"Id": item_id, "Type": "Audio", "Name": f"Sang {item_id}", "Artists": ["Testkunstner"],
                                "AlbumId": "talb", "RunTimeTicks": 200 * T},
             "PlayState": {"PositionTicks": int(pos * T), "IsPaused": paused}}]


class FakeSessions:
    def __init__(self, polls):
        self.polls = polls

    async def sessions(self):
        return self.polls.pop(0)

    async def track(self, item_id, user_id):
        return None

    async def image(self, item_id):
        return None


def run_polls(polls):
    c = collector.Collector(Settings(poll_interval=10), FakeSessions(polls))
    now = [1_700_000_000.0]
    real = collector.time.time
    collector.time.time = lambda: now[0]
    try:
        async def go():
            while c.client.polls:
                await c.poll()
                now[0] += 10
            await asyncio.sleep(0.05)
        asyncio.run(go())
    finally:
        collector.time.time = real


def plays_of(item_id):
    return db.query("SELECT ROUND(listened) AS l, counted FROM plays WHERE item_id = ? ORDER BY id", [item_id])


def test_pause_is_not_counted_and_skip_and_repeat_are_detected():
    # ta: 200 s played with a 60 s pause; tb skipped after ~20 s; then ta again on repeat
    polls = ([session("ta", 0)] + [session("ta", 10 * i) for i in range(1, 6)] + [session("ta", 50, True)] * 6
             + [session("ta", 50 + 10 * i) for i in range(1, 16)] + [session("tb", 5), session("tb", 15), session("ta", 5)]
             + [session("ta", 5 + 10 * i) for i in range(1, 20)] + [session("ta", 3)] + [[]])
    run_polls(polls)
    assert plays_of("ta") == [{"l": 200, "counted": 1}, {"l": 200, "counted": 1}, {"l": 13, "counted": 0}]
    assert plays_of("tb") == [{"l": 25, "counted": 0}]


def test_quick_skip_is_stored_as_skip():
    run_polls([session("tpeek", 0), []])  # seen once, then gone: a skip, which feeds the skip rate
    assert plays_of("tpeek") == [{"l": 10, "counted": 0}]


# --- backup collector -------------------------------------------------------

def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.1234567Z")


def jf_item(i, count, last):
    return {"Id": i, "Type": "Audio", "Name": f"Sang {i}", "Artists": ["Backupkunstner"], "AlbumId": "balb",
            "RunTimeTicks": 200 * T, "UserData": {"PlayCount": count, "LastPlayedDate": iso(last) if last else None}}


class FakeLibrary:
    items = []

    async def recently_played(self, user_id, limit=50):
        return self.items

    async def image(self, item_id):
        return None


def test_backup_collector_finds_silent_plays_without_doubles():
    jf = FakeLibrary()
    live = collector.Collector(Settings(poll_interval=10), jf)
    b = backup.BackupCollector(jf, live)
    t0 = 1_750_000_000
    t1 = t0 + 600

    async def go():
        jf.items = [jf_item("bA", 5, t0 - 3600), jf_item("bB", 2, t0 - 7200), jf_item("bC", 1, t0 - 9000),
                    jf_item("bF", 1, t0 - 5000)]
        await b.check_user("bu", "Backup", t0)  # baseline: nothing recorded
        assert not db.query("SELECT 1 FROM plays WHERE user_id = 'bu'")

        # bB was seen live on the phone; bF is still playing live
        db.insert_play({"item_id": "bB", "user_id": "bu", "user_name": "Backup", "client": "Android", "device": "Tlf",
                        "started_at": t1 - 205, "ended_at": t1 - 3, "listened": 200, "duration": 200, "counted": 1})
        live.state.active["s"] = collector.ActivePlay("bF", "bu", "Backup", "JMP", "PC", "Sang bF", [], 200, t1 - 190, t1)
        jf.items = [jf_item("bD", 1, t1 - 100), jf_item("bA", 6, t1 - 300), jf_item("bB", 3, t1),
                    jf_item("bC", 3, t1 - 50), jf_item("bF", 2, t1), jf_item("bE", 4, t0 - 86400)]
        await b.check_user("bu", "Backup", t1)
        live.state.active.clear()
        await b.check_user("bu", "Backup", t1 + 90)  # nothing changed since: nothing new
        await asyncio.sleep(0.05)

    asyncio.run(go())
    rows = db.query("SELECT item_id, source, COUNT(*) AS n FROM plays WHERE user_id = 'bu' GROUP BY item_id, source")
    assert {(r["item_id"], r["source"]): r["n"] for r in rows} == {
        ("bA", "backup"): 1, ("bB", "live"): 1, ("bC", "backup"): 2, ("bD", "backup"): 1}
    assert db.query("SELECT 1 FROM tracks WHERE item_id = 'bD'")


def test_parse_jellyfin_time():
    assert backup.parse_time("2026-11-06T13:56:28.1234567Z") == 1793973388
    assert backup.parse_time(None) is None and backup.parse_time("garbage") is None


# --- database -----------------------------------------------------------------

def test_old_database_gets_new_columns(tmp_path, monkeypatch):
    path = tmp_path / "music_stats.db"
    old = sqlite3.connect(path)
    old.execute("""CREATE TABLE plays (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT NOT NULL, user_id TEXT,
                   user_name TEXT, client TEXT, device TEXT, started_at INTEGER NOT NULL, ended_at INTEGER NOT NULL,
                   listened REAL NOT NULL, duration REAL, counted INTEGER NOT NULL)""")
    old.execute("INSERT INTO plays (item_id, started_at, ended_at, listened, counted) VALUES ('x', 1, 2, 1, 1)")
    old.commit()
    old.close()
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "_conn", None)
    assert db.query("SELECT source FROM plays") == [{"source": "live"}]
    db._conn.close()


def test_database_moves_from_private_data_folder(tmp_path, monkeypatch):
    data, cfg = tmp_path / "data", tmp_path / "config"
    data.mkdir()
    old = sqlite3.connect(data / "music_stats.db")
    old.execute("CREATE TABLE marker (x)")
    old.commit()
    old.close()
    monkeypatch.setattr(db, "DATA_DIR", data)
    monkeypatch.setattr(db, "DB_DIR", cfg)
    monkeypatch.setattr(db, "_conn", None)
    db.connect()
    assert (cfg / "music_stats.db").exists() and not (data / "music_stats.db").exists()
    assert db.query("SELECT name FROM sqlite_master WHERE name = 'marker'")
    db._conn.close()


# --- images -----------------------------------------------------------------

class FakeImages:
    def __init__(self):
        self.gone = False

    async def image(self, item_id):
        if self.gone:
            return None
        return type("R", (), {"content": b"img-" + item_id.encode(), "headers": {"content-type": "image/webp"}})()


def test_cover_survives_deletion():
    fake = FakeImages()
    assert asyncio.run(images.get(fake, "timg1")).read_bytes() == b"img-timg1"
    fake.gone = True
    assert asyncio.run(images.get(fake, "timg1")).name == "timg1.webp"
    assert asyncio.run(images.get(None, "timg1")) is not None  # Jellyfin not configured at all


def test_image_endpoint_serves_cached_cover(client):
    asyncio.run(images.get(FakeImages(), "timg2"))
    r = client.get("/api/image/timg2")
    assert r.status_code == 200 and r.content == b"img-timg2"
    assert client.get("/api/image/missing").status_code == 404


# --- genres -----------------------------------------------------------------

def test_genre_spellings_are_merged_and_mapped():
    base = {"name": "x", "album": None, "album_id": None, "album_artist": None, "artists": ["G"], "tags": [],
            "year": None, "duration": 100, "fetched_at": 0}
    tagged = [["Synth-Pop"], ["synth pop"], ["Synth-Pop", "Alternative"], ["Alternativ"], ["Alternativ"]]
    for i, g in enumerate(tagged):
        db.upsert_track({**base, "item_id": f"tg{i}", "genres": g})

    def stored():
        rows = db.query("SELECT item_id, genres, genres_raw FROM tracks WHERE item_id LIKE 'tg%'")
        return {r["item_id"]: (json.loads(r["genres"]), json.loads(r["genres_raw"])) for r in rows}

    genres.rebuild()
    assert stored()["tg1"][0] == ["Synth-Pop"]  # case and hyphen merged; the most used spelling wins
    assert ("Alternative", "Alternativ") in genres.suggestions()

    genres.configure(["alternative = Alternativ"])
    try:
        genres.rebuild()  # a new genre_map is applied to tracks already in the database
        merged, raw = stored()["tg2"]
        assert merged == ["Synth-Pop", "Alternativ"] and raw == ["Synth-Pop", "Alternative"]
        assert ("Alternative", "Alternativ") not in genres.suggestions()
    finally:
        genres.configure([])
        genres.rebuild()
    assert stored()["tg2"][0] == ["Synth-Pop", "Alternative"]  # and removing it brings the original back


def test_genre_map_parsing():
    assert genres.parse_map(["Hip_Hop=Hip-Hop", "broken", "=x", ""]) == {"hip hop": "Hip-Hop"}
