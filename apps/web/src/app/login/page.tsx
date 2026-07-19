"use client";

/**
 * Login screen, built from the design-system export's
 * ui_kits/chat/LoginScreen.jsx, wired to POST /auth/login via the
 * auth context.
 */
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { Wordmark } from "@/components/Wordmark";
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
    <main className="auth">
      <section className="auth__brand u-gridfield">
        <Wordmark size="lg" sublabel="Collective agreement index" />
        <p className="auth__statement">
          Grounded, cited answers across every EPSCA collective agreement.
        </p>
        <p className="auth__disclaimer">
          Reference only — not legal advice. All answers must be verified against the
          governing collective agreement.
        </p>
      </section>

      <section className="auth__panel">
        <form onSubmit={handleSubmit} className="auth__form">
          <h1 className="auth__title">Sign in</h1>
          <p className="auth__sub">Grounded answers for EPSCA collective agreements.</p>

          <div className="auth__fields">
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
            <div role="alert" className="auth__error">
              {error}
            </div>
          ) : null}

          <div className="auth__submit">
            <Button type="submit" variant="primary" size="md" disabled={submitting}>
              {submitting ? "Signing in…" : "Sign in"}
            </Button>
          </div>
        </form>
      </section>
    </main>
  );
}
