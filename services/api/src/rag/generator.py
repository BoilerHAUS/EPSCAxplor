"""RAG generation layer — Step 4 of the EPSCAxplor query pipeline.

Calls Claude with the assembled context and system prompt, returning
the generated answer with token usage and latency.

Prompt caching is enabled: the system prompt is passed as a cached
TextBlock so repeated calls within the 5-minute TTL avoid re-billing
for system-prompt tokens.
"""

from __future__ import annotations

import time

import anthropic
from anthropic.types import TextBlock
from pydantic import BaseModel

from src.config import Settings

DISCLAIMER = (
    "This answer is for reference only and does not constitute legal advice. "
    "Consult qualified labour relations counsel for binding interpretations."
)

_STANDARD_SYSTEM_PROMPT = """\
You are EPSCAxplor, a specialist reference assistant for EPSCA collective agreements \
covering construction trade unions in Ontario, Canada.

Your job is to answer questions about collective agreement terms, wages, working \
conditions, and labour relations using only the source documents provided in this \
conversation. You do not use general knowledge. You do not guess. You do not infer \
beyond what the documents state.

CITATION RULES — these are non-negotiable:

1. Every factual claim in your answer must be attributed to a specific source using \
   the format [SOURCE N] where N matches the source number in the provided context.

2. State an article or section number ONLY if it appears in that source's citation header \
   (the "Article — Title | Section N" line above the quoted text). Do NOT infer a section number \
   from numbers inside the quoted body text — a clause routinely sits beside adjacent section \
   numbers, page footers, and cross-references that are not the provision you are citing. If the \
   header shows no section number, cite the article title (or document title) and page number \
   instead. Never guess or invent a number.

3. If two sources say different things about the same topic (for example, a Primary CA \
   and a Nuclear Project Agreement), you must surface the conflict explicitly and explain \
   which document governs which context.

4. Never combine information from multiple sources into a single unattributed statement.

REFUSAL RULES:

5. If the answer to a question is not present in the provided sources, say so directly: \
   "The provided documents do not contain information about [topic]." Do not speculate \
   or draw on general knowledge to fill the gap.

6. If the question requires a legal interpretation or advice about which party is right \
   in a dispute, decline to make that determination. Provide the relevant clause text \
   and note that interpretation is a matter for qualified labour relations counsel.

ANSWER FORMAT:

- Lead with a direct answer to the question.
- Follow with the supporting clause text and citation.
- End every response with this exact disclaimer on its own line:
  "\u26a0\ufe0f This answer is for reference only and does not constitute legal advice."

Provided sources follow."""

_COMPARISON_ADDENDUM = """

COMPARISON RULES:

When comparing provisions across multiple unions:
- Address each union's position separately before summarizing differences.
- Use a consistent structure: [Union Name]: [provision], citing [SOURCE N].
- If a union's agreement is silent on a topic that other agreements address explicitly, \
  note the absence — do not assume the provision does not exist."""


_PINNED_RATE_ADDENDUM = """

PINNED RATE SOURCE RULES:

One source is labelled "PINNED — STRUCTURED RATE LOOKUP". It was resolved by an exact \
classification and location match against the wage schedule data — not by semantic \
search — and its rate figures are authoritative for this query.
- Quote the pinned source's wage figures verbatim: exact dollar values and effective \
  dates, unmodified and unrounded.
- If the question asks for the current rate, use the row marked "Currently in effect".
- Other sources may add surrounding context (overtime rules, fund breakdowns, \
  travel provisions) but must not override the pinned source's figures."""


def build_system_prompt(is_cross_union: bool, has_pinned_rate: bool = False) -> str:
    """Return the appropriate system prompt variant.

    Each flag combination yields a stable prompt string, so every variant
    remains an effective prompt-cache anchor.
    """
    prompt = _STANDARD_SYSTEM_PROMPT
    if is_cross_union:
        prompt += _COMPARISON_ADDENDUM
    if has_pinned_rate:
        prompt += _PINNED_RATE_ADDENDUM
    return prompt


class GeneratorResult(BaseModel):
    answer: str
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int


async def generate(
    query: str,
    context: str,
    *,
    is_cross_union: bool,
    has_pinned_rate: bool = False,
    settings: Settings,
) -> GeneratorResult:
    """Call Claude with the query and assembled context, returning a GeneratorResult.

    Args:
        query: Raw user question.
        context: Assembled source blocks from assemble_context().
        is_cross_union: Routes to Sonnet when True, Haiku when False.
        has_pinned_rate: When True, append the pinned-rate rules so the model
            quotes the structured rate lookup source verbatim (issue #89).
        settings: Application settings (API key, model IDs).

    Returns:
        GeneratorResult with answer text, model, token counts, and latency.
    """
    model = (
        settings.claude_sonnet_model if is_cross_union else settings.claude_haiku_model
    )
    system_prompt = build_system_prompt(is_cross_union, has_pinned_rate)
    user_content = f"{query}\n\n{context}" if context else query

    start = time.monotonic()
    async with anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key) as client:
        response = await client.messages.create(
            model=model,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],
        )
    latency_ms = int((time.monotonic() - start) * 1000)

    first_block = response.content[0]
    if not isinstance(first_block, TextBlock):
        raise ValueError(f"Unexpected content block type: {type(first_block)}")

    return GeneratorResult(
        answer=first_block.text,
        model_used=model,
        prompt_tokens=response.usage.input_tokens,
        completion_tokens=response.usage.output_tokens,
        latency_ms=latency_ms,
    )
