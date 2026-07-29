"""Tests for services/api/src/rag/condense.py — history-aware query condensation (#167).

Covers:
- Turn model: role whitelist + content bounds validated at the boundary
- build_condense_messages: pure, deterministic transcript builder (oldest→newest,
  follow-up last)
- condense_query: empty history short-circuits with NO LLM call (single-turn
  cost/latency parity); pronoun / ellipsis / topic carry-over follow-ups are
  rewritten to a standalone retrieval query; failure / empty output falls back to
  the original query (fail-safe); the condense system prompt is a stable, cached
  anchor on the cheap condense model.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic.types import TextBlock
from pydantic import ValidationError

from src.config import Settings
from src.rag.condense import (
    PER_TURN_CHAR_CAP,
    Turn,
    build_condense_messages,
    condense_query,
)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql://user:pass@localhost/epsca",
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret="test-jwt-secret",  # noqa: S106
    )


def _make_mock_response(text: str) -> MagicMock:
    block = TextBlock(type="text", text=text)
    response = MagicMock()
    response.content = [block]
    return response


def _mock_client(mock_create: AsyncMock) -> MagicMock:
    """Return a mock AsyncAnthropic instance wired as an async context manager."""
    instance = MagicMock()
    instance.__aenter__ = AsyncMock(return_value=instance)
    instance.__aexit__ = AsyncMock(return_value=False)
    instance.messages.create = mock_create
    return instance


# ─── Turn model ────────────────────────────────────────────────────────────────


def test_turn_accepts_valid_roles() -> None:
    assert Turn(role="user", content="hi").role == "user"
    assert Turn(role="assistant", content="hi").role == "assistant"


def test_turn_rejects_invalid_role() -> None:
    with pytest.raises(ValidationError):
        Turn(role="system", content="hi")


def test_turn_rejects_blank_content() -> None:
    with pytest.raises(ValidationError):
        Turn(role="user", content="")


def test_turn_rejects_oversized_content() -> None:
    with pytest.raises(ValidationError):
        Turn(role="assistant", content="x" * (PER_TURN_CHAR_CAP + 1))


# ─── build_condense_messages (pure) ─────────────────────────────────────────────


def test_build_condense_messages_is_pure_and_ordered() -> None:
    history = [
        Turn(role="user", content="What is the IBEW foreman wage?"),
        Turn(role="assistant", content="The IBEW foreman premium is 15%."),
    ]
    messages = build_condense_messages("what about the boilermakers?", history)

    # A single user message carries the transcript + follow-up.
    assert isinstance(messages, list)
    assert messages[-1]["role"] == "user"
    content = messages[-1]["content"]

    # Oldest → newest ordering preserved.
    assert content.index("What is the IBEW foreman wage?") < content.index(
        "The IBEW foreman premium is 15%."
    )
    # The follow-up is the last thing the model sees.
    assert content.rstrip().endswith("what about the boilermakers?")

    # Purity: identical inputs → identical output, no hidden state.
    assert build_condense_messages("what about the boilermakers?", history) == messages


# ─── condense_query ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_empty_history_returns_original_without_llm_call(settings: Settings) -> None:
    with patch("src.rag.condense.anthropic.AsyncAnthropic") as mock_anthropic:
        result = await condense_query("what is the overtime rate?", [], settings=settings)

    assert result == "what is the overtime rate?"
    mock_anthropic.assert_not_called()


@pytest.mark.asyncio
async def test_pronoun_followup_rewritten(settings: Settings) -> None:
    history = [
        Turn(role="user", content="What is the foreman rate for all unions?"),
        Turn(role="assistant", content="Rates vary by union; here are the foreman rates..."),
    ]
    mock_create = AsyncMock(return_value=_make_mock_response("Boilermaker foreman wage rate"))

    with patch(
        "src.rag.condense.anthropic.AsyncAnthropic", return_value=_mock_client(mock_create)
    ):
        result = await condense_query("what about the boilermakers?", history, settings=settings)

    assert result == "Boilermaker foreman wage rate"
    # The follow-up AND the prior turn were handed to the model.
    sent = mock_create.call_args.kwargs["messages"][-1]["content"]
    assert "what about the boilermakers?" in sent
    assert "foreman rate for all unions" in sent


@pytest.mark.asyncio
async def test_ellipsis_followup_rewritten(settings: Settings) -> None:
    history = [
        Turn(role="user", content="What is the IBEW journeyperson rate?"),
        Turn(role="assistant", content="$54.30/hr effective May 2025 [SOURCE 1]."),
    ]
    mock_create = AsyncMock(return_value=_make_mock_response("IBEW apprentice wage rate"))

    with patch(
        "src.rag.condense.anthropic.AsyncAnthropic", return_value=_mock_client(mock_create)
    ):
        result = await condense_query("and the apprentice rate?", history, settings=settings)

    assert result == "IBEW apprentice wage rate"


@pytest.mark.asyncio
async def test_topic_carryover_rewritten(settings: Settings) -> None:
    history = [
        Turn(role="user", content="What is the IBEW foreman wage premium?"),
        Turn(role="assistant", content="The premium is 15% above journeyperson [SOURCE 1]."),
    ]
    mock_create = AsyncMock(
        return_value=_make_mock_response("IBEW foreman wage premium at Darlington")
    )

    with patch(
        "src.rag.condense.anthropic.AsyncAnthropic", return_value=_mock_client(mock_create)
    ):
        result = await condense_query("how about at Darlington?", history, settings=settings)

    assert "Darlington" in result


@pytest.mark.asyncio
async def test_condense_failure_falls_back_to_original(settings: Settings) -> None:
    history = [Turn(role="user", content="q"), Turn(role="assistant", content="a")]
    mock_create = AsyncMock(side_effect=RuntimeError("boom"))

    with patch(
        "src.rag.condense.anthropic.AsyncAnthropic", return_value=_mock_client(mock_create)
    ):
        result = await condense_query("what about the boilermakers?", history, settings=settings)

    assert result == "what about the boilermakers?"


@pytest.mark.asyncio
async def test_condense_empty_output_falls_back(settings: Settings) -> None:
    history = [Turn(role="user", content="q"), Turn(role="assistant", content="a")]
    mock_create = AsyncMock(return_value=_make_mock_response("   "))

    with patch(
        "src.rag.condense.anthropic.AsyncAnthropic", return_value=_mock_client(mock_create)
    ):
        result = await condense_query("what about the boilermakers?", history, settings=settings)

    assert result == "what about the boilermakers?"


@pytest.mark.asyncio
async def test_condense_strips_wrapping_quotes_and_whitespace(settings: Settings) -> None:
    history = [Turn(role="user", content="q"), Turn(role="assistant", content="a")]
    mock_create = AsyncMock(
        return_value=_make_mock_response('  "Boilermaker foreman wage rate"  ')
    )

    with patch(
        "src.rag.condense.anthropic.AsyncAnthropic", return_value=_mock_client(mock_create)
    ):
        result = await condense_query("x", history, settings=settings)

    assert result == "Boilermaker foreman wage rate"


@pytest.mark.asyncio
async def test_condense_uses_condense_model_and_cached_system(settings: Settings) -> None:
    history = [Turn(role="user", content="q"), Turn(role="assistant", content="a")]
    mock_create = AsyncMock(return_value=_make_mock_response("standalone query"))

    with patch(
        "src.rag.condense.anthropic.AsyncAnthropic", return_value=_mock_client(mock_create)
    ):
        await condense_query("x", history, settings=settings)

    kwargs = mock_create.call_args.kwargs
    # Cheap, dedicated condense model — not the generation model path.
    assert kwargs["model"] == settings.claude_condense_model
    # Bounded output: a rewritten query is short, so cap tokens hard.
    assert kwargs["max_tokens"] <= 256
    # System prompt is the stable, cached anchor (prompt-cache preservation).
    system_blocks = kwargs["system"]
    assert isinstance(system_blocks, list)
    assert system_blocks[0]["cache_control"] == {"type": "ephemeral"}
