"""History-aware query condensation — Step 0 of the multi-turn query pipeline (#167).

A bare follow-up ("what about the boilermakers?") embeds to generic chunks, so
retrieval must run on a STANDALONE query. This module rewrites a follow-up plus
recent conversation turns into a self-contained retrieval query BEFORE
``preprocess()`` / ``retrieve()`` run — the history-aware-retriever pattern.

The step is deliberately cheap and fail-safe:

* Empty history short-circuits with **no** network call, so the single-turn path
  is byte-for-byte unchanged (no added latency, cost, or eval regression).
* Any failure or empty rewrite falls back to the original query, so a broken
  condense step degrades to plain single-turn retrieval rather than erroring.

Prompt caching: the condense system prompt is a stable, ephemeral-cached anchor,
mirroring ``generator.py``.
"""

from __future__ import annotations

import logging
from typing import Literal

import anthropic
from anthropic.types import MessageParam, TextBlock
from pydantic import BaseModel, Field

from src.config import Settings

logger = logging.getLogger(__name__)

# History bounds — the single source of truth, imported by the query route so the
# API-boundary validation and this module can never drift.
MAX_HISTORY_TURNS: int = 6  # 3 user + 3 assistant exchanges
PER_TURN_CHAR_CAP: int = 4000  # ~1k tokens; a full grounded answer + disclaimer fits
# ~3k tokens summed across retained turns. Intentionally tighter than
# MAX_HISTORY_TURNS * PER_TURN_CHAR_CAP (24000), so this aggregate cap is the
# binding constraint — keep it below that product if the other two are retuned.
TOTAL_HISTORY_CHAR_BUDGET: int = 12000

# A rewritten query is a short phrase; cap output hard to keep the step cheap.
_CONDENSE_MAX_TOKENS: int = 128


class Turn(BaseModel):
    """One conversational turn supplied by the client for multi-turn context.

    Bounded at the boundary: an unknown role is rejected and content is capped so
    a single turn cannot blow the condense/generation token budget. This is the
    shared shape used by the query route, this module, and the generator.
    """

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=PER_TURN_CHAR_CAP)


_CONDENSE_SYSTEM_PROMPT = """\
You rewrite a follow-up question into a standalone search query for a retrieval \
system over EPSCA collective agreements (Ontario construction trade unions).

Given the conversation so far and a follow-up question, resolve pronouns, \
ellipsis, and implied topic so the query stands on its own without the \
conversation. Preserve every concrete entity the retrieval needs:
- union / trade names (e.g. Boilermakers, IBEW, Sheet Metal, United Association)
- nuclear sites and agreements (Darlington, Pickering, Bruce Power, OPG, NPA)
- classifications and provisions (journeyperson, foreman, apprentice, overtime, \
subsistence, premium, differential, rate)

Rules:
- Output ONLY the rewritten query — no preamble, quotes, or explanation.
- If the follow-up is already standalone, return it essentially unchanged.
- Never invent a union, site, or figure that is not present in the conversation."""


def build_condense_messages(query: str, history: list[Turn]) -> list[MessageParam]:
    """Render *history* + *query* into the condense call's messages list (pure).

    Produces a single user message: an oldest→newest transcript followed by the
    follow-up as the final line. No I/O and no hidden state, so it is directly
    unit-testable and deterministic.

    Assumes (does not enforce) that *history* is well-formed alternating turns;
    the ``QueryRequest`` boundary validator guarantees that in production. Because
    the transcript is rendered as prose inside one user message (not role-tagged
    API turns), a malformed sequence here degrades output quality but cannot
    trigger an Anthropic 400.
    """
    lines = ["Conversation so far:"]
    for turn in history:
        speaker = "User" if turn.role == "user" else "Assistant"
        lines.append(f"{speaker}: {turn.content}")
    lines.append("")
    lines.append(f"Follow-up question: {query}")
    return [{"role": "user", "content": "\n".join(lines)}]


def _clean(text: str) -> str:
    """Strip whitespace and a single pair of wrapping quotes from a rewrite."""
    cleaned = text.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in ("'", '"'):
        cleaned = cleaned[1:-1].strip()
    return cleaned


async def condense_query(query: str, history: list[Turn], *, settings: Settings) -> str:
    """Return a standalone retrieval query from *query* and recent *history*.

    On empty history the original query is returned immediately with no network
    call (single-turn parity). Otherwise a cheap Claude call rewrites the
    follow-up; any failure or empty result falls back to the original query so
    retrieval is never blocked by a condense error.
    """
    if not history:
        return query

    try:
        async with anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key) as client:
            response = await client.messages.create(
                model=settings.claude_condense_model,
                max_tokens=_CONDENSE_MAX_TOKENS,
                system=[
                    {
                        "type": "text",
                        "text": _CONDENSE_SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=build_condense_messages(query, history),
            )
        first_block = response.content[0]
        rewritten = _clean(first_block.text) if isinstance(first_block, TextBlock) else ""
        return rewritten or query
    except Exception:  # noqa: BLE001
        logger.warning("query condensation failed; falling back to raw query", exc_info=True)
        return query
