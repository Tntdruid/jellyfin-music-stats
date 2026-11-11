"""Backup collector for apps that never report what they are playing.

Some clients (Jellyfin Media Player, at times) don't send "now playing" updates, so the live
collector never sees them. They do still tell Jellyfin when a track was played to the end,
which bumps the track's PlayCount. Every couple of minutes we compare each user's recently
played tracks with the counts we saw last time and record the difference as plays, unless the
live collector already has them.

What we can't know here is how much of a track was heard, so these always count as full
listens and are stored with source='backup'.
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import db
import enrich
from collector import Collector, describe_error
from jellyfin import JellyfinClient, to_track

log = logging.getLogger("backup")

CHECK_EVERY = 90  # seconds
MAX_PER_TRACK = 10  # cap on plays recorded for one track in one check
DEFAULT_DURATION = 180  # used when Jellyfin doesn't know the track length
OVERLAP_SLACK = 120  # seconds of clock and timing slack when matching live plays


def parse_time(value: Optional[str]) -> Optional[int]:
    """Jellyfin dates are UTC with up to 7 fractional digits, e.g. 2026-11-06T13:56:28.1234567Z."""
    if not value:
        return None
    try:
        return int(datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
    except ValueError:
        return None


class BackupCollector:
    def __init__(self, client: JellyfinClient, collector: Collector):
        self.client = client
        self.collector = collector
        self.last_error: Optional[str] = None
        self.plays_recorded = 0

    async def run(self) -> None:
        await asyncio.sleep(30)  # give the live collector a head start after a restart
        while True:
            try:
                await self.check()
                self.last_error = None
            except Exception as e:
                self.last_error = describe_error(e)
                log.warning("backup check failed: %s", self.last_error)
            await asyncio.sleep(CHECK_EVERY)

    async def check(self) -> None:
        now = int(time.time())
        for user in await self.client.users():
            await self.check_user(user["Id"], user.get("Name"), now)

    async def check_user(self, user_id: str, user_name: Optional[str], now: int) -> None:
        items = await self.client.recently_played(user_id)
        started = db.query("SELECT since FROM backup_users WHERE user_id = ?", [user_id])
        if not started:
            # first look at this user: take today's counts as the baseline and record nothing,
            # otherwise their whole history would land as plays "just now"
            for item in items:
                self._remember(user_id, item)
            db.execute("INSERT INTO backup_users (user_id, since) VALUES (?, ?)", (user_id, now))
            log.info("backup-opsamler holder nu øje med %s", user_name or user_id)
            return

        since = started[0]["since"]
        seen = {
            r["item_id"]: r["play_count"]
            for r in db.query("SELECT item_id, play_count FROM seen_play_counts WHERE user_id = ?", [user_id])
        }
        for item in items:
            data = item.get("UserData") or {}
            count = data.get("PlayCount") or 0
            last_played = parse_time(data.get("LastPlayedDate"))
            previous = seen.get(item["Id"])
            if previous is None:
                # not among the recent tracks last time: new if it was played after we started watching
                new_plays = 1 if last_played and last_played > since else 0
            else:
                new_plays = count - previous
            if new_plays > 0 and last_played:
                self._record(user_id, user_name, item, min(new_plays, MAX_PER_TRACK), last_played)
            if previous != count:
                self._remember(user_id, item)

    def _remember(self, user_id: str, item: dict) -> None:
        count = (item.get("UserData") or {}).get("PlayCount") or 0
        db.execute(
            """INSERT INTO seen_play_counts (user_id, item_id, play_count) VALUES (?, ?, ?)
               ON CONFLICT(user_id, item_id) DO UPDATE SET play_count = excluded.play_count""",
            (user_id, item["Id"], count),
        )

    def _record(self, user_id: str, user_name: Optional[str], item: dict, plays: int, last_played: int) -> None:
        track = to_track(item)
        if track["item_id"] not in self.collector.known_tracks:
            db.upsert_track(track)
            self.collector.known_tracks.add(track["item_id"])
            enrich.queue(track["item_id"])

        if self._playing_live(user_id, track["item_id"]):
            return  # the live collector will save this one itself
        duration = track["duration"] or DEFAULT_DURATION
        # LastPlayedDate marks the latest play; earlier ones are assumed to come right before it
        for k in range(plays):
            ended = last_played - int(k * duration)
            started = ended - int(duration)
            if self._saved_live(user_id, track["item_id"], started, ended):
                continue
            db.insert_play({
                "item_id": track["item_id"], "user_id": user_id, "user_name": user_name,
                "client": None, "device": None, "started_at": started, "ended_at": ended,
                "listened": duration, "duration": track["duration"], "counted": 1, "source": "backup",
            })
            self.plays_recorded += 1
            log.info("fundet bagefter: '%s' (%s)", track["name"], user_name)

    def _playing_live(self, user_id: str, item_id: str) -> bool:
        return any(p.user_id == user_id and p.item_id == item_id for p in self.collector.state.active.values())

    @staticmethod
    def _saved_live(user_id: str, item_id: str, started: int, ended: int) -> bool:
        return bool(db.query(
            """SELECT 1 FROM plays WHERE user_id = ? AND item_id = ? AND source = 'live'
                 AND started_at <= ? AND ended_at >= ? LIMIT 1""",
            [user_id, item_id, ended + OVERLAP_SLACK, started - OVERLAP_SLACK],
        ))
