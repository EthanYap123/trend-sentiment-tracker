from datetime import timedelta

import pytest

from pipeline import db, run
from pipeline.sentiment import polarity, score_text
from pipeline.transform import canonical_url, classify, enrich, transform
from pipeline.text import tokenize

from .conftest import NOW, synthetic_rows


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Startup raises $40M to accelerate growth", "positive"),
        ("Massive outage takes down cloud provider", "negative"),
        ("Company announces layoffs as revenue falls", "negative"),
        ("Parser combinators in 200 lines", "neutral"),
        ("Show HN: a weekend hack to kill zombie processes", "neutral"),
    ],
)
def test_headline_polarity(title, expected):
    assert polarity(score_text(title)) == expected


def test_negation_flips_and_intensifier_boosts():
    assert score_text("The quarter was profitable") > 0
    assert score_text("The quarter was not profitable") < 0
    assert score_text("very strong growth") > score_text("strong growth")


def test_phrases_score_as_one_unit():
    assert score_text("Engineers laid off") < 0
    assert score_text("Shares hit an all-time high") > 0


def test_scores_stay_in_range():
    huge = " ".join(["excellent breakthrough success"] * 50)
    assert 0.99 < score_text(huge) <= 1
    assert -1 <= score_text(" ".join(["catastrophic fraud scandal"] * 50)) < -0.99


def test_classify_picks_best_sector_and_tracks_terms():
    assert classify(tokenize("Nvidia unveils new GPU chips")) == "Hardware & Chips"
    assert classify(tokenize("Ransomware gang exploits zero-day vulnerability")) == "Cybersecurity"
    assert classify(tokenize("A history of typewriters")) == "General Tech"
    assert enrich("OpenAI and Nvidia sign a chips deal", "")["keywords"] == ["Chips", "Nvidia", "OpenAI"]


def test_canonical_url_strips_tracking_and_www():
    assert canonical_url("http://www.Example.com/a/?utm_source=x&id=3#top") == "https://example.com/a?id=3"
    assert canonical_url("not a url") == ""


def test_transform_cleans_dedupes_and_drops_bad_rows():
    rows = synthetic_rows(20)
    rows.append(dict(rows[0], url=rows[0]["url"] + "&utm_medium=social", engagement=999))  # same link
    rows.append(dict(rows[1], url="https://other.example/syndicated"))  # same headline
    rows.append(dict(rows[2], title="  ", url="https://example.com/empty"))  # no title
    rows.append(dict(rows[3], published_at="garbage", url="https://example.com/bad-date"))
    rows.append(dict(rows[4], published_at=(NOW - timedelta(days=400)).isoformat(), url="https://example.com/old"))

    df, stats = transform(rows, NOW)
    assert stats == {"fetched": 25, "invalid": 2, "out_of_window": 1, "duplicates": 2, "clean": 20}
    assert df["id"].is_unique
    kept = df[df["url"] == canonical_url(rows[0]["url"])]
    assert kept["engagement"].iloc[0] == 999  # the more-engaged duplicate wins
    assert not df["summary"].str.contains("<p>").any()
    assert set(df["polarity"]) <= {"positive", "negative", "neutral"}


def test_upsert_is_idempotent_and_refreshes_engagement(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    df, _ = transform(synthetic_rows(50), NOW)
    assert db.upsert_articles(conn, df, 1) == (50, 0)

    df.loc[0, "engagement"] = 12345
    assert db.upsert_articles(conn, df, 2) == (0, 50)
    assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 50
    assert conn.execute("SELECT engagement FROM articles WHERE id = ?", (df.loc[0, "id"],)).fetchone()[0] == 12345
    keyword_rows = conn.execute("SELECT COUNT(*) FROM article_keywords").fetchone()[0]
    assert keyword_rows == sum(len(k) for k in df["keywords"])


def test_rescore_updates_rows_from_older_versions(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    df, _ = transform(synthetic_rows(10), NOW)
    db.upsert_articles(conn, df, 1)
    conn.execute("UPDATE articles SET enrich_version = 0, sentiment = 0.5")
    assert db.rescore_stale(conn) == 10
    assert db.rescore_stale(conn) == 0


def test_run_pipeline_logs_partial_failures(tmp_path, monkeypatch):
    def fake_extract(hn_since, devto_days):
        return synthetic_rows(30), {"Hacker News": 30, "Wired": 0}, {"Wired": "HTTPError: 503"}

    monkeypatch.setattr(run, "extract", fake_extract)
    result = run.run_pipeline("test", db_path=tmp_path / "t.db")
    assert result["status"] == "partial"
    assert result["inserted"] == 30

    conn = db.connect(tmp_path / "t.db")
    logged = conn.execute("SELECT status, inserted, errors FROM pipeline_runs").fetchone()
    assert logged["status"] == "partial" and logged["inserted"] == 30 and "503" in logged["errors"]


def test_run_pipeline_refuses_overlapping_runs(tmp_path):
    run._lock.acquire()
    try:
        with pytest.raises(run.PipelineBusy):
            run.run_pipeline("test", db_path=tmp_path / "t.db")
    finally:
        run._lock.release()
