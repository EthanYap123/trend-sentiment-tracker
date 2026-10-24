"""The Pages demo answers queries in JavaScript (dashboard/src/lib/analytics.js);
this checks it agrees with the Python analytics the API uses."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from pipeline import analytics
from pipeline.config import SECTOR_NAMES
from pipeline.export import build_snapshot

SCRIPT = Path(__file__).with_name("parity.mjs")
CASES = [
    {},
    {"start": "2026-08-20", "end": "2026-10-24"},
    {"start": "2026-10-01", "end": "2026-10-10", "sector": "AI & ML"},
    {"polarity": "negative", "source": "Hacker News"},
    {"start": "2026-10-20", "end": "2026-10-01"},  # reversed range
    {"start": "2026-09-01", "end": "2026-09-30", "q": "nvidia"},
]


def close(a, b):
    if isinstance(a, float) or isinstance(b, float):
        return a is not None and b is not None and abs(a - b) < 2e-4
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    return a == b


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_js_analytics_match_python(seeded_db, tmp_path):
    conn, _ = seeded_db
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps(build_snapshot(conn)))
    out = subprocess.run(
        ["node", str(SCRIPT), str(snapshot), json.dumps(CASES), json.dumps(SECTOR_NAMES)],
        capture_output=True, text=True, check=True,
    )
    js_results = json.loads(out.stdout)

    for case, js in zip(CASES, js_results):
        f = analytics.Filters(**{k: v for k, v in case.items() if k != "q"})
        py = {
            "summary": analytics.summary(conn, f),
            "timeseries": analytics.timeseries(conn, f),
            "sectors": analytics.sectors(conn, f),
            "keywords": analytics.keywords(conn, f, 15),
            "articles": analytics.articles(conn, f, case.get("q"), 25, 0),
        }
        # The snapshot trims long summaries; compare everything else on each article.
        for page in (py["articles"], js["articles"]):
            for item in page["items"]:
                item.pop("summary")
        for name in py:
            assert close(py[name], js[name]), f"{name} differs for {case}"
