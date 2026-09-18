# Meeting Reality Engine

Turns a raw meeting transcript into structured, evidence-grounded intelligence: what was decided, what was committed (with owner/deadline), what's still only discussed, where participants explicitly conflicted, and what was implied but never resolved. Every claim is traceable back to the exact line it came from.

This repo has two parts with a deliberate division of labor:

- **`app/`** — a Next.js marketing/landing page (the persuasive front door).
- **`main.py` + `static/index.html`** — the actual working tool: paste a transcript, it segments it into evidence events, synthesizes meeting state via an LLM, and renders an interactive graph, insights sidebar, and action board.

## Running the marketing site

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Running the working tool

```bash
pip install -r requirements.txt
```

Create a `.env` file (see `.env` in the repo for the expected shape) with:

```
OPENROUTER_API_KEY=your_real_key_here
ASSEMBLYAI_API_KEY=your_real_key_here
```

Model calls go through [OpenRouter](https://openrouter.ai) (`openai/gpt-5-mini`), not the OpenAI API directly. `ASSEMBLYAI_API_KEY` is only needed for the recording-upload flow (speaker diarization) — the paste-a-transcript flow works without it.

```bash
uvicorn main:app --reload
```

Open [http://localhost:8000/static/](http://localhost:8000/static/). Either:

- Click **Load demo** for a ready-made transcript, or paste your own, then **Analyze**; or
- Switch to **Upload recording**, drop an mp4/audio file, then **Transcribe & detect speakers**. Speakers come back labeled "User 1", "User 2", ... — rename them (with an inline play-sample per speaker) on the "Who's who?" screen, then **Continue to analysis**.

## Tests

```bash
pytest
```

Every `/api/*` endpoint has coverage in `test_main.py`, including a full structural test of the demo transcript's expected output.

## Stack

- **Frontend (marketing):** Next.js 14, TypeScript, Tailwind CSS, shadcn-style `components/ui`.
- **Frontend (tool):** vanilla HTML/CSS/JS, no build step.
- **Backend:** FastAPI, served with Uvicorn.
- **Model provider:** OpenRouter.
