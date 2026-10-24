// Runs the dashboard's JS analytics over a snapshot for tests/test_parity.py.
// usage: node parity.mjs <snapshot.json> <cases json> <sector order json>
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const lib = await import(
  pathToFileURL(resolve(import.meta.dirname, "../dashboard/src/lib/analytics.js")).href
);
const [snapshotPath, casesJson, sectorsJson] = process.argv.slice(2);
const { articles } = lib.decodeSnapshot(JSON.parse(readFileSync(snapshotPath, "utf8")));
const sectorOrder = JSON.parse(sectorsJson);

const results = JSON.parse(casesJson).map(({ q, ...f }) => ({
  summary: lib.summary(articles, f),
  timeseries: lib.timeseries(articles, f, sectorOrder),
  sectors: lib.sectors(articles, f),
  keywords: lib.keywords(articles, f, 15),
  articles: lib.articlesPage(articles, f, q, 25, 0),
}));
process.stdout.write(JSON.stringify(results));
