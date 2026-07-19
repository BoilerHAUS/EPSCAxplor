"use client";

/**
 * Design-system Button. Variant, size, and hover are CSS-driven (forms.css);
 * keyboard focus uses the global :focus-visible ring (globals.css). No JS
 * focus/hover state — the element just carries the right classes.
 */
import type { ReactNode } from "react";

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

export function Button({
  children,
  variant = "primary",
  size = "md",
  disabled = false,
  onClick,
  type = "button",
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`btn btn--${variant} btn--${size}`}
    >
      {children}
    </button>
  );
}
