/**
 * Legal disclaimer shown under every generated answer — a pipeline
 * requirement, not decoration. Ported from the design-system export's
 * DisclaimerBar (components/feedback/DisclaimerBar.jsx).
 */

export const DEFAULT_DISCLAIMER =
  "This answer is for reference only and does not constitute legal advice. " +
  "Consult qualified labour relations counsel for binding interpretations.";

export interface LegalDisclaimerProps {
  /** Disclaimer text from the /query response; falls back to the standard line. */
  text?: string;
}

export function LegalDisclaimer({ text }: LegalDisclaimerProps) {
  return (
    <div
      role="note"
      aria-label="Legal disclaimer"
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 8,
        padding: "10px 14px",
        background: "var(--status-warning-subtle)",
        border: "1px solid var(--accent-border)",
        borderRadius: "var(--radius-md)",
        font: "var(--text-small)",
        fontFamily: "var(--font-sans)",
        color: "var(--text-secondary)",
      }}
    >
      <span aria-hidden="true">⚠️</span>
      <span>{text || DEFAULT_DISCLAIMER}</span>
    </div>
  );
}
