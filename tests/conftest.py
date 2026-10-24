import os
import random
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Point the API at a throwaway database before anything imports the config.
_tmp = Path(tempfile.mkdtemp(prefix="tracker-tests-"))
os.environ["TRACKER_DB"] = str(_tmp / "api.db")
os.environ["SCHEDULER_ENABLED"] = "false"

from pipeline import db  # noqa: E402
from pipeline.transform import transform  # noqa: E402

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)

SUBJECTS = [
    "Nvidia", "OpenAI", "Startup", "Kubernetes release", "Rust compiler", "Bitcoin", "Apple",
    "Ransomware gang", "Google", "Tesla", "Linux kernel", "Fintech app", "Hiring market", "SpaceX",
]
PREDICATES = [
    "posts record profits", "faces massive outage", "raises $40M in funding", "announces layoffs",
    "ships a faster release", "is not profitable", "hit by data breach", "wins antitrust case",
    "launches open source tools", "warns of chip shortage", "rallies after earnings", "explained",
]
SOURCES = [("Hacker News", "api"), ("DEV.to", "api"), ("TechCrunch", "rss"), ("Wired", "rss")]


def synthetic_rows(n: int = 600, days: int = 75, seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        source, kind = rng.choice(SOURCES)
        published = NOW - timedelta(minutes=rng.randrange(days * 24 * 60))
        rows.append({
            "source": source,
            "source_type": kind,
            "title": f"{rng.choice(SUBJECTS)} {rng.choice(PREDICATES)} #{i}",
            "summary": rng.choice(["", "Analysts are optimistic.", "Users report problems.", "<p>More &amp; more</p>"]),
            "url": f"https://example.com/story/{i}?utm_source=feed",
            "author": "someone",
            "published_at": published.isoformat(),
            "engagement": rng.randrange(20, 900) if kind == "api" else None,
            "comments": rng.randrange(0, 300) if kind == "api" else None,
        })
    return rows


@pytest.fixture
def seeded_db(tmp_path):
    path = tmp_path / "tracker.db"
    conn = db.connect(path)
    run_id = db.start_run(conn, "test")
    df, stats = transform(synthetic_rows(), NOW)
    stats["inserted"], stats["updated"] = db.upsert_articles(conn, df, run_id)
    db.finish_run(conn, run_id, "success", stats, {"Hacker News": 10}, {})
    yield conn, path
    conn.close()
