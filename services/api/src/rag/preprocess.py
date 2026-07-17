"""Query pre-processing for the EPSCAxplor RAG pipeline.

Performs lightweight query analysis before embedding and retrieval:
- Nuclear context detection (widens retrieval to include NPAs)
- Union name detection (restricts retrieval to a single union)
- Scope detection for IBEW/Labourers (generation vs. transmission)
- Cross-union complexity classification (routes to Sonnet vs. Haiku)
"""

import functools
import re

from pydantic import BaseModel, Field

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

# Word-boundary aliases for union names that users rarely spell out in full.
# Keyed by the canonical union_name stored in PostgreSQL / Qdrant payloads.
_UNION_ALIASES: dict[str, list[re.Pattern[str]]] = {
    "United Association": [
        re.compile(r"\bUA\b", re.IGNORECASE),
        re.compile(r"\bplumbers?\b", re.IGNORECASE),
        re.compile(r"\bpipefitters?\b", re.IGNORECASE),
        re.compile(r"\bsteamfitters?\b", re.IGNORECASE),
    ],
    "IBEW": [
        re.compile(r"\belectrical workers\b", re.IGNORECASE),
    ],
    "Sheet Metal": [
        re.compile(r"\bsheet metal\b", re.IGNORECASE),
    ],
    "Brick and Allied Craft Union": [
        re.compile(r"\bBACU\b", re.IGNORECASE),
        re.compile(r"\bbricklayers?\b", re.IGNORECASE),
    ],
    "Labourers": [
        re.compile(r"\bLiUNA\b", re.IGNORECASE),
        re.compile(r"\blaborers?\b", re.IGNORECASE),  # US spelling
    ],
    "Rodmen": [
        re.compile(r"\brodman\b", re.IGNORECASE),
    ],
    "Operating Engineers": [
        re.compile(r"\bIUOE\b", re.IGNORECASE),
    ],
    "Tile and Terrazzo": [
        re.compile(r"\bterrazzo\b", re.IGNORECASE),
        re.compile(r"\bmarble/tile\b", re.IGNORECASE),
    ],
}


@functools.lru_cache(maxsize=64)
def _union_patterns(union: str) -> tuple[re.Pattern[str], ...]:
    """Compiled alias patterns for *union*, including its singular form.

    Plural union names ("Carpenters", "Teamsters", "Cement Masons") should
    match singular mentions ("the carpenter rate"); names not ending in "s"
    (IBEW, Rodmen, United Association) rely on explicit aliases instead.
    """
    patterns = list(_UNION_ALIASES.get(union, []))
    lower = union.lower()
    if lower.endswith("s"):
        patterns.append(re.compile(rf"\b{re.escape(lower[:-1])}\b", re.IGNORECASE))
    return tuple(patterns)

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

# Focused query-expansion terms for specific-provision recall (issue #78).
# Plain cosine on the full user query lands near "related" sections, not the
# definitive clause; re-embedding a short, focused phrase pulls the specific
# provision (a narrative clause or a terse table) back into retrieval range.
# Each rule maps a trigger pattern to the expansion phrase(s) the retrieval
# layer embeds as secondary query vectors. Expansions are DATA (eval-tunable) —
# adjust phrasing here without touching retrieval logic.
_PROVISION_TERM_RULES: list[tuple[re.Pattern[str], tuple[str, ...]]] = [
    # O07 — double-time / overtime-rate provision (UA CA Art. 24.1).
    (
        re.compile(r"\bdouble[\s-]?time\b", re.IGNORECASE),
        ("double time overtime rate",),
    ),
    # W02 — foreperson wage differential / premium (IBEW CA §600 F). Requires a
    # foreman token to co-occur with "premium" or "differential" so a
    # shift/radiation "premium" or a "differential pressure" (nuclear) query
    # does not pull the foreperson clause.
    (
        re.compile(
            r"\bfore(?:man|person|woman)\b.*\b(?:premium|differential)\b"
            r"|\b(?:premium|differential)\b.*\bfore(?:man|person|woman)\b",
            re.IGNORECASE,
        ),
        ("foreperson wage differential", "foreman premium percentage"),
    ),
    # T03 — subsistence allowance table (SM CA §26.2(b)).
    (
        re.compile(r"\bsubsistence\b", re.IGNORECASE),
        ("subsistence allowance",),
    ),
    # N02 — nuclear site-specific provisions (e.g. IBEW NPA Darlington LOU).
    # These tokens also set include_nuclear_pa (see _NUCLEAR_PATTERNS), so the
    # site-specific LOU is filter-eligible when the term pass runs. "Bruce"
    # matches the "Bruce Power" phrase (not a bare word) to mirror
    # _NUCLEAR_PATTERNS and avoid firing on the given name "Bruce".
    (
        re.compile(r"\bDarlington\b", re.IGNORECASE),
        ("Darlington",),
    ),
    (
        re.compile(r"\bPickering\b", re.IGNORECASE),
        ("Pickering",),
    ),
    (
        re.compile(r"Bruce Power", re.IGNORECASE),
        ("Bruce",),
    ),
]


class QueryContext(BaseModel):
    """Structured output of query pre-processing."""

    union_filters: list[str]
    include_nuclear_pa: bool
    agreement_scope: str | None
    is_cross_union: bool
    is_wage_query: bool
    provision_terms: list[str] = Field(default_factory=list)

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

    Matching is case-insensitive substring search on the canonical union name,
    plus word-boundary alias patterns (e.g. "UA" or "plumber" for United
    Association) so trade shorthand still restricts retrieval correctly.
    """
    lower = query.lower()
    matches: list[tuple[int, int, str]] = []

    for index, union in enumerate(known_unions):
        position = lower.find(union.lower())
        if position == -1:
            for pattern in _union_patterns(union):
                alias_match = pattern.search(query)
                if alias_match:
                    position = alias_match.start()
                    break
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


def detect_provision_terms(query: str) -> list[str]:
    """Return focused query-expansion terms for specific-provision recall.

    Some provisions (double-time rules, foreperson differentials, subsistence
    tables, nuclear-site LOUs) exist in the corpus but are missed by plain
    cosine on the full query, which surfaces related sections rather than the
    specific clause (issue #78). Each matched rule contributes a short focused
    phrase that the retrieval layer re-embeds as a secondary query vector.
    Terms are returned de-duplicated, preserving rule order; an empty list
    means no provision-recall pass is needed.
    """
    terms: list[str] = []
    for pattern, expansions in _PROVISION_TERM_RULES:
        if pattern.search(query):
            terms.extend(expansions)
    # De-duplicate, preserving first-seen order (mirrors retrieve()'s dict trick).
    return list(dict.fromkeys(terms))


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
        provision_terms=detect_provision_terms(query),
    )
