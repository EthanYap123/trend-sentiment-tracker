import { fmtInt, fmtScore } from "@/lib/format";

function Delta({ value, format, betterWhenUp = true, unit = "" }) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return <span className="text-muted">no earlier data</span>;
  }
  // Judge "no change" on the rounded text, so -0.3% never shows as a red "-0%".
  const text = format(value);
  const flat = Number(text) === 0;
  const good = flat ? null : value > 0 === betterWhenUp;
  const color = good === null ? "text-muted" : good ? "text-good-ink" : "text-critical-ink";
  return (
    <span className={`${color} tabular`}>
      {flat ? "■ " : value > 0 ? "▲ " : "▼ "}
      {flat ? text.replace(/^[+-]/, "") : text}
      {unit}
    </span>
  );
}

function Tile({ label, value, delta, hint }) {
  return (
    <div className="min-w-0 rounded-xl border border-line bg-surface px-4 py-3.5">
      <p className="text-[13px] text-ink-2">{label}</p>
      <p className="mt-1 text-[28px] font-semibold leading-tight tracking-tight text-ink">{value}</p>
      <p className="mt-1 truncate text-[12px]">
        {delta} {hint && <span className="text-muted">{hint}</span>}
      </p>
    </div>
  );
}

const share = (part, whole) => (whole ? (part / whole) * 100 : null);

export default function KpiRow({ summary }) {
  const prev = summary.previous;
  const vs = `vs prior ${summary.days}d`;
  const posShare = share(summary.positive, summary.count);
  const negShare = share(summary.negative, summary.count);
  const prevPos = prev ? share(prev.positive, prev.count) : null;
  const prevNeg = prev ? share(prev.negative, prev.count) : null;
  const pctDelta = (a, b) => (a === null || b === null ? null : a - b);
  const signed = (v, digits = 1) => `${v > 0 ? "+" : ""}${v.toFixed(digits)}`;

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Tile
        label="Articles analysed"
        value={fmtInt(summary.count)}
        delta={
          <Delta
            value={prev?.count ? ((summary.count - prev.count) / prev.count) * 100 : null}
            format={(v) => signed(v, 0)}
            unit="%"
          />
        }
        hint={prev?.count ? vs : null}
      />
      <Tile
        label="Average sentiment"
        value={fmtScore(summary.avg_sentiment)}
        delta={
          <Delta
            value={
              prev?.avg_sentiment !== null && prev?.avg_sentiment !== undefined && summary.avg_sentiment !== null
                ? summary.avg_sentiment - prev.avg_sentiment
                : null
            }
            format={(v) => signed(v, 3)}
          />
        }
        hint={prev ? vs : null}
      />
      <Tile
        label="Positive share"
        value={posShare === null ? "–" : `${Math.round(posShare)}%`}
        delta={<Delta value={pctDelta(posShare, prevPos)} format={(v) => signed(v)} unit=" pts" />}
        hint={prev ? vs : null}
      />
      <Tile
        label="Negative share"
        value={negShare === null ? "–" : `${Math.round(negShare)}%`}
        delta={
          <Delta value={pctDelta(negShare, prevNeg)} format={(v) => signed(v)} unit=" pts" betterWhenUp={false} />
        }
        hint={prev ? vs : null}
      />
    </div>
  );
}
