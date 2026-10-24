"use client";

import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { daysBetween, fmtDay, fmtInt, fmtScore, rolling } from "@/lib/format";
import useTokens from "@/lib/useTokens";
import ChartTooltip from "./ChartTooltip";
import { Button, Card, Empty, Legend, Skeleton } from "./ui";

export function symmetricDomain(values, floor = 0.1) {
  const max = Math.max(floor, ...values.filter((v) => v !== null).map(Math.abs));
  const top = Math.ceil(max * 10) / 10;
  return [-top, top];
}

/** Five evenly spaced ticks with zero in the middle, e.g. -0.2, -0.1, 0, +0.1, +0.2. */
export const symmetricTicks = ([low, high]) => [low, low / 2, 0, high / 2, high];
export const fmtTick = (v) => (v > 0 ? `+${v.toFixed(2)}` : v < 0 ? v.toFixed(2) : "0");

function axisProps(t) {
  return {
    tick: { fill: t.muted, fontSize: 11 },
    tickLine: false,
    axisLine: { stroke: t.axis },
  };
}

const today = () => new Date().toISOString().slice(0, 10);
const dayTitle = (date) =>
  fmtDay(date, { weekday: "short", month: "short", day: "numeric" }) + (date === today() ? " · so far today" : "");

function SentimentTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <ChartTooltip
      title={dayTitle(d.date)}
      rows={[
        { label: "7-day average", value: fmtScore(d.rolling), color: "var(--accent)", shape: "line" },
        { label: "Daily average", value: fmtScore(d.avg), color: "var(--muted)", shape: "line" },
        { label: "Articles", value: fmtInt(d.count) },
      ]}
    />
  );
}

function VolumeTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <ChartTooltip
      title={dayTitle(d.date)}
      rows={[
        { label: "Positive", value: fmtInt(d.positive), color: "var(--positive)" },
        { label: "Neutral", value: fmtInt(d.neutral), color: "var(--neutral)" },
        { label: "Negative", value: fmtInt(d.negative), color: "var(--negative)" },
      ]}
      footer={`${fmtInt(d.count)} articles`}
    />
  );
}

function DailyTable({ rows }) {
  return (
    <div className="max-h-80 overflow-auto rounded-lg border border-line">
      <table className="w-full text-left text-[12px] tabular">
        <thead className="sticky top-0 bg-surface-2 text-ink-2">
          <tr>
            {["Date", "Articles", "Daily avg", "7-day avg", "Positive", "Neutral", "Negative"].map((h) => (
              <th key={h} className="px-3 py-2 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {[...rows].reverse().map((r) => (
            <tr key={r.date} className="border-t border-line text-ink">
              <td className="px-3 py-1.5">{fmtDay(r.date)}</td>
              <td className="px-3 py-1.5">{fmtInt(r.count)}</td>
              <td className="px-3 py-1.5">{fmtScore(r.avg)}</td>
              <td className="px-3 py-1.5">{fmtScore(r.rolling)}</td>
              <td className="px-3 py-1.5">{fmtInt(r.positive)}</td>
              <td className="px-3 py-1.5">{fmtInt(r.neutral)}</td>
              <td className="px-3 py-1.5">{fmtInt(r.negative)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function TrendCharts({ timeseries, range }) {
  const t = useTokens();
  const [asTable, setAsTable] = useState(false);

  const rows = useMemo(() => {
    const dates = daysBetween(range.start, range.end);
    const byDate = new Map(timeseries.series.map((d) => [d.date, d]));
    const avg7 = rolling(timeseries.series, dates);
    return dates.map((date, i) => {
      const d = byDate.get(date);
      return {
        date,
        avg: d?.avg_sentiment ?? null,
        rolling: avg7[i],
        count: d?.count ?? 0,
        positive: d?.positive ?? 0,
        neutral: d?.neutral ?? 0,
        negative: d?.negative ?? 0,
      };
    });
  }, [timeseries, range]);

  const hasData = timeseries.series.length > 0;
  const domain = symmetricDomain(rows.map((r) => r.avg));
  const tickGap = rows.length > 45 ? 40 : 24;
  const toggle = (
    <Button onClick={() => setAsTable((v) => !v)} aria-pressed={asTable}>
      {asTable ? "Show charts" : "View as table"}
    </Button>
  );

  return (
    <Card
      title="Sentiment over time"
      subtitle="Average score per day from −1 (negative) to +1 (positive), with a volume-weighted 7-day trend"
      actions={hasData && toggle}
    >
      {!hasData ? (
        <Empty />
      ) : asTable ? (
        <DailyTable rows={rows} />
      ) : !t ? (
        <Skeleton className="h-[25rem]" />
      ) : (
        <>
          <Legend
            items={[
              { label: "7-day average", color: t.accent, shape: "line" },
              { label: "Daily average", color: t.muted, shape: "line" },
            ]}
          />
          <div className="mt-2 h-60">
            <ResponsiveContainer>
              <LineChart data={rows} syncId="trend" margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
                <CartesianGrid vertical={false} stroke={t.grid} />
                <XAxis dataKey="date" tickFormatter={(d) => fmtDay(d)} minTickGap={tickGap} {...axisProps(t)} />
                <YAxis
                  domain={domain}
                  ticks={symmetricTicks(domain)}
                  tickFormatter={fmtTick}
                  width={48}
                  {...axisProps(t)}
                  axisLine={false}
                />
                <ReferenceLine y={0} stroke={t.axis} />
                <Tooltip content={<SentimentTooltip />} cursor={{ stroke: t.axis }} />
                <Line
                  dataKey="avg"
                  stroke={t.muted}
                  strokeWidth={1.25}
                  strokeOpacity={0.7}
                  dot={false}
                  activeDot={{ r: 3, fill: t.muted, stroke: t.surface, strokeWidth: 2 }}
                  isAnimationActive={false}
                />
                <Line
                  dataKey="rolling"
                  stroke={t.accent}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4.5, fill: t.accent, stroke: t.surface, strokeWidth: 2 }}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-5 flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="text-[13px] font-semibold text-ink">Daily volume by polarity</h3>
            <Legend
              items={[
                { label: "Positive", color: t.positive },
                { label: "Neutral", color: t.neutral },
                { label: "Negative", color: t.negative },
              ]}
            />
          </div>
          <div className="mt-2 h-36">
            <ResponsiveContainer>
              <BarChart data={rows} syncId="trend" barCategoryGap={rows.length > 45 ? 1 : 3} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
                <CartesianGrid vertical={false} stroke={t.grid} />
                <XAxis dataKey="date" tickFormatter={(d) => fmtDay(d)} minTickGap={tickGap} {...axisProps(t)} />
                <YAxis width={48} allowDecimals={false} {...axisProps(t)} axisLine={false} />
                <Tooltip content={<VolumeTooltip />} cursor={{ fill: t.grid, fillOpacity: 0.6 }} />
                <Bar dataKey="negative" stackId="v" fill={t.negative} stroke={t.surface} strokeWidth={1} isAnimationActive={false} />
                <Bar dataKey="neutral" stackId="v" fill={t.neutral} stroke={t.surface} strokeWidth={1} isAnimationActive={false} />
                <Bar
                  dataKey="positive"
                  stackId="v"
                  fill={t.positive}
                  stroke={t.surface}
                  strokeWidth={1}
                  radius={[3, 3, 0, 0]}
                  isAnimationActive={false}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </Card>
  );
}
