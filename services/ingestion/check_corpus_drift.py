"""Detect corpus drift against epsca.org (issue #91).

EPSCA reissues wage schedules mid-cycle (e.g. eight Phase 1 schedules were
silently superseded by May 2026 reissues), so the checked-in corpus goes stale
without any signal.  This script fetches epsca.org/resources, parses the
embedded ``var wageSchedules`` JSON plus the CA/NPA/MOA resource links, and
diffs them against ``corpus_manifest.yaml``:

- **reissued** — a wage schedule whose identity (map code + local + city) is
  unchanged but whose effective date differs (the stale-corpus failure mode);
- **new** / **removed** — documents present on the site but not the manifest,
  or vice versa.

Exit code 0 when the manifest matches the site, 1 when drift is found (so a
scheduled workflow can open an issue), 2 on a fetch/parse error.  The parse and
diff helpers are pure; only ``fetch_epsca_html`` touches the network.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import httpx
import yaml

logger = logging.getLogger(__name__)

EPSCA_RESOURCES_URL = "https://www.epsca.org/resources"
_HERE = Path(__file__).parent
CORPUS_MANIFEST = _HERE / "corpus_manifest.yaml"

_WAGE_SCHEDULES_ANCHOR = re.compile(r"var\s+wageSchedules\s*=\s*")
# CA/NPA/MOA download links: upload/request/<id>?file=<name>.pdf
_RESOURCE_LINK_RE = re.compile(
    r"upload/request/(\d+)\?file=([^\"'&]+?\.pdf)", re.IGNORECASE
)
# The date suffix EPSCA appends to each wage-schedule filename, e.g.
# "... - May 1, 2025.pdf".  Everything before it is the schedule's identity.
_DATE_SUFFIX_RE = re.compile(
    r"\s*-\s*[A-Z][a-z]+\.?\s+\d{1,2},\s+\d{4}\.pdf$", re.IGNORECASE
)
# The resources page also links administrative OPG forms (travel/board sheets,
# clearance requests, reference guides) that are out of ingestion scope and
# would otherwise be perpetual false-positive "new" drift.  Corpus agreement
# documents (CA / NPA / MOA) always name themselves as such, so allow-list on
# those tokens rather than deny-listing the ever-growing set of forms.
_AGREEMENT_TOKENS = ("agreement", "moa", "memorandum")


@dataclass(frozen=True)
class RemoteDoc:
    """A document advertised on epsca.org."""

    filename: str
    download_url: str
    is_wage_schedule: bool


@dataclass
class DriftReport:
    """Corpus drift between the site and the manifest."""

    reissued: list[tuple[str, str]] = field(default_factory=list)  # (old, new)
    new_wage: list[str] = field(default_factory=list)
    removed_wage: list[str] = field(default_factory=list)
    new_other: list[str] = field(default_factory=list)
    removed_other: list[str] = field(default_factory=list)

    @property
    def has_drift(self) -> bool:
        return bool(
            self.reissued
            or self.new_wage
            or self.removed_wage
            or self.new_other
            or self.removed_other
        )


def _extract_braced(text: str, start: int) -> str:
    """Return the balanced ``{...}`` block beginning at index *start*.

    A non-greedy regex would stop at the first ``}`` inside the nested
    ``wageSchedules`` object, so scan with a brace counter instead.
    """
    depth = 0
    for i in range(start, len(text)):
        char = text[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError("unbalanced braces in wageSchedules object")


def parse_wage_schedules(html: str) -> list[RemoteDoc]:
    """Parse the ``var wageSchedules`` object into a flat list of documents.

    The object is keyed ``trade_id -> folder_id -> [entries]``; each entry
    carries a decoded ``name`` and an escaped ``download_url``.
    """
    anchor = _WAGE_SCHEDULES_ANCHOR.search(html)
    if anchor is None:
        raise ValueError("var wageSchedules not found in page")
    brace_start = html.index("{", anchor.end())
    data = json.loads(_extract_braced(html, brace_start))

    docs: list[RemoteDoc] = []
    for folders in data.values():
        for entries in folders.values():
            for entry in entries:
                url = entry.get("download_url")  # json.loads unescapes \/ → /
                if not url:
                    continue
                # The download_url ``file=`` param is the authoritative filename
                # and always carries ".pdf"; the sibling ``name`` field is
                # sometimes truncated (e.g. OE schedules drop the extension), so
                # keying on it against the manifest would false-flag drift.
                name = entry.get("name")
                fallback = name.strip() if isinstance(name, str) else ""
                filename = site_filename_from_url(url) or fallback
                if not filename:
                    continue
                docs.append(
                    RemoteDoc(
                        filename=filename,
                        download_url=str(url),
                        is_wage_schedule=True,
                    )
                )
    return docs


def _looks_like_agreement(filename: str) -> bool:
    """True when a filename names a corpus agreement (CA / NPA / MOA).

    Filters out the administrative OPG forms the resources page also links, so
    they are not reported as new agreement documents every month.
    """
    lower = filename.lower()
    return any(token in lower for token in _AGREEMENT_TOKENS)


def parse_resource_links(html: str, *, wage_filenames: set[str]) -> list[RemoteDoc]:
    """Return the corpus agreement PDF links (CAs, NPAs, MOAs) on the page.

    The page links both agreements and out-of-scope OPG forms as
    ``upload/request`` PDFs; wage schedules are excluded by filename and the
    remaining links are kept only when they look like an agreement
    (``_looks_like_agreement``) so administrative forms don't register as drift.
    """
    seen: dict[str, RemoteDoc] = {}
    for match in _RESOURCE_LINK_RE.finditer(html):
        request_id, encoded = match.group(1), match.group(2)
        filename = unquote(encoded)
        if filename in wage_filenames or filename in seen:
            continue
        if not _looks_like_agreement(filename):
            continue
        seen[filename] = RemoteDoc(
            filename=filename,
            download_url=(
                f"https://www.epsca.org/upload/request/{request_id}"
                f"?file={encoded}&download=1"
            ),
            is_wage_schedule=False,
        )
    return list(seen.values())


def schedule_key(filename: str) -> str:
    """Return a wage schedule's identity: the filename minus its date suffix.

    "AD-1 LU 494 Windsor - May 1, 2025.pdf" and its 2026 reissue share the key
    "AD-1 LU 494 Windsor", so a reissue is detectable as a same-key filename
    change rather than an unrelated add + remove.
    """
    return _DATE_SUFFIX_RE.sub("", filename).strip()


def site_filename_from_url(url: str | None) -> str | None:
    """Return the site's original filename from a manifest ``source_url``.

    The manifest's ``source_filename`` is the *local* target name, which the
    curators sometimes rename (e.g. "UA -" → "United Association -"), so it is
    not a reliable join key against the site.  The ``file=`` query parameter of
    ``source_url`` is the site's own filename and is the correct key.  Returns
    None for missing/PLACEHOLDER URLs with no ``file=`` parameter.
    """
    if not url or "file=" not in url:
        return None
    values = parse_qs(urlsplit(url).query).get("file")  # parse_qs urldecodes
    if not values:
        return None
    return values[0].strip() or None


def load_manifest_filenames(path: Path = CORPUS_MANIFEST) -> tuple[set[str], set[str]]:
    """Return (wage_schedule, other) site filenames the manifest tracks.

    Keyed on the ``source_url`` ``file=`` name (the site's own filename), not
    the local ``source_filename`` — see ``site_filename_from_url``.
    """
    with path.open() as handle:
        data = yaml.safe_load(handle) or {}
    wage: set[str] = set()
    other: set[str] = set()
    for entry in data.get("documents", []):
        filename = site_filename_from_url(entry.get("source_url"))
        if not filename:
            continue
        if entry.get("document_type") == "wage_schedule":
            wage.add(filename)
        else:
            other.add(filename)
    return wage, other


def build_drift_report(
    *,
    remote_docs: list[RemoteDoc],
    manifest_wage: set[str],
    manifest_other: set[str],
) -> DriftReport:
    """Diff the site's documents against the manifest.

    Wage schedules are matched by exact filename first; any leftover add/remove
    pair that shares a schedule identity is reclassified as a reissue so a
    superseded schedule is surfaced as such, not as an unrelated churn.
    """
    remote_wage = {d.filename for d in remote_docs if d.is_wage_schedule}
    remote_other = {d.filename for d in remote_docs if not d.is_wage_schedule}

    added = remote_wage - manifest_wage
    removed = manifest_wage - remote_wage

    # Group removed schedules by identity so a reissue (same identity, new date)
    # pairs with its prior version.  Each prior is consumed at most once (pop),
    # so two adds sharing a key can't both claim the same prior, and a genuine
    # extra removal with the same key is left in removed_wage rather than lost.
    removed_by_key: dict[str, list[str]] = defaultdict(list)
    for name in sorted(removed):
        removed_by_key[schedule_key(name)].append(name)

    reissued: list[tuple[str, str]] = []
    new_wage: list[str] = []
    consumed: set[str] = set()
    for name in sorted(added):
        bucket = removed_by_key.get(schedule_key(name))
        if bucket:
            prior = bucket.pop(0)
            reissued.append((prior, name))
            consumed.add(prior)
        else:
            new_wage.append(name)

    return DriftReport(
        reissued=sorted(reissued),
        new_wage=new_wage,
        removed_wage=sorted(removed - consumed),
        new_other=sorted(remote_other - manifest_other),
        removed_other=sorted(manifest_other - remote_other),
    )


def format_report(report: DriftReport) -> str:
    """Render a drift report as a Markdown summary."""
    if not report.has_drift:
        return "No corpus drift detected — the manifest matches epsca.org."

    lines = ["## Corpus drift detected against epsca.org", ""]
    if report.reissued:
        lines.append(f"### Reissued wage schedules ({len(report.reissued)})")
        lines.append("These are superseded in the corpus — reingest required:")
        for old, new in report.reissued:
            lines.append(f"- `{old}` → `{new}`")
        lines.append("")
    if report.new_wage:
        lines.append(f"### New wage schedules ({len(report.new_wage)})")
        lines.extend(f"- `{name}`" for name in report.new_wage)
        lines.append("")
    if report.removed_wage:
        lines.append(f"### Removed wage schedules ({len(report.removed_wage)})")
        lines.extend(f"- `{name}`" for name in report.removed_wage)
        lines.append("")
    if report.new_other:
        lines.append(f"### New agreement documents ({len(report.new_other)})")
        lines.extend(f"- `{name}`" for name in report.new_other)
        lines.append("")
    if report.removed_other:
        lines.append(f"### Removed agreement documents ({len(report.removed_other)})")
        lines.extend(f"- `{name}`" for name in report.removed_other)
        lines.append("")
    lines.append(
        "Update `services/ingestion/corpus_manifest.yaml` and reingest the "
        "affected documents (see docs/runbooks/ingestion.md)."
    )
    return "\n".join(lines)


def fetch_epsca_html(url: str = EPSCA_RESOURCES_URL, *, timeout: float = 30.0) -> str:
    """Fetch the epsca.org resources page HTML."""
    response = httpx.get(url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    return response.text


def check_drift(
    *,
    html: str,
    manifest_path: Path = CORPUS_MANIFEST,
) -> DriftReport:
    """Parse *html* and diff it against the manifest at *manifest_path*."""
    wage_docs = parse_wage_schedules(html)
    wage_filenames = {d.filename for d in wage_docs}
    other_docs = parse_resource_links(html, wage_filenames=wage_filenames)
    manifest_wage, manifest_other = load_manifest_filenames(manifest_path)
    return build_drift_report(
        remote_docs=[*wage_docs, *other_docs],
        manifest_wage=manifest_wage,
        manifest_other=manifest_other,
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        html = fetch_epsca_html()
        report = check_drift(html=html)
    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
        logger.error("Corpus drift check failed: %s", exc)
        return 2

    summary = format_report(report)
    print(summary)  # noqa: T201 — the workflow captures stdout for the issue body
    return 1 if report.has_drift else 0


if __name__ == "__main__":
    sys.exit(main())
