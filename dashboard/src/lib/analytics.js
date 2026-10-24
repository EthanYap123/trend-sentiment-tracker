// Browser port of pipeline/analytics.py. The GitHub Pages build has no API, so
// it loads the static snapshot and answers the same queries here.
// tests/test_parity.py checks both return the same results: change them together.

export const DEFAULT_WINDOW_DAYS = 30;
const DAY_MS = 86_400_000;

const toDay = (iso) => Date.parse(`${iso}T00:00:00Z`);
const fromDay = (ms) => new Date(ms).toISOString().slice(0, 10);
const addDays = (iso, n) => fromDay(toDay(iso) + n * DAY_MS);
const round4 = (x) => Math.round(x * 1e4) / 1e4;
const byString = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

export function dataBounds(articles) {
  let first = null;
  let last = null;
  for (const a of articles) {
    const d = a.published_at.slice(0, 10);
    if (first === null || d < first) first = d;
    if (last === null || d > last) last = d;
  }
  return [first, last];
}

export function resolveRange(articles, f) {
  const [, last] = dataBounds(articles);
  let end = f.end || last || fromDay(Date.now());
  let start = f.start || addDays(end, -(DEFAULT_WINDOW_DAYS - 1));
  if (start > end) [start, end] = [end, start];
  return [start, end];
}

function select(articles, f, start, end) {
  return articles.filter((a) => {
    const d = a.published_at.slice(0, 10);
    return (
      d >= start &&
      d <= end &&
      (!f.sector || a.sector === f.sector) &&
      (!f.polarity || a.polarity === f.polarity) &&
      (!f.source || a.source === f.source)
    );
  });
}

function counts(rows) {
  const out = { count: rows.length, avg_sentiment: null, positive: 0, negative: 0, neutral: 0 };
  if (!rows.length) return out;
  let sum = 0;
  for (const r of rows) {
    sum += r.sentiment;
    out[r.polarity] += 1;
  }
  out.avg_sentiment = round4(sum / rows.length);
  return out;
}

function groupBy(rows, key) {
  const groups = new Map();
  for (const r of rows) {
    const k = key(r);
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(r);
  }
  return groups;
}

const daySpan = (start, end) => Math.round((toDay(end) - toDay(start)) / DAY_MS) + 1;

export function summary(articles, f) {
  const [start, end] = resolveRange(articles, f);
  const rows = select(articles, f, start, end);
  const days = daySpan(start, end);
  const prevStart = addDays(start, -days);
  const [first] = dataBounds(articles);
  const previous =
    first && prevStart >= first ? counts(select(articles, f, prevStart, addDays(start, -1))) : null;
  return {
    start,
    end,
    days,
    ...counts(rows),
    sources: new Set(rows.map((r) => r.source)).size,
    previous,
  };
}

export function timeseries(articles, f, sectorOrder) {
  const [start, end] = resolveRange(articles, f);
  const rows = select(articles, f, start, end);
  const day = (r) => r.published_at.slice(0, 10);
  const series = [...groupBy(rows, day)]
    .sort(([a], [b]) => byString(a, b))
    .map(([date, group]) => ({ date, ...counts(group) }));
  const bySector = {};
  const sectors = groupBy(rows, (r) => r.sector);
  for (const name of sectorOrder) {
    if (!sectors.has(name)) continue;
    bySector[name] = [...groupBy(sectors.get(name), day)]
      .sort(([a], [b]) => byString(a, b))
      .map(([date, group]) => {
        const c = counts(group);
        return { date, count: c.count, avg_sentiment: c.avg_sentiment };
      });
  }
  return { series, by_sector: bySector };
}

export function sectors(articles, f) {
  const [start, end] = resolveRange(articles, f);
  return [...groupBy(select(articles, f, start, end), (r) => r.sector)]
    .map(([sector, group]) => ({ sector, ...counts(group) }))
    .sort((a, b) => b.count - a.count || byString(a.sector, b.sector));
}

export function keywords(articles, f, limit = 15) {
  const [start, end] = resolveRange(articles, f);
  const mid = addDays(start, Math.floor(daySpan(start, end) / 2));
  const groups = new Map();
  for (const a of select(articles, f, start, end)) {
    for (const k of a.keywords) {
      if (!groups.has(k)) groups.set(k, []);
      groups.get(k).push(a);
    }
  }
  return [...groups]
    .map(([keyword, group]) => {
      const recent = group.filter((a) => a.published_at.slice(0, 10) >= mid).length;
      const earlier = group.length - recent;
      return { keyword, ...counts(group), recent, earlier, momentum: recent - earlier };
    })
    .sort((a, b) => b.count - a.count || byString(a.keyword, b.keyword))
    .slice(0, limit);
}

export function articlesPage(articles, f, q, limit = 25, offset = 0) {
  const [start, end] = resolveRange(articles, f);
  let rows = select(articles, f, start, end);
  if (q) {
    const needle = q.toLowerCase();
    rows = rows.filter((a) => a.title.toLowerCase().includes(needle));
  }
  rows.sort((a, b) => byString(b.published_at, a.published_at) || byString(a.id, b.id));
  return { total: rows.length, limit, offset, items: rows.slice(offset, offset + limit) };
}

// The snapshot stores articles as {fields, rows} to keep the download small.
export function decodeSnapshot(snapshot) {
  const { fields, rows } = snapshot.articles;
  const articles = rows.map((row) => Object.fromEntries(fields.map((name, i) => [name, row[i]])));
  return { ...snapshot, articles };
}
