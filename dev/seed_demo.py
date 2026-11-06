"""Fill dev/data/music_stats.db with a year of fake listening so the dashboard can be tried without Jellyfin.

    DATA_DIR=dev/data python dev/seed_demo.py
"""
import os
import random
import sys
import time
from pathlib import Path

os.environ.setdefault("DATA_DIR", str(Path(__file__).parent / "data"))
sys.path.insert(0, str(Path(__file__).parent.parent / "jellyfin_music_stats" / "app"))

import db  # noqa: E402
from enrich import moods_from_genres, moods_from_tags  # noqa: E402

random.seed(7)

ARTISTS = [
    ("Nordlys", ["Indie Pop"], ["uplifting", "summer"]),
    ("Kvartet Mørke", ["Darkwave"], ["dark", "brooding"]),
    ("Sølvbølge", ["Ambient"], ["calm", "sleep"]),
    ("Brand & Bly", ["Metal"], ["aggressive"]),
    ("Disco Dorthe", ["Disco", "Dance"], ["party", "groovy"]),
    ("Regnvejr", ["Folk"], ["melancholic", "sad"]),
    ("Hjertebanken", ["Soul", "R&B"], ["romantic"]),
    ("Turbo Trio", ["Rock"], ["energetic"]),
    ("Lo-Fi Lars", ["Lo-Fi", "Hip Hop"], []),
    ("Jazzkatten", ["Jazz"], []),
    ("Nyt Navn", ["Electronic", "House"], ["dance"]),
]

db.connect()
db.execute("DELETE FROM plays")
db.execute("DELETE FROM tracks")

tracks = []
for ai, (artist, genres, tags) in enumerate(ARTISTS):
    for alb in range(2):
        album_id = f"alb{ai}x{alb}"
        for n in range(8):
            item_id = f"trk{ai}x{alb}x{n}"
            t = {
                "item_id": item_id, "name": f"{artist.split()[0]} sang {alb * 8 + n + 1}",
                "album": f"{artist} – Album {alb + 1}", "album_id": album_id, "album_artist": artist,
                "artists": [artist], "genres": genres, "tags": tags, "year": 2015 + ai,
                "duration": random.randint(150, 330), "fetched_at": int(time.time()),
            }
            db.upsert_track(t)
            moods = moods_from_tags(tags) or moods_from_genres(genres)
            db.set_moods(item_id, moods, "tags" if tags else "genre")
            tracks.append((ai, t))

now = time.time()
DAY = 86400
users = [("u1", "Christian"), ("u2", "Gæst")]
for day in range(400, -1, -1):
    if random.random() < 0.15:
        continue
    weekend = time.localtime(now - day * DAY).tm_wday >= 5
    for _ in range(random.randint(1, 3)):
        hour = random.choice([7, 8, 12, 17, 18, 19, 20, 21, 22] + ([10, 11, 14, 15, 23, 0] if weekend else []))
        t = now - day * DAY
        lt = time.localtime(t)
        t = t - (lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec) + hour * 3600 + random.randint(0, 3000)
        if t > now:
            continue
        uid, uname = users[0] if random.random() < 0.85 else users[1]
        # taste drifts over the year; "Nyt Navn" only appears in the last month
        weights = []
        for ai, _ in tracks:
            w = 1.0
            if ai == 10:
                w = 6 if day < 30 else 0
            elif ai == 3:
                w = 3 if day > 200 else 0.5
            elif ai == 4:
                w = 4 if weekend else 0.5
            elif ai == 2:
                w = 4 if hour in (23, 0, 7) else 0.7
            elif ai == 0:
                w = 3
            weights.append(w)
        for _ in range(random.randint(4, 18)):
            ai, tr = random.choices(tracks, weights)[0]
            skip = random.random() < (0.35 if ai == 7 else 0.1)
            listened = random.uniform(5, 40) if skip else tr["duration"] * random.uniform(0.85, 1)
            db.insert_play({
                "item_id": tr["item_id"], "user_id": uid, "user_name": uname, "client": "Finamp",
                "device": "Telefon", "started_at": int(t), "ended_at": int(t + listened),
                "listened": listened, "duration": tr["duration"], "counted": int(not skip),
            })
            t += listened + random.randint(0, 5)

print(db.query("SELECT COUNT(*) AS n FROM plays")[0]["n"], "plays seeded")
