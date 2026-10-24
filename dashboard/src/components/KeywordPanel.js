"use client";

import { useState } from "react";
import { fmtInt, fmtPct, fmtScore, POLARITY_COLOR } from "@/lib/format";
import ChartTooltip from "./ChartTooltip";
import { Card, Empty, Swatch } from "./ui";

const polarityOf = (score) => (score >= 0.05 ? "positive" : score <= -0.05 ? "negative" : "neutral");

function Momentum({ value }) {
  if (!value) return <span className="text-muted">■ 0</span>;
  return (
    <span className="text-ink-2">
      {value > 0 ? "▲" : "▼"} {Math.abs(value)}
    </span>
  );
}

export default function KeywordPanel({ keywords, range }) {
  const [hover, setHover] = useState(null);
  const max = Math.max(1, ...keywords.map((k) => k.count));
  return (
    <Card
      title="Top trending keywords"
      subtitle="Tracked terms by mentions. Momentum compares the second half of the range with the first."
    >
      {!keywords.length ? (
        <Empty />
      ) : (
        <>
          <div className="mb-1 grid grid-cols-[minmax(0,7.5rem)_minmax(0,1fr)_3.5rem_3rem] gap-x-3 px-2 text-[11px] text-muted">
            <span>Keyword</span>
            <span>Mentions</span>
            <span className="text-right">Avg</span>
            <span className="text-right">Trend</span>
          </div>
          <ol className="space-y-0.5">
            {keywords.map((k, i) => (
              <li
                key={k.keyword}
                tabIndex={0}
                onMouseEnter={() => setHover(k.keyword)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(k.keyword)}
                onBlur={() => setHover(null)}
                className="relative grid grid-cols-[minmax(0,7.5rem)_minmax(0,1fr)_3.5rem_3rem] items-center gap-x-3 rounded-lg px-2 py-1.5 outline-none hover:bg-surface-2 focus-visible:bg-surface-2"
              >
                <span className="truncate text-[13px] text-ink">
                  <span className="mr-1.5 text-muted tabular">{i + 1}</span>
                  {k.keyword}
                </span>
                <span className="flex min-w-0 items-center gap-2">
                  <span className="min-w-0 flex-1">
                    <span
                      className="block h-2.5 rounded-r-[3px] bg-accent"
                      style={{ width: `${Math.max(2, (k.count / max) * 100)}%` }}
                    />
                  </span>
                  <span className="w-8 shrink-0 text-right text-[12px] text-ink-2 tabular">{fmtInt(k.count)}</span>
                </span>
                <span className="flex items-center justify-end gap-1.5 text-[12px] text-ink-2 tabular">
                  <Swatch color={POLARITY_COLOR[polarityOf(k.avg_sentiment)]} shape="dot" />
                  {fmtScore(k.avg_sentiment).replace(/^([+-]?)0\./, "$1.")}
                </span>
                <span className="text-right text-[12px] tabular">
                  <Momentum value={k.momentum} />
                </span>
                {hover === k.keyword && (
                  <div className="absolute left-1/3 top-full z-10 mt-1">
                    <ChartTooltip
                      title={k.keyword}
                      rows={[
                        { label: "Mentions", value: fmtInt(k.count) },
                        { label: "Average score", value: fmtScore(k.avg_sentiment) },
                        { label: "Positive", value: fmtPct(k.positive, k.count), color: "var(--positive)" },
                        { label: "Negative", value: fmtPct(k.negative, k.count), color: "var(--negative)" },
                        { label: "Earlier half", value: fmtInt(k.earlier) },
                        { label: "Later half", value: fmtInt(k.recent) },
                      ]}
                      footer={`${range.start} → ${range.end}`}
                    />
                  </div>
                )}
              </li>
            ))}
          </ol>
        </>
      )}
    </Card>
  );
}
