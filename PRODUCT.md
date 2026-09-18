# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: team leads, PMs, and other meeting owners deciding whether to adopt the tool. They run standups, planning sessions, and sync calls, and are evaluating this page as proof the product surfaces real decisions, conflicts, and gaps rather than being a generic AI-wrapper demo.

## Product Purpose

Meeting Reality Engine turns a raw meeting transcript into structured, evidence-grounded intelligence: what was decided, what was committed (with owner/deadline), what's still only discussed, where participants explicitly conflicted, and what was implied but never resolved. Success is a team leaving a meeting with an accurate, verifiable record of what is now true — not a summary of what was said.

## Positioning

Most meeting-notes/AI-summary tools produce a prose recap. This product reconstructs *state* (decided / committed / discussed / conflict / unknown) per topic, every claim traceable to the exact transcript line it came from, and explicitly surfaces what was never resolved (gaps) and what could go wrong (risks with a suggested follow-up question) — categories a plain summarizer has no concept of.

## Operating Context

- Two frontends exist in this repo with a deliberate division of labor:
  - `static/index.html` + FastAPI (`main.py`) is the working product surface: paste a transcript **or upload a recording**, it segments/diarizes into evidence events, then synthesizes meeting_state / conflicts / gaps / risks / dependencies via an LLM (OpenRouter), and renders an interactive graph + insights sidebar + action board.
  - The Next.js app (`app/`) is the marketing/landing front door — a persuasive surface for the audience above, linking or embedding toward the working tool rather than reimplementing its logic.
- Model calls go through OpenRouter (`OPENROUTER_API_KEY`, `openai/gpt-5-mini`), never api.openai.com directly — see AGENTS.md.
- Speaker diarization for uploaded audio/video goes through AssemblyAI (`ASSEMBLYAI_API_KEY`) — OpenRouter only routes text LLMs, it has no transcription capability.
- Status taxonomy (functional meaning, not just color): DECIDED (green), COMMITTED (blue), DISCUSSED (amber), CONFLICT (red), UNKNOWN (gray). This mapping is product semantics and must be preserved across any redesign.

## Capabilities and Constraints

- Evidence-id validation: any claim whose cited evidence_ids don't exist in the transcript is stripped server-side before it reaches the UI — the product's core trust guarantee.
- Existing working-tool UI already includes: dependency graph with node cards, side panel with full evidence quotes, "What wasn't decided" / "What could go wrong" insights sidebar, a read-only Action Board for COMMITTED items, and a "Load demo" transcript for live demos.
- Media upload flow: upload mp4/audio → AssemblyAI diarizes it into "User 1" / "User 2" ... speaker-labeled events (in order of first appearance) → the user renames each speaker (with an in-browser play-sample control seeked to that speaker's first line, no server round-trip) → renamed events go straight to synthesis (segmentation is skipped — diarization already produced the events).
- `gpt-5-mini` is a reasoning model: its internal reasoning tokens draw from the same `max_tokens` budget as the visible JSON output. Too-small a cap truncates the response silently (invalid JSON) rather than failing loudly; the app checks `finish_reason` and returns a clear error instead. Confirmed against the live API.
- OpenRouter pre-authorizes the full requested `max_tokens` against account balance, regardless of actual usage — a low-balance key can get a 402 even for a two-line meeting. Not fixable in code; requires the account to hold sufficient credit for `SYNTHESIS_MAX_TOKENS` (currently 16384).
- The Next.js landing page currently has no real analyze functionality — it is presentational only.

## Brand Commitments

- Product name: "Meeting Reality Engine."
- Existing dark, evidence/transcript-forward visual language (JetBrains Mono for transcript/evidence text, Inter for UI) in the working tool — informs but does not obligate the landing page's direction.

## Evidence on Hand

- Real product screenshots are not applicable (text-based tool); the working FastAPI app itself (`static/index.html`) is the evidence — no testimonials, logos, or press exist and none should be fabricated.

## Product Principles

1. Every claim on screen must be traceable to a real transcript line — never dress up the UI with numbers or quotes that imply unverified certainty.
2. Show state, not summary: decided / committed / discussed / conflict / unknown is the product's core mental model and should read clearly at a glance.
3. What's missing matters as much as what's present — gaps and risks are first-class, not an afterthought section.
4. The landing page sells credibility to a skeptical PM/team-lead audience, not hype to a general consumer audience.
