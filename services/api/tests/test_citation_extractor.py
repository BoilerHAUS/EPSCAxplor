"""Tests for services/api/src/rag/citation_extractor.py.

Covers:
- extract_citations: basic [SOURCE N] extraction
- extract_citations: deduplication of repeated references
- extract_citations: out-of-range source numbers ignored
- extract_citations: case-insensitive matching
- extract_citations: sorted ascending by source_number
- extract_citations: title_map applied over source_filename
- extract_citations: empty answer and empty chunks edge cases
"""

from __future__ import annotations

import pytest

from src.rag.citation_extractor import CitationRef, extract_citations
from src.rag.retrieval import ChunkResult


def make_chunk(
    *,
    document_id: str = "doc-001",
    source_filename: str = "IBEW_CA_2025.pdf",
    union_name: str = "IBEW",
    document_type: str = "primary_ca",
    effective_date: str | None = "2025-05-01",
    expiry_date: str | None = "2030-04-30",
    article_number: str | None = "Article 12",
    article_title: str | None = "Overtime",
    section_number: str | None = "12.03",
    page_number: int | None = 34,
    text: str = "Overtime shall be paid at time and one-half.",
) -> ChunkResult:
    return ChunkResult(
        point_id="pt-001",
        score=0.9,
        document_id=document_id,
        source_filename=source_filename,
        union_name=union_name,
        document_type=document_type,
        agreement_scope=None,
        effective_date=effective_date,
        expiry_date=expiry_date,
        article_number=article_number,
        article_title=article_title,
        section_number=section_number,
        page_number=page_number,
        is_table=False,
        text=text,
    )


# ─── Basic extraction ─────────────────────────────────────────────────────────


def test_single_source_extracted() -> None:
    chunk = make_chunk()
    result = extract_citations("See [SOURCE 1] for details.", [chunk])
    assert len(result) == 1
    assert result[0].source_number == 1
    assert result[0].union_name == "IBEW"
    assert result[0].article == "Article 12"
    assert result[0].section == "12.03"
    assert result[0].excerpt == chunk.text


def test_multiple_sources_extracted() -> None:
    c1 = make_chunk(union_name="IBEW", text="IBEW clause")
    c2 = make_chunk(union_name="UA", document_id="doc-002", text="UA clause")
    answer = "See [SOURCE 1] and [SOURCE 2]."
    result = extract_citations(answer, [c1, c2])
    assert len(result) == 2
    assert result[0].source_number == 1
    assert result[1].source_number == 2


def test_sorted_ascending() -> None:
    c1 = make_chunk(union_name="IBEW")
    c2 = make_chunk(union_name="UA", document_id="doc-002")
    answer = "[SOURCE 2] then [SOURCE 1]"
    result = extract_citations(answer, [c1, c2])
    assert [c.source_number for c in result] == [1, 2]


# ─── Deduplication ───────────────────────────────────────────────────────────


def test_duplicate_references_deduplicated() -> None:
    chunk = make_chunk()
    answer = "[SOURCE 1] confirms this. As noted in [SOURCE 1], it applies."
    result = extract_citations(answer, [chunk])
    assert len(result) == 1


# ─── Out-of-range ─────────────────────────────────────────────────────────────


def test_out_of_range_source_ignored() -> None:
    chunk = make_chunk()
    result = extract_citations("[SOURCE 5] is cited.", [chunk])
    assert result == []


def test_source_zero_ignored() -> None:
    chunk = make_chunk()
    result = extract_citations("[SOURCE 0]", [chunk])
    assert result == []


# ─── Case-insensitive ─────────────────────────────────────────────────────────


def test_case_insensitive_match() -> None:
    chunk = make_chunk()
    result = extract_citations("[source 1] is referenced.", [chunk])
    assert len(result) == 1


# ─── title_map ────────────────────────────────────────────────────────────────


def test_title_map_overrides_source_filename() -> None:
    chunk = make_chunk(document_id="doc-001", source_filename="IBEW_CA_2025.pdf")
    title_map = {"doc-001": "IBEW Generation 2025-2030 Collective Agreement"}
    result = extract_citations("[SOURCE 1]", [chunk], title_map=title_map)
    assert result[0].document_title == "IBEW Generation 2025-2030 Collective Agreement"


def test_missing_title_falls_back_to_filename() -> None:
    chunk = make_chunk(document_id="doc-001", source_filename="fallback.pdf")
    result = extract_citations("[SOURCE 1]", [chunk], title_map=None)
    assert result[0].document_title == "fallback.pdf"


# ─── Edge cases ───────────────────────────────────────────────────────────────


def test_empty_answer_returns_empty() -> None:
    assert extract_citations("", [make_chunk()]) == []


def test_empty_chunks_returns_empty() -> None:
    assert extract_citations("[SOURCE 1]", []) == []


def test_no_source_markers_returns_empty() -> None:
    assert extract_citations("No sources cited here.", [make_chunk()]) == []


def test_refusal_answer_without_source_markers_returns_empty() -> None:
    answer = (
        "The provided documents do not contain information about pension benefits "
        "for retired Boilermakers under EPSCA agreements."
    )
    assert extract_citations(answer, [make_chunk()]) == []


def test_optional_fields_none() -> None:
    chunk = make_chunk(article_number=None, section_number=None, article_title=None, page_number=None)
    result = extract_citations("[SOURCE 1]", [chunk])
    assert result[0].article is None
    assert result[0].section is None
    assert result[0].article_title is None
    assert result[0].page_number is None


def test_citation_ref_model_fields() -> None:
    chunk = make_chunk()
    result = extract_citations("[SOURCE 1]", [chunk])
    ref = result[0]
    assert isinstance(ref, CitationRef)
    assert ref.document_type == "primary_ca"
    assert ref.effective_date == "2025-05-01"
