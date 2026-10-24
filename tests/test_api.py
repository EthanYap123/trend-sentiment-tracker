import os
import shutil

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(seeded_db):
    conn, path = seeded_db
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")  # flush the WAL so the copy has every row
    target = os.environ["TRACKER_DB"]
    for suffix in ("-wal", "-shm"):
        if os.path.exists(target + suffix):
            os.remove(target + suffix)
    shutil.copy(path, target)
    from api.main import app

    with TestClient(app) as c:
        yield c


def test_health_and_meta(client):
    assert client.get("/api/health").json() == {"status": "ok", "articles": 600}
    meta = client.get("/api/meta").json()
    assert meta["last_date"] == "2026-10-24"
    assert meta["last_run"]["status"] == "success"
    assert "General Tech" in meta["sectors"]


def test_summary_defaults_to_last_30_days(client):
    body = client.get("/api/summary").json()
    assert (body["start"], body["end"], body["days"]) == ("2026-09-25", "2026-10-24", 30)
    assert body["count"] == body["positive"] + body["negative"] + body["neutral"]
    assert body["previous"]["count"] > 0


def test_filters_narrow_every_endpoint(client):
    params = {"sector": "General Tech", "polarity": "negative", "start": "2026-09-01", "end": "2026-10-24"}
    summary = client.get("/api/summary", params=params).json()
    assert summary["count"] == summary["negative"] > 0
    sectors = client.get("/api/sectors", params=params).json()
    assert [s["sector"] for s in sectors] == ["General Tech"]
    series = client.get("/api/sentiment/timeseries", params=params).json()
    assert sum(d["count"] for d in series["series"]) == summary["count"]
    page = client.get("/api/articles", params={**params, "limit": 5}).json()
    assert page["total"] == summary["count"] and len(page["items"]) == 5
    assert all(a["polarity"] == "negative" for a in page["items"])


def test_keywords_and_search(client):
    kws = client.get("/api/keywords", params={"limit": 3}).json()
    assert len(kws) == 3 and kws[0]["count"] >= kws[1]["count"] >= kws[2]["count"]
    assert all(k["recent"] + k["earlier"] == k["count"] for k in kws)
    hits = client.get("/api/articles", params={"q": "bitcoin", "start": "2026-08-01"}).json()
    assert hits["total"] > 0 and all("bitcoin" in a["title"].lower() for a in hits["items"])


def test_runs_and_schedule(client):
    runs = client.get("/api/pipeline/runs").json()
    assert runs[0]["source_counts"] == {"Hacker News": 10}
    assert client.get("/api/pipeline/schedule").json()["enabled"] is False


@pytest.mark.parametrize(
    "query", ["sector=Nope", "polarity=happy", "start=2026-13", "limit=0", "limit=500"]
)
def test_bad_parameters_are_rejected(client, query):
    path = "/api/articles" if "limit" in query else "/api/summary"
    assert client.get(f"{path}?{query}").status_code == 422
