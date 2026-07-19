/**
 * EPSCAxplor wordmark. A mono logotype stamped with a single amber index
 * tick — replaces the earlier `EPSCA<accent>xplor</accent>` split-color
 * treatment (a generic AI tell) with one deliberate mark. Optional sublabel
 * reads as a document designation in the rail / login masthead.
 */

export interface WordmarkProps {
  size?: "md" | "lg";
  /** Optional uppercase designation shown beneath the mark. */
  sublabel?: string;
}

export function Wordmark({ size = "md", sublabel }: WordmarkProps) {
  return (
    <div>
      <div
        className={size === "lg" ? "wordmark wordmark--lg" : "wordmark"}
        aria-label="EPSCAxplor"
      >
        <span className="wordmark__tick" aria-hidden="true" />
        <span>
          EPSCA<span style={{ color: "var(--text-tertiary)" }}>XPLOR</span>
        </span>
      </div>
      {sublabel ? (
        <div className="u-label" style={{ marginTop: 7 }}>
          {sublabel}
        </div>
      ) : null}
    </div>
  );
}
