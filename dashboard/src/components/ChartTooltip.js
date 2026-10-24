import { Swatch } from "./ui";

/** Shared tooltip shell: a heading plus label/value rows with optional swatches. */
export default function ChartTooltip({ title, rows, footer }) {
  return (
    <div className="pointer-events-none min-w-[11rem] rounded-lg border border-line bg-surface px-3 py-2.5 text-[12px] shadow-lg">
      <p className="mb-1.5 font-semibold text-ink">{title}</p>
      <dl className="space-y-1">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center justify-between gap-4">
            <dt className="flex items-center gap-1.5 text-ink-2">
              {row.color && <Swatch color={row.color} shape={row.shape} />}
              {row.label}
            </dt>
            <dd className="font-medium text-ink tabular">{row.value}</dd>
          </div>
        ))}
      </dl>
      {footer && <p className="mt-1.5 border-t border-line pt-1.5 text-muted">{footer}</p>}
    </div>
  );
}
