"use client";

/**
 * Login screen, built from the design-system export's
 * ui_kits/chat/LoginScreen.jsx, wired to POST /auth/login via the
 * auth context.
 */
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { status, login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/chat");
    }
  }, [status, router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.replace("/chat");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Invalid email or password.");
      } else if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Unable to reach the server. Try again.");
      }
      setSubmitting(false);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--surface-app)",
        fontFamily: "var(--font-sans)",
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          width: 340,
          background: "var(--surface-card)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-xl)",
          boxShadow: "var(--shadow-lg)",
          padding: "32px 28px",
        }}
      >
        <div
          style={{
            font: "800 24px var(--font-sans)",
            color: "var(--text-primary)",
            marginBottom: 4,
            letterSpacing: "var(--tracking-tight)",
          }}
        >
          EPSCA<span style={{ color: "var(--accent-primary)" }}>xplor</span>
        </div>
        <div
          style={{
            font: "var(--text-small)",
            color: "var(--text-tertiary)",
            marginBottom: 22,
          }}
        >
          Grounded answers for EPSCA collective agreements.
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 12,
            marginBottom: 18,
          }}
        >
          <Input
            placeholder="you@company.com"
            value={email}
            onChange={setEmail}
            type="email"
            name="email"
            autoComplete="email"
            required
            ariaLabel="Email"
            disabled={submitting}
          />
          <Input
            placeholder="Password"
            value={password}
            onChange={setPassword}
            type="password"
            name="password"
            autoComplete="current-password"
            required
            ariaLabel="Password"
            disabled={submitting}
          />
        </div>

        {error ? (
          <div
            role="alert"
            style={{
              font: "var(--text-small)",
              color: "var(--status-error)",
              marginTop: -6,
              marginBottom: 14,
            }}
          >
            {error}
          </div>
        ) : null}

        <Button type="submit" variant="primary" size="md" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </Button>

        <div
          style={{
            font: "var(--text-micro)",
            color: "var(--text-tertiary)",
            marginTop: 18,
            lineHeight: 1.5,
          }}
        >
          Reference only — not legal advice. All answers must be verified
          against the governing collective agreement.
        </div>
      </form>
    </main>
  );
}
