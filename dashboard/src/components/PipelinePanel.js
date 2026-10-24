"use client";

import { Fragment, useState } from "react";
import { fmtDateTime, fmtDuration, fmtInt, timeAgo } from "@/lib/format";
import { Card, Empty, StatusBadge } from "./ui";

function scheduleText(schedule) {
  if (!schedule) return null;
  if (schedule.via) return `Runs every ${schedule.interval_minutes / 60} hours on ${schedule.via}`;
  if (!schedule.enabled) return "Scheduler off (SCHEDULER_ENABLED=false)";
  const next = schedule.next_run_at ? ` · next ${fmtDateTime(schedule.next_run_at)}` : "";
  return `Runs every ${schedule.interval_minutes} min${next}`;
}

export default function PipelinePanel({ runs, schedule }) {
  const [open, setOpen] = useState(null);
  return (
    <Card title="Pipeline runs" subtitle={scheduleText(schedule)}>
      {!runs.length ? (
        <Empty>No pipeline runs yet.</Empty>
      ) : (
        <div className="-mx-4 overflow-x-auto sm:mx-0">
          <table className="w-full min-w-[38rem] text-left text-[12px] tabular">
            <thead className="text-ink-2">
              <tr className="border-b border-line">
                <th className="px-4 py-2 font-medium sm:pl-2">Run</th>
                <th className="px-2 py-2 font-medium">Status</th>
                <th className="px-2 py-2 font-medium">Started</th>
                <th className="px-2 py-2 text-right font-medium">Duration</th>
                <th className="px-2 py-2 text-right font-medium" title="Rows fetched from all sources">
                  Fetched
                </th>
                <th className="px-2 py-2 text-right font-medium" title="Rows that survived cleaning and de-duplication">
                  Clean
                </th>
                <th className="px-2 py-2 text-right font-medium">New</th>
                <th className="px-4 py-2 text-right font-medium sm:pr-2">Sources</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => {
                const sources = Object.entries(r.source_counts || {});
                const failed = Object.keys(r.errors || {});
                const expanded = open === r.id;
                return (
                  <Fragment key={r.id}>
                    <tr className="border-b border-line text-ink last:border-0">
                      <td className="px-4 py-2 sm:pl-2">
                        #{r.id} <span className="text-muted">{r.trigger}</span>
                      </td>
                      <td className="px-2 py-2">
                        <StatusBadge status={r.status} />
                      </td>
                      <td className="whitespace-nowrap px-2 py-2 text-ink-2" title={r.started_at}>
                        {fmtDateTime(r.started_at)} <span className="text-muted">({timeAgo(r.started_at)})</span>
                      </td>
                      <td className="px-2 py-2 text-right text-ink-2">{fmtDuration(r.duration_ms)}</td>
                      <td className="px-2 py-2 text-right">{fmtInt(r.fetched)}</td>
                      <td className="px-2 py-2 text-right">{fmtInt(r.clean)}</td>
                      <td className="px-2 py-2 text-right">{fmtInt(r.inserted)}</td>
                      <td className="px-4 py-2 text-right sm:pr-2">
                        <button
                          type="button"
                          aria-expanded={expanded}
                          onClick={() => setOpen(expanded ? null : r.id)}
                          className="rounded px-1 text-accent-ink hover:underline"
                        >
                          {sources.length - failed.length}/{sources.length || "–"} ok
                        </button>
                      </td>
                    </tr>
                    {expanded && (
                      <tr className="border-b border-line bg-surface-2">
                        <td colSpan={8} className="px-4 py-3 sm:px-3">
                          <ul className="grid gap-x-6 gap-y-1 sm:grid-cols-2 lg:grid-cols-4">
                            {sources.map(([name, count]) => (
                              <li key={name} className="flex justify-between gap-2">
                                <span className="text-ink-2">{name}</span>
                                <span className={r.errors?.[name] ? "font-medium text-critical-ink" : "text-ink"}>
                                  {r.errors?.[name] ? "failed" : `${fmtInt(count)} rows`}
                                </span>
                              </li>
                            ))}
                          </ul>
                          {failed.map((name) => (
                            <p key={name} className="mt-2 break-words text-critical-ink">
                              {name}: {r.errors[name]}
                            </p>
                          ))}
                          <p className="mt-2 text-muted">
                            {fmtInt(r.duplicates)} duplicates and {fmtInt(r.invalid)} invalid rows dropped ·{" "}
                            {fmtInt(r.updated)} existing articles refreshed · {fmtInt(r.pruned)} pruned past retention
                          </p>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
