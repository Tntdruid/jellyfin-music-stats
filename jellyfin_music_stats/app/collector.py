"""Polls Jellyfin's /Sessions and turns what it sees into play records.

Jellyfin keeps no listening history of its own, so every poll we compare the
sessions against what was playing last time. Listening time is measured as
wall-clock time while not paused, which stays correct when people seek.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

import httpx

import db
import enrich
from config import Settings
from jellyfin import TICKS_PER_SECOND, JellyfinClient, to_track

log = logging.getLogger("collector")

SCROBBLE_CAP = 240  # like Last.fm: 4 minutes always counts, however long the track
MIN_LISTEN = 30  # tracks shorter than this still need this much to count


@dataclass
class ActivePlay:
    item_id: str
    user_id: Optional[str]
    user_name: Optional[str]
    client: Optional[str]
    device: Optional[str]
    name: str
    artists: list
    duration: Optional[float]
    started_at: float
    last_seen: float
    position: float = 0.0
    paused: bool = False
    listened: float = 0.0
    album_id: Optional[str] = None


def describe_error(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        if e.response.status_code in (401, 403):
            return "Jellyfin afviste API-nøglen – tjek api_key i add-on'ets konfiguration"
        return f"Jellyfin svarede {e.response.status_code}"
    if isinstance(e, httpx.ConnectError):
        return f"Kan ikke forbinde til Jellyfin – tjek jellyfin_url ({e})"
    if isinstance(e, httpx.TimeoutException):
        return "Jellyfin svarer ikke (timeout)"
    return str(e)


@dataclass
class CollectorState:
    active: Dict[str, ActivePlay] = field(default_factory=dict)
    last_poll: Optional[float] = None
    last_error: Optional[str] = None
    plays_recorded: int = 0


class Collector:
    def __init__(self, settings: Settings, client: JellyfinClient):
        self.settings = settings
        self.client = client
        self.state = CollectorState()
        self.known_tracks = {r["item_id"] for r in db.query("SELECT item_id FROM tracks")}

    async def run(self) -> None:
        while True:
            try:
                await self.poll()
                self.state.last_error = None
            except Exception as e:  # keep polling; Jellyfin may just be restarting
                self.state.last_error = describe_error(e)
                log.warning("poll failed: %s", self.state.last_error)
            await asyncio.sleep(self.settings.poll_interval)

    async def poll(self) -> None:
        now = time.time()
        sessions = await self.client.sessions()
        self.state.last_poll = now
        seen = set()

        for s in sessions:
            item = s.get("NowPlayingItem")
            if not item or item.get("Type") != "Audio":
                continue
            sid = s["Id"]
            seen.add(sid)
            play_state = s.get("PlayState") or {}
            position = (play_state.get("PositionTicks") or 0) / TICKS_PER_SECOND
            paused = bool(play_state.get("IsPaused"))

            current = self.state.active.get(sid)
            if current and current.item_id == item["Id"] and not self._restarted(current, position):
                if not current.paused:
                    current.listened += min(now - current.last_seen, self.settings.poll_interval * 3)
                current.position, current.paused, current.last_seen = position, paused, now
                continue

            if current:
                self._finish(current, now)
            track = to_track(item)
            self.state.active[sid] = ActivePlay(
                item_id=item["Id"],
                user_id=s.get("UserId"),
                user_name=s.get("UserName"),
                client=s.get("Client"),
                device=s.get("DeviceName"),
                name=track["name"],
                artists=track["artists"],
                album_id=track["album_id"],
                duration=track["duration"],
                started_at=now - min(position, self.settings.poll_interval),
                last_seen=now,
                position=position,
                paused=paused,
                listened=0.0 if paused else min(position, self.settings.poll_interval),
            )
            if item["Id"] not in self.known_tracks:
                await self._fetch_track(item["Id"], s.get("UserId"), fallback=track)

        for sid in list(self.state.active):
            if sid not in seen:
                self._finish(self.state.active.pop(sid), now)

    def flush(self) -> None:
        now = time.time()
        for play in self.state.active.values():
            self._finish(play, now)
        self.state.active.clear()

    @staticmethod
    def _restarted(play: ActivePlay, position: float) -> bool:
        """Same track again on repeat: position jumped back to the start after nearly finishing."""
        return bool(play.duration) and position < 15 and play.position > play.duration * 0.8

    def _finish(self, play: ActivePlay, now: float) -> None:
        if not play.paused:
            play.listened += min(now - play.last_seen, self.settings.poll_interval)
        listened = min(play.listened, play.duration) if play.duration else play.listened
        if listened < 3:
            return
        needed = SCROBBLE_CAP
        if play.duration:
            needed = min(play.duration * self.settings.min_play_percent / 100, SCROBBLE_CAP)
            needed = max(needed, min(MIN_LISTEN, play.duration * 0.9))
        db.insert_play({
            "item_id": play.item_id,
            "user_id": play.user_id,
            "user_name": play.user_name,
            "client": play.client,
            "device": play.device,
            "started_at": int(play.started_at),
            "ended_at": int(now),
            "listened": round(listened, 1),
            "duration": play.duration,
            "counted": int(listened >= needed),
        })
        self.state.plays_recorded += 1

    async def _fetch_track(self, item_id: str, user_id: Optional[str], fallback: dict) -> None:
        try:
            track = await self.client.track(item_id, user_id) or fallback
        except Exception as e:
            log.warning("could not fetch item %s: %s", item_id, e)
            track = fallback
        db.upsert_track(track)
        self.known_tracks.add(item_id)
        enrich.queue(item_id)

    def now_playing(self) -> list:
        return [
            {
                "item_id": p.item_id,
                "name": p.name,
                "artists": p.artists,
                "album_id": p.album_id,
                "user_name": p.user_name,
                "device": p.device,
                "position": p.position,
                "duration": p.duration,
                "paused": p.paused,
            }
            for p in self.state.active.values()
        ]
