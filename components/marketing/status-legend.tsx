const STATES = [
  { label: "Decided", color: "var(--status-decided)", def: "the group reached a clear call" },
  { label: "Committed", color: "var(--status-committed)", def: "someone took the action item" },
  { label: "Discussed", color: "var(--status-discussed)", def: "talked about, nothing landed" },
  { label: "Conflict", color: "var(--status-conflict)", def: "two people said opposite things" },
  { label: "Unknown", color: "var(--status-unknown)", def: "implied, never actually resolved" },
];

export function StatusLegend() {
  return (
    <div className="flex flex-wrap gap-x-8 gap-y-4">
      {STATES.map((s) => (
        <div key={s.label} className="flex items-baseline gap-2">
          <span
            className="h-[7px] w-[7px] rounded-full shrink-0 translate-y-[-1px]"
            style={{ backgroundColor: s.color }}
          />
          <span className="text-sm font-medium text-[var(--text-primary)]">
            {s.label}
          </span>
          <span className="text-sm text-[var(--text-disabled)]">{s.def}</span>
        </div>
      ))}
    </div>
  );
}
