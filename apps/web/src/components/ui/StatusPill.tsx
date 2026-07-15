/**
 * Design-system StatusPill, ported from the design-system export
 * (components/feedback/StatusPill.jsx + .d.ts). Document/system state
 * only — never decorative.
 */

export interface StatusPillProps {
  /** Preset document/system state */
  status?: "verified" | "expired" | "superseded" | "nuclear";
  /** Override label text */
  label?: string;
}

interface PillStyle {
  label: string;
  color: string;
  bg: string;
}

const statusMap: Record<NonNullable<StatusPillProps["status"]>, PillStyle> = {
  verified: {
    label: "Verified source",
    color: "var(--status-success)",
    bg: "var(--status-success-subtle)",
  },
  expired: {
    label: "Expired agreement",
    color: "var(--status-error)",
    bg: "var(--status-error-subtle)",
  },
  superseded: {
    label: "Superseded",
    color: "var(--status-warning)",
    bg: "var(--status-warning-subtle)",
  },
  nuclear: {
    label: "Nuclear project context",
    color: "var(--status-info)",
    bg: "var(--status-info-subtle)",
  },
};

export function StatusPill({ status, label }: StatusPillProps) {
  const s: PillStyle = (status && statusMap[status]) || {
    label: label ?? status ?? "",
    color: "var(--text-tertiary)",
    bg: "var(--surface-hover)",
  };
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        font: "var(--text-small)",
        fontFamily: "var(--font-sans)",
        color: s.color,
        background: s.bg,
        borderRadius: "var(--radius-pill)",
        padding: "5px 12px 5px 10px",
        whiteSpace: "nowrap",
        flexShrink: 0,
      }}
    >
      <span
        style={{
          width: 7,
          height: 7,
          borderRadius: "50%",
          background: s.color,
          flexShrink: 0,
        }}
      />
      {label || s.label}
    </span>
  );
}
