/**
 * Structured citations under an answer: union, document, article/section,
 * effective date, page, and excerpt — the traceability surface every
 * answer must carry. Card layout from the design-system export's
 * CitationCard; monospace for the legal/numeric metadata per the type
 * system ("precision reads as data").
 */
import type { Citation } from "@/lib/types";
import { SourceMarker } from "./SourceMarker";

export interface CitationListProps {
  citations: Citation[];
}

function metadataLine(citation: Citation): string {
  const segments: string[] = [];
  const article = [
    citation.article,
    citation.section ? `§${citation.section}` : null,
    citation.article_title,
  ]
    .filter(Boolean)
    .join(" ");
  if (article) segments.push(article);
  if (citation.effective_date) segments.push(`Effective ${citation.effective_date}`);
  if (citation.page_number !== null) segments.push(`p.${citation.page_number}`);
  return segments.join(" · ");
}

export function CitationList({ citations }: CitationListProps) {
  if (citations.length === 0) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {citations.map((citation) => {
        const meta = metadataLine(citation);
        return (
          <div
            key={citation.source_number}
            style={{
              background: "var(--surface-card)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-lg)",
              padding: "14px 16px",
              fontFamily: "var(--font-sans)",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 8,
              }}
            >
              <SourceMarker number={citation.source_number} size="md" />
              <span style={{ font: "var(--text-body-medium)", color: "var(--text-primary)" }}>
                {citation.union_name}
              </span>
            </div>
            <div
              style={{
                font: "var(--text-small)",
                color: "var(--text-secondary)",
                marginBottom: meta ? 6 : 10,
              }}
            >
              {citation.document_title}
            </div>
            {meta ? (
              <div
                style={{
                  font: "var(--text-mono-small)",
                  color: "var(--text-tertiary)",
                  marginBottom: 10,
                }}
              >
                {meta}
              </div>
            ) : null}
            <div
              style={{
                font: "var(--text-mono-body)",
                color: "var(--text-primary)",
                background: "var(--surface-sunken)",
                borderRadius: "var(--radius-md)",
                padding: "10px 12px",
              }}
            >
              “{citation.excerpt}”
            </div>
          </div>
        );
      })}
    </div>
  );
}
