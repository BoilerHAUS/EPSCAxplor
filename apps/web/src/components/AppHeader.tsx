"use client";

/**
 * Shared authenticated app header: wordmark, primary navigation, and
 * sign-out. Hairline bottom border per the design system — flat
 * surfaces, no shadow.
 */
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth";

const NAV_ITEMS = [
  { href: "/chat", label: "Chat" },
  { href: "/documents", label: "Documents" },
  { href: "/history", label: "History" },
] as const;

export function AppHeader() {
  const { logout } = useAuth();
  const pathname = usePathname();

  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "12px 20px",
        borderBottom: "1px solid var(--border-subtle)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
        <div
          style={{
            font: "800 18px var(--font-sans)",
            color: "var(--text-primary)",
            letterSpacing: "var(--tracking-tight)",
          }}
        >
          EPSCA<span style={{ color: "var(--accent-primary)" }}>xplor</span>
        </div>
        <nav style={{ display: "flex", gap: 16 }}>
          {NAV_ITEMS.map(({ href, label }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                style={{
                  font: "var(--text-body-medium)",
                  color: active ? "var(--accent-primary)" : "var(--text-secondary)",
                  textDecoration: "none",
                }}
              >
                {label}
              </Link>
            );
          })}
        </nav>
      </div>
      <Button variant="ghost" size="sm" onClick={() => void logout()}>
        Sign out
      </Button>
    </header>
  );
}
