"""Writes the static snapshot the GitHub Pages dashboard reads instead of the API."""

import json
from datetime import datetime, timezone
from pathlib import Path

from . import analytics, db
from .config import DB_PATH, SNAPSHOT_PATH

SNAPSHOT_SUMMARY_LIMIT = 180
FIELDS = [
    "id", "source", "title", "summary", "url", "published_at", "sector", "sentiment",
    "polarity", "engagement", "comments", "keywords",
]


def build_snapshot(conn) -> dict:
    """Every stored article (the database only keeps RETENTION_DAYS), plus meta and the run log."""
    meta = analytics.meta(conn)
    rows = []
    if meta["last_date"]:
        everything = analytics.Filters(start=meta["first_date"], end=meta["last_date"])
        rows = analytics.articles(conn, everything, limit=1_000_000)["items"]
    for row in rows:
        if len(row["summary"]) > SNAPSHOT_SUMMARY_LIMIT:
            row["summary"] = row["summary"][:SNAPSHOT_SUMMARY_LIMIT].rsplit(" ", 1)[0] + "…"
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "meta": meta,
        "runs": analytics.runs(conn, 50),
        # Column-oriented so the field names aren't repeated 10,000 times.
        "articles": {"fields": FIELDS, "rows": [[row[f] for f in FIELDS] for row in rows]},
    }


def write_snapshot(db_path=DB_PATH, out: Path = SNAPSHOT_PATH) -> tuple[Path, int]:
    conn = db.connect(db_path)
    try:
        snapshot = build_snapshot(conn)
    finally:
        conn.close()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return out, len(snapshot["articles"]["rows"])
