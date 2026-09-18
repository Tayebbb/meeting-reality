"use client";

import * as React from "react";
import { RotateCw } from "lucide-react";

import { AiStreamingText } from "@/components/ui/streaming-text";
import { cn } from "@/lib/utils";

const LINE =
  "My API timeline is soft — I said end of week but honestly if the retry logic gets ugly it could slip. I don't want that to be the thing everyone plans around.";
const SPEAKER = "Rahim";

export function HeroDemo() {
  const [resolved, setResolved] = React.useState(false);
  const [runId, setRunId] = React.useState(0);

  function replay() {
    setResolved(false);
    setRunId((n) => n + 1);
  }

  return (
    <div className="relative w-full max-w-md rounded-2xl border border-[var(--border)] bg-[var(--surface)]/80 backdrop-blur-sm p-5 shadow-surface-lg">
      <div className="flex items-center justify-between mb-3">
        <span className="text-2xs font-mono uppercase tracking-[0.08em] text-[var(--text-disabled)]">
          Transcript · 00:21:04
        </span>
        <button
          type="button"
          onClick={replay}
          aria-label="Replay the demo"
          className="flex items-center gap-1 rounded-md border border-[var(--border)] px-2 py-1 text-2xs text-[var(--text-secondary)] transition-colors hover:border-[var(--border-subtle)] hover:text-[var(--text-primary)] focus-visible:outline-2 focus-visible:outline-[var(--status-committed)]"
        >
          <RotateCw className="h-3 w-3" strokeWidth={2} />
          Replay
        </button>
      </div>

      <div className="min-h-[92px] transcript text-sm leading-relaxed text-[var(--text-secondary)]">
        <span className="text-[var(--text-primary)] font-medium">{SPEAKER}: </span>
        <AiStreamingText
          key={runId}
          text={LINE}
          speed={16}
          showCursor
          onComplete={() => setResolved(true)}
        />
      </div>

      <div className="my-4 h-px bg-[var(--border)]" />

      <div
        className={cn(
          "space-y-2 transition-all duration-500 ease-out",
          resolved ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2 pointer-events-none"
        )}
        aria-hidden={!resolved}
      >
        <div className="flex items-center gap-2">
          <span className="status-badge status-committed">
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            Committed
          </span>
          <span className="text-2xs font-mono text-[var(--status-discussed)]">tentative</span>
        </div>
        <p className="text-sm font-medium text-[var(--text-primary)]">
          API completion — owner: {SPEAKER}
        </p>
        <p className="text-xs leading-relaxed text-[var(--text-disabled)]">
          No confirmed deadline. Rahim called the timeline soft — that&apos;s a
          risk, not a plan.
        </p>
      </div>
    </div>
  );
}
