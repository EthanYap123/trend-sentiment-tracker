"""Transform step: clean, de-duplicate and enrich raw records with pandas."""

import hashlib
import html
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd

from .config import DEFAULT_SECTOR, RETENTION_DAYS, SECTORS, TRACKED_TERMS
from .sentiment import polarity, score_text
from .text import PhraseMatcher, tokenize

# Bump when the lexicon, sector dictionaries or tracked terms change, so stored
# articles get re-scored on the next run.
ENRICH_VERSION = 1

SUMMARY_LIMIT = 400
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
TRACKING_PARAMS = re.compile(r"^(utm_\w+|ref|ref_src|cmpid|guccounter|mc_cid|mc_eid|fbclid|gclid)$", re.I)

sector_matcher = PhraseMatcher(SECTORS)
term_matcher = PhraseMatcher(TRACKED_TERMS)

COLUMNS = [
    "id", "source", "source_type", "title", "summary", "url", "author", "published_at",
    "published_date", "engagement", "comments", "sector", "sentiment", "polarity", "keywords",
]


def clean_text(value) -> str:
    if not isinstance(value, str):
        return ""
    text = html.unescape(TAG_RE.sub(" ", value))
    return SPACE_RE.sub(" ", text).strip()


def truncate(text: str, limit: int = SUMMARY_LIMIT) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(" ,.;:") + "…"


def canonical_url(url) -> str:
    if not isinstance(url, str) or not url.startswith("http"):
        return ""
    parts = urlsplit(url.strip())
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not TRACKING_PARAMS.match(k)])
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(("https", parts.netloc.lower().removeprefix("www."), path, query, ""))


def title_key(title: str) -> str:
    return " ".join(tokenize(title))


def classify(tokens: list[str]) -> str:
    hits = sector_matcher.counts(tokens)
    if not hits:
        return DEFAULT_SECTOR
    # max() keeps the first sector on ties, and dict order follows SECTORS.
    return max(hits, key=hits.get)


def enrich(title: str, summary: str) -> dict:
    tokens = tokenize(f"{title} {summary}")
    score = score_text(title, summary)
    return {
        "sector": classify(tokens),
        "sentiment": score,
        "polarity": polarity(score),
        "keywords": sorted(term_matcher.counts(tokens)),
    }


def transform(rows: list[dict], now: datetime | None = None) -> tuple[pd.DataFrame, dict[str, int]]:
    """Returns the cleaned frame plus counts of what was dropped and why."""
    now = now or datetime.now(timezone.utc)
    stats = {"fetched": len(rows), "invalid": 0, "out_of_window": 0, "duplicates": 0, "clean": 0}
    if not rows:
        return pd.DataFrame(columns=COLUMNS), stats

    df = pd.DataFrame(rows)
    df["title"] = df["title"].map(clean_text)
    df["summary"] = df["summary"].map(clean_text).map(truncate)
    df["url"] = df["url"].map(canonical_url)
    df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce", format="mixed")

    valid = (df["title"] != "") & (df["url"] != "") & df["published_at"].notna()
    stats["invalid"] = int((~valid).sum())
    df = df[valid]

    in_window = (df["published_at"] <= now + timedelta(hours=1)) & (
        df["published_at"] >= now - timedelta(days=RETENTION_DAYS)
    )
    stats["out_of_window"] = int((~in_window).sum())
    df = df[in_window].copy()

    # Keep the most-engaged copy when the same story shows up twice (same link,
    # or the same headline syndicated under different links).
    before = len(df)
    df["_title_key"] = df["title"].map(title_key)
    df = (
        df.sort_values("engagement", ascending=False, na_position="last")
        .drop_duplicates("url")
        .drop_duplicates("_title_key")
    )
    stats["duplicates"] = before - len(df)

    df["id"] = df["url"].map(lambda u: hashlib.sha1(u.encode()).hexdigest()[:16])
    df["published_date"] = df["published_at"].dt.strftime("%Y-%m-%d")
    df["published_at"] = df["published_at"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    for col in ("engagement", "comments"):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    enriched = pd.DataFrame([enrich(t, s) for t, s in zip(df["title"], df["summary"])], index=df.index)
    df = pd.concat([df, enriched], axis=1)
    df = df.sort_values("published_at", ascending=False)[COLUMNS].reset_index(drop=True)
    stats["clean"] = len(df)
    return df, stats
