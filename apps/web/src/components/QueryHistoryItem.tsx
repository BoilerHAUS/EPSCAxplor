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
    <div
      style={{
        background: "var(--surface-card)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
        overflow: "hidden",
      }}
    >
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((prev) => !prev)}
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          gap: 16,
          width: "100%",
          padding: "14px 16px",
          background: "transparent",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
          fontFamily: "var(--font-sans)",
        }}
      >
        <span
          style={{
            font: "var(--text-body-medium)",
            color: "var(--text-primary)",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {item.query_text}
        </span>
        <span
          style={{
            display: "inline-flex",
            gap: 12,
            flexShrink: 0,
            font: "var(--text-mono-small)",
            color: "var(--text-tertiary)",
          }}
        >
          <span>{formatTimestamp(item.created_at)}</span>
          <span>{item.model_used}</span>
          <span>
            {citationCount} {citationCount === 1 ? "citation" : "citations"}
          </span>
        </span>
      </button>

      {expanded ? (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 12,
            padding: "0 16px 16px",
            borderTop: "1px solid var(--border-subtle)",
            paddingTop: 14,
          }}
        >
          <AnswerCard answer={item.answer} />
          <CitationList citations={item.citations} />
          <LegalDisclaimer />
        </div>
      ) : null}
    </div>
  );
}
