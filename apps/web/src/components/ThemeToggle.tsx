"use client";

/**
 * Light/dark theme toggle. The color system already ships a full
 * [data-theme="light"] override (tokens/colors.css) that nothing exercised;
 * this surfaces it. The choice persists to localStorage and is applied
 * pre-paint by the init script in app/layout.tsx (no flash on reload).
 */
import { useEffect, useState } from "react";

const STORAGE_KEY = "epsca-theme";

export function ThemeToggle() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    setTheme(document.documentElement.dataset.theme === "light" ? "light" : "dark");
  }, []);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // storage unavailable (private mode / blocked) — theme still applies for the session
    }
  }

  const goingLight = theme === "dark";

  return (
    <button
      type="button"
      className="rail-action"
      onClick={toggle}
      aria-label={goingLight ? "Switch to light theme" : "Switch to dark theme"}
    >
      {goingLight ? (
        <svg
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      ) : (
        <svg
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
        </svg>
      )}
      <span>{goingLight ? "Light" : "Dark"}</span>
    </button>
  );
}
