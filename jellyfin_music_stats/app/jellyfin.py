import time
from typing import Optional

import httpx

TICKS_PER_SECOND = 10_000_000


class JellyfinClient:
    def __init__(self, base_url: str, api_key: str):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                # the standard scheme; newer Jellyfin versions can reject the legacy X-Emby-Token header
                "Authorization": (
                    'MediaBrowser Client="Jellyfin Music Stats", Device="Home Assistant", '
                    f'DeviceId="jellyfin-music-stats", Version="0.1", Token="{api_key}"'
                ),
                "X-Emby-Token": api_key,
                "Accept": "application/json",
            },
            timeout=15,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def sessions(self) -> list:
        r = await self.client.get("/Sessions")
        r.raise_for_status()
        return r.json()

    async def track(self, item_id: str, user_id: Optional[str]) -> Optional[dict]:
        params = {
            "ids": item_id,
            "fields": "Genres,Tags,ProductionYear",
            "enableImages": "false",
        }
        if user_id:
            params["userId"] = user_id
        r = await self.client.get("/Items", params=params)
        r.raise_for_status()
        items = r.json().get("Items", [])
        return to_track(items[0]) if items else None

    async def image(self, item_id: str, max_width: int = 300) -> Optional[httpx.Response]:
        r = await self.client.get(
            f"/Items/{item_id}/Images/Primary", params={"maxWidth": max_width, "quality": 85}
        )
        return r if r.status_code == 200 else None


def to_track(item: dict) -> dict:
    ticks = item.get("RunTimeTicks") or 0
    artists = item.get("Artists") or ([item["AlbumArtist"]] if item.get("AlbumArtist") else [])
    return {
        "item_id": item["Id"],
        "name": item.get("Name") or "Ukendt",
        "album": item.get("Album"),
        "album_id": item.get("AlbumId"),
        "album_artist": item.get("AlbumArtist"),
        "artists": artists,
        "genres": item.get("Genres") or [],
        "tags": item.get("Tags") or [],
        "year": item.get("ProductionYear"),
        "duration": ticks / TICKS_PER_SECOND if ticks else None,
        "fetched_at": int(time.time()),
    }
