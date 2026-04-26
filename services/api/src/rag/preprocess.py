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

_WAGE_KEYWORDS: list[str] = [
    "rate",
    "wage",
    "pay",
    "hourly",
    "salary",
    "earn",
    "journeyperson",
    "journeyman",
    "apprentice",
    "compensation",
    "base rate",
    "base pay",
    "total package",
]


class QueryContext(BaseModel):
    """Structured output of query pre-processing."""

    union_filters: list[str]
    include_nuclear_pa: bool
    agreement_scope: str | None
    is_cross_union: bool
    is_wage_query: bool

    @property
    def union_filter(self) -> str | None:
        """Return the single detected union, if and only if exactly one exists."""
        if len(self.union_filters) == 1:
            return self.union_filters[0]
        return None


def detect_nuclear(query: str) -> bool:
    """Return True if the query contains any nuclear-related keyword.

    Matching uses word-boundary-aware regex (case-insensitive) to avoid
    false positives from substrings (e.g. "non-nuclear" still matches
    "nuclear", but "npa" embedded in another word does not match "NPA").
    """
    return any(p.search(query) is not None for p in _NUCLEAR_PATTERNS)


def detect_unions(query: str, known_unions: list[str]) -> list[str]:
    """Return every known union mentioned in the query, ordered by appearance.

    Matching remains case-insensitive substring search to preserve the current
    detection semantics, but all matches are retained instead of collapsing to
    the first union in ``known_unions`` order.
    """
    lower = query.lower()
    matches: list[tuple[int, int, str]] = []

    for index, union in enumerate(known_unions):
        position = lower.find(union.lower())
        if position != -1:
            matches.append((position, index, union))

    matches.sort(key=lambda item: (item[0], item[1]))
    return [union for _, _, union in matches]


def detect_union(query: str, known_unions: list[str]) -> str | None:
    """Return the verbatim name of the first union found in the query.

    Iterates *known_unions* in order; returns the first whose name appears
    (case-insensitively) as a substring of *query*. Returns None when no
    match is found.
    """
    unions = detect_unions(query, known_unions)
    return unions[0] if unions else None


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


def detect_wage_query(query: str) -> bool:
    """Return True if the query is asking about wages, rates, or pay.

    Triggers a secondary wage_schedule-focused retrieval pass to ensure
    tabular wage data is included in context even when CA narrative text
    scores higher in the primary similarity search.
    """
    lower = query.lower()
    return any(kw in lower for kw in _WAGE_KEYWORDS)


def preprocess(query: str, known_unions: list[str]) -> QueryContext:
    """Analyse *query* and return a populated QueryContext.

    Args:
        query: The raw user query string.
        known_unions: Union names to match against, typically sourced from
            the database or corpus manifest at request time.

    Returns:
        A QueryContext describing retrieval filters and model routing.
    """
    detected_unions = detect_unions(query, known_unions)

    return QueryContext(
        union_filters=detected_unions,
        include_nuclear_pa=detect_nuclear(query),
        agreement_scope=detect_scope(query),
        is_cross_union=classify_complexity(query) or len(detected_unions) > 1,
        is_wage_query=detect_wage_query(query),
    )
