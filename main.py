from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from openai import OpenAI, OpenAIError
from dotenv import load_dotenv

import httpx
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


class AnalyzeResponse(BaseModel):
    events: list[Event]
    analysis: AnalysisResult


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
    "   - CONFLICT: two or more participants explicitly disagree.\n"
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

# This project is stress-tested against OpenRouter, never the real OpenAI
# API — every model call goes through OPENROUTER_BASE_URL using an
# OpenRouter model slug.
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
MODEL: str = "openai/gpt-5-mini"

# Explicit output caps. Without these, some OpenRouter models default to a
# max_tokens near the full context window, which OpenRouter pre-authorizes
# against account balance up front — a small/free-tier balance then gets
# rejected with a 402 even though actual usage would be far smaller.
#
# gpt-5-mini is a reasoning model: its internal reasoning tokens are drawn
# from the same max_tokens budget as the visible completion, and can consume
# the large majority of it before any JSON is written. A cap that's generous
# enough for the visible schema but not for reasoning overhead silently
# truncates the JSON response (finish_reason "length") instead of failing
# loudly — confirmed against the live API, where a 2500-token cap spent 1792
# tokens on reasoning alone for a two-line meeting. These caps carry real
# headroom for that; lowering them without accounting for reasoning tokens
# will reintroduce mid-JSON truncation on real (larger) meetings.
SEGMENTATION_MAX_TOKENS: int = 8192
SYNTHESIS_MAX_TOKENS: int = 16384

# Speaker diarization for uploaded recordings goes through AssemblyAI —
# OpenRouter only routes text LLMs, it has no audio/transcription capability.
ASSEMBLYAI_BASE_URL: str = "https://api.assemblyai.com/v2"
ASSEMBLYAI_POLL_INTERVAL_SECONDS: float = 3.0
ASSEMBLYAI_POLL_TIMEOUT_SECONDS: float = 600.0
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
    """Return an OpenAI-SDK client pointed at OpenRouter.

    Reads OPENROUTER_API_KEY from the environment. This project is
    stress-tested against OpenRouter, never the real OpenAI API — the client
    always targets OPENROUTER_BASE_URL, not api.openai.com.
    """
    api_key: str | None = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENROUTER_API_KEY is not set in the environment.",
        )
    return OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)


def _get_assemblyai_key() -> str:
    """Return the AssemblyAI API key, reading ASSEMBLYAI_API_KEY from the environment."""
    api_key: str | None = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="ASSEMBLYAI_API_KEY is not set in the environment.",
        )
    return api_key


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
        synthesis_response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": synthesis_user_content},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": SYNTHESIS_SCHEMA,
            },
            max_tokens=SYNTHESIS_MAX_TOKENS,
        )
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


# ── AssemblyAI diarization ─────────────────────────────────────────────────

def _assemblyai_transcribe(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """Upload media to AssemblyAI and run transcription with speaker diarization.

    Blocks synchronously until the job completes or ASSEMBLYAI_POLL_TIMEOUT_SECONDS
    elapses. Returns the raw AssemblyAI transcript object (contains `utterances`).
    """
    api_key = _get_assemblyai_key()
    headers = {"authorization": api_key}

    with httpx.Client(timeout=60.0) as http:
        try:
            upload_response = http.post(
                f"{ASSEMBLYAI_BASE_URL}/upload",
                headers=headers,
                content=file_bytes,
            )
            upload_response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"AssemblyAI upload failed: {exc}",
            ) from exc

        upload_url: str | None = upload_response.json().get("upload_url")
        if not upload_url:
            raise HTTPException(
                status_code=502,
                detail="AssemblyAI upload did not return an upload_url.",
            )

        try:
            transcript_response = http.post(
                f"{ASSEMBLYAI_BASE_URL}/transcript",
                headers=headers,
                json={"audio_url": upload_url, "speaker_labels": True},
            )
            transcript_response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"AssemblyAI transcript request failed: {exc}",
            ) from exc

        transcript_id: str = transcript_response.json()["id"]

        deadline = time.monotonic() + ASSEMBLYAI_POLL_TIMEOUT_SECONDS
        while True:
            try:
                poll_response = http.get(
                    f"{ASSEMBLYAI_BASE_URL}/transcript/{transcript_id}",
                    headers=headers,
                )
                poll_response.raise_for_status()
            except httpx.HTTPError as exc:
                raise HTTPException(
                    status_code=502,
                    detail=f"AssemblyAI polling failed: {exc}",
                ) from exc

            poll_data: dict[str, Any] = poll_response.json()
            status: str = poll_data.get("status", "")

            if status == "completed":
                return poll_data
            if status == "error":
                raise HTTPException(
                    status_code=502,
                    detail=f"AssemblyAI transcription failed: {poll_data.get('error')}",
                )
            if time.monotonic() > deadline:
                raise HTTPException(
                    status_code=504,
                    detail=(
                        "AssemblyAI transcription timed out after "
                        f"{ASSEMBLYAI_POLL_TIMEOUT_SECONDS:.0f}s. The file may be "
                        "too long — try a shorter clip."
                    ),
                )
            time.sleep(ASSEMBLYAI_POLL_INTERVAL_SECONDS)


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
        segmentation_response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SEGMENTATION_SYSTEM_PROMPT},
                {"role": "user", "content": request.transcript},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": SEGMENTATION_SCHEMA,
            },
            max_tokens=SEGMENTATION_MAX_TOKENS,
        )
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

    # ── Call 2: Synthesis ──────────────────────────────────────────────
    analysis_data = _run_synthesis(client, events, request.title, request.participants)

    return {"events": events, "analysis": analysis_data}


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
    """Upload a recording (audio or video) and diarize it into speaker-labeled events.

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

    transcript = _assemblyai_transcribe(file_bytes, file.filename or "upload")
    utterances: list[dict[str, Any]] = transcript.get("utterances") or []

    if not utterances:
        raise HTTPException(
            status_code=502,
            detail="AssemblyAI returned no speech/utterances for this file.",
        )

    # Map AssemblyAI's raw speaker labels ("A", "B", ...) to "User 1", "User 2",
    # ... in order of first appearance, per the requested UX.
    speaker_map: dict[str, str] = {}
    events: list[TranscribedEvent] = []
    for i, utt in enumerate(utterances):
        raw_speaker: str = utt.get("speaker", "?")
        if raw_speaker not in speaker_map:
            speaker_map[raw_speaker] = f"User {len(speaker_map) + 1}"
        events.append(
            TranscribedEvent(
                id=f"e{i + 1}",
                speaker=speaker_map[raw_speaker],
                text=utt.get("text", ""),
                start_ms=utt.get("start", 0),
                end_ms=utt.get("end", 0),
            )
        )

    return TranscribeMediaResponse(
        events=events,
        speakers=list(speaker_map.values()),
        duration_ms=transcript.get("audio_duration", 0) * 1000
        if isinstance(transcript.get("audio_duration"), (int, float))
        else max((e.end_ms for e in events), default=0),
    )
