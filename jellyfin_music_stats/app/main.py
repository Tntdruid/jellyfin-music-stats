import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import db
import stats
import views
from collector import Collector
from config import load_settings
from enrich import Enricher
from jellyfin import JellyfinClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # otherwise one line per poll
log = logging.getLogger("main")

settings = load_settings()
STATIC = Path(__file__).parent / "static"
state = {"collector": None, "client": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.connect()
    tasks = [asyncio.create_task(Enricher(settings.lastfm_api_key).run())]
    if settings.collector_enabled:
        client = JellyfinClient(settings.jellyfin_url, settings.api_key)
        collector = Collector(settings, client)
        state.update(client=client, collector=collector)
        tasks.append(asyncio.create_task(collector.run()))
        log.info("collecting from %s every %ss", settings.jellyfin_url, settings.poll_interval)
    else:
        log.warning("jellyfin_url/api_key not set - collector disabled, serving existing data only")
    yield
    for t in tasks:
        t.cancel()
    if state["collector"]:
        state["collector"].flush()
        await state["client"].close()


app = FastAPI(lifespan=lifespan)


def scope(start: Optional[int], end: Optional[int], user: Optional[str]) -> stats.Scope:
    return stats.Scope(start or 0, end or int(time.time()) + 60, user or None)


@app.get("/api/meta")
def meta():
    c = state["collector"]
    return {
        "users": stats.users(),
        "first_play": stats.first_play(),
        "moods": stats.mood_labels(),
        "collector": {
            "enabled": settings.collector_enabled,
            "last_poll": c.state.last_poll if c else None,
            "last_error": c.state.last_error if c else None,
            "lastfm": bool(settings.lastfm_api_key),
        },
    }


@app.get("/api/now")
def now_playing():
    c = state["collector"]
    return c.now_playing() if c else []


@app.get("/api/latest")
def latest():
    """Cheap change marker; the page polls it and reloads its data when it moves."""
    row = db.query("SELECT MAX(id) AS play, (SELECT COUNT(*) FROM tracks WHERE moods IS NOT NULL) AS enriched FROM plays")[0]
    return {"marker": f"{row['play']}-{row['enriched']}"}


@app.get("/api/summary")
def summary(start: Optional[int] = None, end: Optional[int] = None, user: Optional[str] = None):
    return stats.summary(scope(start, end, user))


@app.get("/api/timeline")
def timeline(start: Optional[int] = None, end: Optional[int] = None, user: Optional[str] = None,
             bucket: str = Query("day", pattern="^(day|week|month)$")):
    return stats.timeline(scope(start, end, user), bucket)


@app.get("/api/top")
def top(start: Optional[int] = None, end: Optional[int] = None, user: Optional[str] = None,
        kind: str = Query("artists", pattern="^(artists|albums|tracks)$"), limit: int = Query(10, le=100)):
    return stats.top(scope(start, end, user), kind, limit)


@app.get("/api/genres")
def genres(start: Optional[int] = None, end: Optional[int] = None, user: Optional[str] = None,
           bucket: str = Query("month", pattern="^(day|week|month)$")):
    return stats.genres(scope(start, end, user), bucket)


@app.get("/api/moods")
def moods(start: Optional[int] = None, end: Optional[int] = None, user: Optional[str] = None,
          bucket: str = Query("month", pattern="^(day|week|month)$")):
    return stats.moods(scope(start, end, user), bucket)


@app.get("/api/heatmap")
def heatmap(start: Optional[int] = None, end: Optional[int] = None, user: Optional[str] = None):
    return stats.heatmap(scope(start, end, user))


@app.get("/api/recent")
def recent(start: Optional[int] = None, end: Optional[int] = None, user: Optional[str] = None):
    return stats.recent(scope(start, end, user))


@app.get("/api/insights")
def insights(start: Optional[int] = None, end: Optional[int] = None, user: Optional[str] = None):
    return stats.insights(scope(start, end, user))


@app.get("/api/detail")
def detail(key: str, kind: str = Query(pattern="^(artist|album|track)$"),
           start: Optional[int] = None, end: Optional[int] = None, user: Optional[str] = None):
    data = views.detail(scope(start, end, user), kind, key)
    if not data:
        raise HTTPException(404, "Ingen lytninger i perioden")
    return data


@app.get("/api/wrapped")
def wrapped(year: Optional[int] = None, user: Optional[str] = None):
    years = views.wrapped_years()
    year = year or (years[0] if years else datetime.now().year)
    return {"years": years, **views.wrapped(year, user or None)}


@app.get("/api/compare")
def compare(start: Optional[int] = None, end: Optional[int] = None):
    return views.compare(scope(start, end, None))


@app.get("/api/export.csv")
def export(start: Optional[int] = None, end: Optional[int] = None, user: Optional[str] = None):
    filename = f"musikstatistik-{datetime.now():%Y-%m-%d}.csv"
    return Response(views.export_csv(scope(start, end, user)), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/api/image/{item_id}")
async def image(item_id: str):
    if not state["client"] or not item_id.isalnum():
        raise HTTPException(404)
    r = await state["client"].image(item_id)
    if not r:
        raise HTTPException(404)
    return Response(r.content, media_type=r.headers.get("content-type", "image/jpeg"),
                    headers={"Cache-Control": "public, max-age=604800"})


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
