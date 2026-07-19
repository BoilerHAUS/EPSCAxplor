"""Tests for check_corpus_drift.py (issue #91).

The parse/diff functions are pure and exercised here with small inline
fixtures; the live epsca.org fetch is isolated in fetch_epsca_html and not
tested against the network.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from check_corpus_drift import (
    RemoteDoc,
    build_drift_report,
    format_report,
    load_manifest_filenames,
    parse_resource_links,
    parse_wage_schedules,
    schedule_key,
    site_filename_from_url,
)

# A trimmed stand-in for the epsca.org/resources page: a `var wageSchedules`
# object (trade -> folder -> [entries]) plus a couple of CA/NPA resource links.
# The CA/NPA anchors are built from wrapped literals to keep lines <100 cols.
_IBEW_CA_LINK = (
    '<a href="https://www.epsca.org/upload/request/5'
    "?file=IBEW%20Generation-%202025-2030%20Collective%20Agreement.pdf"
    '&download=1">IBEW CA</a>'
)
_IBEW_NPA_LINK = (
    '<a href="https://www.epsca.org/upload/request/27'
    "?file=IBEW%20Nuclear%20Project%20Agreement.pdf"
    '&download=1">IBEW NPA</a>'
)
_WAGE_SCRIPT = textwrap.dedent(
    r"""
    <html><body>
    <script>
    var wageSchedules = {"2":{"15":[
      {"trade_id":"2","folder_id":"15","folder_name":"Acoustic and Drywall",
       "uploaded_file_id":"2151","name":"AD-1 LU 494 Windsor - May 1, 2025.pdf",
       "download_url":"https:\/\/www.epsca.org\/upload\/request\/15?file=AD-1%20LU%20494%20Windsor%20-%20May%201%2C%202025.pdf&download=1"},
      {"trade_id":"2","folder_id":"15","folder_name":"Acoustic and Drywall",
       "uploaded_file_id":"2152","name":"AD-2 LU 1256 Sarnia - May 1, 2025.pdf",
       "download_url":"https:\/\/www.epsca.org\/upload\/request\/15?file=AD-2%20LU%201256%20Sarnia%20-%20May%201%2C%202025.pdf&download=1"}
    ]},"3":{"20":[
      {"trade_id":"3","folder_id":"20","folder_name":"Carpenters",
       "uploaded_file_id":"3001","name":"CA-1 LU 27 Toronto - May 1, 2025.pdf",
       "download_url":"https:\/\/www.epsca.org\/upload\/request\/20?file=CA-1%20LU%2027%20Toronto%20-%20May%201%2C%202025.pdf&download=1"}
    ]}};
    var windowDisplayed = false;
    </script>
    """
)
_SAMPLE_HTML = f"{_WAGE_SCRIPT}{_IBEW_CA_LINK}\n{_IBEW_NPA_LINK}\n</body></html>"


class TestParseWageSchedules:
    def test_flattens_all_trades_and_folders(self) -> None:
        docs = parse_wage_schedules(_SAMPLE_HTML)
        assert len(docs) == 3
        assert all(d.is_wage_schedule for d in docs)

    def test_filename_comes_from_download_url_not_name_field(self) -> None:
        # The name field is sometimes truncated (OE schedules drop ".pdf");
        # the filename must be derived from the download_url file= param.
        html = _SAMPLE_HTML.replace(
            '"name":"AD-1 LU 494 Windsor - May 1, 2025.pdf"',
            '"name":"AD-1 LU 494 Windsor"',  # truncated, no .pdf
        )
        docs = parse_wage_schedules(html)
        assert "AD-1 LU 494 Windsor - May 1, 2025.pdf" in {d.filename for d in docs}

    def test_names_are_decoded_and_urls_unescaped(self) -> None:
        docs = parse_wage_schedules(_SAMPLE_HTML)
        by_name = {d.filename: d for d in docs}
        assert "AD-1 LU 494 Windsor - May 1, 2025.pdf" in by_name
        url = by_name["AD-1 LU 494 Windsor - May 1, 2025.pdf"].download_url
        assert url.startswith("https://www.epsca.org/upload/request/15")
        assert "\\/" not in url

    def test_missing_var_raises(self) -> None:
        import pytest

        with pytest.raises(ValueError, match="wageSchedules"):
            parse_wage_schedules("<html>no schedules here</html>")

    def test_nested_braces_do_not_truncate_json(self) -> None:
        # The balanced-brace extractor must capture the whole object, not stop
        # at the first closing brace.
        docs = parse_wage_schedules(_SAMPLE_HTML)
        assert "CA-1 LU 27 Toronto - May 1, 2025.pdf" in {d.filename for d in docs}


class TestParseResourceLinks:
    def test_returns_non_wage_pdfs_only(self) -> None:
        wage = {d.filename for d in parse_wage_schedules(_SAMPLE_HTML)}
        links = parse_resource_links(_SAMPLE_HTML, wage_filenames=wage)
        names = {d.filename for d in links}
        assert "IBEW Generation- 2025-2030 Collective Agreement.pdf" in names
        assert "IBEW Nuclear Project Agreement.pdf" in names
        assert all(not d.is_wage_schedule for d in links)

    def test_excludes_wage_schedule_links(self) -> None:
        wage = {d.filename for d in parse_wage_schedules(_SAMPLE_HTML)}
        links = parse_resource_links(_SAMPLE_HTML, wage_filenames=wage)
        assert "AD-1 LU 494 Windsor - May 1, 2025.pdf" not in {d.filename for d in links}

    def test_filenames_are_url_decoded(self) -> None:
        links = parse_resource_links(_SAMPLE_HTML, wage_filenames=set())
        names = {d.filename for d in links}
        assert "IBEW Generation- 2025-2030 Collective Agreement.pdf" in names

    def test_excludes_non_agreement_forms(self) -> None:
        # OPG administrative forms are out of corpus scope and must not be
        # reported as agreement documents (perpetual false-positive drift).
        html = _SAMPLE_HTML.replace(
            "</body></html>",
            '<a href="https://www.epsca.org/upload/request/9'
            '?file=EPSCA%20Clearance%20Request%20Form%20-%20January%202025.pdf'
            '&download=1">Form</a></body></html>',
        )
        links = parse_resource_links(html, wage_filenames=set())
        names = {d.filename for d in links}
        assert "EPSCA Clearance Request Form - January 2025.pdf" not in names
        assert "IBEW Generation- 2025-2030 Collective Agreement.pdf" in names

    def test_keeps_moa_documents(self) -> None:
        html = _SAMPLE_HTML.replace(
            "</body></html>",
            '<a href="https://www.epsca.org/upload/request/56'
            "?file=Travel%20%26%20Board%20MOA%20Updates-%202019%20-%20Painters.pdf"
            '&download=1">MOA</a></body></html>',
        )
        names = {d.filename for d in parse_resource_links(html, wage_filenames=set())}
        assert "Travel & Board MOA Updates- 2019 - Painters.pdf" in names


class TestSiteFilenameFromUrl:
    def test_extracts_and_decodes_file_param(self) -> None:
        url = (
            "https://www.epsca.org/upload/request/13"
            "?file=UA%20-%202025-2030%20Collective%20Agreement.pdf&download=1"
        )
        assert site_filename_from_url(url) == "UA - 2025-2030 Collective Agreement.pdf"

    def test_placeholder_or_missing_returns_none(self) -> None:
        assert site_filename_from_url("PLACEHOLDER") is None
        assert site_filename_from_url(None) is None
        assert site_filename_from_url("") is None


class TestLoadManifestFilenames:
    def test_keys_on_source_url_not_local_source_filename(self, tmp_path: Path) -> None:
        # source_filename is the renamed local name; the join key must be the
        # site's own filename from source_url's file= param.
        manifest = tmp_path / "corpus_manifest.yaml"
        manifest.write_text(
            "documents:\n"
            '  - document_type: "primary_ca"\n'
            '    source_filename: "United Association - 2025-2030 Collective Agreement.pdf"\n'
            '    source_url: "https://www.epsca.org/upload/request/13?file=UA%20-%202025-2030%20Collective%20Agreement.pdf&download=1"\n'
            '  - document_type: "wage_schedule"\n'
            '    source_filename: "Local 46 Barrie UA - May 1 2025 (1).pdf"\n'
            '    source_url: "https://www.epsca.org/upload/request/78?file=UA-1%20LU%2046%20Barrie%20-%20May%201%2C%202025.pdf&download=1"\n'
            '  - document_type: "wage_schedule"\n'
            '    source_filename: "no url doc.pdf"\n'
            '    source_url: "PLACEHOLDER"\n',
            encoding="utf-8",
        )
        wage, other = load_manifest_filenames(manifest)
        assert other == {"UA - 2025-2030 Collective Agreement.pdf"}
        assert wage == {"UA-1 LU 46 Barrie - May 1, 2025.pdf"}


class TestScheduleKey:
    def test_strips_trailing_date(self) -> None:
        assert (
            schedule_key("AD-1 LU 494 Windsor - May 1, 2025.pdf")
            == "AD-1 LU 494 Windsor"
        )

    def test_reissue_shares_key_with_prior_date(self) -> None:
        assert schedule_key("AD-1 LU 494 Windsor - May 1, 2026.pdf") == schedule_key(
            "AD-1 LU 494 Windsor - May 1, 2025.pdf"
        )

    def test_filename_without_date_returns_stem(self) -> None:
        assert schedule_key("SomeSchedule.pdf") == "SomeSchedule.pdf"


def _remote(filename: str, *, wage: bool = True) -> RemoteDoc:
    return RemoteDoc(filename=filename, download_url=f"https://x/{filename}", is_wage_schedule=wage)


class TestBuildDriftReport:
    def test_no_drift_when_manifest_matches_site(self) -> None:
        remote = [_remote("AD-1 LU 494 Windsor - May 1, 2025.pdf")]
        report = build_drift_report(
            remote_docs=remote,
            manifest_wage={"AD-1 LU 494 Windsor - May 1, 2025.pdf"},
            manifest_other=set(),
        )
        assert not report.has_drift

    def test_detects_reissue_as_supersede_not_new_plus_removed(self) -> None:
        remote = [_remote("AD-1 LU 494 Windsor - May 1, 2026.pdf")]
        report = build_drift_report(
            remote_docs=remote,
            manifest_wage={"AD-1 LU 494 Windsor - May 1, 2025.pdf"},
            manifest_other=set(),
        )
        assert report.has_drift
        assert report.reissued == [
            ("AD-1 LU 494 Windsor - May 1, 2025.pdf", "AD-1 LU 494 Windsor - May 1, 2026.pdf")
        ]
        assert report.new_wage == []
        assert report.removed_wage == []

    def test_detects_genuinely_new_schedule(self) -> None:
        remote = [
            _remote("AD-1 LU 494 Windsor - May 1, 2025.pdf"),
            _remote("ZZ-9 LU 999 Newtown - May 1, 2025.pdf"),
        ]
        report = build_drift_report(
            remote_docs=remote,
            manifest_wage={"AD-1 LU 494 Windsor - May 1, 2025.pdf"},
            manifest_other=set(),
        )
        assert report.new_wage == ["ZZ-9 LU 999 Newtown - May 1, 2025.pdf"]
        assert report.reissued == []

    def test_two_adds_sharing_a_key_consume_prior_once(self) -> None:
        # One prior + two new dates of the same schedule: exactly one reissue
        # pair (the earliest add), the other add is genuinely new — the prior
        # must not be double-counted.
        remote = [
            _remote("AD-1 LU 494 Windsor - May 1, 2025.pdf"),
            _remote("AD-1 LU 494 Windsor - May 1, 2026.pdf"),
        ]
        report = build_drift_report(
            remote_docs=remote,
            manifest_wage={"AD-1 LU 494 Windsor - May 1, 2024.pdf"},
            manifest_other=set(),
        )
        assert report.reissued == [
            ("AD-1 LU 494 Windsor - May 1, 2024.pdf", "AD-1 LU 494 Windsor - May 1, 2025.pdf")
        ]
        assert report.new_wage == ["AD-1 LU 494 Windsor - May 1, 2026.pdf"]
        assert report.removed_wage == []

    def test_two_priors_sharing_a_key_are_not_dropped(self) -> None:
        # Two stale manifest entries share an identity; one reissue on the site.
        # One prior pairs; the other must remain reported as removed, not lost.
        report = build_drift_report(
            remote_docs=[_remote("AD-1 LU 494 Windsor - May 1, 2026.pdf")],
            manifest_wage={
                "AD-1 LU 494 Windsor - May 1, 2024.pdf",
                "AD-1 LU 494 Windsor - May 1, 2025.pdf",
            },
            manifest_other=set(),
        )
        assert len(report.reissued) == 1
        assert report.removed_wage == ["AD-1 LU 494 Windsor - May 1, 2025.pdf"]
        assert report.new_wage == []

    def test_detects_removed_schedule(self) -> None:
        report = build_drift_report(
            remote_docs=[_remote("AD-1 LU 494 Windsor - May 1, 2025.pdf")],
            manifest_wage={
                "AD-1 LU 494 Windsor - May 1, 2025.pdf",
                "OLD-1 LU 111 Gone - May 1, 2025.pdf",
            },
            manifest_other=set(),
        )
        assert report.removed_wage == ["OLD-1 LU 111 Gone - May 1, 2025.pdf"]

    def test_detects_new_and_removed_resource_docs(self) -> None:
        remote = [
            _remote("IBEW Generation- 2025-2030 Collective Agreement.pdf", wage=False),
        ]
        report = build_drift_report(
            remote_docs=remote,
            manifest_wage=set(),
            manifest_other={"Sheet Metal - 2025-2030 Collective Agreement.pdf"},
        )
        assert report.new_other == ["IBEW Generation- 2025-2030 Collective Agreement.pdf"]
        assert report.removed_other == ["Sheet Metal - 2025-2030 Collective Agreement.pdf"]

    def test_format_report_is_readable_and_lists_reissues(self) -> None:
        report = build_drift_report(
            remote_docs=[_remote("AD-1 LU 494 Windsor - May 1, 2026.pdf")],
            manifest_wage={"AD-1 LU 494 Windsor - May 1, 2025.pdf"},
            manifest_other=set(),
        )
        text = format_report(report)
        assert "Reissued" in text
        assert "May 1, 2025" in text
        assert "May 1, 2026" in text
