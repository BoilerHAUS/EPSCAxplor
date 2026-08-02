"""Tests for run_pipeline entry selection (targeted reingest, #178).

``_select_entries`` is the pure filter behind ``--doc-type`` and
``--source-filename``: it lets a drift fix reingest just the handful of changed
documents instead of re-embedding an entire document_type.
"""

from __future__ import annotations

from run_pipeline import _select_entries


def _entry(doc_type: str, source_filename: str) -> dict[str, str]:
    return {"document_type": doc_type, "source_filename": source_filename}


_ENTRIES = [
    _entry("wage_schedule", "E-10-C LU 353 Oshawa-Port Hope - May 01, 2026.pdf"),
    _entry("wage_schedule", "SM - 14 LU 504 Sudbury - May 1, 2025.pdf"),
    _entry("primary_ca", "IBEW Generation- 2025-2030 Collective Agreement.pdf"),
]


class TestSelectEntries:
    def test_no_filters_returns_all(self) -> None:
        assert _select_entries(_ENTRIES, doc_type=None, source_filenames=None) == _ENTRIES

    def test_doc_type_filter(self) -> None:
        selected = _select_entries(_ENTRIES, doc_type="wage_schedule", source_filenames=None)
        assert [e["source_filename"] for e in selected] == [
            "E-10-C LU 353 Oshawa-Port Hope - May 01, 2026.pdf",
            "SM - 14 LU 504 Sudbury - May 1, 2025.pdf",
        ]

    def test_source_filename_filter_is_exact(self) -> None:
        selected = _select_entries(
            _ENTRIES,
            doc_type=None,
            source_filenames=["SM - 14 LU 504 Sudbury - May 1, 2025.pdf"],
        )
        assert len(selected) == 1
        assert selected[0]["document_type"] == "wage_schedule"

    def test_source_filename_filter_multiple(self) -> None:
        selected = _select_entries(
            _ENTRIES,
            doc_type=None,
            source_filenames=[
                "E-10-C LU 353 Oshawa-Port Hope - May 01, 2026.pdf",
                "IBEW Generation- 2025-2030 Collective Agreement.pdf",
            ],
        )
        assert len(selected) == 2

    def test_filters_compose_as_and(self) -> None:
        # doc_type + source_filename are ANDed: a name of the wrong type drops.
        selected = _select_entries(
            _ENTRIES,
            doc_type="wage_schedule",
            source_filenames=["IBEW Generation- 2025-2030 Collective Agreement.pdf"],
        )
        assert selected == []

    def test_unknown_source_filename_selects_nothing(self) -> None:
        selected = _select_entries(_ENTRIES, doc_type=None, source_filenames=["nope.pdf"])
        assert selected == []

    def test_empty_source_filenames_list_is_ignored(self) -> None:
        # An empty list means "no source filter", not "match nothing".
        assert _select_entries(_ENTRIES, doc_type=None, source_filenames=[]) == _ENTRIES
