"use client";

import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { daysBetween, fmtDay, fmtInt, fmtPct, fmtScore, rolling } from "@/lib/format";
import useTokens from "@/lib/useTokens";
import ChartTooltip from "./ChartTooltip";
import { fmtTick, symmetricDomain, symmetricTicks } from "./TrendCharts";
import { Card, Empty, Legend, Skeleton, Swatch } from "./ui";

const SLOTS = ["series-1", "series-2", "series-3"];

export function SectorBreakdown({ sectors, selected, onSelect }) {
  const [hover, setHover] = useState(null);
  const max = Math.max(1, ...sectors.map((s) => s.count));
  return (
    <Card
      title="Sentiment by sector"
      subtitle="Share of negative, neutral and positive articles. Select a row to filter the whole dashboard."
      actions={
        <Legend
          items={[
            { label: "Negative", color: "var(--negative)" },
            { label: "Neutral", color: "var(--neutral)" },
            { label: "Positive", color: "var(--positive)" },
          ]}
        />
      }
    >
      {!sectors.length ? (
        <Empty />
      ) : (
        <ul className="space-y-1">
          {sectors.map((s) => {
            const active = selected === s.sector;
            return (
              <li key={s.sector} className="relative">
                <button
                  type="button"
                  aria-pressed={active}
                  onClick={() => onSelect(active ? "" : s.sector)}
                  onMouseEnter={() => setHover(s.sector)}
                  onMouseLeave={() => setHover(null)}
                  onFocus={() => setHover(s.sector)}
                  onBlur={() => setHover(null)}
                  className={`grid w-full grid-cols-[minmax(0,8.5rem)_minmax(0,1fr)_3.25rem] items-center gap-x-3 rounded-lg px-2 py-1.5 text-left transition sm:grid-cols-[10rem_minmax(0,1fr)_4rem_3.5rem] ${
                    active ? "bg-surface-2 ring-1 ring-line" : "hover:bg-surface-2"
                  }`}
                >
                  <span className="truncate text-[13px] text-ink">{s.sector}</span>
                  <span className="flex h-3 gap-[2px]" style={{ width: `${Math.max(8, (s.count / max) * 100)}%` }}>
                    {["negative", "neutral", "positive"].map((p, i) =>
                      s[p] ? (
                        <span
                          key={p}
                          className={`h-full ${i === 0 ? "rounded-l-[3px]" : ""} ${i === 2 || (i === 1 && !s.positive) ? "rounded-r-[3px]" : ""}`}
                          style={{ flexGrow: s[p], flexBasis: 0, background: `var(--${p})`, minWidth: 2 }}
                        />
                      ) : null,
                    )}
                  </span>
                  <span className="text-right text-[12px] text-ink-2 tabular">{fmtScore(s.avg_sentiment)}</span>
                  <span className="hidden text-right text-[12px] text-muted tabular sm:block">{fmtInt(s.count)}</span>
                </button>
                {hover === s.sector && (
                  <div className="absolute left-1/3 top-full z-10 mt-1">
                    <ChartTooltip
                      title={s.sector}
                      rows={[
                        { label: "Positive", value: `${fmtInt(s.positive)} · ${fmtPct(s.positive, s.count)}`, color: "var(--positive)" },
                        { label: "Neutral", value: `${fmtInt(s.neutral)} · ${fmtPct(s.neutral, s.count)}`, color: "var(--neutral)" },
                        { label: "Negative", value: `${fmtInt(s.negative)} · ${fmtPct(s.negative, s.count)}`, color: "var(--negative)" },
                        { label: "Average score", value: fmtScore(s.avg_sentiment) },
                      ]}
                      footer={`${fmtInt(s.count)} articles`}
                    />
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
      {sectors.length > 0 && (
        <p className="mt-3 flex justify-end gap-6 pr-2 text-[11px] text-muted">
          <span>avg score</span>
          <span className="hidden sm:inline">articles</span>
        </p>
      )}
    </Card>
  );
}

function CompareTooltip({ active, payload, picks }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <ChartTooltip
      title={fmtDay(d.date, { weekday: "short", month: "short", day: "numeric" })}
      rows={picks
        .map((sector, slot) => sector && { label: sector, value: fmtScore(d[sector]), color: `var(--${SLOTS[slot]})`, shape: "line" })
        .filter(Boolean)}
      footer="7-day volume-weighted average"
    />
  );
}

export function SectorCompare({ timeseries, sectors, range }) {
  const t = useTokens();
  const available = sectors.map((s) => s.sector);
  // picks[slot] = sector name. A sector keeps its slot (and colour) until removed,
  // so removing one never repaints the others.
  const [picks, setPicks] = useState([null, null, null]);

  useEffect(() => {
    setPicks((current) => {
      const kept = current.map((s) => (s && available.includes(s) ? s : null));
      if (kept.some(Boolean)) return kept;
      const defaults = available.filter((s) => s !== "General Tech").slice(0, 3);
      return [0, 1, 2].map((i) => defaults[i] ?? null);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [available.join("|")]);

  const toggle = (sector) =>
    setPicks((current) => {
      const at = current.indexOf(sector);
      if (at >= 0) return current.map((s, i) => (i === at ? null : s));
      const free = current.indexOf(null);
      return free < 0 ? current : current.map((s, i) => (i === free ? sector : s));
    });

  const rows = useMemo(() => {
    const dates = daysBetween(range.start, range.end);
    const lines = Object.fromEntries(
      picks.filter(Boolean).map((sector) => [sector, rolling(timeseries.by_sector[sector] ?? [], dates)]),
    );
    return dates.map((date, i) => ({ date, ...Object.fromEntries(Object.entries(lines).map(([s, v]) => [s, v[i]])) }));
  }, [timeseries, range, picks]);

  const values = rows.flatMap((r) => picks.filter(Boolean).map((s) => r[s] ?? null));
  const full = picks.every(Boolean);
  const domain = symmetricDomain(values);

  return (
    <Card title="Compare sectors" subtitle="7-day sentiment trend for up to three sectors">
      <div className="flex flex-wrap gap-1.5">
        {available.map((sector) => {
          const slot = picks.indexOf(sector);
          const on = slot >= 0;
          return (
            <button
              key={sector}
              type="button"
              aria-pressed={on}
              disabled={!on && full}
              onClick={() => toggle(sector)}
              title={!on && full ? "Remove a sector to add another" : undefined}
              className={`inline-flex h-7 items-center gap-1.5 rounded-full border px-2.5 text-[12px] transition disabled:cursor-not-allowed disabled:opacity-40 ${
                on ? "border-ink/20 bg-surface-2 font-medium text-ink" : "border-line text-ink-2 hover:bg-surface-2"
              }`}
            >
              {on && <Swatch color={`var(--${SLOTS[slot]})`} shape="line" />}
              {sector}
            </button>
          );
        })}
      </div>
      <div className="mt-3 h-56">
        {!available.length ? (
          <Empty />
        ) : !t ? (
          <Skeleton className="h-full" />
        ) : !picks.some(Boolean) ? (
          <Empty>Pick a sector above to plot it.</Empty>
        ) : (
          <ResponsiveContainer>
            <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
              <CartesianGrid vertical={false} stroke={t.grid} />
              <XAxis
                dataKey="date"
                tickFormatter={(d) => fmtDay(d)}
                minTickGap={32}
                tick={{ fill: t.muted, fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: t.axis }}
              />
              <YAxis
                domain={domain}
                ticks={symmetricTicks(domain)}
                tickFormatter={fmtTick}
                width={48}
                tick={{ fill: t.muted, fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <ReferenceLine y={0} stroke={t.axis} />
              <Tooltip content={<CompareTooltip picks={picks} />} cursor={{ stroke: t.axis }} />
              {picks.map((sector, slot) =>
                sector ? (
                  <Line
                    key={sector}
                    dataKey={sector}
                    stroke={t[SLOTS[slot]]}
                    strokeWidth={2}
                    dot={false}
                    connectNulls={false}
                    activeDot={{ r: 4.5, fill: t[SLOTS[slot]], stroke: t.surface, strokeWidth: 2 }}
                    isAnimationActive={false}
                  />
                ) : null,
              )}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}
