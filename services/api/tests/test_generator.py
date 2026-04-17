"""Tests for services/api/src/rag/generator.py.

Covers:
- build_system_prompt: standard vs cross-union variants
- generate: happy path via mocked AsyncAnthropic
- generate: uses Sonnet for cross-union, Haiku for standard
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic.types import TextBlock, Usage

from src.config import Settings
from src.rag.generator import DISCLAIMER, GeneratorResult, build_system_prompt, generate


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql://user:pass@localhost/epsca",
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret="test-jwt-secret",  # noqa: S106
    )


# ─── build_system_prompt ──────────────────────────────────────────────────────


def test_standard_prompt_contains_citation_rules() -> None:
    prompt = build_system_prompt(is_cross_union=False)
    assert "CITATION RULES" in prompt
    assert "COMPARISON RULES" not in prompt


def test_cross_union_prompt_appends_comparison_rules() -> None:
    prompt = build_system_prompt(is_cross_union=True)
    assert "CITATION RULES" in prompt
    assert "COMPARISON RULES" in prompt


def test_standard_prompt_ends_with_sources_follow() -> None:
    prompt = build_system_prompt(is_cross_union=False)
    assert prompt.endswith("Provided sources follow.")


def test_cross_union_prompt_ends_with_comparison_addendum() -> None:
    prompt = build_system_prompt(is_cross_union=True)
    assert "note the absence" in prompt


# ─── DISCLAIMER ───────────────────────────────────────────────────────────────


def test_disclaimer_content() -> None:
    assert "reference only" in DISCLAIMER
    assert "legal advice" in DISCLAIMER


# ─── generate ─────────────────────────────────────────────────────────────────


def _make_mock_response(text: str, input_tokens: int = 100, output_tokens: int = 50) -> MagicMock:
    block = TextBlock(type="text", text=text)
    usage = MagicMock(spec=Usage)
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    response = MagicMock()
    response.content = [block]
    response.usage = usage
    return response


def _mock_client(mock_create: AsyncMock) -> MagicMock:
    """Return a mock AsyncAnthropic instance wired as an async context manager."""
    instance = MagicMock()
    instance.__aenter__ = AsyncMock(return_value=instance)
    instance.__aexit__ = AsyncMock(return_value=False)
    instance.messages.create = mock_create
    return instance


@pytest.mark.asyncio
async def test_generate_standard_uses_haiku(settings: Settings) -> None:
    mock_response = _make_mock_response("Standard answer [SOURCE 1]")
    mock_create = AsyncMock(return_value=mock_response)

    with patch("src.rag.generator.anthropic.AsyncAnthropic", return_value=_mock_client(mock_create)):
        result = await generate("What is overtime?", "context", is_cross_union=False, settings=settings)

    assert result.model_used == settings.claude_haiku_model
    assert result.answer == "Standard answer [SOURCE 1]"
    assert result.prompt_tokens == 100
    assert result.completion_tokens == 50
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_generate_cross_union_uses_sonnet(settings: Settings) -> None:
    mock_response = _make_mock_response("Compare answer [SOURCE 1] vs [SOURCE 2]")
    mock_create = AsyncMock(return_value=mock_response)

    with patch("src.rag.generator.anthropic.AsyncAnthropic", return_value=_mock_client(mock_create)):
        result = await generate(
            "Compare overtime across unions", "context", is_cross_union=True, settings=settings
        )

    assert result.model_used == settings.claude_sonnet_model


@pytest.mark.asyncio
async def test_generate_empty_context_sends_query_only(settings: Settings) -> None:
    mock_response = _make_mock_response("No docs found")
    mock_create = AsyncMock(return_value=mock_response)

    with patch("src.rag.generator.anthropic.AsyncAnthropic", return_value=_mock_client(mock_create)):
        await generate("What is overtime?", "", is_cross_union=False, settings=settings)

    call_args = mock_create.call_args
    messages = call_args.kwargs["messages"]
    assert messages[0]["content"] == "What is overtime?"


@pytest.mark.asyncio
async def test_generate_system_prompt_cached(settings: Settings) -> None:
    mock_response = _make_mock_response("Answer")
    mock_create = AsyncMock(return_value=mock_response)

    with patch("src.rag.generator.anthropic.AsyncAnthropic", return_value=_mock_client(mock_create)):
        await generate("query", "ctx", is_cross_union=False, settings=settings)

    call_args = mock_create.call_args
    system_blocks = call_args.kwargs["system"]
    assert isinstance(system_blocks, list)
    assert system_blocks[0]["cache_control"] == {"type": "ephemeral"}


@pytest.mark.asyncio
async def test_generate_returns_generator_result(settings: Settings) -> None:
    mock_response = _make_mock_response("Answer", input_tokens=200, output_tokens=80)
    mock_create = AsyncMock(return_value=mock_response)

    with patch("src.rag.generator.anthropic.AsyncAnthropic", return_value=_mock_client(mock_create)):
        result = await generate("q", "ctx", is_cross_union=False, settings=settings)

    assert isinstance(result, GeneratorResult)
    assert result.prompt_tokens == 200
    assert result.completion_tokens == 80
