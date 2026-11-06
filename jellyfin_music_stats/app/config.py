"""Settings come from Home Assistant's /data/options.json, with env vars as fallback for local dev."""
import json
import os
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
# The add-on's public config folder (map: addon_config), visible as addon_configs/<slug> over Samba.
# Falls back to DATA_DIR when it isn't mounted, e.g. in local development.
DB_DIR = Path(os.environ.get("DB_DIR") or ("/config" if os.path.isdir("/config") else DATA_DIR))


@dataclass
class Settings:
    jellyfin_url: str = ""
    api_key: str = ""
    poll_interval: int = 10
    min_play_percent: int = 50
    lastfm_api_key: str = ""

    @property
    def collector_enabled(self) -> bool:
        return bool(self.jellyfin_url and self.api_key)


def load_settings() -> Settings:
    options = {}
    options_file = DATA_DIR / "options.json"
    if options_file.exists():
        options = json.loads(options_file.read_text(encoding="utf-8"))

    def pick(key, default):
        return options.get(key) or os.environ.get(key.upper()) or default

    return Settings(
        jellyfin_url=str(pick("jellyfin_url", "")).rstrip("/"),
        api_key=str(pick("api_key", "")).strip(),
        poll_interval=int(pick("poll_interval", 10)),
        min_play_percent=int(pick("min_play_percent", 50)),
        lastfm_api_key=str(pick("lastfm_api_key", "")).strip(),
    )
