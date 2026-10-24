"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DataLog from "@/components/DataLog";
import FilterBar from "@/components/FilterBar";
import KeywordPanel from "@/components/KeywordPanel";
import KpiRow from "@/components/KpiRow";
import PipelinePanel from "@/components/PipelinePanel";
import { SectorBreakdown, SectorCompare } from "@/components/SectorPanels";
import TrendCharts from "@/components/TrendCharts";
import { Button, ErrorNote, Skeleton, StatusBadge } from "@/components/ui";
import { SOURCE, getDashboard, getMeta, getRuns, getSchedule, triggerRun } from "@/lib/data";
import { addDays, fmtInt, timeAgo } from "@/lib/format";

const REPO_URL = "https://github.com/EthanYap123/trend-sentiment-tracker";
const DEFAULT_FILTERS = { range: "30", start: "", end: "", sector: "", polarity: "", source: "" };
const URL_KEYS = Object.keys(DEFAULT_FILTERS);

function readUrlFilters() {
  const params = new URLSearchParams(window.location.search);
  const out = { ...DEFAULT_FILTERS };
  for (const key of URL_KEYS) if (params.get(key)) out[key] = params.get(key);
  if (!["7", "30", "90", "custom"].includes(out.range)) out.range = "30";
  return out;
}

function writeUrlFilters(filters) {
  const params = new URLSearchParams();
  for (const key of URL_KEYS) {
    if (filters[key] && filters[key] !== DEFAULT_FILTERS[key]) params.set(key, filters[key]);
  }
  if (filters.range !== "custom") {
    params.delete("start");
    params.delete("end");
  }
  const qs = params.toString();
  window.history.replaceState(null, "", qs ? `?${qs}` : window.location.pathname);
}

/** Turns the UI state into concrete query filters, anchored on the latest day with data. */
function toQuery(ui, meta) {
  const last = meta.last_date;
  let start, end;
  if (ui.range === "custom") {
    start = ui.start || addDays(last, -29);
    end = ui.end || last;
    if (start > end) [start, end] = [end, start];
  } else {
    end = last;
    start = addDays(last, -(Number(ui.range) - 1));
  }
  if (meta.first_date && start < meta.first_date) start = meta.first_date;
  return { start, end, sector: ui.sector, polarity: ui.polarity, source: ui.source };
}

function Header({ meta, running, onRun }) {
  const last = meta?.last_run;
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <p className="text-[12px] font-medium uppercase tracking-[0.08em] text-accent-ink">ETL pipeline · NLP · Analytics</p>
        <h1 className="mt-1 text-[26px] font-semibold leading-tight tracking-tight text-ink sm:text-[30px]">
          Tech Trend Sentiment Tracker
        </h1>
        <p className="mt-1 max-w-2xl text-[14px] text-ink-2">
          Headlines from Hacker News, DEV.to and six tech and market news feeds, cleaned, scored for sentiment and
          tagged by sector on a schedule.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-[12px] text-ink-2">
        {meta && (
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            {last && <StatusBadge status={running ? "running" : last.status} />}
            <span>
              Last run {last ? timeAgo(last.finished_at ?? last.started_at) : "never"} · {fmtInt(meta.total_articles)}{" "}
              articles
            </span>
          </span>
        )}
        {SOURCE === "api" ? (
          <Button variant="primary" onClick={onRun} disabled={running}>
            {running ? "Running…" : "Run pipeline now"}
          </Button>
        ) : (
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-line bg-surface px-3 text-[13px] font-medium text-ink hover:bg-surface-2"
          >
            <svg aria-hidden viewBox="0 0 16 16" className="size-4 fill-current">
              <path d="M8 0a8 8 0 0 0-2.53 15.59c.4.07.55-.17.55-.38v-1.33c-2.23.48-2.7-1.07-2.7-1.07-.36-.92-.89-1.17-.89-1.17-.73-.5.06-.49.06-.49.8.06 1.23.83 1.23.83.72 1.22 1.87.87 2.33.67.07-.52.28-.87.5-1.07-1.78-.2-3.65-.89-3.65-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.22 2.2.82a7.6 7.6 0 0 1 4 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.28.82 2.15 0 3.07-1.87 3.75-3.66 3.95.29.25.54.73.54 1.48v2.2c0 .21.15.46.55.38A8 8 0 0 0 8 0Z" />
            </svg>
            Source on GitHub
          </a>
        )}
      </div>
    </header>
  );
}

export default function Home() {
  const [meta, setMeta] = useState(null);
  const [ui, setUi] = useState(null);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [runs, setRuns] = useState([]);
  const [schedule, setSchedule] = useState(null);
  const [version, setVersion] = useState(0);
  const [running, setRunning] = useState(false);
  const [notice, setNotice] = useState(null);
  const pollRef = useRef(null);

  const loadMeta = useCallback(async () => {
    const [m, r, s] = await Promise.all([getMeta(), getRuns(), getSchedule()]);
    setMeta(m);
    setRuns(r);
    setSchedule(s);
    return m;
  }, []);

  useEffect(() => {
    setUi(readUrlFilters());
    loadMeta().catch(setError);
    return () => clearInterval(pollRef.current);
  }, [loadMeta]);

  const query = useMemo(() => (meta?.last_date && ui ? toQuery(ui, meta) : null), [meta, ui]);

  useEffect(() => {
    if (!query) return;
    let live = true;
    setLoading(true);
    getDashboard(query)
      .then((d) => {
        if (!live) return;
        setData(d);
        setError(null);
      })
      .catch((e) => live && setError(e))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, [query, version]);

  const updateFilters = (next) => {
    setUi(next);
    writeUrlFilters(next);
  };

  const runNow = async () => {
    setNotice(null);
    const before = runs[0]?.id ?? 0;
    try {
      setRunning(true);
      await triggerRun();
    } catch (e) {
      setRunning(false);
      setNotice(e.message);
      return;
    }
    clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const latest = await getRuns();
        setRuns(latest);
        const run = latest[0];
        if (run && run.id > before && run.status !== "running") {
          clearInterval(pollRef.current);
          setRunning(false);
          setNotice(`Run #${run.id} finished: ${fmtInt(run.inserted)} new, ${fmtInt(run.updated)} refreshed.`);
          await loadMeta();
          setVersion((v) => v + 1);
        }
      } catch (e) {
        clearInterval(pollRef.current);
        setRunning(false);
        setNotice(e.message);
      }
    }, 2500);
  };

  const isDefault = ui && URL_KEYS.every((k) => ui[k] === DEFAULT_FILTERS[k]);
  const range = query && { start: query.start, end: query.end };
  const emptyDb = meta && !meta.last_date;

  return (
    <main className="mx-auto max-w-[1280px] px-4 pb-16 pt-8 sm:px-6 lg:px-8">
      <Header meta={meta} running={running} onRun={runNow} />

      {notice && (
        <p role="status" className="mt-4 rounded-lg border border-line bg-surface px-4 py-2.5 text-[13px] text-ink-2">
          {notice}
        </p>
      )}

      <div className="z-20 -mx-4 mt-6 lg:sticky lg:top-0 border-b border-line bg-page px-4 py-3 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
        {meta && ui ? (
          <div className="flex flex-wrap items-center justify-between gap-2">
            <FilterBar
              filters={ui}
              meta={meta}
              onChange={updateFilters}
              onReset={() => updateFilters(DEFAULT_FILTERS)}
              isDefault={isDefault}
            />
            {range && (
              <span className="text-[12px] text-muted tabular" aria-live="polite">
                {loading ? "Updating…" : `${range.start} → ${range.end} (UTC)`}
              </span>
            )}
          </div>
        ) : (
          <Skeleton className="h-8 w-full max-w-2xl" />
        )}
      </div>

      <div className="mt-6 space-y-4">
        {error && <ErrorNote error={error} onRetry={() => (meta ? setVersion((v) => v + 1) : loadMeta().catch(setError))} />}

        {emptyDb ? (
          <ErrorNote error="The database is empty. Run `python -m pipeline.run --backfill 30` to load history." />
        ) : !data || !range ? (
          !error && (
            <>
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                {[0, 1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-[6.5rem]" />
                ))}
              </div>
              <Skeleton className="h-[30rem]" />
            </>
          )
        ) : (
          <div className={`space-y-4 transition-opacity ${loading ? "opacity-70" : ""}`}>
            <KpiRow summary={data.summary} />
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
              <TrendCharts timeseries={data.timeseries} range={range} />
              <KeywordPanel keywords={data.keywords} range={range} />
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <SectorBreakdown
                sectors={data.sectors}
                selected={ui.sector}
                onSelect={(sector) => updateFilters({ ...ui, sector })}
              />
              <SectorCompare timeseries={data.timeseries} sectors={data.sectors} range={range} />
            </div>
            <DataLog filters={query} version={version} />
            <PipelinePanel runs={runs} schedule={schedule} />
          </div>
        )}
      </div>

      <footer className="mt-10 border-t border-line pt-5 text-[12px] leading-relaxed text-muted">
        <p>
          Sources: Hacker News (Algolia API, stories with 20+ points), DEV.to API, and RSS from TechCrunch, The Verge,
          Ars Technica, CNBC Tech, Wired and Engadget. Sentiment uses the VADER lexicon with a tech and markets
          dictionary on top; scores run from −1 to +1, and anything within ±0.05 counts as neutral. Dates are UTC.
        </p>
        <p className="mt-2">
          {SOURCE === "static"
            ? "This demo reads a snapshot that a GitHub Actions cron job rebuilds every 6 hours. "
            : "Served by the FastAPI backend. "}
          <a href={REPO_URL} target="_blank" rel="noopener noreferrer" className="text-accent-ink hover:underline">
            Source and pipeline docs on GitHub
          </a>
          .
        </p>
      </footer>
    </main>
  );
}
