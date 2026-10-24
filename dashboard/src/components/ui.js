import { POLARITY_COLOR, POLARITY_LABEL, fmtScore } from "@/lib/format";

export function Card({ title, subtitle, actions, children, className = "" }) {
  return (
    <section className={`rounded-xl border border-line bg-surface p-4 sm:p-5 min-w-0 ${className}`}>
      {(title || actions) && (
        <header className="mb-4 flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
          <div className="min-w-0">
            <h2 className="text-[15px] font-semibold text-ink">{title}</h2>
            {subtitle && <p className="mt-0.5 text-[13px] text-muted">{subtitle}</p>}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

export function Swatch({ color, shape = "square" }) {
  const base = shape === "line" ? "h-[3px] w-3.5 rounded-full" : shape === "dot" ? "size-2 rounded-full" : "size-2.5 rounded-[3px]";
  return <span aria-hidden className={`inline-block shrink-0 ${base}`} style={{ background: color }} />;
}

export function Legend({ items }) {
  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px] text-ink-2">
      {items.map((item) => (
        <li key={item.label} className="flex items-center gap-1.5">
          <Swatch color={item.color} shape={item.shape} />
          {item.label}
        </li>
      ))}
    </ul>
  );
}

export function PolarityChip({ polarity, score }) {
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-[12px] text-ink-2 tabular">
      <Swatch color={POLARITY_COLOR[polarity]} shape="dot" />
      <span className="sr-only">{POLARITY_LABEL[polarity]}</span>
      <span title={POLARITY_LABEL[polarity]}>{fmtScore(score)}</span>
    </span>
  );
}

const STATUS = {
  success: { label: "Success", icon: "✓", color: "var(--good)" },
  partial: { label: "Partial", icon: "!", color: "var(--warning)" },
  failed: { label: "Failed", icon: "✕", color: "var(--critical)" },
  running: { label: "Running", icon: "…", color: "var(--accent)" },
};

export function StatusBadge({ status }) {
  const s = STATUS[status] ?? STATUS.running;
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-[12px] font-medium text-ink">
      <span
        aria-hidden
        className="grid size-4 place-items-center rounded-full text-[10px] font-bold leading-none text-white"
        style={{ background: s.color }}
      >
        {s.icon}
      </span>
      {s.label}
    </span>
  );
}

export function Button({ children, variant = "ghost", className = "", ...props }) {
  const styles =
    variant === "primary"
      ? "bg-accent text-white hover:opacity-90 border-transparent"
      : "bg-surface text-ink hover:bg-surface-2 border-line";
  return (
    <button
      type="button"
      className={`inline-flex h-8 items-center justify-center gap-1.5 rounded-lg border px-3 text-[13px] font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Skeleton({ className = "" }) {
  return <div className={`animate-pulse rounded-lg bg-surface-2 ${className}`} />;
}

export function ErrorNote({ error, onRetry }) {
  return (
    <div role="alert" className="flex flex-wrap items-center gap-3 rounded-lg border border-line bg-surface-2 px-4 py-3 text-[13px] text-ink-2">
      <span className="font-semibold text-critical-ink">Couldn't load data.</span>
      <span className="min-w-0 break-words">{String(error?.message ?? error)}</span>
      {onRetry && (
        <Button onClick={onRetry} className="ml-auto">
          Retry
        </Button>
      )}
    </div>
  );
}

export function Empty({ children = "No articles match these filters." }) {
  return <p className="py-10 text-center text-[13px] text-muted">{children}</p>;
}
