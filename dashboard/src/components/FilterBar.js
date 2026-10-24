import { Button } from "./ui";

export const RANGES = [
  { id: "7", label: "7D" },
  { id: "30", label: "30D" },
  { id: "90", label: "90D" },
  { id: "custom", label: "Custom" },
];
const POLARITIES = [
  { id: "", label: "All" },
  { id: "positive", label: "Positive" },
  { id: "neutral", label: "Neutral" },
  { id: "negative", label: "Negative" },
];

function Segmented({ label, options, value, onChange }) {
  return (
    <div role="radiogroup" aria-label={label} className="flex h-8 rounded-lg border border-line bg-surface-2 p-0.5">
      {options.map((o) => (
        <button
          key={o.id}
          type="button"
          role="radio"
          aria-checked={value === o.id}
          onClick={() => onChange(o.id)}
          className={`rounded-md px-2.5 text-[13px] font-medium transition ${
            value === o.id ? "bg-surface text-ink shadow-sm" : "text-ink-2 hover:text-ink"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function Select({ label, value, onChange, options, allLabel }) {
  return (
    <label className="flex h-8 min-w-0 items-center gap-2 rounded-lg border border-line bg-surface pl-2.5 text-[13px]">
      <span className="text-muted">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-full min-w-0 max-w-[11rem] cursor-pointer rounded-lg bg-transparent pr-2 font-medium text-ink outline-none"
      >
        <option value="">{allLabel}</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}

function DateInput({ label, value, min, max, onChange }) {
  return (
    <label className="flex h-8 items-center gap-2 rounded-lg border border-line bg-surface px-2.5 text-[13px]">
      <span className="text-muted">{label}</span>
      <input
        type="date"
        value={value}
        min={min}
        max={max}
        onChange={(e) => e.target.value && onChange(e.target.value)}
        className="bg-transparent font-medium text-ink outline-none tabular"
      />
    </label>
  );
}

export default function FilterBar({ filters, meta, onChange, onReset, isDefault }) {
  const set = (patch) => onChange({ ...filters, ...patch });
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Segmented
        label="Date range"
        options={RANGES}
        value={filters.range}
        onChange={(range) => set({ range })}
      />
      {filters.range === "custom" && (
        <>
          <DateInput
            label="From"
            value={filters.start}
            min={meta.first_date}
            max={meta.last_date}
            onChange={(start) => set({ start })}
          />
          <DateInput
            label="To"
            value={filters.end}
            min={meta.first_date}
            max={meta.last_date}
            onChange={(end) => set({ end })}
          />
        </>
      )}
      <Select
        label="Sector"
        value={filters.sector}
        onChange={(sector) => set({ sector })}
        options={meta.sectors}
        allLabel="All sectors"
      />
      <Select
        label="Source"
        value={filters.source}
        onChange={(source) => set({ source })}
        options={meta.sources}
        allLabel="All sources"
      />
      <Segmented
        label="Polarity"
        options={POLARITIES}
        value={filters.polarity}
        onChange={(polarity) => set({ polarity })}
      />
      {!isDefault && (
        <Button onClick={onReset} className="text-ink-2">
          Reset
        </Button>
      )}
    </div>
  );
}
