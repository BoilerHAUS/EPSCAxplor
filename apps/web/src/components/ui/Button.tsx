"use client";

/**
 * Design-system Button, ported from the design-system export
 * (components/forms/Button.jsx + Button.d.ts). Inline styles over CSS
 * custom properties — no utility framework.
 */
import { useState, type CSSProperties, type ReactNode } from "react";

export interface ButtonProps {
  /** Button label / content */
  children: ReactNode;
  /** Visual style */
  variant?: "primary" | "secondary" | "ghost" | "danger";
  /** Size */
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  onClick?: () => void;
  type?: "button" | "submit";
}

const sizeStyles: Record<NonNullable<ButtonProps["size"]>, CSSProperties> = {
  sm: { padding: "6px 12px", font: "var(--text-small)" },
  md: { padding: "8px 16px", font: "var(--text-body-medium)" },
  lg: { padding: "10px 20px", font: "var(--text-body-lg)" },
};

interface VariantStyles {
  base: CSSProperties;
  hover: CSSProperties;
}

function variantStyles(variant: NonNullable<ButtonProps["variant"]>): VariantStyles {
  switch (variant) {
    case "secondary":
      return {
        base: {
          background: "var(--surface-card)",
          color: "var(--text-primary)",
          border: "1px solid var(--border-default)",
        },
        hover: { background: "var(--surface-hover)" },
      };
    case "ghost":
      return {
        base: {
          background: "transparent",
          color: "var(--text-primary)",
          border: "1px solid transparent",
        },
        hover: { background: "var(--surface-hover)" },
      };
    case "danger":
      return {
        base: {
          background: "var(--status-error)",
          color: "#fff",
          border: "1px solid transparent",
        },
        hover: { filter: "brightness(0.92)" },
      };
    default:
      return {
        base: {
          background: "var(--accent-primary)",
          color: "var(--text-on-accent)",
          border: "1px solid transparent",
        },
        hover: { background: "var(--accent-primary-hover)" },
      };
  }
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  disabled = false,
  onClick,
  type = "button",
}: ButtonProps) {
  const [hover, setHover] = useState(false);
  const [focused, setFocused] = useState(false);
  const v = variantStyles(variant);
  const style: CSSProperties = {
    ...sizeStyles[size],
    ...v.base,
    ...(hover && !disabled ? v.hover : {}),
    boxShadow: focused ? "var(--shadow-focus)" : "none",
    borderRadius: "var(--radius-md)",
    fontFamily: "var(--font-sans)",
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.45 : 1,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "8px",
    lineHeight: 1,
    whiteSpace: "nowrap",
    transition: "background 120ms ease-out, filter 120ms ease-out",
  };

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={style}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
    >
      {children}
    </button>
  );
}
