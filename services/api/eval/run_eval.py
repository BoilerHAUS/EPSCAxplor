"""Phase 1 POC evaluation runner.

Submits 30 gold questions to the live API and records structured results
in docs/evaluation/phase1_results.md for manual review.

Usage:
    python services/api/eval/run_eval.py
    python services/api/eval/run_eval.py --api-url https://api.epscaxplor.boilerhaus.org
    python services/api/eval/run_eval.py --output docs/evaluation/phase1_results.md

Environment:
    API_URL  Override the default live API endpoint.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:
    print("httpx not installed. Run: pip install httpx", file=sys.stderr)
    sys.exit(1)

DEFAULT_API_URL = "https://api.epscaxplor.boilerhaus.org"
DEFAULT_OUTPUT = Path(__file__).parent.parent.parent.parent / "docs" / "evaluation" / "phase1_results.md"

# ---------------------------------------------------------------------------
# Gold question set — 30 questions covering Phase 1 POC unions:
# IBEW Generation, Sheet Metal, United Association
# ---------------------------------------------------------------------------

@dataclass
class GoldQuestion:
    id: str
    category: str
    union: str
    question: str
    expected_contains: list[str] = field(default_factory=list)
    is_refusal: bool = False
    is_cross_union: bool = False
    is_nuclear: bool = False


GOLD_QUESTIONS: list[GoldQuestion] = [
    # ── Wages & Rates ────────────────────────────────────────────────────────
    GoldQuestion(
        id="W01",
        category="Wages & Rates",
        union="IBEW",
        question="What is the journeyperson hourly rate for IBEW Generation electricians effective May 1, 2025?",
    ),
    GoldQuestion(
        id="W02",
        category="Wages & Rates",
        union="IBEW",
        question="What is the foreman wage premium for IBEW Generation electricians?",
    ),
    GoldQuestion(
        id="W03",
        category="Wages & Rates",
        union="IBEW",
        question="What is the tool allowance for IBEW Generation electricians?",
    ),
    GoldQuestion(
        id="W04",
        category="Wages & Rates",
        union="Sheet Metal",
        question="What is the journeyperson hourly rate for Sheet Metal workers effective May 1, 2025?",
    ),
    GoldQuestion(
        id="W05",
        category="Wages & Rates",
        union="Sheet Metal",
        question="What apprentice wage rates apply to Sheet Metal workers under the 2025-2030 collective agreement?",
    ),
    GoldQuestion(
        id="W06",
        category="Wages & Rates",
        union="Sheet Metal",
        question="What is the general foreman wage rate for Sheet Metal workers?",
    ),
    GoldQuestion(
        id="W07",
        category="Wages & Rates",
        union="United Association",
        question="What is the journeyperson hourly rate for United Association plumbers effective May 1, 2025?",
    ),
    GoldQuestion(
        id="W08",
        category="Wages & Rates",
        union="United Association",
        question="What is the foreman premium percentage for United Association workers?",
    ),
    # ── Overtime & Hours ─────────────────────────────────────────────────────
    GoldQuestion(
        id="O01",
        category="Overtime & Hours",
        union="IBEW",
        question="What constitutes overtime for IBEW Generation electricians under the 2025-2030 agreement?",
    ),
    GoldQuestion(
        id="O02",
        category="Overtime & Hours",
        union="IBEW",
        question="What is the overtime rate for IBEW Generation workers on a Saturday?",
    ),
    GoldQuestion(
        id="O03",
        category="Overtime & Hours",
        union="IBEW",
        question="What is the maximum number of regular daily hours for IBEW Generation workers?",
    ),
    GoldQuestion(
        id="O04",
        category="Overtime & Hours",
        union="Sheet Metal",
        question="What are the regular daily hours of work for Sheet Metal workers?",
    ),
    GoldQuestion(
        id="O05",
        category="Overtime & Hours",
        union="Sheet Metal",
        question="What is the overtime rate for Sheet Metal workers on a Sunday?",
    ),
    GoldQuestion(
        id="O06",
        category="Overtime & Hours",
        union="Sheet Metal",
        question="What are the daily overtime rules for Sheet Metal workers under the 2025-2030 agreement?",
    ),
    GoldQuestion(
        id="O07",
        category="Overtime & Hours",
        union="United Association",
        question="What is the double-time rate provision for United Association workers?",
    ),
    GoldQuestion(
        id="O08",
        category="Overtime & Hours",
        union="United Association",
        question="What time does a regular shift start for United Association workers under the 2025-2030 agreement?",
    ),
    # ── Travel & Board ───────────────────────────────────────────────────────
    GoldQuestion(
        id="T01",
        category="Travel & Board",
        union="IBEW",
        question="What is the board allowance for IBEW Generation workers working away from home?",
    ),
    GoldQuestion(
        id="T02",
        category="Travel & Board",
        union="IBEW",
        question="How far from home must an IBEW Generation worker be to qualify for board allowance?",
    ),
    GoldQuestion(
        id="T03",
        category="Travel & Board",
        union="Sheet Metal",
        question="What is the subsistence allowance for Sheet Metal workers working away from home?",
    ),
    GoldQuestion(
        id="T04",
        category="Travel & Board",
        union="Sheet Metal",
        question="What are the travel zone provisions for Sheet Metal workers?",
    ),
    GoldQuestion(
        id="T05",
        category="Travel & Board",
        union="United Association",
        question="How is travel time compensated for United Association plumbers under the 2025-2030 agreement?",
    ),
    # ── Nuclear Project Specific ─────────────────────────────────────────────
    GoldQuestion(
        id="N01",
        category="Nuclear Project Specific",
        union="IBEW",
        question="Are there different overtime rules for IBEW Generation workers at a nuclear project site?",
        is_nuclear=True,
    ),
    GoldQuestion(
        id="N02",
        category="Nuclear Project Specific",
        union="IBEW",
        question="What additional provisions apply to IBEW Generation electricians working at Darlington?",
        is_nuclear=True,
    ),
    GoldQuestion(
        id="N03",
        category="Nuclear Project Specific",
        union="Sheet Metal",
        question="What special conditions apply to Sheet Metal workers under the Nuclear Project Agreement?",
        is_nuclear=True,
    ),
    GoldQuestion(
        id="N04",
        category="Nuclear Project Specific",
        union="United Association",
        question="Do United Association workers receive any premium for working on a nuclear project site?",
        is_nuclear=True,
    ),
    GoldQuestion(
        id="N05",
        category="Nuclear Project Specific",
        union="IBEW",
        question="What are the travel provisions for IBEW Generation workers under the Nuclear Project Agreement?",
        is_nuclear=True,
    ),
    # ── Cross-Union Comparisons ───────────────────────────────────────────────
    GoldQuestion(
        id="C01",
        category="Cross-Union Comparison",
        union="IBEW / Sheet Metal",
        question="Compare the overtime rules for IBEW Generation and Sheet Metal workers under their 2025-2030 agreements.",
        is_cross_union=True,
    ),
    GoldQuestion(
        id="C02",
        category="Cross-Union Comparison",
        union="IBEW / United Association",
        question="Which union has the higher journeyperson base rate as of May 2025: IBEW Generation or United Association?",
        is_cross_union=True,
    ),
    # ── Refusal / Out-of-scope ────────────────────────────────────────────────
    GoldQuestion(
        id="R01",
        category="Refusal",
        union="N/A (out of corpus)",
        question="What are the pension benefits for retired Boilermakers under EPSCA agreements?",
        is_refusal=True,
    ),
    GoldQuestion(
        id="R02",
        category="Refusal",
        union="N/A (out of corpus)",
        question="What is the grievance arbitration process for IBEW Transmission workers at Bruce Power?",
        is_refusal=True,
    ),
]


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

@dataclass
class EvalResult:
    question: GoldQuestion
    answer: str
    citations: list[dict[str, Any]]
    model_used: str
    query_log_id: str | None
    latency_ms: int
    error: str | None = None

    @property
    def citation_count(self) -> int:
        return len(self.citations)

    @property
    def is_refusal_response(self) -> bool:
        refusal_phrases = [
            "not present in the provided sources",
            "not covered in the sources",
            "information is not available",
            "not in the documents",
            "cannot find",
            "no information",
            "not found in",
        ]
        return any(phrase in self.answer.lower() for phrase in refusal_phrases)


def _submit_question(client: httpx.Client, api_url: str, question: str) -> dict[str, Any]:
    resp = client.post(
        f"{api_url}/query",
        json={"query": question},
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()


def run_eval(api_url: str, output_path: Path) -> list[EvalResult]:
    results: list[EvalResult] = []

    print(f"Submitting {len(GOLD_QUESTIONS)} questions to {api_url}")
    print("-" * 60)

    with httpx.Client() as client:
        for i, gq in enumerate(GOLD_QUESTIONS, 1):
            print(f"[{i:02d}/{len(GOLD_QUESTIONS)}] {gq.id} — {gq.question[:70]}...")
            start = time.monotonic()
            error = None
            raw: dict[str, Any] = {}
            try:
                raw = _submit_question(client, api_url, gq.question)
            except httpx.HTTPStatusError as exc:
                error = f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            except Exception as exc:  # noqa: BLE001
                error = str(exc)

            latency_ms = int((time.monotonic() - start) * 1000)

            result = EvalResult(
                question=gq,
                answer=raw.get("answer", ""),
                citations=raw.get("citations", []),
                model_used=raw.get("model_used", ""),
                query_log_id=raw.get("query_log_id"),
                latency_ms=latency_ms,
                error=error,
            )
            results.append(result)

            status = "ERROR" if error else f"{result.citation_count} citations"
            print(f"         → {status} ({latency_ms}ms)")

    _write_markdown(results, output_path)
    _write_json(results, output_path.with_suffix(".json"))
    print(f"\nResults written to {output_path}")
    return results


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def _write_json(results: list[EvalResult], path: Path) -> None:
    data = []
    for r in results:
        data.append({
            "id": r.question.id,
            "category": r.question.category,
            "union": r.question.union,
            "question": r.question.question,
            "answer": r.answer,
            "citations": r.citations,
            "model_used": r.model_used,
            "query_log_id": r.query_log_id,
            "latency_ms": r.latency_ms,
            "error": r.error,
            "flags": {
                "is_nuclear": r.question.is_nuclear,
                "is_cross_union": r.question.is_cross_union,
                "is_refusal": r.question.is_refusal,
            },
        })
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _citation_table(citations: list[dict[str, Any]]) -> str:
    if not citations:
        return "_No citations returned._"
    rows = ["| # | Union | Document | Article | Section |",
            "|---|-------|----------|---------|---------|"]
    for c in citations:
        rows.append(
            f"| {c.get('source_number', '')} "
            f"| {c.get('union_name', '')} "
            f"| {c.get('document_title', '')[:50]} "
            f"| {c.get('article', '') or ''} "
            f"| {c.get('section', '') or ''} |"
        )
    return "\n".join(rows)


def _write_markdown(results: list[EvalResult], path: Path) -> None:
    run_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total = len(results)
    errors = sum(1 for r in results if r.error)

    lines: list[str] = [
        "# Phase 1 POC Evaluation Results",
        "",
        f"**Run date:** {run_at}  ",
        f"**Questions:** {total}  ",
        f"**API errors:** {errors}  ",
        "",
        "> **Note:** Correctness and citation accuracy scores require manual review against",
        "> the source PDFs. Fill in the `Correct?` and `Citations valid?` columns below.",
        "",
        "## Acceptance Criteria",
        "",
        "| Criterion | Threshold | Result |",
        "|-----------|-----------|--------|",
        "| Correctness | ≥ 85% | _pending review_ |",
        "| Citation accuracy | 100% | _pending review_ |",
        "| Zero hallucinated facts on refusal questions | 0 | _pending review_ |",
        "| Cross-union comparison valid | Pass/Fail | _pending review_ |",
        "| Nuclear context includes NPA chunks | Pass/Fail | _pending review_ |",
        "",
        "---",
        "",
    ]

    categories: dict[str, list[EvalResult]] = {}
    for r in results:
        categories.setdefault(r.question.category, []).append(r)

    for category, cat_results in categories.items():
        lines += [f"## {category}", ""]
        for r in cat_results:
            lines += [
                f"### {r.question.id} — {r.question.union}",
                "",
                f"**Question:** {r.question.question}",
                "",
            ]

            if r.error:
                lines += [f"> **ERROR:** {r.error}", ""]
                continue

            lines += [
                "**Answer:**",
                "",
                r.answer,
                "",
                "**Citations:**",
                "",
                _citation_table(r.citations),
                "",
                f"**Model used:** `{r.model_used}`  ",
                f"**Latency:** {r.latency_ms}ms  ",
                f"**Query log ID:** `{r.query_log_id or 'N/A'}`",
                "",
                "**Manual review:**",
                "",
                "| Correct? | Citations valid? | Notes |",
                "|----------|-----------------|-------|",
                "| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |",
                "",
                "---",
                "",
            ]

    lines += [
        "## Summary Table",
        "",
        "Fill in after reviewing all answers:",
        "",
        "| ID | Category | Union | Correct? | Citations valid? | Notes |",
        "|----|----------|-------|----------|-----------------|-------|",
    ]
    for r in results:
        lines.append(
            f"| {r.question.id} | {r.question.category} | {r.question.union} "
            "| | | |"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="EPSCAxplor Phase 1 evaluation runner")
    parser.add_argument(
        "--api-url",
        default=os.environ.get("API_URL", DEFAULT_API_URL),
        help="Base URL of the live API (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output markdown file path (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print questions without submitting to API",
    )
    args = parser.parse_args()

    if args.dry_run:
        for gq in GOLD_QUESTIONS:
            print(f"[{gq.id}] ({gq.category}) {gq.question}")
        return

    run_eval(args.api_url, args.output)


if __name__ == "__main__":
    main()
