"use client";

/**
 * Authenticated app frame: a fixed left rail (wordmark, primary nav, theme
 * toggle + sign-out) that collapses to a segmented top bar under 768px.
 * Replaces the earlier wordmark+links top header. Pages render their own
 * content — including their own scroll region — into the main slot.
 */
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Wordmark } from "@/components/Wordmark";
import { useAuth } from "@/lib/auth";

const NAV_ITEMS = [
  { href: "/chat", label: "Chat" },
  { href: "/documents", label: "Documents" },
  { href: "/history", label: "History" },
] as const;

function SignOutIcon() {
  return (
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
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { logout } = useAuth();
  const pathname = usePathname();

  return (
    <div className="shell">
      <aside className="rail">
        <div className="rail__brand">
          <Wordmark sublabel="Agreement index" />
        </div>
        <nav className="rail__nav" aria-label="Primary">
          {NAV_ITEMS.map(({ href, label }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={active ? "rail__link rail__link--active" : "rail__link"}
              >
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="rail__spacer" />
        <div className="rail__foot">
          <ThemeToggle />
          <button type="button" className="rail-action" onClick={() => void logout()}>
            <SignOutIcon />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      <header className="topbar">
        <div className="topbar__top">
          <Wordmark />
          <div className="topbar__actions">
            <ThemeToggle />
            <button
              type="button"
              className="rail-action"
              onClick={() => void logout()}
              aria-label="Sign out"
            >
              <SignOutIcon />
              <span>Sign out</span>
            </button>
          </div>
        </div>
        <nav className="topbar__nav" aria-label="Primary">
          {NAV_ITEMS.map(({ href, label }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={active ? "topbar__link topbar__link--active" : "topbar__link"}
              >
                {label}
              </Link>
            );
          })}
        </nav>
      </header>

      <div className="shell__main">{children}</div>
    </div>
  );
}
