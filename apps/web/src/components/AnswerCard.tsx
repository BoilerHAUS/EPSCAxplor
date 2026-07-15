/**
 * Assistant answer bubble. Renders the generated answer with [SOURCE N]
 * markers replaced by numbered source badges that correspond to the
 * citation cards below. Bubble style from the design-system export's
 * ChatBubble (assistant variant).
 *
 * Marker syntax mirrors the backend's citation extractor
 * (services/api/src/rag/citation_extractor.py): [SOURCE N] plus extended
 * forms like [SOURCE N, Page X], case-insensitive.
 */
import { Fragment, type ReactNode } from "react";
import { SourceMarker } from "./SourceMarker";

const SOURCE_PATTERN = /\[SOURCE\s+(\d+)[^\]]*\]/gi;

export interface AnswerCardProps {
  answer: string;
}

function renderWithMarkers(answer: string): ReactNode[] {
  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;
  for (const match of answer.matchAll(SOURCE_PATTERN)) {
    const index = match.index ?? 0;
    if (index > lastIndex) {
      parts.push(<Fragment key={key++}>{answer.slice(lastIndex, index)}</Fragment>);
    }
    parts.push(<SourceMarker key={key++} number={Number(match[1])} />);
    lastIndex = index + match[0].length;
  }
  if (lastIndex < answer.length) {
    parts.push(<Fragment key={key++}>{answer.slice(lastIndex)}</Fragment>);
  }
  return parts;
}

export function AnswerCard({ answer }: AnswerCardProps) {
  return (
    <div style={{ display: "flex", justifyContent: "flex-start" }}>
      <div
        style={{
          maxWidth: "78%",
          background: "var(--surface-card)",
          color: "var(--text-primary)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-lg)",
          padding: "10px 14px",
          font: "var(--text-body)",
          fontFamily: "var(--font-sans)",
          lineHeight: 1.55,
          whiteSpace: "pre-wrap",
        }}
      >
        {renderWithMarkers(answer)}
      </div>
    </div>
  );
}
