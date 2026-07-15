"use client";

/**
 * Placeholder chat route so the authenticated redirect target exists.
 * The real chat interface (query submission + citations) lands in #28.
 */
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth";

export default function ChatPage() {
  const { status, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  if (status !== "authenticated") {
    return null;
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "var(--space-4)",
        background: "var(--surface-app)",
        fontFamily: "var(--font-sans)",
      }}
    >
      <div
        style={{
          font: "800 24px var(--font-sans)",
          color: "var(--text-primary)",
          letterSpacing: "var(--tracking-tight)",
        }}
      >
        EPSCA<span style={{ color: "var(--accent-primary)" }}>xplor</span>
      </div>
      <div style={{ font: "var(--text-body)", color: "var(--text-secondary)" }}>
        The chat interface is not yet available.
      </div>
      <Button variant="ghost" size="sm" onClick={() => void logout()}>
        Sign out
      </Button>
    </main>
  );
}
