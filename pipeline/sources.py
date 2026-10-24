"""Extract step: pull raw stories from keyless public sources.

Every fetcher returns plain dicts with the same keys so the transform step can
load them straight into one DataFrame.
"""

import logging
import time
from datetime import datetime, timedelta, timezone

import feedparser
import requests

from .config import HN_MIN_POINTS, HTTP_TIMEOUT, RSS_FEEDS, USER_AGENT

log = logging.getLogger(__name__)

HN_SEARCH = "https://hn.algolia.com/api/v1/search_by_date"
DEVTO_ARTICLES = "https://dev.to/api/articles"

session = requests.Session()
session.headers["User-Agent"] = USER_AGENT


def _get(url: str, **params) -> requests.Response:
    for attempt in range(3):
        try:
            res = session.get(url, params=params or None, timeout=HTTP_TIMEOUT)
            if res.status_code == 429 or res.status_code >= 500:
                raise requests.HTTPError(f"{res.status_code} from {url}", response=res)
            res.raise_for_status()
            return res
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    raise AssertionError("unreachable")


def record(source, source_type, title, url, published_at, summary="", author=None, engagement=None, comments=None):
    return {
        "source": source,
        "source_type": source_type,
        "title": title,
        "summary": summary or "",
        "url": url,
        "author": author,
        "published_at": published_at,
        "engagement": engagement,
        "comments": comments,
    }


def fetch_hacker_news(since: datetime, until: datetime | None = None) -> list[dict]:
    """Stories with at least HN_MIN_POINTS points, one request per day window."""
    until = until or datetime.now(timezone.utc)
    rows, start = [], since
    while start < until:
        end = min(start + timedelta(days=1), until)
        data = _get(
            HN_SEARCH,
            tags="story",
            hitsPerPage=1000,
            numericFilters=f"created_at_i>{int(start.timestamp())},created_at_i<={int(end.timestamp())},points>={HN_MIN_POINTS}",
        ).json()
        for hit in data.get("hits", []):
            if not hit.get("title"):
                continue
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"
            rows.append(record(
                "Hacker News", "api", hit["title"], url, hit.get("created_at"),
                summary=hit.get("story_text") or "", author=hit.get("author"),
                engagement=hit.get("points"), comments=hit.get("num_comments"),
            ))
        start = end
    return rows


def fetch_devto(days: int) -> list[dict]:
    """Most-reacted DEV.to articles over the last `days` days."""
    rows = []
    pages = max(1, min(10, days // 7 + 1))
    for page in range(1, pages + 1):
        items = _get(DEVTO_ARTICLES, per_page=100, top=max(1, days), page=page).json()
        if not items:
            break
        for item in items:
            rows.append(record(
                "DEV.to", "api", item.get("title"), item.get("url"), item.get("published_at"),
                summary=" ".join(filter(None, [item.get("description"), " ".join(item.get("tag_list") or [])])),
                author=(item.get("user") or {}).get("name"),
                engagement=item.get("positive_reactions_count"), comments=item.get("comments_count"),
            ))
    return rows


def _entry_time(entry) -> str | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()
    return entry.get("published") or entry.get("updated")


def fetch_rss(name: str, url: str) -> list[dict]:
    feed = feedparser.parse(_get(url).content)
    if feed.bozo and not feed.entries:
        raise ValueError(f"could not parse feed: {feed.bozo_exception}")
    return [
        record(name, "rss", e.get("title"), e.get("link"), _entry_time(e),
               summary=e.get("summary", ""), author=e.get("author"))
        for e in feed.entries
    ]


def extract(hn_since: datetime, devto_days: int) -> tuple[list[dict], dict[str, int], dict[str, str]]:
    """Run every source. A failing source is logged and skipped, not fatal."""
    jobs = {
        "Hacker News": lambda: fetch_hacker_news(hn_since),
        "DEV.to": lambda: fetch_devto(devto_days),
        **{name: (lambda n=name, u=url: fetch_rss(n, u)) for name, url in RSS_FEEDS.items()},
    }
    rows, counts, errors = [], {}, {}
    for name, job in jobs.items():
        try:
            fetched = job()
            rows.extend(fetched)
            counts[name] = len(fetched)
            log.info("extract %-12s %4d rows", name, len(fetched))
        except Exception as exc:  # noqa: BLE001 - one bad source must not stop the run
            counts[name] = 0
            errors[name] = f"{type(exc).__name__}: {exc}"[:300]
            log.warning("extract %s failed: %s", name, exc)
    return rows, counts, errors
