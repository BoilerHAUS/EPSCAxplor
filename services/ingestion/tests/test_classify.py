"""Tests for classify.py — Stage 3 of the ingestion pipeline."""

from pathlib import Path

import pytest
import yaml

from classify import ClassifiedDocument, DocumentMetadata, classify
from extract import ExtractedDocument

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_manifest(entries: list[dict]) -> dict:
    return {"documents": entries}


def _manifest_entry(
    source_filename: str,
    union_name: str = "IBEW",
    document_type: str = "primary_ca",
    agreement_scope: str | None = "generation",
    effective_date: str = "2025-05-01",
    expiry_date: str | None = "2030-04-30",
    title: str = "IBEW Test Agreement",
    source_url: str | None = "PLACEHOLDER",
) -> dict:
    return {
        "union_name": union_name,
        "document_type": document_type,
        "agreement_scope": agreement_scope,
        "source_filename": source_filename,
        "effective_date": effective_date,
        "expiry_date": expiry_date,
        "title": title,
        "source_url": source_url,
    }


def _write_manifest(tmp_path: Path, entries: list[dict]) -> Path:
    p = tmp_path / "manifest.yaml"
    p.write_text(yaml.dump(_make_manifest(entries)))
    return p


def _make_extracted(filename: str, tmp_path: Path) -> ExtractedDocument:
    pdf = tmp_path / filename
    pdf.write_bytes(b"%PDF-1.4 fake")
    return ExtractedDocument(source_path=pdf)


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestClassifyReturnType:
    def test_returns_classified_document(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(tmp_path, [_manifest_entry("test.pdf")])
        doc = _make_extracted("test.pdf", tmp_path)
        result = classify(doc, manifest_path)
        assert isinstance(result, ClassifiedDocument)

    def test_extracted_document_is_preserved(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(tmp_path, [_manifest_entry("test.pdf")])
        doc = _make_extracted("test.pdf", tmp_path)
        result = classify(doc, manifest_path)
        assert result.extracted is doc

    def test_metadata_is_document_metadata(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(tmp_path, [_manifest_entry("test.pdf")])
        doc = _make_extracted("test.pdf", tmp_path)
        result = classify(doc, manifest_path)
        assert isinstance(result.metadata, DocumentMetadata)


class TestMetadataFields:
    def test_union_name_assigned(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(
            tmp_path, [_manifest_entry("sm.pdf", union_name="Sheet Metal")]
        )
        doc = _make_extracted("sm.pdf", tmp_path)
        result = classify(doc, manifest_path)
        assert result.metadata.union_name == "Sheet Metal"

    def test_document_type_primary_ca(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(
            tmp_path, [_manifest_entry("ca.pdf", document_type="primary_ca")]
        )
        doc = _make_extracted("ca.pdf", tmp_path)
        result = classify(doc, manifest_path)
        assert result.metadata.document_type == "primary_ca"

    def test_document_type_nuclear_pa(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(
            tmp_path, [_manifest_entry("npa.pdf", document_type="nuclear_pa")]
        )
        doc = _make_extracted("npa.pdf", tmp_path)
        result = classify(doc, manifest_path)
        assert result.metadata.document_type == "nuclear_pa"

    def test_document_type_wage_schedule(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(
            tmp_path,
            [_manifest_entry("wage.pdf", document_type="wage_schedule", expiry_date=None)],
        )
        doc = _make_extracted("wage.pdf", tmp_path)
        result = classify(doc, manifest_path)
        assert result.metadata.document_type == "wage_schedule"

    def test_agreement_scope_generation(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(
            tmp_path, [_manifest_entry("ibew.pdf", agreement_scope="generation")]
        )
        doc = _make_extracted("ibew.pdf", tmp_path)
        result = classify(doc, manifest_path)
        assert result.metadata.agreement_scope == "generation"

    def test_agreement_scope_none_for_unions_without_scope(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(
            tmp_path, [_manifest_entry("sm.pdf", agreement_scope=None)]
        )
        doc = _make_extracted("sm.pdf", tmp_path)
        result = classify(doc, manifest_path)
        assert result.metadata.agreement_scope is None

    def test_effective_date_assigned(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(
            tmp_path, [_manifest_entry("test.pdf", effective_date="2025-05-01")]
        )
        doc = _make_extracted("test.pdf", tmp_path)
        result = classify(doc, manifest_path)
        assert result.metadata.effective_date == "2025-05-01"

    def test_expiry_date_assigned(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(
            tmp_path, [_manifest_entry("test.pdf", expiry_date="2030-04-30")]
        )
        doc = _make_extracted("test.pdf", tmp_path)
        result = classify(doc, manifest_path)
        assert result.metadata.expiry_date == "2030-04-30"

    def test_expiry_date_none_for_wage_schedules(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(
            tmp_path,
            [_manifest_entry("wage.pdf", document_type="wage_schedule", expiry_date=None)],
        )
        doc = _make_extracted("wage.pdf", tmp_path)
        result = classify(doc, manifest_path)
        assert result.metadata.expiry_date is None

    def test_title_assigned(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(
            tmp_path,
            [_manifest_entry("ibew.pdf", title="IBEW Generation 2025-2030 Collective Agreement")],
        )
        doc = _make_extracted("ibew.pdf", tmp_path)
        result = classify(doc, manifest_path)
        assert result.metadata.title == "IBEW Generation 2025-2030 Collective Agreement"

    def test_source_url_assigned(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(
            tmp_path,
            [_manifest_entry("ibew.pdf", source_url="https://example.com/doc.pdf")],
        )
        doc = _make_extracted("ibew.pdf", tmp_path)
        result = classify(doc, manifest_path)
        assert result.metadata.source_url == "https://example.com/doc.pdf"

    def test_source_url_none_when_absent_from_manifest(self, tmp_path: Path) -> None:
        entry = _manifest_entry("ibew.pdf")
        del entry["source_url"]
        manifest_path = _write_manifest(tmp_path, [entry])
        doc = _make_extracted("ibew.pdf", tmp_path)
        result = classify(doc, manifest_path)
        assert result.metadata.source_url is None


class TestFilenameMatching:
    def test_matches_by_source_filename(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(
            tmp_path, [_manifest_entry("IBEW Generation- 2025-2030 Collective Agreement.pdf")]
        )
        doc = _make_extracted("IBEW Generation- 2025-2030 Collective Agreement.pdf", tmp_path)
        result = classify(doc, manifest_path)
        assert result.metadata.union_name == "IBEW"

    def test_matches_regardless_of_parent_directory(self, tmp_path: Path) -> None:
        """File in a subdirectory matches by filename only."""
        manifest_path = _write_manifest(tmp_path, [_manifest_entry("match.pdf")])
        subdir = tmp_path / "ibew" / "primary_ca"
        subdir.mkdir(parents=True)
        pdf = subdir / "match.pdf"
        pdf.write_bytes(b"%PDF fake")
        doc = ExtractedDocument(source_path=pdf)
        result = classify(doc, manifest_path)
        assert result.metadata.union_name == "IBEW"

    def test_selects_correct_entry_from_multiple(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(
            tmp_path,
            [
                _manifest_entry("ibew.pdf", union_name="IBEW"),
                _manifest_entry("sm.pdf", union_name="Sheet Metal"),
                _manifest_entry("ua.pdf", union_name="United Association"),
            ],
        )
        doc = _make_extracted("sm.pdf", tmp_path)
        result = classify(doc, manifest_path)
        assert result.metadata.union_name == "Sheet Metal"


class TestErrorHandling:
    def test_raises_value_error_for_unknown_document(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(tmp_path, [_manifest_entry("known.pdf")])
        doc = _make_extracted("unknown.pdf", tmp_path)
        with pytest.raises(ValueError, match="unknown.pdf"):
            classify(doc, manifest_path)

    def test_error_message_includes_filename(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(tmp_path, [])
        doc = _make_extracted("missing-doc.pdf", tmp_path)
        with pytest.raises(ValueError, match="missing-doc.pdf"):
            classify(doc, manifest_path)


class TestYamlDateNormalisation:
    def test_bare_yaml_date_normalised_to_iso_string(self, tmp_path: Path) -> None:
        """PyYAML parses unquoted YYYY-MM-DD as datetime.date; we must coerce to str."""
        # Write manifest with unquoted dates so PyYAML produces datetime.date objects
        manifest_path = tmp_path / "manifest.yaml"
        manifest_path.write_text(
            "documents:\n"
            "  - union_name: IBEW\n"
            "    document_type: primary_ca\n"
            "    agreement_scope: generation\n"
            "    title: IBEW Test\n"
            "    source_url: PLACEHOLDER\n"
            "    source_filename: date-test.pdf\n"
            "    effective_date: 2025-05-01\n"  # bare date → datetime.date
            "    expiry_date: 2030-04-30\n"      # bare date → datetime.date
        )
        doc = _make_extracted("date-test.pdf", tmp_path)
        result = classify(doc, manifest_path)
        assert result.metadata.effective_date == "2025-05-01"
        assert isinstance(result.metadata.effective_date, str)

    def test_bare_yaml_expiry_date_normalised(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "manifest2.yaml"
        manifest_path.write_text(
            "documents:\n"
            "  - union_name: Sheet Metal\n"
            "    document_type: primary_ca\n"
            "    agreement_scope: null\n"
            "    title: Sheet Metal Test\n"
            "    source_url: PLACEHOLDER\n"
            "    source_filename: sm-date.pdf\n"
            "    effective_date: 2025-05-01\n"
            "    expiry_date: 2030-04-30\n"
        )
        doc = _make_extracted("sm-date.pdf", tmp_path)
        result = classify(doc, manifest_path)
        assert result.metadata.expiry_date == "2030-04-30"
        assert isinstance(result.metadata.expiry_date, str)
