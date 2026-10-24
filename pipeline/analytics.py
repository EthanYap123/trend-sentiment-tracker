"""Analytics queries behind the API.

`dashboard/src/lib/analytics.js` computes the same results from the static
snapshot for the GitHub Pages demo, and `tests/test_parity.py` checks the two
agree. Change both together.
"""

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta

from .config import SECTOR_NAMES

DEFAULT_WINDOW_DAYS = 30
POLARITIES = ("positive", "negative", "neutral")


@dataclass
class Filters:
    start: str | None = None
    end: str | None = None
    sector: str | None = None
    polarity: str | None = None
    source: str | None = None


def data_bounds(conn: sqlite3.Connection) -> tuple[str | None, str | None]:
    row = conn.execute("SELECT MIN(published_date), MAX(published_date) FROM articles").fetchone()
    return row[0], row[1]


def resolve_range(conn: sqlite3.Connection, f: Filters) -> tuple[str, str]:
    """Missing dates default to the latest 30 days that have data."""
    first, last = data_bounds(conn)
    end = f.end or last or date.today().isoformat()
    start = f.start or (date.fromisoformat(end) - timedelta(days=DEFAULT_WINDOW_DAYS - 1)).isoformat()
    if start > end:
        start, end = end, start
    return start, end


def _where(conn: sqlite3.Connection, f: Filters, start: str | None = None, end: str | None = None, alias: str = "a"):
    if start is None:
        start, end = resolve_range(conn, f)
    clauses = [f"{alias}.published_date BETWEEN ? AND ?"]
    params: list = [start, end]
    for column, value in (("sector", f.sector), ("polarity", f.polarity), ("source", f.source)):
        if value:
            clauses.append(f"{alias}.{column} = ?")
            params.append(value)
    return " AND ".join(clauses), params


def _counts(row) -> dict:
    count = row["n"] or 0
    return {
        "count": count,
        "avg_sentiment": round(row["avg"], 4) if count else None,
        "positive": row["pos"] or 0,
        "negative": row["neg"] or 0,
        "neutral": row["neu"] or 0,
    }


AGGREGATES = """COUNT(*) AS n, AVG(a.sentiment) AS avg,
    SUM(a.polarity = 'positive') AS pos, SUM(a.polarity = 'negative') AS neg, SUM(a.polarity = 'neutral') AS neu"""


def summary(conn: sqlite3.Connection, f: Filters) -> dict:
    start, end = resolve_range(conn, f)
    where, params = _where(conn, f, start, end)
    current = conn.execute(f"SELECT {AGGREGATES}, COUNT(DISTINCT a.source) AS sources FROM articles a WHERE {where}", params).fetchone()

    # The window of the same length just before this one, for the KPI deltas.
    # Skipped when the stored history doesn't reach back that far, since a
    # half-covered window would make every delta look like growth.
    days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    prev_end = (date.fromisoformat(start) - timedelta(days=1)).isoformat()
    prev_start = (date.fromisoformat(start) - timedelta(days=days)).isoformat()
    first, _ = data_bounds(conn)
    previous = None
    if first and prev_start >= first:
        where_prev, params_prev = _where(conn, f, prev_start, prev_end)
        previous = _counts(conn.execute(f"SELECT {AGGREGATES} FROM articles a WHERE {where_prev}", params_prev).fetchone())

    return {
        "start": start,
        "end": end,
        "days": days,
        **_counts(current),
        "sources": current["sources"],
        "previous": previous,
    }


def timeseries(conn: sqlite3.Connection, f: Filters) -> dict:
    where, params = _where(conn, f)
    daily = conn.execute(
        f"SELECT a.published_date AS date, {AGGREGATES} FROM articles a WHERE {where} GROUP BY a.published_date ORDER BY date",
        params,
    ).fetchall()
    by_sector: dict[str, list] = {}
    for row in conn.execute(
        f"""SELECT a.sector, a.published_date AS date, COUNT(*) AS n, AVG(a.sentiment) AS avg
            FROM articles a WHERE {where} GROUP BY a.sector, a.published_date ORDER BY a.sector, date""",
        params,
    ):
        by_sector.setdefault(row["sector"], []).append(
            {"date": row["date"], "count": row["n"], "avg_sentiment": round(row["avg"], 4)}
        )
    return {
        "series": [{"date": r["date"], **_counts(r)} for r in daily],
        "by_sector": {s: by_sector[s] for s in SECTOR_NAMES if s in by_sector},
    }


def sectors(conn: sqlite3.Connection, f: Filters) -> list[dict]:
    where, params = _where(conn, f)
    rows = conn.execute(
        f"SELECT a.sector, {AGGREGATES} FROM articles a WHERE {where} GROUP BY a.sector ORDER BY n DESC, a.sector",
        params,
    ).fetchall()
    return [{"sector": r["sector"], **_counts(r)} for r in rows]


def keywords(conn: sqlite3.Connection, f: Filters, limit: int = 15) -> list[dict]:
    """Most-mentioned tracked terms, with momentum = later half of the range vs the earlier half."""
    start, end = resolve_range(conn, f)
    where, params = _where(conn, f, start, end)
    days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    mid = (date.fromisoformat(start) + timedelta(days=days // 2)).isoformat()
    rows = conn.execute(
        f"""SELECT k.keyword, COUNT(*) AS n, AVG(a.sentiment) AS avg,
                SUM(a.polarity = 'positive') AS pos, SUM(a.polarity = 'negative') AS neg,
                SUM(a.polarity = 'neutral') AS neu,
                SUM(a.published_date >= ?) AS recent, SUM(a.published_date < ?) AS earlier
            FROM article_keywords k JOIN articles a ON a.id = k.article_id
            WHERE {where} GROUP BY k.keyword ORDER BY n DESC, k.keyword LIMIT ?""",
        [mid, mid, *params, limit],
    ).fetchall()
    return [
        {"keyword": r["keyword"], **_counts(r), "recent": r["recent"], "earlier": r["earlier"], "momentum": r["recent"] - r["earlier"]}
        for r in rows
    ]


def articles(conn: sqlite3.Connection, f: Filters, q: str | None = None, limit: int = 25, offset: int = 0) -> dict:
    where, params = _where(conn, f)
    if q:
        where += " AND LOWER(a.title) LIKE ?"
        params.append(f"%{q.lower()}%")
    total = conn.execute(f"SELECT COUNT(*) FROM articles a WHERE {where}", params).fetchone()[0]
    rows = conn.execute(
        f"""SELECT a.*, (SELECT GROUP_CONCAT(keyword, '|') FROM
                (SELECT keyword FROM article_keywords WHERE article_id = a.id ORDER BY keyword)) AS kw
            FROM articles a WHERE {where} ORDER BY a.published_at DESC, a.id LIMIT ? OFFSET ?""",
        [*params, limit, offset],
    ).fetchall()
    items = [
        {
            "id": r["id"], "source": r["source"], "title": r["title"], "summary": r["summary"], "url": r["url"],
            "published_at": r["published_at"], "sector": r["sector"], "sentiment": r["sentiment"],
            "polarity": r["polarity"], "engagement": r["engagement"], "comments": r["comments"],
            "keywords": r["kw"].split("|") if r["kw"] else [],
        }
        for r in rows
    ]
    return {"total": total, "limit": limit, "offset": offset, "items": items}


def runs(conn: sqlite3.Connection, limit: int = 20) -> list[dict]:
    rows = conn.execute("SELECT * FROM pipeline_runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    result = []
    for r in rows:
        item = dict(r)
        item["source_counts"] = json.loads(item["source_counts"]) if item["source_counts"] else {}
        item["errors"] = json.loads(item["errors"]) if item["errors"] else {}
        result.append(item)
    return result


def meta(conn: sqlite3.Connection) -> dict:
    first, last = data_bounds(conn)
    total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    sources = [r[0] for r in conn.execute("SELECT DISTINCT source FROM articles ORDER BY source")]
    last_run = runs(conn, 1)
    return {
        "first_date": first,
        "last_date": last,
        "total_articles": total,
        "sectors": SECTOR_NAMES,
        "sources": sources,
        "polarities": list(POLARITIES),
        "last_run": last_run[0] if last_run else None,
    }
