# Meeting Reality Engine

**Most meeting tools summarize what was said. This one tells you what's now true.**

Paste a transcript — or upload the recording — and get back what was actually decided, what was committed (and by whom, and by when), what was only discussed, where people explicitly disagreed, and what was implied but never resolved. Every claim is traceable back to the exact line it came from, and every claim without real evidence is stripped out before it ever reaches the UI.

## Why this exists

Every other AI notetaker hands you a paragraph of prose and calls it done. This one reconstructs *state* — DECIDED / COMMITTED / DISCUSSED / CONFLICT / UNKNOWN, per topic — instead of a summary. Categories a plain summarizer has no concept of:

- **Gaps** — topics the transcript clearly implies matter, but that never actually got resolved.
- **Conflicts** — pairs of statements where two people said contradictory things, shown side by side.
- **Risks** — what could go wrong based on soft commitments or unresolved tension, each with a suggested follow-up question.
- **Dependencies** — when one topic explicitly blocks another.

Nothing is invented. Every claim in `meeting_state`, `conflicts`, and `risks` carries `evidence_ids` pointing at real transcript lines; anything the model cites that doesn't check out against the actual input is dropped server-side before the response ever leaves the API.

## Features

- **Paste a transcript or upload a recording.** Drop in an mp4/audio file and it's automatically diarized into speaker-labeled events — no manual splitting required.
- **Speaker rename with audio preview.** Detected speakers come back as "User 1", "User 2", ...; rename each one inline, with a one-click play-sample of their actual first line so you know who you're naming.
- **Interactive state graph.** Every topic renders as a node card colored by status, connected by dependency lines where one topic blocks another.
- **Evidence panel.** Click any node to see the full reasoning and the exact transcript lines it's grounded in.
- **"What wasn't decided" / "What could go wrong."** Gaps and risks get their own sidebar, not buried in a wall of text — each risk ships with a ready-to-ask follow-up question.
- **Action Board.** A read-only summary of every COMMITTED item — owner, deadline (or an honest "No confirmed deadline"), and confidence.
- **Copy summary.** One click to get a plain-text recap for Slack or email.
- **Built-in demo.** A ready-made three-person launch-planning transcript (with a real date conflict, a real payment-provider conflict, and a genuinely ambiguous commitment) to try instantly, no setup required.

## How it works

```
                    ┌─────────────────────┐
   transcript  ───▶ │   Segmentation LLM   │ ───▶  speaker-labeled
                    │ (OpenAI API call 1)  │       events [{id, speaker, text}]
                    └─────────────────────┘
                              │
   recording   ───▶ ┌─────────────────────┐        (skips segmentation —
                     │  AssemblyAI diarize  │ ───▶   diarization already
                     │  + speaker rename UI │        produced the events)
                     └─────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │    Synthesis LLM      │ ───▶  meeting_state / conflicts /
                    │ (OpenAI API call 2)   │       gaps / risks / dependencies
                    └─────────────────────┘
                              │
                              ▼
                    evidence_id validation
                    (strip any unverifiable claim)
                              │
                              ▼
                     interactive graph UI
```

This repo intentionally has two frontends with a clean split of responsibility:

| | Purpose | Stack |
|---|---|---|
| **`app/`** | Marketing/landing page — the persuasive front door | Next.js 14, TypeScript, Tailwind, shadcn-style `components/ui` |
| **`main.py` + `static/index.html`** | The actual working tool | FastAPI backend, vanilla HTML/CSS/JS frontend (no build step) |

## Getting started

### Marketing site

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### The working tool

```bash
pip install -r requirements.txt
```

Model calls use OpenAI API keys. (OpenRouter was used only for stress-testing during development — not part of normal operation.)

Create a `.env` file:

```env
OPENROUTER_API_KEY=your_real_key_here
ASSEMBLYAI_API_KEY=your_real_key_here
```

| Variable | Required for | Notes |
|---|---|---|
| `OPENROUTER_API_KEY` | Everything | Your OpenAI API key (`openai/gpt-5-mini`) for all model calls. Needs enough account credit to afford `SYNTHESIS_MAX_TOKENS` (16384) — the full cap is pre-authorized against your balance regardless of actual usage. |
| `ASSEMBLYAI_API_KEY` | Recording upload only | Speaker diarization goes through [AssemblyAI](https://www.assemblyai.com/) — the OpenAI API only handles text, it has no transcription capability. The paste-a-transcript flow works without this key. |

```bash
uvicorn main:app --reload
```

Open [http://localhost:8000/static/](http://localhost:8000/static/). Either:

- Click **Load demo** for a ready-made transcript, or paste your own, then **Analyze**; or
- Switch to **Upload recording**, drop an mp4/audio file, then **Transcribe & detect speakers**. Rename each detected speaker on the "Who's who?" screen (with an inline play-sample), then **Continue to analysis**.

## API reference

| Endpoint | Method | Body | Returns |
|---|---|---|---|
| `/api/analyze` | POST | `{ transcript, title?, participants? }` | `{ events, analysis }` — segments the raw transcript, then synthesizes. |
| `/api/analyze-events` | POST | `{ events, title?, participants? }` | `{ events, analysis }` — synthesizes pre-segmented, speaker-labeled events directly (used by the upload flow). |
| `/api/transcribe` | POST | `multipart/form-data`, field `file` | `{ events, speakers, duration_ms }` — uploads to AssemblyAI and diarizes; speakers come back as `"User 1"`, `"User 2"`, ... in order of first appearance. |
| `/health` | GET | — | `{ status: "ok" }` |

`analysis` is always shaped as:

```ts
{
  meeting_state: { topic, status, value, owner, deadline, confidence, evidence_ids, reasoning }[],
  conflicts:     { topic, statement_a, statement_b }[],
  gaps:          { topic, why_it_matters, implied_by_evidence_ids }[],
  risks:         { statement, reason, suggested_followup_question, evidence_ids }[],
  dependencies:  { from_topic, to_topic, reason }[],
  summary_stats: { decisions, commitments, conflicts, gaps },
}
```

## Tests

```bash
pytest
```

Every endpoint is covered in `test_main.py` — 24 cases, including evidence-id stripping, truncated-response handling, and a full structural test of the demo transcript's expected output, all mocked against a canned model response (no live API calls, no cost).

## Project structure

```
app/                       Next.js marketing site
components/
  ui/streaming-text.tsx    Shared "AI typing" component
  marketing/               Landing-page-specific components
main.py                    FastAPI backend
static/index.html          The working tool's frontend (vanilla JS)
test_main.py                Backend test suite
PRODUCT.md, DESIGN.md       Durable product/design decisions
```

## Stack

- **Frontend (marketing):** Next.js 14, TypeScript, Tailwind CSS, shadcn-style `components/ui`, self-hosted Space Grotesk / Inter / JetBrains Mono.
- **Frontend (tool):** vanilla HTML/CSS/JS, no build step, no framework.
- **Backend:** FastAPI, served with Uvicorn.
- **Model provider:** OpenAI API (`openai/gpt-5-mini`). OpenRouter was used only for stress-testing during development.
- **Speech-to-text & diarization:** [AssemblyAI](https://www.assemblyai.com/).

## Status

Alpha. The core analysis pipeline (transcript and recording, both paths) is functional and tested. There is no deployment config yet, and GitHub Pages (or any static host) can only serve the Next.js marketing page — `main.py` needs a real Python host (Render, Railway, Fly.io, etc.) to actually run.
