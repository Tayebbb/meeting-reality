from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from openai import OpenAI, OpenAIError, RateLimitError
from dotenv import load_dotenv

import asyncio
import json
import logging
import os
import time
from typing import Any

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(title="Meeting Reality Engine")

# Serve static/ folder; index.html will be accessible at "/static/"
app.mount("/static", StaticFiles(directory="static", html=True), name="static")


# ── Request / Response models ──────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    transcript: str
    title: str | None = None
    participants: str | None = None

    @field_validator("transcript")
    @classmethod
    def transcript_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("transcript must not be empty or whitespace-only")
        return value


class TranscribedEvent(BaseModel):
    id: str
    speaker: str
    text: str
    start_ms: int
    end_ms: int


class TranscribeMediaResponse(BaseModel):
    events: list[TranscribedEvent]
    speakers: list[str]
    duration_ms: int


class Event(BaseModel):
    id: str
    speaker: str
    text: str


class AnalyzeEventsRequest(BaseModel):
    """Analyze pre-segmented events directly — used by the media-upload flow,
    where diarization already produced speaker-labeled events and the user
    has renamed the speakers, so segmentation is skipped entirely.
    """
    events: list[Event]
    title: str | None = None
    participants: str | None = None


class SegmentationResult(BaseModel):
    events: list[Event]


class StatementRef(BaseModel):
    text: str
    evidence_ids: list[str]


class MeetingStateItem(BaseModel):
    topic: str
    status: str  # DECIDED | COMMITTED | DISCUSSED | CONFLICT | UNKNOWN
    value: str | None = None
    owner: str | None = None
    deadline: str | None = None
    confidence: str | None = None  # firm | tentative | null
    evidence_ids: list[str]
    reasoning: str


class Conflict(BaseModel):
    topic: str
    statement_a: StatementRef
    statement_b: StatementRef


class Gap(BaseModel):
    topic: str
    why_it_matters: str
    implied_by_evidence_ids: list[str]


class Risk(BaseModel):
    statement: str
    reason: str
    suggested_followup_question: str
    evidence_ids: list[str]


class Dependency(BaseModel):
    from_topic: str
    to_topic: str
    reason: str


class SummaryStats(BaseModel):
    decisions: int
    commitments: int
    conflicts: int
    gaps: int


class AnalysisResult(BaseModel):
    meeting_state: list[MeetingStateItem]
    conflicts: list[Conflict]
    gaps: list[Gap]
    risks: list[Risk]
    dependencies: list[Dependency]
    summary_stats: SummaryStats


class RecapBeat(BaseModel):
    text: str
    related_topic: str | None = None
    evidence_ids: list[str]


class Recap(BaseModel):
    overview: str
    beats: list[RecapBeat]


class AnalyzeResponse(BaseModel):
    events: list[Event]
    analysis: AnalysisResult
    recap: Recap | None = None


# ── JSON schemas for structured outputs ────────────────────────────────────

SEGMENTATION_SCHEMA: dict[str, Any] = {
    "name": "segmentation",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "speaker": {"type": "string"},
                        "text": {"type": "string"},
                    },
                    "required": ["id", "speaker", "text"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["events"],
        "additionalProperties": False,
    },
}

SYNTHESIS_SCHEMA: dict[str, Any] = {
    "name": "synthesis",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "meeting_state": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "status": {"type": "string"},
                        "value": {"type": ["string", "null"]},
                        "owner": {"type": ["string", "null"]},
                        "deadline": {"type": ["string", "null"]},
                        "confidence": {"type": ["string", "null"]},
                        "evidence_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "reasoning": {"type": "string"},
                    },
                    "required": [
                        "topic", "status", "value", "owner",
                        "deadline", "confidence", "evidence_ids", "reasoning",
                    ],
                    "additionalProperties": False,
                },
            },
            "conflicts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "statement_a": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "evidence_ids": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": ["text", "evidence_ids"],
                            "additionalProperties": False,
                        },
                        "statement_b": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "evidence_ids": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": ["text", "evidence_ids"],
                            "additionalProperties": False,
                        },
                    },
                    "required": ["topic", "statement_a", "statement_b"],
                    "additionalProperties": False,
                },
            },
            "gaps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "why_it_matters": {"type": "string"},
                        "implied_by_evidence_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["topic", "why_it_matters", "implied_by_evidence_ids"],
                    "additionalProperties": False,
                },
            },
            "risks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "statement": {"type": "string"},
                        "reason": {"type": "string"},
                        "suggested_followup_question": {"type": "string"},
                        "evidence_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "statement", "reason",
                        "suggested_followup_question", "evidence_ids",
                    ],
                    "additionalProperties": False,
                },
            },
            "dependencies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "from_topic": {"type": "string"},
                        "to_topic": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["from_topic", "to_topic", "reason"],
                    "additionalProperties": False,
                },
            },
            "summary_stats": {
                "type": "object",
                "properties": {
                    "decisions": {"type": "integer"},
                    "commitments": {"type": "integer"},
                    "conflicts": {"type": "integer"},
                    "gaps": {"type": "integer"},
                },
                "required": ["decisions", "commitments", "conflicts", "gaps"],
                "additionalProperties": False,
            },
        },
        "required": [
            "meeting_state", "conflicts", "gaps",
            "risks", "dependencies", "summary_stats",
        ],
        "additionalProperties": False,
    },
}

RECAP_SCHEMA: dict[str, Any] = {
    "name": "recap",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "overview": {"type": "string"},
            "beats": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "related_topic": {"type": ["string", "null"]},
                        "evidence_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["text", "related_topic", "evidence_ids"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["overview", "beats"],
        "additionalProperties": False,
    },
}


# ── System prompts ─────────────────────────────────────────────────────────

SEGMENTATION_SYSTEM_PROMPT: str = (
    "You are a transcript segmentation engine. Your job is to split the "
    "meeting transcript into discrete events.\n\n"
    "Rules:\n"
    "1. Preserve the original wording of each statement EXACTLY — do not "
    "paraphrase, summarize, or edit.\n"
    "2. Assign sequential ids: e1, e2, e3, and so on.\n"
    "3. If the transcript lines are labeled with speaker names "
    '(e.g. "Alice: …"), use those names as the speaker field.\n'
    "4. If a line has no speaker label, use \"Unknown Speaker\".\n"
    "5. Each distinct statement or thought by a speaker should be one event. "
    "If a speaker says multiple sentences in one block, keep them together "
    "as a single event."
)

SYNTHESIS_SYSTEM_PROMPT: str = (
    "You are a meeting analyst. Your job is NOT to summarize what was said. "
    "Your job is to reconstruct what is now TRUE after this meeting.\n\n"
    "You will receive an array of events, each with an id, speaker, and text. "
    "From these events, extract ALL of the following in one pass:\n\n"
    "1. meeting_state — every topic discussed. Assign a status:\n"
    "   - DECIDED: the group reached a clear decision.\n"
    "   - COMMITTED: someone took on an action item.\n"
    "   - DISCUSSED: talked about but no decision or commitment.\n"
    "   - CONFLICT: two or more participants explicitly disagree, AND the "
    "transcript never shows the disagreeing party retracting or agreeing. "
    "One person unilaterally declaring a decision, restating their own "
    "position more firmly, or asserting \"that's final\" does NOT resolve "
    "a conflict by itself — it stays CONFLICT unless the other side is "
    "shown backing down or agreeing.\n"
    "   - UNKNOWN: the transcript clearly implies this topic matters "
    "(referenced or obviously required by what was discussed) but it was "
    "never actually resolved. Do NOT invent topics with no basis in the "
    "transcript.\n\n"
    "2. conflicts — pairs of contradictory statements.\n"
    "3. gaps — topics implied but never addressed.\n"
    "4. risks — things that could go wrong based on what was said.\n"
    "5. dependencies — when one topic clearly blocks another.\n"
    "6. summary_stats — counts of decisions, commitments, conflicts, gaps.\n\n"
    "CRITICAL RULES:\n"
    "- Every claim in meeting_state, conflicts, and risks MUST include "
    "evidence_ids referencing actual event ids from the input. NEVER invent "
    "an evidence_id that does not exist in the input events.\n"
    "- Distinguish soft commitments (\"I'll probably...\", \"I might...\") "
    "from firm ones. Soft language MUST produce confidence: \"tentative\", "
    "never upgraded to \"firm\".\n"
    "- dependencies should only appear when the transcript explicitly or "
    "very clearly implies one topic blocks another.\n"
    "- For UNKNOWN status: only flag topics the transcript actually implies "
    "matter. Do not invent topics from thin air."
)

RECAP_SYSTEM_PROMPT: str = (
    "You are catching a coworker up on a meeting they missed. Write a plain-"
    "language, conversational, chronological recap — this is the opposite of "
    "a formal classification report.\n\n"
    "You will receive an array of events, each with an id, speaker, and text. "
    "Produce:\n\n"
    "1. overview — 2-3 sentences, plain language, what this meeting was "
    "about and roughly where things landed.\n"
    "2. beats — up to 8 short, plain sentences describing what happened, in "
    "chronological order. Each beat should read like something you'd "
    "actually say out loud to a coworker, not a database entry.\n\n"
    "CRITICAL RULES:\n"
    "- NEVER use the words DECIDED, COMMITTED, DISCUSSED, CONFLICT, or "
    "UNKNOWN (in any capitalization) anywhere in overview or beat text. "
    "Those are labels from a separate, more formal classification pass — "
    "this recap must read completely differently: plain and conversational, "
    "never a reformatted list of statuses.\n"
    "- Maximum 8 beats, regardless of transcript length. Pick the 8 most "
    "important moments.\n"
    "- Each beat's evidence_ids MUST reference actual event ids from the "
    "input. NEVER invent an evidence_id that does not exist.\n"
    "- related_topic is optional — set it to a short topic name only when "
    "the beat clearly maps to one specific subject, otherwise null."
)

# OpenAI API configuration
# Uses GPT-6 Astra — supports Chat Completions structured outputs (json_schema)
# Users should set their own OPENAI_API_KEY environment variable
MODEL: str = "gpt-6-astra"

# Explicit output caps. Some models spend part of max_tokens on hidden
# reasoning tokens before any visible JSON is written, which can silently
# truncate the response (finish_reason "length") instead of failing loudly
# if the cap is too tight — confirmed against the live API. These caps carry
# real headroom for that; lowering them without re-testing live will
# reintroduce mid-JSON truncation on real (larger) meetings.
SEGMENTATION_MAX_TOKENS: int = 8192
SYNTHESIS_MAX_TOKENS: int = 16384
RECAP_MAX_TOKENS: int = 8000

# Rough token estimate (chars / 4, no tokenizer dependency) above which the
# recap call (Call 3) is skipped entirely rather than risking a truncated or
# unaffordable response on a long transcript. Chunked/map-reduce
# summarization for long transcripts is a documented but unbuilt Phase 2
# feature — this threshold is the deliberate MVP boundary, not a bug.
RECAP_TOKEN_THRESHOLD: int = 6000

# Audio transcription uses OpenAI Whisper API
# Speaker identification is done by the LLM analyzing the transcript text
MAX_UPLOAD_BYTES: int = 500 * 1024 * 1024  # 500 MB


# ── Evidence validation ────────────────────────────────────────────────────

def validate_evidence_ids(
    analysis: dict[str, Any],
    valid_ids: set[str],
) -> dict[str, Any]:
    """Strip any claims whose evidence_ids reference non-existent event ids.

    Mutates and returns *analysis* in place. Logs a warning for each
    dropped claim.
    """
    # meeting_state
    original_state = analysis.get("meeting_state", [])
    validated_state: list[dict[str, Any]] = []
    for item in original_state:
        if all(eid in valid_ids for eid in item.get("evidence_ids", [])):
            validated_state.append(item)
        else:
            bad = [e for e in item.get("evidence_ids", []) if e not in valid_ids]
            logger.warning(
                "Stripped meeting_state item '%s': invalid evidence_ids %s",
                item.get("topic"), bad,
            )
    analysis["meeting_state"] = validated_state

    # conflicts
    original_conflicts = analysis.get("conflicts", [])
    validated_conflicts: list[dict[str, Any]] = []
    for conflict in original_conflicts:
        a_ids = conflict.get("statement_a", {}).get("evidence_ids", [])
        b_ids = conflict.get("statement_b", {}).get("evidence_ids", [])
        all_ids = a_ids + b_ids
        if all(eid in valid_ids for eid in all_ids):
            validated_conflicts.append(conflict)
        else:
            bad = [e for e in all_ids if e not in valid_ids]
            logger.warning(
                "Stripped conflict '%s': invalid evidence_ids %s",
                conflict.get("topic"), bad,
            )
    analysis["conflicts"] = validated_conflicts

    # risks
    original_risks = analysis.get("risks", [])
    validated_risks: list[dict[str, Any]] = []
    for risk in original_risks:
        if all(eid in valid_ids for eid in risk.get("evidence_ids", [])):
            validated_risks.append(risk)
        else:
            bad = [e for e in risk.get("evidence_ids", []) if e not in valid_ids]
            logger.warning(
                "Stripped risk '%s': invalid evidence_ids %s",
                risk.get("statement"), bad,
            )
    analysis["risks"] = validated_risks

    # gaps — validate implied_by_evidence_ids
    original_gaps = analysis.get("gaps", [])
    validated_gaps: list[dict[str, Any]] = []
    for gap in original_gaps:
        if all(eid in valid_ids for eid in gap.get("implied_by_evidence_ids", [])):
            validated_gaps.append(gap)
        else:
            bad = [
                e for e in gap.get("implied_by_evidence_ids", [])
                if e not in valid_ids
            ]
            logger.warning(
                "Stripped gap '%s': invalid evidence_ids %s",
                gap.get("topic"), bad,
            )
    analysis["gaps"] = validated_gaps

    return analysis


# ── OpenAI client factory ──────────────────────────────────────────────────

def _get_openai_client() -> OpenAI:
    """Return an OpenAI-SDK client for the OpenAI API.

    Reads OPENAI_API_KEY from the environment.
    """
    api_key: str | None = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set in the environment. Please set your OpenAI API key.",
        )
    return OpenAI(api_key=api_key)


def _call_with_retry(fn, max_retries: int = 2, base_delay_seconds: float = 3.0):
    """Call fn() and retry on 429 (rate-limited upstream) — routine, expected
    behavior under OpenAI API load, not a hard failure. Any other OpenAIError
    propagates immediately, unretried.
    """
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except RateLimitError:
            if attempt >= max_retries:
                raise
            time.sleep(base_delay_seconds * (attempt + 1))




# ── Synthesis (shared by transcript and media-upload flows) ───────────────

def _run_synthesis(
    client: OpenAI,
    events: list[dict[str, str]],
    title: str | None,
    participants: str | None,
) -> dict[str, Any]:
    """Run the synthesis LLM call over already-segmented events and validate it.

    Shared by /api/analyze (segments a raw transcript first) and
    /api/analyze-events (events already come segmented and speaker-labeled
    from the diarization flow).
    """
    valid_ids: set[str] = {e["id"] for e in events}
    events_payload: str = json.dumps(events, indent=2)

    synthesis_user_content: str = (
        f"Here are the segmented events from the meeting:\n\n{events_payload}"
    )
    if title:
        synthesis_user_content = f"Meeting title: {title}\n\n{synthesis_user_content}"
    if participants:
        synthesis_user_content = (
            f"Participants: {participants}\n\n{synthesis_user_content}"
        )

    try:
        synthesis_response = _call_with_retry(lambda: client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": synthesis_user_content},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": SYNTHESIS_SCHEMA,
            },
            max_completion_tokens=SYNTHESIS_MAX_TOKENS,
        ))
    except OpenAIError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI synthesis call failed: {exc}",
        ) from exc

    if synthesis_response.choices[0].finish_reason == "length":
        raise HTTPException(
            status_code=502,
            detail=(
                "Synthesis response was truncated (hit the model's max_tokens "
                f"limit of {SYNTHESIS_MAX_TOKENS}). This meeting produced more "
                "structured output than the current budget allows — try a "
                "shorter transcript, or raise SYNTHESIS_MAX_TOKENS in main.py."
            ),
        )

    synthesis_raw: str | None = synthesis_response.choices[0].message.content
    if not synthesis_raw:
        raise HTTPException(
            status_code=502,
            detail="OpenAI synthesis call returned empty content.",
        )

    try:
        analysis_data: dict[str, Any] = json.loads(synthesis_raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to parse synthesis response as JSON: {exc}",
        ) from exc

    return validate_evidence_ids(analysis_data, valid_ids)


def _run_recap(client: OpenAI, events: list[dict[str, str]]) -> dict[str, Any] | None:
    """Run the recap LLM call (Call 3) over already-segmented events.

    Runs in parallel with synthesis (Call 2) — both depend only on Call 1's
    segmented events, nothing from Call 2. Unlike synthesis, failures here
    are non-fatal: the recap is a fast, skimmable on-ramp, not the
    analytical core of the response, so any error degrades to `None`
    (recap: null) rather than failing the whole /api/analyze request.
    """
    valid_ids: set[str] = {e["id"] for e in events}
    events_payload: str = json.dumps(events, indent=2)
    user_content: str = (
        f"Here are the segmented events from the meeting:\n\n{events_payload}"
    )

    try:
        response = _call_with_retry(lambda: client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": RECAP_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": RECAP_SCHEMA,
            },
            max_completion_tokens=RECAP_MAX_TOKENS,
        ))
    except OpenAIError as exc:
        logger.warning("Recap call (Call 3) failed, degrading to recap: null: %s", exc)
        return None

    if response.choices[0].finish_reason == "length":
        logger.warning(
            "Recap call (Call 3) truncated at max_tokens=%d, degrading to recap: null.",
            RECAP_MAX_TOKENS,
        )
        return None

    raw: str | None = response.choices[0].message.content
    if not raw:
        logger.warning("Recap call (Call 3) returned empty content, degrading to recap: null.")
        return None

    try:
        recap_data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning(
            "Recap call (Call 3) response was not valid JSON, degrading to recap: null: %s",
            exc,
        )
        return None

    # Strip any beat whose evidence_ids reference nonexistent events, same
    # non-fatal-drop pattern as validate_evidence_ids uses for synthesis.
    original_beats: list[dict[str, Any]] = recap_data.get("beats", [])
    validated_beats: list[dict[str, Any]] = []
    for beat in original_beats:
        if all(eid in valid_ids for eid in beat.get("evidence_ids", [])):
            validated_beats.append(beat)
        else:
            bad = [e for e in beat.get("evidence_ids", []) if e not in valid_ids]
            logger.warning(
                "Stripped recap beat '%s': invalid evidence_ids %s",
                beat.get("text"), bad,
            )
    recap_data["beats"] = validated_beats

    return recap_data


# ── OpenAI Whisper transcription ───────────────────────────────────────────

def _openai_transcribe(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """Transcribe audio using OpenAI Whisper API.

    Returns a dict with utterances in the format expected by the speaker flow,
    with generic speaker labels "User 1", "User 2", etc. based on detected pauses.
    """
    client = _get_openai_client()

    try:
        # Transcribe using Whisper API
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.mp3", file_bytes, "audio/mpeg"),
            language="en",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI Whisper transcription failed: {exc}",
        ) from exc

    if not transcript.text:
        raise HTTPException(
            status_code=502,
            detail="Whisper returned empty transcription.",
        )

    # Use LLM to identify speakers from the transcript
    # This is a simple heuristic: we assume speaker changes at natural breaks
    try:
        speaker_response = _call_with_retry(lambda: client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a meeting transcription assistant. Your job is to identify "
                        "speaker changes in a transcript based on contextual clues (names mentioned, "
                        "pronouns, context shifts, etc.). Return a JSON array of objects with "
                        '{"text": "...", "speaker": "Speaker 1"/"Speaker 2"/etc}. '
                        "If you cannot reliably identify speakers, assign them sequentially as the "
                        "speaker seems to change based on context. Preserve the original text exactly."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Identify speakers in this transcript:\n\n{transcript.text}",
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "speaker_segments",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "segments": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "text": {"type": "string"},
                                        "speaker": {"type": "string"},
                                    },
                                    "required": ["text", "speaker"],
                                },
                            }
                        },
                        "required": ["segments"],
                    },
                },
            },
            max_completion_tokens=4096,
        ))
    except Exception as exc:
        logger.warning(
            "Speaker identification failed, using generic labels: %s", exc
        )
        # Fallback: just use generic speaker labels
        speaker_response = None

    # Parse speaker segments or use fallback
    if speaker_response and speaker_response.choices[0].message.content:
        try:
            parsed = json.loads(speaker_response.choices[0].message.content)
            segments = parsed.get("segments", [])
        except json.JSONDecodeError:
            segments = []
    else:
        segments = []

    # If parsing failed, create a simple fallback with alternating speakers
    if not segments:
        sentences = transcript.text.split(". ")
        segments = [
            {
                "text": (sent + (".") if not sent.endswith(".") else sent).strip(),
                "speaker": f"Speaker {(i % 2) + 1}",
            }
            for i, sent in enumerate(sentences)
            if sent.strip()
        ]

    # Map speaker names to "User 1", "User 2", etc.
    speaker_map = {}
    utterances = []
    for i, segment in enumerate(segments):
        speaker = segment.get("speaker", "Unknown")
        if speaker not in speaker_map:
            speaker_map[speaker] = f"User {len(speaker_map) + 1}"

        utterances.append({
            "id": f"e{i + 1}",
            "speaker": speaker_map[speaker],
            "text": segment.get("text", ""),
            "start": 0,  # Whisper doesn't provide timestamps by default
            "end": 0,
        })

    return {
        "utterances": utterances,
        "audio_duration": 0,  # Not available from Whisper
    }


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint — returns the engine name."""
    return {"message": "Meeting Reality Engine"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Health-check endpoint."""
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    """Analyze a meeting transcript: segment into events, then synthesize."""
    client: OpenAI = _get_openai_client()

    # ── Call 1: Segmentation ───────────────────────────────────────────
    try:
        segmentation_response = _call_with_retry(lambda: client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SEGMENTATION_SYSTEM_PROMPT},
                {"role": "user", "content": request.transcript},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": SEGMENTATION_SCHEMA,
            },
            max_completion_tokens=SEGMENTATION_MAX_TOKENS,
        ))
    except OpenAIError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI segmentation call failed: {exc}",
        ) from exc

    if segmentation_response.choices[0].finish_reason == "length":
        raise HTTPException(
            status_code=502,
            detail=(
                "Segmentation response was truncated (hit the model's "
                f"max_tokens limit of {SEGMENTATION_MAX_TOKENS}). Try a "
                "shorter transcript, or raise SEGMENTATION_MAX_TOKENS in main.py."
            ),
        )

    segmentation_raw: str | None = segmentation_response.choices[0].message.content
    if not segmentation_raw:
        raise HTTPException(
            status_code=502,
            detail="OpenAI segmentation call returned empty content.",
        )

    try:
        segmentation_data: dict[str, Any] = json.loads(segmentation_raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to parse segmentation response as JSON: {exc}",
        ) from exc

    events: list[dict[str, str]] = segmentation_data.get("events", [])

    # ── Calls 2 & 3: Synthesis + Recap ───────────────────────────────────
    # Both depend only on Call 1's events, nothing on each other, so they
    # run concurrently rather than sequentially. The sync OpenAI client is
    # dispatched to a thread per call so asyncio.gather actually overlaps
    # them instead of blocking the event loop twice in a row.
    estimated_tokens: float = len(request.transcript) / 4
    if estimated_tokens > RECAP_TOKEN_THRESHOLD:
        logger.info(
            "Skipping recap (Call 3): estimated %.0f tokens exceeds the "
            "%d-token threshold. Chunked/map-reduce summarization for long "
            "transcripts is a documented but unbuilt Phase 2 feature.",
            estimated_tokens, RECAP_TOKEN_THRESHOLD,
        )
        analysis_data = await asyncio.to_thread(
            _run_synthesis, client, events, request.title, request.participants
        )
        recap_data = None
    else:
        analysis_data, recap_data = await asyncio.gather(
            asyncio.to_thread(
                _run_synthesis, client, events, request.title, request.participants
            ),
            asyncio.to_thread(_run_recap, client, events),
        )

    return {"events": events, "analysis": analysis_data, "recap": recap_data}


@app.post("/api/analyze-events")
async def analyze_events(request: AnalyzeEventsRequest) -> dict[str, Any]:
    """Synthesize meeting state from already-segmented, speaker-labeled events.

    Used by the media-upload flow: diarization already produced events with
    real speaker names (after the user renamed them), so there is nothing
    left to segment — this goes straight to synthesis.
    """
    client: OpenAI = _get_openai_client()
    events: list[dict[str, str]] = [e.model_dump() for e in request.events]

    analysis_data = _run_synthesis(client, events, request.title, request.participants)

    return {"events": events, "analysis": analysis_data}


@app.post("/api/transcribe")
async def transcribe(file: UploadFile) -> TranscribeMediaResponse:
    """Upload a recording (audio or video) and transcribe it into speaker-labeled events.

    Uses OpenAI Whisper for transcription and LLM-based speaker identification.
    Speakers are returned as generic placeholders ("User 1", "User 2", ...)
    in order of first appearance; the frontend lets the user rename them
    before the result is sent to /api/analyze-events.
    """
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB upload limit.",
        )

    transcript = await asyncio.to_thread(
        _openai_transcribe, file_bytes, file.filename or "upload"
    )
    utterances: list[dict[str, Any]] = transcript.get("utterances") or []

    if not utterances:
        raise HTTPException(
            status_code=502,
            detail="Whisper returned no speech/utterances for this file.",
        )

    # _openai_transcribe already assigns "User 1", "User 2", ... in order of
    # first appearance, so just carry those labels through in order.
    speakers_seen: list[str] = []
    events: list[TranscribedEvent] = []
    for i, utt in enumerate(utterances):
        speaker: str = utt.get("speaker", "?")
        if speaker not in speakers_seen:
            speakers_seen.append(speaker)
        events.append(
            TranscribedEvent(
                id=f"e{i + 1}",
                speaker=speaker,
                text=utt.get("text", ""),
                start_ms=utt.get("start", 0),
                end_ms=utt.get("end", 0),
            )
        )

    return TranscribeMediaResponse(
        events=events,
        speakers=speakers_seen,
        duration_ms=transcript.get("audio_duration", 0) * 1000
        if isinstance(transcript.get("audio_duration"), (int, float))
        else max((e.end_ms for e in events), default=0),
    )
