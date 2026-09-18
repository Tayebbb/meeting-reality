const NOISE_BARS = [42, 68, 30, 74, 52, 38, 62, 46, 82, 34, 58, 44, 70, 50, 40, 60];

const REAL_CLUSTERS: {
  label: string;
  count: number;
  color: string;
  heights: number[];
}[] = [
  { label: "decided", count: 0, color: "var(--status-decided)", heights: [6] },
  { label: "committed", count: 2, color: "var(--status-committed)", heights: [82, 74] },
  { label: "conflict", count: 2, color: "var(--status-conflict)", heights: [90, 68] },
  { label: "unresolved", count: 2, color: "var(--status-unknown)", heights: [55, 60] },
];

function NoiseChart() {
  return (
    <div className="flex items-end gap-[3px] h-20">
      {NOISE_BARS.map((h, i) => (
        <div
          key={i}
          className="flex-1 rounded-[2px]"
          style={{ height: `${h}%`, backgroundColor: "rgba(248,113,113,0.35)" }}
        />
      ))}
    </div>
  );
}

function RealChart() {
  return (
    <div className="flex items-end gap-3 h-20">
      {REAL_CLUSTERS.map((cluster) => (
        <div key={cluster.label} className="flex items-end gap-[3px] flex-1">
          {cluster.heights.map((h, i) => (
            <div
              key={i}
              className="flex-1 rounded-[2px]"
              style={{ height: `${h}%`, backgroundColor: cluster.color }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

export function StateComparison() {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {/* Before */}
      <div className="relative overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6">
        <div
          className="glow-spot h-40 w-40 -right-10 -top-10"
          style={{ backgroundColor: "rgba(248,113,113,0.18)" }}
        />
        <div className="relative flex flex-col-reverse items-start gap-3 sm:flex-row sm:justify-between">
          <p className="font-display text-2xl font-medium text-[var(--text-primary)] sm:max-w-[14rem]">
            32 statements. No structure.
          </p>
          <span className="status-badge status-conflict shrink-0">
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            unprocessed
          </span>
        </div>

        <div className="relative mt-6">
          <NoiseChart />
          <div className="mt-3 h-[3px] w-full rounded-full bg-[var(--status-conflict)]/70" />
        </div>

        <p className="relative mt-5 text-sm leading-relaxed text-[var(--text-secondary)]">
          Just talk, in the order it happened. You&apos;d have to re-read the
          whole thing to know what actually matters.
        </p>

        <p className="relative mt-4 text-xs font-mono text-[var(--text-disabled)]">
          ↳ still just a transcript
        </p>
      </div>

      {/* After */}
      <div className="relative overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6">
        <div
          className="glow-spot h-40 w-40 -right-10 -top-10"
          style={{ backgroundColor: "rgba(52,211,153,0.18)" }}
        />
        <div className="relative flex flex-col-reverse items-start gap-3 sm:flex-row sm:justify-between">
          <p className="font-display text-2xl font-medium text-[var(--text-primary)] sm:max-w-[14rem]">
            2 commitments. 2 conflicts. 0 clean decisions.
          </p>
          <span className="status-badge status-decided shrink-0">
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            reconstructed
          </span>
        </div>

        <div className="relative mt-6">
          <RealChart />
          <div className="mt-3 h-[3px] w-full rounded-full bg-[var(--status-decided)]/70" />
        </div>

        <p className="relative mt-5 text-sm leading-relaxed text-[var(--text-secondary)]">
          Same meeting. Every one of those numbers traces back to the exact
          line it came from — nothing invented, nothing rounded up.
        </p>

        <p className="relative mt-4 text-xs font-mono text-[var(--text-disabled)]">
          ↳ ready to act on
        </p>
      </div>
    </div>
  );
}
