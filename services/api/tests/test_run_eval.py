"""Tests for eval/run_eval.py — smoke-eval subset selection and regression checks (#87)."""

from __future__ import annotations

import pytest

from eval.run_eval import (
    GOLD_QUESTIONS,
    EvalResult,
    GoldQuestion,
    filter_questions,
    find_regressions,
)


def _result(
    question: GoldQuestion,
    *,
    answer: str = "",
    citations: list[dict[str, object]] | None = None,
    error: str | None = None,
) -> EvalResult:
    return EvalResult(
        question=question,
        answer=answer,
        citations=citations or [],
        model_used="claude-haiku",
        query_log_id="log-1",
        latency_ms=100,
        error=error,
    )


def _gold(qid: str) -> GoldQuestion:
    return next(q for q in GOLD_QUESTIONS if q.id == qid)


# ── filter_questions ─────────────────────────────────────────────────────────

def test_filter_questions_returns_requested_ids() -> None:
    qs = filter_questions(["W10", "R03"])
    assert [q.id for q in qs] == ["W10", "R03"]


def test_filter_questions_preserves_requested_order() -> None:
    qs = filter_questions(["R03", "W10", "N06"])
    assert [q.id for q in qs] == ["R03", "W10", "N06"]


def test_filter_questions_raises_on_unknown_id() -> None:
    with pytest.raises(ValueError, match="ZZ99"):
        filter_questions(["W10", "ZZ99"])


# The nightly workflow runs this exact subset — keep in sync with
# .github/workflows/nightly-smoke.yml. Only DETERMINISTIC gates belong here:
# specific-figure auto-checks (W10 wage / C03 cross-union) plus one in-corpus
# nuclear question that reliably cites (N06). The nondeterministic borderline
# gates — union-less N07 and out-of-corpus refusal R03 — were removed in #163
# after they flip-flopped night to night at temperature 1.0; they stay in the
# full gold set for the periodic manual eval.
SMOKE_SUBSET_IDS = ["W10", "N06", "C03"]


def test_smoke_subset_ids_all_exist() -> None:
    # Guard against a future gold-question rename breaking the nightly subset.
    assert [q.id for q in filter_questions(SMOKE_SUBSET_IDS)] == SMOKE_SUBSET_IDS


def test_smoke_subset_gates_are_deterministic() -> None:
    # Regression guard against re-introducing a flaky gate (#163). Every nightly
    # smoke question must be a deterministic pass/fail: never a refusal (which
    # reds the build whenever the model happens to cite a tangential chunk), and
    # always targeting a real in-corpus union (so retrieval reliably returns
    # citeable chunks — excludes the union-less / out-of-corpus shapes whose
    # citation count is nondeterministic at temperature 1.0). Each must also
    # carry a concrete assertion: an expected figure or a citation requirement.
    for q in filter_questions(SMOKE_SUBSET_IDS):
        assert not q.is_refusal, f"{q.id}: refusal gates are nondeterministic"
        assert not q.union.startswith("N/A"), (
            f"{q.id}: union-less/out-of-corpus gates are nondeterministic"
        )
        assert q.expected_contains or q.expect_citations, (
            f"{q.id}: nightly gate needs a deterministic assertion"
        )


def test_n06_carries_the_nightly_citation_guard() -> None:
    # N06 (in-corpus Boilermakers/Darlington nuclear) reliably returns citations,
    # so in the nightly it carries the "grounded answers keep their [SOURCE N]
    # citations" guard (the #119 property) in place of the nondeterministic
    # union-less N07 (#163). N07 keeps the same assertion in the full gold set.
    q = _gold("N06")
    assert q.expect_citations is True
    assert q.is_nuclear is True
    assert not q.union.startswith("N/A")
    # 0 citations on N06 must red the nightly.
    problems = find_regressions([_result(q, answer="Conditions apply.", citations=[])])
    assert len(problems) == 1 and "N06" in problems[0]


def test_n07_is_union_less_nuclear_expecting_citations() -> None:
    # N07 guards the union-LESS nuclear retrieval path that #119 broke: a hedged
    # but grounded answer must keep its [SOURCE N] citations. The question names a
    # nuclear site (Bruce Power) but no union, so it exercises the un-scoped path
    # every other gold question skips.
    q = _gold("N07")
    assert q.is_nuclear is True
    assert q.expect_citations is True
    assert q.is_refusal is False
    assert "bruce power" in q.question.lower()


# ── find_regressions ─────────────────────────────────────────────────────────

def test_no_regressions_on_clean_results() -> None:
    results = [
        _result(_gold("W10"), answer="The rate is $44.69 per hour.",
                citations=[{"source_number": 1}]),
        _result(_gold("R03"), answer="That information is not available in the provided sources.",
                citations=[]),
    ]
    assert find_regressions(results) == []


def test_api_error_is_a_regression() -> None:
    problems = find_regressions([_result(_gold("N06"), error="HTTP 502: bad gateway")])
    assert len(problems) == 1
    assert "N06" in problems[0]
    assert "502" in problems[0]


def test_auto_check_fail_is_a_regression() -> None:
    # W10 expects "44.69"; a wrong rate must be caught.
    problems = find_regressions(
        [_result(_gold("W10"), answer="The rate is $40.00 per hour.",
                 citations=[{"source_number": 1}])]
    )
    assert len(problems) == 1
    assert "W10" in problems[0]
    assert "44.69" in problems[0]


def test_citations_on_refusal_is_a_regression() -> None:
    problems = find_regressions(
        [_result(_gold("R03"), answer="Some fabricated answer.",
                 citations=[{"source_number": 1}])]
    )
    assert len(problems) == 1
    assert "R03" in problems[0]


def test_refusal_without_citations_is_clean() -> None:
    results = [_result(_gold("R03"), answer="Not in the documents.", citations=[])]
    assert find_regressions(results) == []


def _expect_citations_question(qid: str = "EX1") -> GoldQuestion:
    """A union-less nuclear question asserting a grounded (cited) answer (#119)."""
    return GoldQuestion(
        id=qid,
        category="Nuclear Project Specific",
        union="N/A (union-less)",
        question="What are the shift premiums for nuclear work?",
        is_nuclear=True,
        expect_citations=True,
    )


def test_expect_citations_with_zero_is_a_regression() -> None:
    # The exact #119 shape: a grounded answer that came back with no citations
    # because the out-of-corpus refusal stripper zeroed them.
    problems = find_regressions(
        [_result(_expect_citations_question(), answer="Some grounded answer.", citations=[])]
    )
    assert len(problems) == 1
    assert "EX1" in problems[0]


def test_expect_citations_satisfied_is_clean() -> None:
    results = [
        _result(
            _expect_citations_question(),
            answer="Premiums apply. [SOURCE 1]",
            citations=[{"source_number": 1}],
        )
    ]
    assert find_regressions(results) == []


def test_expect_citations_error_reports_only_error() -> None:
    # An errored expect-citations question has zero citations, but the report must
    # surface only the API error — not also a spurious "expected citations" line.
    problems = find_regressions(
        [_result(_expect_citations_question(), error="HTTP 502: bad gateway")]
    )
    assert len(problems) == 1
    assert "error" in problems[0].lower()


def test_error_does_not_double_report_as_auto_check_fail() -> None:
    # An errored wage question has an empty answer (which would FAIL auto-check),
    # but the smoke report should surface only the API error, not both.
    problems = find_regressions([_result(_gold("W10"), error="timeout")])
    assert len(problems) == 1
    assert "error" in problems[0].lower()


# ── enumeration coverage (issue #168) ────────────────────────────────────────


def _coverage_question(threshold: int, qid: str = "EC1") -> GoldQuestion:
    """An enumeration question asserting ≥``threshold`` distinct unions cited."""
    return GoldQuestion(
        id=qid,
        category="Enumeration Coverage",
        union="All unions",
        question="What is the foreman rate for all unions covered under EPSCA?",
        is_cross_union=True,
        min_union_coverage=threshold,
    )


def test_min_union_coverage_defaults_to_zero() -> None:
    # Existing questions must be unaffected: coverage grading only applies when
    # a question opts in with a positive threshold.
    assert _gold("W10").min_union_coverage == 0


def test_union_coverage_counts_distinct_cited_unions() -> None:
    result = _result(
        _coverage_question(3),
        answer="Rates vary by union. [SOURCE 1] [SOURCE 2] [SOURCE 3]",
        citations=[
            {"source_number": 1, "union_name": "IBEW"},
            {"source_number": 2, "union_name": "Carpenters"},
            {"source_number": 3, "union_name": "IBEW"},  # duplicate union
        ],
    )
    assert result.union_coverage == 2


def test_min_union_coverage_shortfall_is_a_regression() -> None:
    problems = find_regressions(
        [
            _result(
                _coverage_question(3),
                answer="Only two unions cited. [SOURCE 1] [SOURCE 2]",
                citations=[
                    {"source_number": 1, "union_name": "IBEW"},
                    {"source_number": 2, "union_name": "Carpenters"},
                ],
            )
        ]
    )
    assert len(problems) == 1
    assert "EC1" in problems[0]
    assert "coverage" in problems[0].lower()


def test_min_union_coverage_met_is_clean() -> None:
    problems = find_regressions(
        [
            _result(
                _coverage_question(3),
                answer="Broad coverage. [SOURCE 1] [SOURCE 2] [SOURCE 3]",
                citations=[
                    {"source_number": 1, "union_name": "IBEW"},
                    {"source_number": 2, "union_name": "Carpenters"},
                    {"source_number": 3, "union_name": "United Association"},
                ],
            )
        ]
    )
    assert problems == []


def test_coverage_error_reports_only_error() -> None:
    # An errored coverage question has zero citations, but the report must
    # surface only the API error — not also a spurious coverage-shortfall line.
    problems = find_regressions(
        [_result(_coverage_question(3), error="HTTP 502: bad gateway")]
    )
    assert len(problems) == 1
    assert "error" in problems[0].lower()


def test_e01_enumeration_gold_question_is_full_eval_only() -> None:
    # The shipped enumeration gold question: asserts multi-union coverage, routes
    # cross-union, and is deliberately kept OUT of the nightly smoke subset (its
    # breadth is nondeterministic at temperature 1.0, like N07/R03 — see #163).
    q = _gold("E01")
    assert q.min_union_coverage >= 2
    assert q.is_cross_union is True
    assert "E01" not in SMOKE_SUBSET_IDS
