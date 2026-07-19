"""Deterministic parser for standard-form EPSCA wage schedule PDFs.

Every EPSCA wage schedule (IBEW, Sheet Metal, UA, …) uses the same printed
form: a MAP CODE header block, the local union and city, a column header
band, then classification blocks whose rate lines are ``YYYY-MM-DD`` followed
by a fixed number of dollar figures.  The text layer parses cleanly with
pdfplumber's layout mode, so no table-recognition model is needed.

The parser emits one embedding-friendly chunk per classification group.  Each
chunk restates its full identity (union, local, city, schedule code) and
spells out every rate column by name, e.g.::

    IBEW Local 105 (Hamilton) — ELECTRICAL WORKERS EPSCA Wage Schedule E-6-C ...
    Classification: JOURNEYMAN / WELDER / ... (occupation codes 410135, ...)
    Effective 2025-05-01: base hourly rate $46.65, ... total wage package $73.72.

Rate rows self-validate: the first five columns (base, vacation, welfare,
pension/retirement, union funds) must sum to the sixth (total wage package).
"""

from __future__ import annotations

import logging
import os
import re
from chunk import Chunk
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


def epsca_wage_parser_enabled() -> bool:
    """Deterministic EPSCA-form parsing is the default wage_schedule path.

    Set INGEST_EPSCA_WAGE_PARSER=0 to fall back to the legacy extraction path.
    """
    raw = os.getenv("INGEST_EPSCA_WAGE_PARSER")
    if raw is None:
        return True
    return raw.strip().lower() in {"1", "true", "yes", "on"}

# Chunk budget mirrors chunk.py (500 tokens ≈ 2 000 chars); notes chunks are
# split to stay under it.
_MAX_NOTES_CHARS = 1800
_SUM_TOLERANCE = 0.06  # dollars; covers per-column rounding in the source PDFs

# Column semantics are resolved per page from the printed column-header band:
# the first columns are always base / vacation / welfare / pension-or-retirement
# (+ optional RRSP) / union funds, then TOTAL WAGE PACKAGE, then a per-trade
# tail (Bill 162, education fund, provincial training fund, EPSCA fund).
_LEADING_FIVE = (
    "base hourly rate",
    "vacation & statutory holiday pay",
    "welfare",
)

_MAP_CODE_LINE_RE = re.compile(r"MAP\s+CODE:", re.IGNORECASE)
_PAGE_OF_RE = re.compile(r"(\d+)\s+OF\s+(\d+)", re.IGNORECASE)
_HUMAN_DATE_RE = re.compile(r"[A-Z][a-z]+\.?\s+\d{1,2},\s+\d{4}")
_DATE_ROW_RE = re.compile(r"^\s*(\d{4}-\d{2}-\d{2})((?:\s+\$?\d+\.\d{2})+)\s*$")
# Grade/step is usually "NN-N" but BACU schedules print "XX".
_GRADE_LABEL_RE = re.compile(r"^\s*(\d{1,2}-\d{1,2}|XX)\s+(\S.*)$")
_OCCUPATION_CODE_RE = re.compile(r"\b(\d{6})\b")
# "1st Period …" (most trades) or "1st 1000 hrs" (Ironworkers apprentices).
_PERIOD_LABEL_RE = re.compile(r"^\d+(?:st|nd|rd|th)\b", re.IGNORECASE)
# Name — optional "- 123456" code(s) — optional "(annotation)" tail.
_LABEL_SPLIT_RE = re.compile(
    r"^(?P<name>.*?)(?:\s*-\s*(?P<codes>\d{6}(?:\s*[,/]\s*\d{6})*))?\s*"
    r"(?P<annotation>\(.+\))?\s*,?\s*$"
)
# Bare (no grade prefix) classification labels: uppercase-dominant lines that
# carry an occupation code, e.g. "ELECTRICIAN APPRENTICE - 410115".
_BARE_LABEL_RE = re.compile(r"^[A-Z][A-Z0-9 .,/&()'’-]*\d{6}[ ,.]*$")
_FOOTNOTE_START_RE = re.compile(r"^(\(\d\)|\*|\*\*)")
_COLUMN_HEADER_KEYWORDS = (
    "CLASSIFICATIONS",
    "OCCUPATION CODES",
    "EFFECTIVE DATES",
)
# Column-header fragments that appear alone on their own line (UA layout).
_COLUMN_HEADER_FRAGMENTS = frozenset({"GRADE", "AND", "STEP", "AND STEP"})
_EPSCA_SCHEDULE_MARKER_RE = re.compile(r"\s+EPSCA\s+WAGE\s+SCHEDULE\b.*$", re.IGNORECASE)
_LOCAL_RE = re.compile(r"\b(Locals?\s+\d+\w*)\b", re.IGNORECASE)
# "Zone 2 - Transmission" line between the header values and the trade name
# (Labourers schedules).
_ZONE_LINE_RE = re.compile(r"^Zone\s+\d", re.IGNORECASE)
# Continuation lines of a multi-local list: "1244, 1410, 1425," (Millwrights).
_LOCALS_CONTINUATION_RE = re.compile(r"^[\d,&\s]+$")


@dataclass(frozen=True)
class WageRateRow:
    """One effective-date line of a classification's rate table."""

    effective_date: str
    values: tuple[float, ...]
    columns: tuple[str, ...]
    sum_valid: bool


@dataclass(frozen=True)
class ClassificationGroup:
    """A classification block: one or more labels sharing a set of rate rows."""

    grade_steps: tuple[str, ...]
    names: tuple[str, ...]
    occupation_codes: tuple[str, ...]
    annotations: tuple[str | None, ...]
    rows: tuple[WageRateRow, ...]


@dataclass(frozen=True)
class WageSchedulePage:
    """A parsed page of an EPSCA wage schedule."""

    map_code: str
    local: str
    city: str
    trade: str
    revised: str | None
    page_in_schedule: int
    pages_in_schedule: int
    pdf_page_number: int
    groups: tuple[ClassificationGroup, ...]
    notes: str | None


# ─── Line-level helpers ───────────────────────────────────────────────────────


def _first_cell(line: str) -> str:
    """Return the leading column of a layout-mode line (split on 2+ spaces)."""
    return re.split(r"\s{2,}", line.strip(), maxsplit=1)[0].strip()


def _trailing_columns(header: str) -> tuple[str, ...]:
    """Column names that follow TOTAL WAGE PACKAGE, per the page's header band."""
    trailing: list[str] = []
    if "BILL" in header:
        trailing.append("Bill 162")
    if "EDUCATION" in header:
        trailing.append("education union fund")
    if "ADMIN" in header:
        trailing.append("administration & training fund")
    elif "PROVINCIAL" in header or "TRAINING FUND" in header:
        trailing.append("provincial training fund")
    if "STABILIZ" in header:  # source PDFs misspell "STABILIZAITON"
        trailing.append("benefits stabilization fund")
    trailing.append("EPSCA association fund")
    return tuple(trailing)


def _find_total_index(values: tuple[float, ...]) -> int | None:
    """Locate the TOTAL WAGE PACKAGE column via the sum invariant.

    The components preceding the total always sum to it.  The standard form
    has 5 components; the RRSP variant (IBEW Local 353) has 6; apprentice and
    probationary rows without a pension column (SM Local 30) have 4; trades
    without printed welfare/pension columns (Cement Masons, Carpenters,
    Plasterers) have 3.
    """
    for k in (5, 6, 4, 3, 7, 2):
        if k < len(values) and abs(sum(values[:k]) - values[k]) <= _SUM_TOLERANCE:
            return k
    return None


_COMPONENT_NAMES: dict[int, tuple[str, ...]] = {
    2: ("base hourly rate", "vacation & statutory holiday pay"),
    3: ("base hourly rate", "vacation & statutory holiday pay", "union funds"),
    4: (*_LEADING_FIVE, "union funds"),
    5: (*_LEADING_FIVE, "{retirement}", "union funds"),
    6: (*_LEADING_FIVE, "{retirement}", "{rrsp}", "union funds"),
    7: (*_LEADING_FIVE, "{retirement}", "{rrsp}", "union funds", "other fund"),
}


def _header_positional_names(count: int, header: str) -> tuple[str, ...] | None:
    """Derive column names purely from the printed header keywords.

    Fallback for schedules whose printed columns do NOT sum to the total
    (e.g. Teamsters, where welfare/pension exist but are not printed).  The
    canonical column order is fixed; we include each column only when its
    keyword appears in the header band, and use the result only when the
    count matches the row.
    """
    names: list[str] = ["base hourly rate", "vacation & statutory holiday pay"]
    if "WELFARE" in header:
        names.append("welfare")
    if "RETIREMENT" in header:
        names.append("retirement fund")
    elif "PENSION" in header:
        names.append("pension")
    if "RRSP" in header:
        names.append("RRSP")
    if "UNION" in header:
        names.append("union funds")
    names.append("total wage package")
    names.extend(_trailing_columns(header))
    return tuple(names) if len(names) == count else None


def _column_names(values: tuple[float, ...], header: str) -> tuple[tuple[str, ...], bool]:
    """Resolve column names for a rate row, returning (names, sum_valid).

    Layout: <components> | total wage package | <trailing per-trade columns>.
    The total's position is found via the sum invariant; component and
    trailing names come from the page's printed column-header keywords.
    When no sum position validates, fall back to purely header-driven
    positional naming (some schedules print totals that include unprinted
    benefit columns).
    """
    count = len(values)
    total_index = _find_total_index(values)
    if total_index is None:
        positional = _header_positional_names(count, header)
        if positional is not None:
            return positional, False
        return tuple(f"column {i + 1}" for i in range(count)), False

    retirement = "retirement fund" if "RETIREMENT" in header else "pension"
    rrsp = "RRSP" if "RRSP" in header else "supplementary fund"
    components = tuple(
        name.format(retirement=retirement, rrsp=rrsp)
        for name in _COMPONENT_NAMES[total_index]
    )

    trailing = _trailing_columns(header)
    n_trailing = count - total_index - 1
    if len(trailing) != n_trailing:
        # Row carries extra printed values the header doesn't explain; keep
        # the validated total position but don't guess the extras' meaning.
        trailing = tuple(f"additional amount {i + 1}" for i in range(n_trailing))

    return (*components, "total wage package", *trailing), True


def _parse_rate_row(match: re.Match[str], header: str) -> WageRateRow:
    effective_date = match.group(1)
    values = tuple(float(v.lstrip("$")) for v in match.group(2).split())
    columns, sum_valid = _column_names(values, header)
    return WageRateRow(
        effective_date=effective_date,
        values=values,
        columns=columns,
        sum_valid=sum_valid,
    )


@dataclass(frozen=True)
class _Label:
    grade_step: str | None
    name: str
    codes: tuple[str, ...]
    annotation: str | None


def _parse_label(text: str, grade_step: str | None) -> _Label:
    text = re.sub(r"\s+", " ", text)
    match = _LABEL_SPLIT_RE.match(text.strip())
    name = text.strip()
    codes: tuple[str, ...] = ()
    annotation: str | None = None
    if match:
        name = match.group("name").strip(" ,-")
        raw_codes = match.group("codes")
        if raw_codes:
            codes = tuple(re.findall(r"\d{6}", raw_codes))
        annotation = match.group("annotation")
        if annotation:
            annotation = annotation.strip()
    # Annotations sometimes precede the code or lack parentheses; keep any
    # residual code found anywhere in the raw text as a fallback.
    if not codes:
        codes = tuple(_OCCUPATION_CODE_RE.findall(text))
        if codes:
            name = re.sub(r"\s*-?\s*\d{6}[ ,.]*", " ", name).strip(" ,-")
    return _Label(grade_step=grade_step, name=name, codes=codes, annotation=annotation)


def _is_column_header_line(line: str) -> bool:
    upper = line.strip().upper()
    return (
        any(keyword in upper for keyword in _COLUMN_HEADER_KEYWORDS)
        or ("GRADE" in upper and "BASE" in upper)
        or upper in _COLUMN_HEADER_FRAGMENTS
    )


def _flush_group(
    labels: list[_Label],
    rows: list[WageRateRow],
    groups: list[ClassificationGroup],
    apprentice_parent: _Label | None,
) -> None:
    if not labels or not rows:
        return

    effective_labels = list(labels)
    # Period-only groups (2nd Period, 3rd Period, …) inherit the most recent
    # apprentice parent label so each chunk names the trade it belongs to.
    if apprentice_parent is not None and all(
        _PERIOD_LABEL_RE.match(label.name) for label in effective_labels
    ):
        effective_labels.insert(0, apprentice_parent)

    groups.append(
        ClassificationGroup(
            grade_steps=tuple(
                dict.fromkeys(
                    label.grade_step for label in effective_labels if label.grade_step
                )
            ),
            names=tuple(dict.fromkeys(label.name for label in effective_labels)),
            occupation_codes=tuple(
                dict.fromkeys(code for label in effective_labels for code in label.codes)
            ),
            annotations=tuple(label.annotation for label in effective_labels),
            rows=tuple(rows),
        )
    )


# ─── Page parsing ─────────────────────────────────────────────────────────────


def parse_wage_schedule_text(
    page_text: str,
    pdf_page_number: int,
) -> WageSchedulePage | None:
    """Parse one page of layout-mode text into a WageSchedulePage.

    Returns None when the page does not carry the standard EPSCA wage
    schedule header (MAP CODE / Local / city block).
    """
    lines = page_text.splitlines()

    header_index = next(
        (i for i, line in enumerate(lines) if _MAP_CODE_LINE_RE.search(line)), None
    )
    if header_index is None:
        return None

    remaining = [line for line in lines[header_index + 1 :]]
    non_blank = [(i, line) for i, line in enumerate(remaining) if line.strip()]
    if len(non_blank) < 4:
        return None

    # Header value line: "E-6-C   May 1, 2022   May 1, 2025   1 OF 2"
    value_line = non_blank[0][1]
    map_code = value_line.split()[0]
    human_dates = _HUMAN_DATE_RE.findall(value_line)
    revised = human_dates[-1] if len(human_dates) >= 2 else None
    page_of = _PAGE_OF_RE.search(value_line)
    page_in_schedule = int(page_of.group(1)) if page_of else 1
    pages_in_schedule = int(page_of.group(2)) if page_of else 1

    # Header block layouts vary: the trade name may span two lines (MARBLE/
    # TILE/TERRAZZO WORKERS), a "Zone N - …" line may precede it (Labourers),
    # the local may read "LOCAL 700" or "LOCALS 1151," with continuation lines
    # (Millwrights), or there may be no local at all (Teamsters, province-
    # wide).  Scan for the local line and derive the rest around it.
    local_index = next(
        (i for i in range(1, min(7, len(non_blank)))
         if _LOCAL_RE.search(non_blank[i][1])),
        None,
    )
    body_start = 4  # classic 4-line header (value / trade / local / city)

    def _trade_from(lines: list[str]) -> str:
        parts = [
            _EPSCA_SCHEDULE_MARKER_RE.sub("", line.strip()).strip()
            for line in lines
            if line.strip() and not _ZONE_LINE_RE.match(line.strip())
        ]
        # Each header line shares space with the schedule description; the
        # trade name is the leading cell of each.
        return " ".join(_first_cell(part) for part in parts if part).strip()

    if local_index is not None:
        local_match = _LOCAL_RE.search(non_blank[local_index][1])
        assert local_match is not None
        local = re.sub(r"\s+", " ", local_match.group(1)).title()
        trade = _trade_from([line for _, line in non_blank[1:local_index]])
        # City: first line after the local that isn't a locals-list
        # continuation ("1244, 1410, 1425,").
        city = ""
        for offset, (_, line) in enumerate(non_blank[local_index + 1 :]):
            cell = _first_cell(line)
            if cell and not _LOCALS_CONTINUATION_RE.match(cell):
                city = cell
                body_start = local_index + 1 + offset + 1
                break
        if not city:
            return None
    else:
        # Province-wide schedule (Teamsters): no local; the line after the
        # trade carries the coverage area.
        if len(non_blank) < 3:
            return None
        local = ""
        trade = _trade_from([non_blank[1][1]])
        # The coverage line may share space with the schedule description
        # ("Province of Ontario GEOGRAPHIC AREA") — strip the trailing
        # all-caps description words.
        city = re.sub(r"(\s+[A-Z][A-Z()0-9,.&/-]*)+$", "", _first_cell(non_blank[2][1]))
        body_start = 3
    if not trade:
        return None

    body_lines = [line for _, line in non_blank[body_start:]]

    groups: list[ClassificationGroup] = []
    note_lines: list[str] = []

    if page_in_schedule > 1:
        # Notes page: overtime rules, union fund breakdowns, zone provisions.
        note_lines = [re.sub(r"\s+", " ", line).strip() for line in body_lines]
    else:
        current_labels: list[_Label] = []
        current_rows: list[WageRateRow] = []
        apprentice_parent: _Label | None = None
        header_text = ""

        for line in body_lines:
            if _is_column_header_line(line):
                header_text += " " + line.strip().upper()
                continue

            date_match = _DATE_ROW_RE.match(line)
            if date_match:
                current_rows.append(_parse_rate_row(date_match, header_text))
                continue

            stripped = line.strip()
            grade_match = _GRADE_LABEL_RE.match(line)
            is_bare_label = bool(_BARE_LABEL_RE.match(stripped)) or (
                "APPRENTICE" in stripped.upper() and not _FOOTNOTE_START_RE.match(stripped)
            )

            if grade_match or is_bare_label:
                if current_rows:
                    _flush_group(current_labels, current_rows, groups, apprentice_parent)
                    current_labels = []
                    current_rows = []
                if grade_match:
                    label = _parse_label(grade_match.group(2), grade_match.group(1))
                else:
                    label = _parse_label(stripped, None)
                if "APPRENTICE" in label.name.upper():
                    apprentice_parent = label
                current_labels.append(label)
                continue

            # Anything else on a rates page (footnotes, stray text) is kept as
            # notes so no source content is silently dropped.
            note_lines.append(re.sub(r"\s+", " ", stripped))

        _flush_group(current_labels, current_rows, groups, apprentice_parent)

    notes_text = "\n".join(line for line in note_lines if line).strip() or None

    return WageSchedulePage(
        map_code=map_code,
        local=local,
        city=city,
        trade=trade,
        revised=revised,
        page_in_schedule=page_in_schedule,
        pages_in_schedule=pages_in_schedule,
        pdf_page_number=pdf_page_number,
        groups=tuple(groups),
        notes=notes_text,
    )


def parse_wage_schedule_pdf(pdf_path: Path) -> list[WageSchedulePage]:
    """Parse every EPSCA wage schedule page in *pdf_path*.

    Raises:
        FileNotFoundError: If pdf_path does not exist.
        ValueError: If no page parses as an EPSCA wage schedule, or no
            classification rate rows are found anywhere in the document.
    """
    import pdfplumber

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages: list[WageSchedulePage] = []
    with pdfplumber.open(pdf_path) as pdf:
        for pdf_page in pdf.pages:
            text = pdf_page.extract_text(layout=True) or ""
            parsed = parse_wage_schedule_text(text, pdf_page_number=pdf_page.page_number)
            if parsed is None or (parsed.page_in_schedule == 1 and not parsed.groups):
                # Oversized page geometries render mostly blank in layout
                # mode; the plain text layer still parses line-by-line.
                plain = pdf_page.extract_text() or ""
                fallback = parse_wage_schedule_text(
                    plain, pdf_page_number=pdf_page.page_number
                )
                if fallback is not None:
                    parsed = fallback
            if parsed is None:
                logger.warning(
                    "%s page %d does not match the EPSCA wage form; skipped",
                    pdf_path.name,
                    pdf_page.page_number,
                )
                continue
            pages.append(parsed)

    if not pages:
        raise ValueError(f"No EPSCA wage schedule pages found in {pdf_path.name}")
    if not any(page.groups for page in pages):
        raise ValueError(f"No classification rate rows parsed from {pdf_path.name}")

    invalid = [
        (page.local, page.city, group.names, row.effective_date)
        for page in pages
        for group in page.groups
        for row in group.rows
        if not row.sum_valid
    ]
    if invalid:
        logger.warning(
            "%s: %d rate rows failed the sum check (base+vacation+welfare+"
            "pension+funds ≈ total): %s",
            pdf_path.name,
            len(invalid),
            invalid[:5],
        )

    return pages


# ─── Chunk building ───────────────────────────────────────────────────────────


def _local_label(page: WageSchedulePage) -> str:
    """"Local 105 Hamilton" or just the coverage area for province-wide docs."""
    return f"{page.local} {page.city}".strip()


def _page_identity(page: WageSchedulePage, union_name: str) -> str:
    revised_part = f", revised {page.revised}" if page.revised else ""
    return (
        f"{union_name} {(page.local + ' ') if page.local else ''}({page.city}) — {page.trade} "
        f"EPSCA Wage Schedule {page.map_code}{revised_part}"
    )


def _format_group_text(
    page: WageSchedulePage,
    group: ClassificationGroup,
    union_name: str,
) -> str:
    names = " / ".join(group.names)
    detail_parts: list[str] = []
    if group.occupation_codes:
        plural = "s" if len(group.occupation_codes) > 1 else ""
        detail_parts.append(f"occupation code{plural} {', '.join(group.occupation_codes)}")
    if group.grade_steps:
        detail_parts.append(f"grade/step {', '.join(group.grade_steps)}")
    detail = f" ({'; '.join(detail_parts)})" if detail_parts else ""

    annotations = [a for a in group.annotations if a]
    annotation_line = f" {' '.join(annotations)}" if annotations else ""

    lines = [
        f"{_page_identity(page, union_name)}.",
        f"Classification: {names}{detail}.{annotation_line}",
        "Hourly rates by effective date:",
    ]
    for row in group.rows:
        pairs = ", ".join(
            f"{column} ${value:.2f}" for column, value in zip(row.columns, row.values, strict=True)
        )
        lines.append(f"- Effective {row.effective_date}: {pairs}.")
    return "\n".join(lines)


def _notes_chunks(
    page: WageSchedulePage,
    union_name: str,
    start_index: int,
) -> list[Chunk]:
    if not page.notes:
        return []

    header = f"{_page_identity(page, union_name)} — schedule notes."
    chunks: list[Chunk] = []
    current: list[str] = []
    current_len = 0

    def _emit() -> None:
        nonlocal current, current_len
        body = "\n".join(current).strip()
        if not body:
            return
        chunks.append(
            Chunk(
                text=f"{header}\n{body}",
                page_number=page.pdf_page_number,
                is_table=False,
                article_number=None,
                section_number=None,
                article_title=f"{_local_label(page)} — Wage Schedule Notes",
                chunk_index=start_index + len(chunks),
                metadata=_base_metadata(page),
            )
        )
        current = []
        current_len = 0

    for line in page.notes.splitlines():
        if current_len + len(line) > _MAX_NOTES_CHARS and current:
            _emit()
        current.append(line)
        current_len += len(line) + 1
    _emit()

    return chunks


def _base_metadata(page: WageSchedulePage) -> dict[str, object]:
    return {
        "wage_schedule": True,
        "table_pipeline": "epsca_form",
        "local": page.local,
        "city": page.city,
        "map_code": page.map_code,
        "trade_name": page.trade,
        "schedule_revised": page.revised,
    }


def build_wage_chunks(
    pages: list[WageSchedulePage],
    union_name: str,
) -> list[Chunk]:
    """Build embedding-ready chunks from parsed wage schedule pages.

    One chunk per classification group (is_table=True, with structured rates
    in metadata) plus notes chunks (is_table=False) for overtime rules, fund
    breakdowns, and rate-page footnotes.
    """
    chunks: list[Chunk] = []

    for page in pages:
        for group in page.groups:
            metadata = _base_metadata(page)
            metadata.update(
                {
                    "classification_names": list(group.names),
                    "occupation_codes": list(group.occupation_codes),
                    "grade_steps": list(group.grade_steps),
                    "rates": [
                        {
                            "effective_date": row.effective_date,
                            "sum_valid": row.sum_valid,
                            **{
                                column: value
                                for column, value in zip(row.columns, row.values, strict=True)
                            },
                        }
                        for row in group.rows
                    ],
                }
            )
            chunks.append(
                Chunk(
                    text=_format_group_text(page, group, union_name),
                    page_number=page.pdf_page_number,
                    is_table=True,
                    article_number=None,
                    section_number=None,
                    article_title=(
                        f"{_local_label(page)} — {group.names[0]} ({page.map_code})"
                    ),
                    chunk_index=len(chunks),
                    metadata=metadata,
                )
            )

        chunks.extend(_notes_chunks(page, union_name, start_index=len(chunks)))

    return chunks
