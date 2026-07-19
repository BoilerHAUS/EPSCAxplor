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
    <article className="record">
      <div className="record__head">
        <span className="u-label">Answer</span>
        <span className="record__status u-label">Grounded</span>
      </div>
      <div className="record__body">{renderWithMarkers(answer)}</div>
    </article>
  );
}
