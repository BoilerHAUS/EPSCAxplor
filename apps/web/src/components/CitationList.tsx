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
    <div className="citations">
      <div className="u-label">
        {citations.length} {citations.length === 1 ? "Citation" : "Citations"}
      </div>
      {citations.map((citation) => {
        const meta = metadataLine(citation);
        return (
          <div key={citation.source_number} className="citation">
            <div className="citation__head">
              <SourceMarker number={citation.source_number} size="md" />
              <span className="citation__union">{citation.union_name}</span>
            </div>
            <div className="citation__doc">{citation.document_title}</div>
            {meta ? <div className="citation__meta">{meta}</div> : null}
            <div className="citation__excerpt">{citation.excerpt}</div>
          </div>
        );
      })}
    </div>
  );
}
