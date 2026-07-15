/**
 * Corpus registry table: union, type, title, effective date, chunk
 * count, ingestion date, and expiry status per document. Hairline row
 * borders per the design system; mono type for dates and counts.
 */
import type { CorpusDocument } from "@/lib/types";
import { StatusPill } from "@/components/ui/StatusPill";

export interface DocumentTableProps {
  documents: CorpusDocument[];
}

const TYPE_LABELS: Record<string, string> = {
  primary_ca: "Primary CA",
  npa: "Nuclear Project Agreement",
  wage_schedule: "Wage Schedule",
};

export function documentTypeLabel(documentType: string): string {
  return (
    TYPE_LABELS[documentType] ??
    documentType
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ")
  );
}

const EM_DASH = "—";

/** ISO timestamp → date portion; null → em dash. */
function dateCell(value: string | null): string {
  return value ? value.slice(0, 10) : EM_DASH;
}

const headerCellStyle = {
  textAlign: "left" as const,
  padding: "10px 12px",
  font: "var(--text-micro)",
  letterSpacing: "var(--tracking-wide)",
  textTransform: "uppercase" as const,
  color: "var(--text-tertiary)",
  borderBottom: "1px solid var(--border-default)",
};

const cellStyle = {
  padding: "12px",
  font: "var(--text-small)",
  color: "var(--text-secondary)",
  borderBottom: "1px solid var(--border-subtle)",
  verticalAlign: "top" as const,
};

const monoCellStyle = {
  ...cellStyle,
  font: "var(--text-mono-small)",
  color: "var(--text-tertiary)",
  whiteSpace: "nowrap" as const,
};

export function DocumentTable({ documents }: DocumentTableProps) {
  if (documents.length === 0) {
    return (
      <div
        style={{
          padding: "40px 20px",
          textAlign: "center",
          color: "var(--text-tertiary)",
          font: "var(--text-body)",
        }}
      >
        No documents match the current filters.
      </div>
    );
  }

  return (
    <table style={{ width: "100%", borderCollapse: "collapse" }}>
      <thead>
        <tr>
          <th scope="col" style={headerCellStyle}>Union</th>
          <th scope="col" style={headerCellStyle}>Type</th>
          <th scope="col" style={headerCellStyle}>Title</th>
          <th scope="col" style={headerCellStyle}>Effective</th>
          <th scope="col" style={headerCellStyle}>Chunks</th>
          <th scope="col" style={headerCellStyle}>Ingested</th>
          <th scope="col" style={headerCellStyle}>Status</th>
        </tr>
      </thead>
      <tbody>
        {documents.map((document) => (
          <tr key={document.id}>
            <td style={{ ...cellStyle, font: "var(--text-body-medium)", color: "var(--text-primary)" }}>
              {document.union_name}
            </td>
            <td style={cellStyle}>{documentTypeLabel(document.document_type)}</td>
            <td style={cellStyle}>{document.title}</td>
            <td style={monoCellStyle}>{dateCell(document.effective_date)}</td>
            <td style={monoCellStyle}>{document.chunk_count ?? EM_DASH}</td>
            <td style={monoCellStyle}>{dateCell(document.ingested_at)}</td>
            <td style={cellStyle}>
              {document.is_expired ? (
                <StatusPill status="expired" />
              ) : (
                <StatusPill status="verified" label="Current" />
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
