import { ArrowDown } from "lucide-react";

import { HeroDemo } from "@/components/marketing/hero-demo";
import { StateComparison } from "@/components/marketing/state-comparison";
import { StatusLegend } from "@/components/marketing/status-legend";

export default function HomePage() {
  return (
    <div className="flex-1 bg-grain">
      {/* ── Hero ── */}
      <section className="relative overflow-hidden px-6 pt-20 pb-24 sm:pt-28 sm:pb-32">
        <div
          className="glow-spot h-[26rem] w-[26rem] -left-40 -top-40"
          style={{ backgroundColor: "rgba(96,165,250,0.12)" }}
        />
        <div
          className="glow-spot h-[22rem] w-[22rem] right-[-6rem] top-10"
          style={{ backgroundColor: "rgba(248,113,113,0.1)" }}
        />

        <div className="relative mx-auto grid max-w-6xl gap-14 lg:grid-cols-[1.1fr_1fr] lg:items-center">
          <div>
            <h1 className="font-display max-w-xl text-[2.75rem] font-medium leading-[1.08] tracking-[-0.03em] text-[var(--text-primary)] sm:text-6xl">
              What actually got decided?
            </h1>

            <p className="mt-6 max-w-lg text-lg leading-relaxed text-[var(--text-secondary)]">
              Paste a transcript. Get back what was decided, what was only
              committed, where people disagreed, and what&apos;s still
              hanging — every line traced back to who said it.
            </p>

            <a
              href="#proof"
              className="mt-9 inline-flex items-center gap-2 rounded-lg bg-[var(--text-primary)] px-5 py-3 text-sm font-medium text-[#0A0A0C] transition-transform duration-150 hover:brightness-110 active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-[var(--status-committed)] focus-visible:outline-offset-2"
            >
              See it change
              <ArrowDown className="h-3.5 w-3.5" strokeWidth={2.5} />
            </a>

            <p className="mt-4 text-xs font-mono text-[var(--text-disabled)]">
              runs on your own OpenRouter key · nothing uploaded to a third party
            </p>
          </div>

          <div className="flex justify-center lg:justify-end">
            <HeroDemo />
          </div>
        </div>
      </section>

      {/* ── Proof: before / after ── */}
      <section id="proof" className="border-t border-[var(--border)] px-6 py-20 sm:py-24">
        <div className="mx-auto max-w-5xl">
          <h2 className="font-display max-w-md text-3xl font-medium leading-tight tracking-[-0.02em] text-[var(--text-primary)] sm:text-4xl">
            Same meeting. Same words. One version you can act on.
          </h2>
          <p className="mt-4 max-w-xl text-base leading-relaxed text-[var(--text-secondary)]">
            This is the exact demo transcript shipped with the tool — three
            people, one launch, two things they never agreed on.
          </p>

          <div className="mt-10">
            <StateComparison />
          </div>
        </div>
      </section>

      {/* ── The five states ── */}
      <section className="border-t border-[var(--border)] px-6 py-20 sm:py-24">
        <div className="mx-auto max-w-5xl">
          <h2 className="font-display max-w-md text-3xl font-medium leading-tight tracking-[-0.02em] text-[var(--text-primary)] sm:text-4xl">
            Five states. Nothing else.
          </h2>
          <p className="mt-4 max-w-xl text-base leading-relaxed text-[var(--text-secondary)]">
            Every topic in a meeting ends up in exactly one of these — no
            sentiment score, no vague &ldquo;action items,&rdquo; no summary
            paragraph standing in for a decision.
          </p>

          <div className="mt-10 border-t border-[var(--border-subtle)] pt-8">
            <StatusLegend />
          </div>
        </div>
      </section>

      {/* ── Close ── */}
      <section className="border-t border-[var(--border)] px-6 py-20 sm:py-24">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="font-display text-3xl font-medium leading-tight tracking-[-0.02em] text-[var(--text-primary)] sm:text-4xl">
            Most meeting tools summarize what was said.
            <br />
            This one tells you what&apos;s now true.
          </h2>
          <p className="mt-6 text-sm font-mono text-[var(--text-disabled)]">
            uvicorn main:app --reload · then open /static/
          </p>
        </div>
      </section>
    </div>
  );
}
