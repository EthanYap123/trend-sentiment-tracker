"""Load step: SQLite schema, upserts, re-scoring and retention."""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from .config import DB_PATH, RETENTION_DAYS
from .transform import ENRICH_VERSION, enrich

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id              TEXT PRIMARY KEY,
    source          TEXT NOT NULL,
    source_type     TEXT NOT NULL,
    title           TEXT NOT NULL,
    summary         TEXT NOT NULL DEFAULT '',
    url             TEXT NOT NULL,
    author          TEXT,
    published_at    TEXT NOT NULL,
    published_date  TEXT NOT NULL,
    engagement      INTEGER,
    comments        INTEGER,
    sector          TEXT NOT NULL,
    sentiment       REAL NOT NULL,
    polarity        TEXT NOT NULL,
    enrich_version  INTEGER NOT NULL,
    first_seen_run  INTEGER,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(published_date);
CREATE INDEX IF NOT EXISTS idx_articles_sector ON articles(sector, published_date);

CREATE TABLE IF NOT EXISTS article_keywords (
    article_id  TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    keyword     TEXT NOT NULL,
    PRIMARY KEY (article_id, keyword)
);
CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON article_keywords(keyword);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger        TEXT NOT NULL,
    status         TEXT NOT NULL,
    started_at     TEXT NOT NULL,
    finished_at    TEXT,
    duration_ms    INTEGER,
    fetched        INTEGER DEFAULT 0,
    clean          INTEGER DEFAULT 0,
    inserted       INTEGER DEFAULT 0,
    updated        INTEGER DEFAULT 0,
    duplicates     INTEGER DEFAULT 0,
    invalid        INTEGER DEFAULT 0,
    rescored       INTEGER DEFAULT 0,
    pruned         INTEGER DEFAULT 0,
    source_counts  TEXT,
    errors         TEXT
);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path: Path | str = DB_PATH) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    return conn


def start_run(conn: sqlite3.Connection, trigger: str) -> int:
    cur = conn.execute(
        "INSERT INTO pipeline_runs (trigger, status, started_at) VALUES (?, 'running', ?)", (trigger, utc_now())
    )
    conn.commit()
    return cur.lastrowid


def finish_run(conn: sqlite3.Connection, run_id: int, status: str, stats: dict, source_counts: dict, errors: dict):
    started = conn.execute("SELECT started_at FROM pipeline_runs WHERE id = ?", (run_id,)).fetchone()[0]
    finished = utc_now()
    duration = datetime.fromisoformat(finished) - datetime.fromisoformat(started)
    conn.execute(
        """UPDATE pipeline_runs SET status = ?, finished_at = ?, duration_ms = ?, fetched = ?, clean = ?,
               inserted = ?, updated = ?, duplicates = ?, invalid = ?, rescored = ?, pruned = ?,
               source_counts = ?, errors = ?
           WHERE id = ?""",
        (
            status, finished, int(duration.total_seconds() * 1000),
            *(stats.get(k, 0) for k in ("fetched", "clean", "inserted", "updated", "duplicates", "invalid", "rescored", "pruned")),
            json.dumps(source_counts), json.dumps(errors) if errors else None, run_id,
        ),
    )
    conn.commit()


def _write_keywords(conn: sqlite3.Connection, article_id: str, keywords: list[str]):
    conn.execute("DELETE FROM article_keywords WHERE article_id = ?", (article_id,))
    conn.executemany(
        "INSERT INTO article_keywords (article_id, keyword) VALUES (?, ?)", [(article_id, k) for k in keywords]
    )


def upsert_articles(conn: sqlite3.Connection, df: pd.DataFrame, run_id: int | None) -> tuple[int, int]:
    """Insert new articles; refresh engagement and scores on ones already stored."""
    if df.empty:
        return 0, 0
    existing = {
        row[0]
        for chunk in range(0, len(df), 500)
        for row in conn.execute(
            f"SELECT id FROM articles WHERE id IN ({','.join('?' * len(df['id'][chunk:chunk + 500]))})",
            list(df["id"][chunk:chunk + 500]),
        )
    }
    now = utc_now()
    for row in df.to_dict("records"):
        values = {k: (None if pd.isna(v) else v) for k, v in row.items() if k != "keywords"}
        conn.execute(
            """INSERT INTO articles (id, source, source_type, title, summary, url, author, published_at,
                   published_date, engagement, comments, sector, sentiment, polarity, enrich_version,
                   first_seen_run, updated_at)
               VALUES (:id, :source, :source_type, :title, :summary, :url, :author, :published_at,
                   :published_date, :engagement, :comments, :sector, :sentiment, :polarity, :version,
                   :run_id, :now)
               ON CONFLICT(id) DO UPDATE SET
                   engagement = COALESCE(excluded.engagement, articles.engagement),
                   comments = COALESCE(excluded.comments, articles.comments),
                   title = excluded.title, summary = excluded.summary, sector = excluded.sector,
                   sentiment = excluded.sentiment, polarity = excluded.polarity,
                   enrich_version = excluded.enrich_version, updated_at = excluded.updated_at""",
            {**values, "version": ENRICH_VERSION, "run_id": run_id, "now": now},
        )
        _write_keywords(conn, row["id"], row["keywords"])
    conn.commit()
    return len(df) - len(existing), len(existing)


def rescore_stale(conn: sqlite3.Connection) -> int:
    """Re-run enrichment on rows scored by an older lexicon or dictionary version."""
    stale = conn.execute(
        "SELECT id, title, summary FROM articles WHERE enrich_version < ?", (ENRICH_VERSION,)
    ).fetchall()
    for row in stale:
        result = enrich(row["title"], row["summary"])
        conn.execute(
            "UPDATE articles SET sector = ?, sentiment = ?, polarity = ?, enrich_version = ?, updated_at = ? WHERE id = ?",
            (result["sector"], result["sentiment"], result["polarity"], ENRICH_VERSION, utc_now(), row["id"]),
        )
        _write_keywords(conn, row["id"], result["keywords"])
    conn.commit()
    return len(stale)


def prune(conn: sqlite3.Connection, days: int = RETENTION_DAYS) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    cur = conn.execute("DELETE FROM articles WHERE published_date < ?", (cutoff,))
    # Keep the run log bounded too.
    conn.execute("DELETE FROM pipeline_runs WHERE id NOT IN (SELECT id FROM pipeline_runs ORDER BY id DESC LIMIT 500)")
    conn.commit()
    return cur.rowcount


def latest_published(conn: sqlite3.Connection, source: str) -> datetime | None:
    value = conn.execute("SELECT MAX(published_at) FROM articles WHERE source = ?", (source,)).fetchone()[0]
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
