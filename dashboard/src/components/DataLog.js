"use client";

import { useEffect, useState } from "react";
import { getArticles } from "@/lib/data";
import { fmtDateTime, fmtInt } from "@/lib/format";
import { Button, Card, Empty, ErrorNote, PolarityChip, Skeleton } from "./ui";

const PAGE_SIZE = 20;

export default function DataLog({ filters, version }) {
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const [state, setState] = useState({ loading: true, error: null, page: null });
  const [retry, setRetry] = useState(0);

  // Debounce typing so each keystroke isn't a request.
  useEffect(() => {
    const id = setTimeout(() => setQ(search.trim()), 300);
    return () => clearTimeout(id);
  }, [search]);

  const key = JSON.stringify(filters);
  useEffect(() => setOffset(0), [key, q]);

  useEffect(() => {
    let live = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    getArticles(filters, q, PAGE_SIZE, offset)
      .then((page) => live && setState({ loading: false, error: null, page }))
      .catch((error) => live && setState({ loading: false, error, page: null }));
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, q, offset, version, retry]);

  const page = state.page;
  const end = page ? Math.min(offset + PAGE_SIZE, page.total) : 0;

  return (
    <Card
      title="Recent data log"
      subtitle="Every processed article, newest first, with its sector and sentiment score"
      actions={
        <label className="flex h-8 w-full items-center gap-2 rounded-lg border border-line bg-surface px-2.5 text-[13px] sm:w-64">
          <svg aria-hidden viewBox="0 0 20 20" className="size-4 shrink-0 fill-muted">
            <path d="M8.5 3a5.5 5.5 0 0 1 4.38 8.82l3.65 3.65-1.06 1.06-3.65-3.65A5.5 5.5 0 1 1 8.5 3Zm0 1.5a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z" />
          </svg>
          <span className="sr-only">Search headlines</span>
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search headlines"
            className="min-w-0 flex-1 bg-transparent text-ink outline-none placeholder:text-muted"
          />
        </label>
      }
    >
      {state.error ? (
        <ErrorNote error={state.error} onRetry={() => setRetry((n) => n + 1)} />
      ) : !page ? (
        <Skeleton className="h-96" />
      ) : !page.items.length ? (
        <Empty>{q ? `No headlines match “${q}”.` : undefined}</Empty>
      ) : (
        <div className={state.loading ? "opacity-60 transition" : "transition"}>
          <div className="-mx-4 overflow-x-auto sm:mx-0">
            <table className="w-full min-w-[40rem] text-left text-[13px]">
              <thead className="text-[12px] text-ink-2">
                <tr className="border-b border-line">
                  <th className="px-4 py-2 font-medium sm:pl-2" title="Shown in your local time zone">
                    Published
                  </th>
                  <th className="px-2 py-2 font-medium">Headline</th>
                  <th className="px-2 py-2 font-medium">Sector</th>
                  <th className="px-2 py-2 text-right font-medium">Score</th>
                  <th className="px-4 py-2 text-right font-medium sm:pr-2">Engagement</th>
                </tr>
              </thead>
              <tbody>
                {page.items.map((a) => (
                  <tr key={a.id} className="border-b border-line align-top last:border-0 hover:bg-surface-2">
                    <td className="whitespace-nowrap px-4 py-2.5 text-[12px] text-muted tabular sm:pl-2">
                      {fmtDateTime(a.published_at)}
                    </td>
                    <td className="max-w-[28rem] px-2 py-2.5">
                      <a
                        href={a.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-ink decoration-line underline-offset-2 hover:text-accent-ink hover:underline"
                      >
                        {a.title}
                      </a>
                      <p className="mt-0.5 text-[12px] text-muted">
                        {a.source}
                        {a.keywords.length > 0 && <> · {a.keywords.join(", ")}</>}
                      </p>
                    </td>
                    <td className="whitespace-nowrap px-2 py-2.5 text-[12px] text-ink-2">{a.sector}</td>
                    <td className="px-2 py-2.5 text-right">
                      <PolarityChip polarity={a.polarity} score={a.sentiment} />
                    </td>
                    <td className="whitespace-nowrap px-4 py-2.5 text-right text-[12px] text-ink-2 tabular sm:pr-2">
                      {a.engagement === null || a.engagement === undefined ? (
                        <span className="text-muted">–</span>
                      ) : (
                        <>
                          {fmtInt(a.engagement)} <span className="text-muted">pts</span>
                          {a.comments !== null && a.comments !== undefined && (
                            <>
                              {" "}
                              · {fmtInt(a.comments)} <span className="text-muted">cmt</span>
                            </>
                          )}
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 flex items-center justify-between gap-3 text-[12px] text-ink-2">
            <span className="tabular">
              {fmtInt(offset + 1)}–{fmtInt(end)} of {fmtInt(page.total)}
            </span>
            <div className="flex gap-2">
              <Button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
                Previous
              </Button>
              <Button disabled={end >= page.total} onClick={() => setOffset(offset + PAGE_SIZE)}>
                Next
              </Button>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
