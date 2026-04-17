"""Query pre-processing for the EPSCAxplor RAG pipeline.

Performs lightweight query analysis before embedding and retrieval:
- Nuclear context detection (widens retrieval to include NPAs)
- Union name detection (restricts retrieval to a single union)
- Scope detection for IBEW/Labourers (generation vs. transmission)
- Cross-union complexity classification (routes to Sonnet vs. Haiku)
"""

import re

from pydantic import BaseModel

NUCLEAR_KEYWORDS: list[str] = [
    "nuclear",
    "OPG",
    "Ontario Power Generation",
    "Bruce Power",
    "Darlington",
    "Pickering",
    "nuclear project",
    "NPA",
]

# Compiled, word-boundary-aware patterns for each nuclear keyword.
# Multi-word phrases use implicit phrase boundaries; single tokens use \b.
_NUCLEAR_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bnuclear\b", re.IGNORECASE),
    re.compile(r"\bOPG\b", re.IGNORECASE),
    re.compile(r"Ontario Power Generation", re.IGNORECASE),
    re.compile(r"Bruce Power", re.IGNORECASE),
    re.compile(r"\bDarlington\b", re.IGNORECASE),
    re.compile(r"\bPickering\b", re.IGNORECASE),
    re.compile(r"\bnuclear\s+project\b", re.IGNORECASE),
    re.compile(r"\bNPA\b", re.IGNORECASE),
]

_SCOPE_PATTERNS: dict[str, re.Pattern[str]] = {
    "generation": re.compile(r"\bgeneration\b", re.IGNORECASE),
    "transmission": re.compile(r"\btransmission\b", re.IGNORECASE),
}

_CROSS_UNION_PHRASES: list[str] = [
    "compare",
    "difference between",
    "all unions",
    "across trades",
]


class QueryContext(BaseModel):
    """Structured output of query pre-processing."""

    union_filter: str | None
    include_nuclear_pa: bool
    agreement_scope: str | None
    is_cross_union: bool


def detect_nuclear(query: str) -> bool:
    """Return True if the query contains any nuclear-related keyword.

    Matching uses word-boundary-aware regex (case-insensitive) to avoid
    false positives from substrings (e.g. "non-nuclear" still matches
    "nuclear", but "npa" embedded in another word does not match "NPA").
    """
    return any(p.search(query) is not None for p in _NUCLEAR_PATTERNS)


def detect_union(query: str, known_unions: list[str]) -> str | None:
    """Return the verbatim name of the first union found in the query.

    Iterates *known_unions* in order; returns the first whose name appears
    (case-insensitively) as a substring of *query*. Returns None when no
    match is found.
    """
    lower = query.lower()
    for union in known_unions:
        if union.lower() in lower:
            return union
    return None


def detect_scope(query: str) -> str | None:
    """Return 'generation' or 'transmission' if the corresponding word appears.

    Word-boundary matching prevents false positives from words that merely
    contain 'generation' or 'transmission' as a substring (e.g. 'regeneration',
    'retransmission'). 'generation' is checked first; if both words appear,
    'generation' is returned.

    Relevant for IBEW and Labourers agreements, which are scoped by site type.
    Returns None when neither word is present.
    """
    if _SCOPE_PATTERNS["generation"].search(query):
        return "generation"
    if _SCOPE_PATTERNS["transmission"].search(query):
        return "transmission"
    return None


def classify_complexity(query: str) -> bool:
    """Return True if the query contains cross-union comparison language.

    True triggers routing to Claude Sonnet; False routes to Claude Haiku.
    """
    lower = query.lower()
    return any(phrase in lower for phrase in _CROSS_UNION_PHRASES)


def preprocess(query: str, known_unions: list[str]) -> QueryContext:
    """Analyse *query* and return a populated QueryContext.

    Args:
        query: The raw user query string.
        known_unions: Union names to match against, typically sourced from
            the database or corpus manifest at request time.

    Returns:
        A QueryContext describing retrieval filters and model routing.
    """
    return QueryContext(
        union_filter=detect_union(query, known_unions),
        include_nuclear_pa=detect_nuclear(query),
        agreement_scope=detect_scope(query),
        is_cross_union=classify_complexity(query),
    )
