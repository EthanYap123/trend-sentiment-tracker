"""Runs the ETL pipeline once: extract -> transform -> load, logged to pipeline_runs.

    python -m pipeline.run                  # incremental run (last 2 days)
    python -m pipeline.run --backfill 30    # first run: pull 30 days of history
    python -m pipeline.run --export         # also write the dashboard's static snapshot
"""

import argparse
import logging
import threading
from datetime import datetime, timedelta, timezone

from . import db
from .config import DB_PATH, RSS_FEEDS
from .sources import extract
from .transform import transform

log = logging.getLogger("pipeline")

# Hacker News points and comment counts keep growing for a day or two, so each
# incremental run re-reads that window to refresh them.
INCREMENTAL_DAYS = 2
_lock = threading.Lock()


class PipelineBusy(RuntimeError):
    pass


def run_pipeline(trigger: str = "manual", backfill_days: int | None = None, db_path=DB_PATH, on_start=None) -> dict:
    if not _lock.acquire(blocking=False):
        raise PipelineBusy("a pipeline run is already in progress")
    conn = db.connect(db_path)
    run_id = db.start_run(conn, trigger)
    if on_start:
        on_start()
    try:
        days = backfill_days or INCREMENTAL_DAYS
        now = datetime.now(timezone.utc)
        rows, source_counts, errors = extract(hn_since=now - timedelta(days=days), devto_days=max(days, 7))
        df, stats = transform(rows, now)
        stats["inserted"], stats["updated"] = db.upsert_articles(conn, df, run_id)
        stats["rescored"] = db.rescore_stale(conn)
        stats["pruned"] = db.prune(conn)

        total_sources = 2 + len(RSS_FEEDS)
        status = "failed" if len(errors) == total_sources else "partial" if errors else "success"
        db.finish_run(conn, run_id, status, stats, source_counts, errors)
        log.info(
            "run %d %s: fetched %d, clean %d, inserted %d, updated %d, duplicates %d",
            run_id, status, stats["fetched"], stats["clean"], stats["inserted"], stats["updated"], stats["duplicates"],
        )
        return {"run_id": run_id, "status": status, **stats, "source_counts": source_counts, "errors": errors}
    except Exception as exc:
        db.finish_run(conn, run_id, "failed", {}, {}, {"pipeline": f"{type(exc).__name__}: {exc}"[:300]})
        raise
    finally:
        conn.close()
        _lock.release()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backfill", type=int, metavar="DAYS", help="pull this many days of history")
    parser.add_argument("--trigger", default="manual", help="label stored in the run log (manual, schedule, ci)")
    parser.add_argument("--export", action="store_true", help="write the static dashboard snapshot afterwards")
    parser.add_argument("--export-only", action="store_true", help="skip the run and only write the snapshot")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not args.export_only:
        trigger = "backfill" if args.backfill and args.trigger == "manual" else args.trigger
        result = run_pipeline(trigger, args.backfill)
        if result["status"] == "failed":
            raise SystemExit("every source failed; see the run log")
    if args.export or args.export_only:
        from .export import write_snapshot

        path, count = write_snapshot()
        log.info("snapshot: %d articles -> %s", count, path)


if __name__ == "__main__":
    main()
