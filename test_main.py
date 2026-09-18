import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app, validate_evidence_ids


# ── Helpers ────────────────────────────────────────────────────────────────

SAMPLE_TRANSCRIPT: str = (
    "Alice: I think we should ship v2 next Monday.\n"
    "Bob: Agreed — let's lock the scope today.\n"
    "Carol: What about the billing migration?"
)

MOCK_SEGMENTATION: dict[str, Any] = {
    "events": [
        {"id": "e1", "speaker": "Alice", "text": "I think we should ship v2 next Monday."},
        {"id": "e2", "speaker": "Bob", "text": "Agreed — let's lock the scope today."},
        {"id": "e3", "speaker": "Carol", "text": "What about the billing migration?"},
    ]
}

MOCK_SYNTHESIS: dict[str, Any] = {
    "meeting_state": [
        {
            "topic": "Ship v2",
            "status": "DECIDED",
            "value": "Ship v2 next Monday",
            "owner": "Alice",
            "deadline": "next Monday",
            "confidence": "firm",
            "evidence_ids": ["e1", "e2"],
            "reasoning": "Alice proposed and Bob agreed.",
        },
        {
            "topic": "Scope lock",
            "status": "COMMITTED",
            "value": "Lock scope today",
            "owner": "Bob",
            "deadline": "today",
            "confidence": "firm",
            "evidence_ids": ["e2"],
            "reasoning": "Bob committed to locking scope.",
        },
        {
            "topic": "Billing migration",
            "status": "UNKNOWN",
            "value": None,
            "owner": None,
            "deadline": None,
            "confidence": None,
            "evidence_ids": ["e3"],
            "reasoning": "Carol raised it but nobody answered.",
        },
    ],
    "conflicts": [],
    "gaps": [
        {
            "topic": "Billing migration plan",
            "why_it_matters": "Billing migration was raised but never discussed.",
            "implied_by_evidence_ids": ["e3"],
        }
    ],
    "risks": [
        {
            "statement": "Shipping v2 may be blocked by billing migration.",
            "reason": "The billing migration status is unknown.",
            "suggested_followup_question": "Does billing migration block the v2 release?",
            "evidence_ids": ["e1", "e3"],
        }
    ],
    "dependencies": [
        {
            "from_topic": "Ship v2",
            "to_topic": "Billing migration",
            "reason": "Carol implied billing migration might affect the release.",
        }
    ],
    "summary_stats": {
        "decisions": 1,
        "commitments": 1,
        "conflicts": 0,
        "gaps": 1,
    },
}


def _make_mock_response(
    content: dict[str, Any], finish_reason: str = "stop"
) -> MagicMock:
    """Create a MagicMock matching the shape of an OpenAI ChatCompletion."""
    message = MagicMock()
    message.content = json.dumps(content)
    choice = MagicMock()
    choice.message = message
    choice.finish_reason = finish_reason
    response = MagicMock()
    response.choices = [choice]
    return response


# ── Existing endpoint tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_root_returns_message() -> None:
    """GET / should return 200 and the engine name."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Meeting Reality Engine"}


@pytest.mark.asyncio
async def test_health_returns_ok() -> None:
    """GET /health should return 200 and status ok."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ── POST /api/analyze tests ───────────────────────────────────────────────

@pytest.mark.asyncio
@patch("main._get_openai_client")
async def test_analyze_success(mock_get_client: MagicMock) -> None:
    """Happy path: segmentation + synthesis → validated response."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        _make_mock_response(MOCK_SEGMENTATION),
        _make_mock_response(MOCK_SYNTHESIS),
    ]
    mock_get_client.return_value = mock_client

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/analyze",
            json={"transcript": SAMPLE_TRANSCRIPT},
        )

    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert "events" in data
    assert "analysis" in data
    assert len(data["events"]) == 3
    assert data["analysis"]["summary_stats"]["decisions"] == 1


@pytest.mark.asyncio
@patch("main._get_openai_client")
async def test_analyze_with_optional_fields(mock_get_client: MagicMock) -> None:
    """Optional title and participants are forwarded without error."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        _make_mock_response(MOCK_SEGMENTATION),
        _make_mock_response(MOCK_SYNTHESIS),
    ]
    mock_get_client.return_value = mock_client

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/analyze",
            json={
                "transcript": SAMPLE_TRANSCRIPT,
                "title": "Sprint Planning",
                "participants": "Alice, Bob, Carol",
            },
        )

    assert response.status_code == 200

    # Verify the synthesis call received title and participants
    synthesis_call = mock_client.chat.completions.create.call_args_list[1]
    user_message: str = synthesis_call.kwargs["messages"][1]["content"]
    assert "Sprint Planning" in user_message
    assert "Alice, Bob, Carol" in user_message


@pytest.mark.asyncio
@patch("main._get_openai_client")
async def test_analyze_strips_invalid_evidence_ids(mock_get_client: MagicMock) -> None:
    """Claims with fabricated evidence_ids are stripped from the response."""
    bad_synthesis = json.loads(json.dumps(MOCK_SYNTHESIS))
    bad_synthesis["meeting_state"].append({
        "topic": "Phantom topic",
        "status": "DECIDED",
        "value": "Something made up",
        "owner": None,
        "deadline": None,
        "confidence": "firm",
        "evidence_ids": ["e99"],  # does not exist
        "reasoning": "This should be stripped.",
    })

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        _make_mock_response(MOCK_SEGMENTATION),
        _make_mock_response(bad_synthesis),
    ]
    mock_get_client.return_value = mock_client

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/analyze",
            json={"transcript": SAMPLE_TRANSCRIPT},
        )

    assert response.status_code == 200
    data: dict[str, Any] = response.json()

    # The phantom topic should have been stripped
    topics = [item["topic"] for item in data["analysis"]["meeting_state"]]
    assert "Phantom topic" not in topics
    # Original 3 items should remain
    assert len(data["analysis"]["meeting_state"]) == 3


@pytest.mark.asyncio
@patch("main._get_openai_client")
async def test_analyze_segmentation_api_error(mock_get_client: MagicMock) -> None:
    """If the segmentation OpenAI call fails, return 502."""
    from openai import APIConnectionError

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = APIConnectionError(
        request=MagicMock(),
    )
    mock_get_client.return_value = mock_client

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/analyze",
            json={"transcript": SAMPLE_TRANSCRIPT},
        )

    assert response.status_code == 502
    assert "segmentation" in response.json()["detail"].lower()


@pytest.mark.asyncio
@patch("main._get_openai_client")
async def test_analyze_synthesis_api_error(mock_get_client: MagicMock) -> None:
    """If the synthesis OpenAI call fails, return 502."""
    from openai import APIConnectionError

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        _make_mock_response(MOCK_SEGMENTATION),
        APIConnectionError(request=MagicMock()),
    ]
    mock_get_client.return_value = mock_client

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/analyze",
            json={"transcript": SAMPLE_TRANSCRIPT},
        )

    assert response.status_code == 502
    assert "synthesis" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_analyze_missing_transcript() -> None:
    """POST with empty body should return 422 (Pydantic validation)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/analyze", json={})

    assert response.status_code == 422


@pytest.mark.asyncio
@patch("main._get_openai_client")
async def test_analyze_empty_content_from_segmentation(
    mock_get_client: MagicMock,
) -> None:
    """If segmentation returns empty content, return 502."""
    message = MagicMock()
    message.content = None
    choice = MagicMock()
    choice.message = message
    empty_response = MagicMock()
    empty_response.choices = [choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = empty_response
    mock_get_client.return_value = mock_client

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/analyze",
            json={"transcript": SAMPLE_TRANSCRIPT},
        )

    assert response.status_code == 502
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
@patch("main._get_openai_client")
async def test_analyze_segmentation_truncated(mock_get_client: MagicMock) -> None:
    """If segmentation hits max_tokens (finish_reason=length), return a clear 502."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response(
        MOCK_SEGMENTATION, finish_reason="length"
    )
    mock_get_client.return_value = mock_client

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/analyze",
            json={"transcript": SAMPLE_TRANSCRIPT},
        )

    assert response.status_code == 502
    assert "truncated" in response.json()["detail"].lower()


@pytest.mark.asyncio
@patch("main._get_openai_client")
async def test_analyze_synthesis_truncated(mock_get_client: MagicMock) -> None:
    """If synthesis hits max_tokens (finish_reason=length), return a clear 502
    instead of a confusing JSON-parse error.

    This is a real failure mode: gpt-5-mini spends part of its max_tokens
    budget on internal reasoning tokens before any visible JSON is written,
    so a too-small cap truncates mid-response — confirmed against the live
    API during development.
    """
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        _make_mock_response(MOCK_SEGMENTATION),
        _make_mock_response(MOCK_SYNTHESIS, finish_reason="length"),
    ]
    mock_get_client.return_value = mock_client

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/analyze",
            json={"transcript": SAMPLE_TRANSCRIPT},
        )

    assert response.status_code == 502
    assert "truncated" in response.json()["detail"].lower()


# ── validate_evidence_ids unit tests ───────────────────────────────────────

def test_validate_strips_bad_meeting_state() -> None:
    """meeting_state items with invalid evidence_ids are removed."""
    analysis: dict[str, Any] = {
        "meeting_state": [
            {"topic": "Good", "evidence_ids": ["e1"]},
            {"topic": "Bad", "evidence_ids": ["e99"]},
        ],
        "conflicts": [],
        "gaps": [],
        "risks": [],
    }
    result = validate_evidence_ids(analysis, {"e1", "e2"})
    assert len(result["meeting_state"]) == 1
    assert result["meeting_state"][0]["topic"] == "Good"


def test_validate_strips_bad_conflicts() -> None:
    """Conflicts with invalid evidence_ids are removed."""
    analysis: dict[str, Any] = {
        "meeting_state": [],
        "conflicts": [
            {
                "topic": "Bad conflict",
                "statement_a": {"text": "A", "evidence_ids": ["e1"]},
                "statement_b": {"text": "B", "evidence_ids": ["e99"]},
            },
        ],
        "gaps": [],
        "risks": [],
    }
    result = validate_evidence_ids(analysis, {"e1"})
    assert len(result["conflicts"]) == 0


def test_validate_strips_bad_risks() -> None:
    """Risks with invalid evidence_ids are removed."""
    analysis: dict[str, Any] = {
        "meeting_state": [],
        "conflicts": [],
        "gaps": [],
        "risks": [
            {"statement": "Bad risk", "evidence_ids": ["e50"]},
        ],
    }
    result = validate_evidence_ids(analysis, {"e1"})
    assert len(result["risks"]) == 0


def test_validate_strips_bad_gaps() -> None:
    """Gaps with invalid implied_by_evidence_ids are removed."""
    analysis: dict[str, Any] = {
        "meeting_state": [],
        "conflicts": [],
        "gaps": [
            {"topic": "Bad gap", "implied_by_evidence_ids": ["e77"]},
        ],
        "risks": [],
    }
    result = validate_evidence_ids(analysis, {"e1"})
    assert len(result["gaps"]) == 0


def test_validate_keeps_valid_entries() -> None:
    """Entries with all valid evidence_ids are preserved."""
    analysis: dict[str, Any] = {
        "meeting_state": [
            {"topic": "Valid", "evidence_ids": ["e1", "e2"]},
        ],
        "conflicts": [
            {
                "topic": "Valid conflict",
                "statement_a": {"text": "A", "evidence_ids": ["e1"]},
                "statement_b": {"text": "B", "evidence_ids": ["e2"]},
            },
        ],
        "gaps": [
            {"topic": "Valid gap", "implied_by_evidence_ids": ["e1"]},
        ],
        "risks": [
            {"statement": "Valid risk", "evidence_ids": ["e2"]},
        ],
    }
    result = validate_evidence_ids(analysis, {"e1", "e2"})
    assert len(result["meeting_state"]) == 1
    assert len(result["conflicts"]) == 1
    assert len(result["gaps"]) == 1
    assert len(result["risks"]) == 1


# ── Demo transcript (Rahim / Nadia / Farhan) end-to-end structure test ─────
#
# This is the exact transcript loaded by the "Load demo" button in
# static/index.html. It's the one that actually gets used live, so it needs
# its own regression test rather than relying on the generic sample above.

DEMO_TRANSCRIPT: str = (
    "Nadia: Okay let's do this quick, I have another call in 20. Where are we on launch?\n"
    "Rahim: I mean... the API is mostly there. I still need to wire up the webhook retries "
    "and test the rate limiting stuff. I'll try to have it done by... I don't know, end of "
    "week maybe? Don't hold me to that.\n"
    "Nadia: End of week as in Friday?\n"
    "Rahim: Yeah probably. Or Monday if something breaks.\n"
    "Nadia: We need to launch Friday, marketing already teased it on social.\n"
    "Farhan: Wait, I thought we agreed Monday last week so QA has the weekend.\n"
    "Nadia: No we said Friday, that's why I told the investors Friday.\n"
    "Farhan: I have it in my notes as Monday, I already told the hosting provider Monday "
    "for the cutover window.\n"
    "Nadia: Well it's Friday now, that's final.\n"
    "Farhan: Okay uh, sure, I'll figure it out.\n"
    "Nadia: Great. Now — payments. Are we still doing Stripe?\n"
    "Rahim: Stripe's the plan yeah, I already have the test keys wired in.\n"
    "Farhan: Hold on, I talked to the Bangladesh team yesterday and they said most of our "
    "users don't have international cards, we basically have to support bKash or we lose "
    "half the signups.\n"
    "Nadia: We can't switch payment providers a week before launch, that's insane.\n"
    "Farhan: I'm just saying bKash is what actually works here, Stripe cards barely clear "
    "for local banks.\n"
    "Nadia: Let's not relitigate this, we're going with Stripe.\n"
    "Farhan: Fine, but someone should tell the Bangladesh team that.\n"
    "Nadia: That's not my job right now, Farhan can you just make sure deployment is sorted?\n"
    "Farhan: Yeah yeah, I'll handle the deployment stuff.\n"
    "Nadia: Great, thank you.\n"
    "Rahim: When you say deployment stuff, do you mean the actual server cutover or also "
    "the CI pipeline and the rollback plan? Because those are pretty different.\n"
    "Farhan: I mean... deployment. I'll handle it.\n"
    "Rahim: Okay, but I can't actually deploy anything until the API is stable, so whatever "
    "Farhan's doing has to wait on me finishing.\n"
    "Farhan: Right, yeah, that's fine, just let me know when you're done.\n"
    "Nadia: Okay, what about marketing? Who's driving the launch post and the email blast?\n"
    "Rahim: Not me, I've got zero bandwidth this week.\n"
    "Farhan: I assumed marketing was already handling their own thing.\n"
    "Nadia: I think Priya was going to do it but she's out this week.\n"
    "Farhan: So... nobody?\n"
    "Nadia: I'll figure it out later, let's move on.\n"
    "Rahim: Also just to be clear, my API timeline is soft — I said end of week but "
    "honestly if the retry logic gets ugly it could slip. I don't want that to be the "
    "thing everyone plans around.\n"
    "Nadia: Noted. Okay I gotta jump, let's regroup tomorrow."
)

DEMO_MOCK_SEGMENTATION: dict[str, Any] = {
    "events": [
        {"id": "e1", "speaker": "Nadia", "text": "Okay let's do this quick, I have another call in 20. Where are we on launch?"},
        {"id": "e2", "speaker": "Rahim", "text": "I'll try to have the API done by end of week maybe, don't hold me to that."},
        {"id": "e3", "speaker": "Nadia", "text": "End of week as in Friday?"},
        {"id": "e4", "speaker": "Rahim", "text": "Yeah probably. Or Monday if something breaks."},
        {"id": "e5", "speaker": "Nadia", "text": "We need to launch Friday, marketing already teased it on social."},
        {"id": "e6", "speaker": "Farhan", "text": "Wait, I thought we agreed Monday last week so QA has the weekend."},
        {"id": "e7", "speaker": "Nadia", "text": "No we said Friday, that's why I told the investors Friday."},
        {"id": "e8", "speaker": "Farhan", "text": "I have it in my notes as Monday, I already told the hosting provider Monday for the cutover window."},
        {"id": "e9", "speaker": "Nadia", "text": "Well it's Friday now, that's final."},
        {"id": "e10", "speaker": "Farhan", "text": "Okay uh, sure, I'll figure it out."},
        {"id": "e11", "speaker": "Nadia", "text": "Are we still doing Stripe?"},
        {"id": "e12", "speaker": "Rahim", "text": "Stripe's the plan yeah, I already have the test keys wired in."},
        {"id": "e13", "speaker": "Farhan", "text": "The Bangladesh team said most users don't have international cards, we basically have to support bKash or we lose half the signups."},
        {"id": "e14", "speaker": "Nadia", "text": "We can't switch payment providers a week before launch, that's insane."},
        {"id": "e15", "speaker": "Farhan", "text": "bKash is what actually works here, Stripe cards barely clear for local banks."},
        {"id": "e16", "speaker": "Nadia", "text": "Let's not relitigate this, we're going with Stripe."},
        {"id": "e17", "speaker": "Farhan", "text": "Fine, but someone should tell the Bangladesh team that."},
        {"id": "e18", "speaker": "Nadia", "text": "Farhan can you just make sure deployment is sorted?"},
        {"id": "e19", "speaker": "Farhan", "text": "Yeah yeah, I'll handle the deployment stuff."},
        {"id": "e20", "speaker": "Nadia", "text": "Great, thank you."},
        {"id": "e21", "speaker": "Rahim", "text": "When you say deployment stuff, do you mean the server cutover or also the CI pipeline and rollback plan?"},
        {"id": "e22", "speaker": "Farhan", "text": "I mean... deployment. I'll handle it."},
        {"id": "e23", "speaker": "Rahim", "text": "I can't actually deploy anything until the API is stable, so whatever Farhan's doing has to wait on me finishing."},
        {"id": "e24", "speaker": "Farhan", "text": "Right, yeah, that's fine, just let me know when you're done."},
        {"id": "e25", "speaker": "Nadia", "text": "What about marketing? Who's driving the launch post and the email blast?"},
        {"id": "e26", "speaker": "Rahim", "text": "Not me, I've got zero bandwidth this week."},
        {"id": "e27", "speaker": "Farhan", "text": "I assumed marketing was already handling their own thing."},
        {"id": "e28", "speaker": "Nadia", "text": "I think Priya was going to do it but she's out this week."},
        {"id": "e29", "speaker": "Farhan", "text": "So... nobody?"},
        {"id": "e30", "speaker": "Nadia", "text": "I'll figure it out later, let's move on."},
        {"id": "e31", "speaker": "Rahim", "text": "My API timeline is soft, if the retry logic gets ugly it could slip. I don't want that to be the thing everyone plans around."},
        {"id": "e32", "speaker": "Nadia", "text": "Noted. Okay I gotta jump, let's regroup tomorrow."},
    ]
}

DEMO_MOCK_SYNTHESIS: dict[str, Any] = {
    "meeting_state": [
        {
            "topic": "Launch date",
            "status": "CONFLICT",
            "value": None,
            "owner": None,
            "deadline": None,
            "confidence": None,
            "evidence_ids": ["e5", "e6", "e7", "e8", "e9"],
            "reasoning": "Nadia insists on Friday while Farhan believed Monday was agreed and already told the hosting provider Monday.",
        },
        {
            "topic": "Payment provider",
            "status": "CONFLICT",
            "value": None,
            "owner": None,
            "deadline": None,
            "confidence": None,
            "evidence_ids": ["e11", "e12", "e13", "e15", "e16"],
            "reasoning": "Nadia and Rahim are proceeding with Stripe while Farhan argues bKash is required for the Bangladesh market.",
        },
        {
            "topic": "API completion",
            "status": "COMMITTED",
            "value": "Wire up webhook retries and rate limiting",
            "owner": "Rahim",
            "deadline": None,
            "confidence": "tentative",
            "evidence_ids": ["e2", "e31"],
            "reasoning": "Rahim committed to finishing the API but explicitly called the timeline soft with no confirmed deadline.",
        },
        {
            "topic": "Deployment",
            "status": "COMMITTED",
            "value": "Handle the deployment stuff",
            "owner": "Farhan",
            "deadline": None,
            "confidence": "tentative",
            "evidence_ids": ["e18", "e19", "e22"],
            "reasoning": "Farhan agreed to handle deployment but never clarified whether that includes CI pipeline or rollback plan.",
        },
        {
            "topic": "Marketing ownership",
            "status": "UNKNOWN",
            "value": None,
            "owner": None,
            "deadline": None,
            "confidence": None,
            "evidence_ids": ["e25", "e27", "e28", "e29", "e30"],
            "reasoning": "Marketing was assumed to be handled but no one actually owns the launch post or email blast.",
        },
    ],
    "conflicts": [
        {
            "topic": "Launch date",
            "statement_a": {
                "text": "We need to launch Friday, that's final.",
                "evidence_ids": ["e5", "e7", "e9"],
            },
            "statement_b": {
                "text": "I thought we agreed Monday, I already told the hosting provider Monday for the cutover window.",
                "evidence_ids": ["e6", "e8"],
            },
        },
        {
            "topic": "Payment provider",
            "statement_a": {
                "text": "We're going with Stripe.",
                "evidence_ids": ["e12", "e16"],
            },
            "statement_b": {
                "text": "bKash is what actually works here, Stripe cards barely clear for local banks.",
                "evidence_ids": ["e13", "e15"],
            },
        },
    ],
    "gaps": [
        {
            "topic": "Scope of Farhan's deployment commitment",
            "why_it_matters": "Farhan agreed to \"handle the deployment stuff\" but never confirmed whether that covers the server cutover, CI pipeline, or rollback plan.",
            "implied_by_evidence_ids": ["e19", "e21", "e22"],
        },
        {
            "topic": "Marketing ownership",
            "why_it_matters": "No one actually committed to the launch post or email blast; the assumed owner is out this week.",
            "implied_by_evidence_ids": ["e25", "e27", "e28", "e29"],
        },
    ],
    "risks": [
        {
            "statement": "Rahim's API timeline is tentative with no confirmed deadline.",
            "reason": "Rahim called the end-of-week estimate soft and warned it could slip if the retry logic gets complicated.",
            "suggested_followup_question": "What is the actual drop-dead date for the API, and what happens to the Friday launch if it slips?",
            "evidence_ids": ["e2", "e31"],
        },
    ],
    "dependencies": [
        {
            "from_topic": "API completion",
            "to_topic": "Deployment",
            "reason": "Rahim said deployment can't happen until the API is stable.",
        },
    ],
    "summary_stats": {
        "decisions": 0,
        "commitments": 2,
        "conflicts": 2,
        "gaps": 2,
    },
}


@pytest.mark.asyncio
@patch("main._get_openai_client")
async def test_analyze_demo_transcript_structure(mock_get_client: MagicMock) -> None:
    """The Rahim/Nadia/Farhan demo transcript produces a structurally valid response.

    This mocks the OpenAI calls with a canned response matching the shape we
    expect the model to produce, and checks that the six signals the demo is
    built around round-trip correctly through the endpoint (including evidence
    validation). It does not prove the real model reasons this way — see the
    live check for that.
    """
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        _make_mock_response(DEMO_MOCK_SEGMENTATION),
        _make_mock_response(DEMO_MOCK_SYNTHESIS),
    ]
    mock_get_client.return_value = mock_client

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/analyze",
            json={
                "transcript": DEMO_TRANSCRIPT,
                "title": "Launch Sync",
                "participants": "Rahim, Nadia, Farhan",
            },
        )

    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert "events" in data
    assert "analysis" in data
    assert len(data["events"]) == 32

    analysis = data["analysis"]
    meeting_state = analysis["meeting_state"]
    conflicts = analysis["conflicts"]
    gaps = analysis["gaps"]
    risks = analysis["risks"]
    dependencies = analysis["dependencies"]

    # No claim should have been stripped by evidence validation.
    assert len(meeting_state) == len(DEMO_MOCK_SYNTHESIS["meeting_state"])
    assert len(conflicts) == len(DEMO_MOCK_SYNTHESIS["conflicts"])
    assert len(gaps) == len(DEMO_MOCK_SYNTHESIS["gaps"])
    assert len(risks) == len(DEMO_MOCK_SYNTHESIS["risks"])
    assert len(dependencies) == len(DEMO_MOCK_SYNTHESIS["dependencies"])

    # 1. CONFLICT node for launch date (Friday vs Monday)
    launch_conflict = next(c for c in conflicts if c["topic"] == "Launch date")
    assert "Friday" in launch_conflict["statement_a"]["text"]
    assert "Monday" in launch_conflict["statement_b"]["text"]
    assert any(
        item["topic"] == "Launch date" and item["status"] == "CONFLICT"
        for item in meeting_state
    )

    # 2. CONFLICT node for payment provider (Stripe vs bKash)
    payment_conflict = next(c for c in conflicts if c["topic"] == "Payment provider")
    assert "Stripe" in payment_conflict["statement_a"]["text"]
    assert "bKash" in payment_conflict["statement_b"]["text"]
    assert any(
        item["topic"] == "Payment provider" and item["status"] == "CONFLICT"
        for item in meeting_state
    )

    # 3. UNKNOWN gap for what Farhan's "deployment stuff" commitment covers
    deployment_gap = next(g for g in gaps if "deployment" in g["topic"].lower())
    assert "deployment" in deployment_gap["why_it_matters"].lower()

    # 4. UNKNOWN gap for marketing ownership
    marketing_gap = next(g for g in gaps if "marketing" in g["topic"].lower())
    assert marketing_gap["why_it_matters"]

    # 5. Dependency line from the API/backend topic to the deployment topic
    api_to_deploy = next(
        d for d in dependencies
        if "api" in d["from_topic"].lower() and "deploy" in d["to_topic"].lower()
    )
    assert api_to_deploy["reason"]

    # 6. Risk entry about Rahim's tentative API timeline with no confirmed deadline
    api_risk = next(r for r in risks if "e31" in r["evidence_ids"])
    assert "tentative" in api_risk["statement"].lower() or "soft" in api_risk["reason"].lower()
    api_item = next(item for item in meeting_state if item["topic"] == "API completion")
    assert api_item["confidence"] == "tentative"
    assert api_item["deadline"] is None


# ── POST /api/analyze-events tests (media-upload flow) ─────────────────────

EVENTS_WITH_REAL_NAMES: list[dict[str, str]] = [
    {"id": "e1", "speaker": "Alice", "text": "I think we should ship v2 next Monday."},
    {"id": "e2", "speaker": "Bob", "text": "Agreed — let's lock the scope today."},
    {"id": "e3", "speaker": "Carol", "text": "What about the billing migration?"},
]


@pytest.mark.asyncio
@patch("main._get_openai_client")
async def test_analyze_events_success(mock_get_client: MagicMock) -> None:
    """Happy path: pre-segmented, speaker-labeled events go straight to synthesis."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response(MOCK_SYNTHESIS)
    mock_get_client.return_value = mock_client

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/analyze-events",
            json={"events": EVENTS_WITH_REAL_NAMES},
        )

    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert data["events"] == EVENTS_WITH_REAL_NAMES
    assert data["analysis"]["summary_stats"]["decisions"] == 1
    # Only one LLM call — segmentation is skipped entirely for this flow.
    assert mock_client.chat.completions.create.call_count == 1


@pytest.mark.asyncio
@patch("main._get_openai_client")
async def test_analyze_events_strips_invalid_evidence_ids(
    mock_get_client: MagicMock,
) -> None:
    """Evidence validation still applies to the media-upload flow."""
    bad_synthesis = json.loads(json.dumps(MOCK_SYNTHESIS))
    bad_synthesis["risks"].append({
        "statement": "Fabricated risk",
        "reason": "Made up",
        "suggested_followup_question": "N/A",
        "evidence_ids": ["e99"],
    })

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response(bad_synthesis)
    mock_get_client.return_value = mock_client

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/analyze-events",
            json={"events": EVENTS_WITH_REAL_NAMES},
        )

    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    statements = [r["statement"] for r in data["analysis"]["risks"]]
    assert "Fabricated risk" not in statements


@pytest.mark.asyncio
async def test_analyze_events_missing_events_field() -> None:
    """POST with no events field should return 422 (Pydantic validation)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/analyze-events", json={})

    assert response.status_code == 422


# ── POST /api/transcribe tests (diarization) ────────────────────────────────

MOCK_ASSEMBLYAI_TRANSCRIPT: dict[str, Any] = {
    "status": "completed",
    "audio_duration": 12,
    "utterances": [
        {"speaker": "A", "text": "Let's ship on Friday.", "start": 0, "end": 2000},
        {"speaker": "B", "text": "I disagree, Monday is safer.", "start": 2100, "end": 4500},
        {"speaker": "A", "text": "Friday it is, final answer.", "start": 4600, "end": 6000},
    ],
}


@pytest.mark.asyncio
@patch("main._assemblyai_transcribe")
async def test_transcribe_success(mock_transcribe: MagicMock) -> None:
    """Happy path: uploaded media is diarized into speaker-labeled events."""
    mock_transcribe.return_value = MOCK_ASSEMBLYAI_TRANSCRIPT

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/transcribe",
            files={"file": ("meeting.mp4", b"fake-video-bytes", "video/mp4")},
        )

    assert response.status_code == 200
    data: dict[str, Any] = response.json()

    # Raw "A"/"B" speaker labels are mapped to "User 1"/"User 2" in order of
    # first appearance, so the caller can rename them before analysis.
    assert data["speakers"] == ["User 1", "User 2"]
    assert [e["speaker"] for e in data["events"]] == ["User 1", "User 2", "User 1"]
    assert data["events"][0]["id"] == "e1"
    assert data["events"][1]["start_ms"] == 2100
    assert data["duration_ms"] == 12000


@pytest.mark.asyncio
async def test_transcribe_empty_file() -> None:
    """An empty upload should return 422, not reach AssemblyAI."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/transcribe",
            files={"file": ("empty.mp4", b"", "video/mp4")},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
@patch("main._assemblyai_transcribe")
async def test_transcribe_no_utterances(mock_transcribe: MagicMock) -> None:
    """A file with no detected speech should return a clear 502, not a crash."""
    mock_transcribe.return_value = {"status": "completed", "utterances": []}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/transcribe",
            files={"file": ("silence.mp4", b"fake-bytes", "video/mp4")},
        )

    assert response.status_code == 502
    assert "utterances" in response.json()["detail"].lower()


def test_get_assemblyai_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """_get_assemblyai_key raises a clear 500 when ASSEMBLYAI_API_KEY is unset."""
    from fastapi import HTTPException

    from main import _get_assemblyai_key

    monkeypatch.delenv("ASSEMBLYAI_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc_info:
        _get_assemblyai_key()

    assert exc_info.value.status_code == 500
    assert "ASSEMBLYAI_API_KEY" in exc_info.value.detail
