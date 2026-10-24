"""FastAPI backend: analytics endpoints plus the in-process pipeline scheduler.

    uvicorn api.main:app --reload
"""

import logging
import os
import threading
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pipeline import analytics, db
from pipeline.config import DB_PATH, ROOT, SECTOR_NAMES
from pipeline.run import PipelineBusy, run_pipeline

log = logging.getLogger("api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

SCHEDULER_ENABLED = os.environ.get("SCHEDULER_ENABLED", "true").lower() != "false"
INTERVAL_MINUTES = int(os.environ.get("PIPELINE_INTERVAL_MINUTES", "60"))
PIPELINE_TOKEN = os.environ.get("PIPELINE_TOKEN")
DASHBOARD_DIR = ROOT / "dashboard" / "out"

scheduler = BackgroundScheduler(timezone="UTC")


def scheduled_run():
    try:
        run_pipeline("schedule")
    except PipelineBusy:
        log.info("scheduled run skipped: another run is in progress")
    except Exception:
        log.exception("scheduled pipeline run failed")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.connect(DB_PATH).close()  # make sure the schema exists before the first request
    if SCHEDULER_ENABLED:
        scheduler.add_job(
            scheduled_run, "interval", minutes=INTERVAL_MINUTES, id="pipeline", coalesce=True, max_instances=1
        )
        scheduler.start()
        log.info("scheduler on: pipeline runs every %d minutes", INTERVAL_MINUTES)
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="Tech Trend Sentiment Tracker API",
    version="1.0.0",
    description="Sentiment scores, trends and keyword breakdowns from tech and market news.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def get_conn():
    conn = db.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


Conn = Annotated[object, Depends(get_conn)]
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


def filters(
    start: str | None = Query(None, pattern=DATE_PATTERN, description="First day, YYYY-MM-DD (UTC)"),
    end: str | None = Query(None, pattern=DATE_PATTERN, description="Last day, YYYY-MM-DD (UTC)"),
    sector: str | None = Query(None, description="One of the sectors listed by /api/meta"),
    polarity: Literal["positive", "negative", "neutral"] | None = None,
    source: str | None = None,
) -> analytics.Filters:
    if sector and sector not in SECTOR_NAMES:
        raise HTTPException(422, f"unknown sector {sector!r}")
    return analytics.Filters(start=start, end=end, sector=sector, polarity=polarity, source=source)


F = Annotated[analytics.Filters, Depends(filters)]


@app.get("/api/health")
def health(conn: Conn):
    return {"status": "ok", "articles": conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]}


@app.get("/api/meta")
def meta(conn: Conn):
    """Date bounds, sectors, sources and the latest pipeline run."""
    return analytics.meta(conn)


@app.get("/api/summary")
def summary(conn: Conn, f: F):
    """Totals and average sentiment for the window, with the previous window for comparison."""
    return analytics.summary(conn, f)


@app.get("/api/sentiment/timeseries")
def timeseries(conn: Conn, f: F):
    """Daily average sentiment and volume, overall and per sector."""
    return analytics.timeseries(conn, f)


@app.get("/api/sectors")
def sectors(conn: Conn, f: F):
    """Volume and sentiment split per sector."""
    return analytics.sectors(conn, f)


@app.get("/api/keywords")
def keywords(conn: Conn, f: F, limit: int = Query(15, ge=1, le=50)):
    """Most-mentioned tracked terms with sentiment and momentum."""
    return analytics.keywords(conn, f, limit)


@app.get("/api/articles")
def articles(
    conn: Conn,
    f: F,
    q: str | None = Query(None, max_length=100),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """The processed data log, newest first."""
    return analytics.articles(conn, f, q, limit, offset)


@app.get("/api/pipeline/runs")
def runs(conn: Conn, limit: int = Query(20, ge=1, le=100)):
    return analytics.runs(conn, limit)


@app.get("/api/pipeline/schedule")
def schedule():
    job = scheduler.get_job("pipeline") if scheduler.running else None
    return {
        "enabled": bool(job),
        "interval_minutes": INTERVAL_MINUTES,
        "next_run_at": job.next_run_time.strftime("%Y-%m-%dT%H:%M:%SZ") if job and job.next_run_time else None,
    }


@app.post("/api/pipeline/run", status_code=202)
def trigger_run(x_pipeline_token: str | None = Header(None)):
    """Starts a pipeline run in the background. Set PIPELINE_TOKEN to require a matching X-Pipeline-Token header."""
    if PIPELINE_TOKEN and x_pipeline_token != PIPELINE_TOKEN:
        raise HTTPException(401, "missing or wrong X-Pipeline-Token")

    started = threading.Event()
    error: list[Exception] = []

    def worker():
        try:
            run_pipeline("manual", on_start=started.set)
        except PipelineBusy as exc:
            error.append(exc)
        except Exception:
            log.exception("manual pipeline run failed")
        finally:
            started.set()

    threading.Thread(target=worker, daemon=True).start()
    started.wait(10)
    if error:
        raise HTTPException(409, str(error[0]))
    return {"status": "started"}


# Serve the built dashboard (npm run build in dashboard/) from the same port.
if DASHBOARD_DIR.is_dir():
    app.mount("/", StaticFiles(directory=DASHBOARD_DIR, html=True), name="dashboard")
