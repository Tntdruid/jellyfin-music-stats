import time
from typing import Optional
from urllib.parse import quote

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

    async def users(self) -> list:
        r = await self.client.get("/Users")
        r.raise_for_status()
        return r.json()

    async def recently_played(self, user_id: str, limit: int = 50) -> list:
        """The user's most recently played tracks, with their UserData (PlayCount, LastPlayedDate)."""
        r = await self.client.get("/Items", params={
            "userId": user_id,
            "includeItemTypes": "Audio",
            "recursive": "true",
            "filters": "IsPlayed",
            "sortBy": "DatePlayed",
            "sortOrder": "Descending",
            "limit": limit,
            "fields": "Genres,Tags,ProductionYear",
            "enableUserData": "true",
            "enableImages": "false",
        })
        r.raise_for_status()
        return r.json().get("Items", [])

    async def artist_tracks(self, name: str, user_id: Optional[str]) -> Optional[list]:
        """Every track in the library that the artist appears on, oldest album first; None if Jellyfin
        doesn't know the artist. With a user, each track carries that user's UserData (Played, PlayCount)."""
        user = {"userId": user_id} if user_id else {}
        r = await self.client.get(f"/Artists/{quote(name, safe='')}", params=user)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        r = await self.client.get("/Items", params={
            **user,
            "artistIds": r.json()["Id"],
            "includeItemTypes": "Audio",
            "recursive": "true",
            "sortBy": "ProductionYear,Album,ParentIndexNumber,IndexNumber,SortName",
            "fields": "ProductionYear",
            "enableUserData": "true" if user_id else "false",
            "enableImages": "false",
        })
        r.raise_for_status()
        return r.json().get("Items", [])

    async def album_tracks(self, album_id: str, user_id: Optional[str]) -> Optional[list]:
        """The album's tracks in disc and track order; None if Jellyfin doesn't have the album any more."""
        user = {"userId": user_id} if user_id else {}
        r = await self.client.get("/Items", params={
            **user,
            "parentId": album_id,
            "includeItemTypes": "Audio",
            "recursive": "true",
            "sortBy": "ParentIndexNumber,IndexNumber,SortName",
            "enableUserData": "true" if user_id else "false",
            "enableImages": "false",
        })
        if r.status_code in (400, 404):
            return None
        r.raise_for_status()
        return r.json().get("Items", []) or None

    async def library_tracks(self, user_id: Optional[str]) -> list:
        """Every track in the music libraries, with when it was added."""
        user = {"userId": user_id} if user_id else {}
        r = await self.client.get("/Items", params={
            **user,
            "includeItemTypes": "Audio",
            "recursive": "true",
            "fields": "DateCreated,ProductionYear",
            "enableUserData": "true" if user_id else "false",
            "enableImages": "false",
        }, timeout=60)
        r.raise_for_status()
        return r.json().get("Items", [])

    # --- playlists (written by the smart playlists) ---

    async def playlist_exists(self, playlist_id: str, user_id: str) -> bool:
        r = await self.client.get("/Items", params={"ids": playlist_id, "userId": user_id, "enableImages": "false"})
        r.raise_for_status()
        return bool(r.json().get("Items"))

    async def playlist_track_ids(self, playlist_id: str, user_id: str) -> list:
        r = await self.client.get(f"/Playlists/{playlist_id}/Items", params={"userId": user_id, "enableImages": "false"})
        r.raise_for_status()
        return [it["Id"] for it in r.json().get("Items", [])]

    async def create_playlist(self, name: str, user_id: str, ids: list) -> str:
        r = await self.client.post("/Playlists", json={
            "Name": name, "Ids": ids, "UserId": user_id, "MediaType": "Audio", "IsPublic": False,
        })
        r.raise_for_status()
        return r.json()["Id"]

    async def update_playlist(self, playlist_id: str, name: str, ids: list) -> bool:
        """Replace name and tracks in one go; False on Jellyfin versions without this endpoint (before 10.9)."""
        r = await self.client.post(f"/Playlists/{playlist_id}", json={"Name": name, "Ids": ids})
        if r.status_code in (404, 405):
            return False
        r.raise_for_status()
        return True

    async def delete_item(self, item_id: str) -> None:
        r = await self.client.delete(f"/Items/{item_id}")
        if r.status_code != 404:
            r.raise_for_status()

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
        "genres": [g.strip() for g in item.get("Genres") or [] if g.strip()],
        "tags": item.get("Tags") or [],
        "year": item.get("ProductionYear"),
        "duration": ticks / TICKS_PER_SECOND if ticks else None,
        "fetched_at": int(time.time()),
    }
