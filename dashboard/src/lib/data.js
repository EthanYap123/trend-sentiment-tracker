// One interface over two backends:
//   "api"    - the FastAPI server (local, or anywhere NEXT_PUBLIC_API_URL points)
//   "static" - the snapshot JSON the scheduled GitHub Action publishes with the Pages build
import * as analytics from "./analytics";

export const SOURCE = process.env.NEXT_PUBLIC_DATA_SOURCE === "static" ? "static" : "api";
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";
const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? (process.env.NODE_ENV === "development" ? "http://localhost:8000" : "");

function query(params) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") search.set(key, value);
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

async function getJson(path, params = {}, init) {
  const res = await fetch(`${API_URL}${path}${query(params)}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `${res.status} ${res.statusText}`);
  }
  return res.json();
}

let snapshotPromise = null;
function snapshot() {
  snapshotPromise ??= fetch(`${BASE_PATH}/data/snapshot.json`, { cache: "no-cache" })
    .then((res) => {
      if (!res.ok) throw new Error(`snapshot: ${res.status} ${res.statusText}`);
      return res.json();
    })
    .then(analytics.decodeSnapshot)
    .catch((err) => {
      snapshotPromise = null;
      throw err;
    });
  return snapshotPromise;
}

export async function getMeta() {
  if (SOURCE === "api") return getJson("/api/meta");
  const snap = await snapshot();
  return { ...snap.meta, generated_at: snap.generated_at };
}

export async function getDashboard(filters, keywordLimit = 15) {
  if (SOURCE === "api") {
    const [summary, timeseries, sectors, keywords] = await Promise.all([
      getJson("/api/summary", filters),
      getJson("/api/sentiment/timeseries", filters),
      getJson("/api/sectors", filters),
      getJson("/api/keywords", { ...filters, limit: keywordLimit }),
    ]);
    return { summary, timeseries, sectors, keywords };
  }
  const { articles, meta } = await snapshot();
  return {
    summary: analytics.summary(articles, filters),
    timeseries: analytics.timeseries(articles, filters, meta.sectors),
    sectors: analytics.sectors(articles, filters),
    keywords: analytics.keywords(articles, filters, keywordLimit),
  };
}

export async function getArticles(filters, q, limit, offset) {
  if (SOURCE === "api") return getJson("/api/articles", { ...filters, q, limit, offset });
  const { articles } = await snapshot();
  return analytics.articlesPage(articles, filters, q, limit, offset);
}

export async function getRuns() {
  if (SOURCE === "api") return getJson("/api/pipeline/runs", { limit: 20 });
  return (await snapshot()).runs.slice(0, 20);
}

export async function getSchedule() {
  if (SOURCE === "api") return getJson("/api/pipeline/schedule");
  // The Pages build is refreshed by the cron in .github/workflows/pipeline.yml.
  return { enabled: true, interval_minutes: 360, next_run_at: null, via: "GitHub Actions" };
}

export async function triggerRun() {
  return getJson("/api/pipeline/run", {}, { method: "POST" });
}
