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

export function DocumentTable({ documents }: DocumentTableProps) {
  if (documents.length === 0) {
    return <div className="ledger-empty">No documents match the current filters.</div>;
  }

  return (
    <table className="ledger">
      <thead>
        <tr>
          <th scope="col">Union</th>
          <th scope="col">Type</th>
          <th scope="col">Title</th>
          <th scope="col">Effective</th>
          <th scope="col">Chunks</th>
          <th scope="col">Ingested</th>
          <th scope="col">Status</th>
        </tr>
      </thead>
      <tbody>
        {documents.map((document) => (
          <tr key={document.id}>
            <td className="ledger__union">{document.union_name}</td>
            <td>{documentTypeLabel(document.document_type)}</td>
            <td>{document.title}</td>
            <td className="ledger__mono">{dateCell(document.effective_date)}</td>
            <td className="ledger__mono">{document.chunk_count ?? EM_DASH}</td>
            <td className="ledger__mono">{dateCell(document.ingested_at)}</td>
            <td>
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
