"use client";

/**
 * One past query in the history list: collapsed row with query text,
 * timestamp, model, and citation count; expands to the full answer,
 * citations, and disclaimer using the same components as live chat.
 * HistoryItem carries no disclaimer field, so the standard line is used.
 */
import { useState } from "react";
import { AnswerCard } from "@/components/AnswerCard";
import { CitationList } from "@/components/CitationList";
import { LegalDisclaimer } from "@/components/LegalDisclaimer";
import type { QueryHistoryItem as HistoryItem } from "@/lib/types";

export interface QueryHistoryItemProps {
  item: HistoryItem;
}

/** ISO timestamp → "YYYY-MM-DD HH:MM" (UTC as stored); em dash if malformed. */
function formatTimestamp(isoTimestamp: string): string {
  if (isoTimestamp.length < 16) return "—";
  return isoTimestamp.slice(0, 16).replace("T", " ");
}

export function QueryHistoryItem({ item }: QueryHistoryItemProps) {
  const [expanded, setExpanded] = useState(false);
  const citationCount = item.citations.length;

  return (
    <div className="log__entry">
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((prev) => !prev)}
        className="log__toggle"
      >
        <span className="log__query">{item.query_text}</span>
        <span className="log__meta">
          <span>{formatTimestamp(item.created_at)}</span>
          <span>{item.model_used}</span>
          <span>
            {citationCount} {citationCount === 1 ? "citation" : "citations"}
          </span>
        </span>
      </button>

      {expanded ? (
        <div className="log__detail">
          <AnswerCard answer={item.answer} />
          <CitationList citations={item.citations} />
          <LegalDisclaimer />
        </div>
      ) : null}
    </div>
  );
}
