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
    <div role="note" aria-label="Legal disclaimer" className="disclaimer">
      <span className="disclaimer__key" aria-hidden="true">
        ⚠️
      </span>
      <span>{text || DEFAULT_DISCLAIMER}</span>
    </div>
  );
}
