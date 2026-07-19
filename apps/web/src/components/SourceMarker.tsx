/**
 * Numbered source reference shared by AnswerCard (inline [SOURCE N] markers)
 * and CitationList (card headers). Rendered as a bracketed monospace footnote
 * ref — [1] — so citations read as legal references, not chat-app chips.
 */

export interface SourceMarkerProps {
  number: number;
  /** Slightly larger in citation card headers. */
  size?: "sm" | "md";
}

export function SourceMarker({ number, size = "sm" }: SourceMarkerProps) {
  return (
    <span
      aria-label={`Source ${number}`}
      className={size === "sm" ? "srcref srcref--inline" : "srcref srcref--lg"}
    >
      [{number}]
    </span>
  );
}
