export const POLARITY_LABEL = { positive: "Positive", neutral: "Neutral", negative: "Negative" };
export const POLARITY_COLOR = {
  positive: "var(--positive)",
  neutral: "var(--neutral)",
  negative: "var(--negative)",
};

const DAY_MS = 86_400_000;

export const fmtInt = (n) => (n ?? 0).toLocaleString("en-US");

export function fmtScore(x) {
  if (x === null || x === undefined) return "–";
  const s = x.toFixed(3);
  return x > 0 ? `+${s}` : s;
}

export const fmtPct = (part, whole) => (whole ? `${Math.round((part / whole) * 100)}%` : "–");

export function fmtDay(iso, opts = { month: "short", day: "numeric" }) {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-US", { ...opts, timeZone: "UTC" });
}

export function fmtDateTime(iso) {
  if (!iso) return "–";
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function timeAgo(iso, now = Date.now()) {
  if (!iso) return "never";
  const mins = Math.round((now - Date.parse(iso)) / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 48) return `${hours} h ago`;
  return `${Math.round(hours / 24)} days ago`;
}

export function fmtDuration(ms) {
  if (ms === null || ms === undefined) return "–";
  if (ms < 1000) return `${ms} ms`;
  const s = ms / 1000;
  return s < 90 ? `${s.toFixed(1)} s` : `${Math.round(s / 60)} min`;
}

export const addDays = (iso, n) => new Date(Date.parse(`${iso}T00:00:00Z`) + n * DAY_MS).toISOString().slice(0, 10);

/** Every calendar day from start to end, so gaps show as gaps instead of being bridged. */
export function daysBetween(start, end) {
  const out = [];
  for (let d = start; d <= end; d = addDays(d, 1)) out.push(d);
  return out;
}

/** Volume-weighted trailing average: sum(score) / sum(count) over the last `window` days. */
export function rolling(series, dates, window = 7) {
  const byDate = new Map(series.map((d) => [d.date, d]));
  return dates.map((date, i) => {
    let sum = 0;
    let count = 0;
    for (let j = Math.max(0, i - window + 1); j <= i; j++) {
      const d = byDate.get(dates[j]);
      if (d && d.count) {
        sum += d.avg_sentiment * d.count;
        count += d.count;
      }
    }
    return count ? sum / count : null;
  });
}
