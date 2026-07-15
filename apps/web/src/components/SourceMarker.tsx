/**
 * Numbered source badge shared by AnswerCard (inline [SOURCE N] markers)
 * and CitationList (card headers). Visual style from the design-system
 * export's CitationChip / CitationCard number bubble.
 */

export interface SourceMarkerProps {
  number: number;
  /** Slightly larger in citation card headers. */
  size?: "sm" | "md";
}

export function SourceMarker({ number, size = "sm" }: SourceMarkerProps) {
  const px = size === "sm" ? 16 : 20;
  return (
    <span
      aria-label={`Source ${number}`}
      style={{
        width: px,
        height: px,
        borderRadius: "50%",
        background: "var(--accent-primary)",
        color: "var(--text-on-accent)",
        fontSize: size === "sm" ? 10 : 11,
        fontWeight: 700,
        fontFamily: "var(--font-sans)",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        verticalAlign: "text-bottom",
      }}
    >
      {number}
    </span>
  );
}
