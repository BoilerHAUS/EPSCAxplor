"use client";

/**
 * Design-system Input. The border reflects the error prop; keyboard focus
 * shows the global :focus-visible ring (globals.css) rather than a JS-driven
 * inline style — no focus state in the component.
 */

export interface InputProps {
  placeholder?: string;
  value?: string;
  onChange?: (value: string) => void;
  disabled?: boolean;
  /** Error message — renders red border + helper text below */
  error?: string;
  type?: "text" | "email" | "password" | "search";
  size?: "sm" | "md";
  id?: string;
  name?: string;
  autoComplete?: string;
  required?: boolean;
  ariaLabel?: string;
}

export function Input({
  placeholder,
  value,
  onChange,
  disabled = false,
  error,
  type = "text",
  size = "md",
  id,
  name,
  autoComplete,
  required,
  ariaLabel,
}: InputProps) {
  return (
    <div>
      <input
        id={id}
        name={name}
        autoComplete={autoComplete}
        required={required}
        aria-label={ariaLabel}
        aria-invalid={error ? true : undefined}
        type={type}
        placeholder={placeholder}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange?.(e.target.value)}
        style={{
          width: "100%",
          boxSizing: "border-box",
          padding: size === "sm" ? "6px 10px" : "9px 12px",
          font: "var(--text-body)",
          fontFamily: "var(--font-sans)",
          color: "var(--text-primary)",
          background: "var(--surface-card)",
          border: `1px solid ${error ? "var(--status-error)" : "var(--border-default)"}`,
          borderRadius: "var(--radius-md)",
          opacity: disabled ? 0.5 : 1,
        }}
      />
      {error ? (
        <div
          role="alert"
          style={{
            font: "var(--text-small)",
            color: "var(--status-error)",
            marginTop: 4,
          }}
        >
          {error}
        </div>
      ) : null}
    </div>
  );
}
