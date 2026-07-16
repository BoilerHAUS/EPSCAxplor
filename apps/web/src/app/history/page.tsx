"use client";

/**
 * Query history (#30): paginated, tenant-scoped list of past queries
 * (newest first per GET /query-history), each expandable to its full
 * answer, citations, and disclaimer. "Load more" appends the next page.
 */
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { QueryHistoryItem } from "@/components/QueryHistoryItem";
import { Button } from "@/components/ui/Button";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth";
import type { QueryHistoryItem as HistoryItem } from "@/lib/types";

const PAGE_SIZE = 20;

export default function HistoryPage() {
  const { status } = useAuth();
  const router = useRouter();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);
  // Server position consumed so far. Advanced by the actual row count the
  // server returned (not the deduped count) so the window keeps moving even
  // if new queries drift items across the page boundary.
  const nextOffsetRef = useRef(0);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  const loadPage = useCallback(async (offset: number) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.getQueryHistory({ limit: PAGE_SIZE, offset });
      if (!mountedRef.current) return;
      setTotal(response.total);
      nextOffsetRef.current = offset + response.queries.length;
      setItems((prev) => {
        const base = offset === 0 ? [] : prev;
        const seen = new Set(base.map((item) => item.id));
        return [...base, ...response.queries.filter((item) => !seen.has(item.id))];
      });
    } catch {
      if (mountedRef.current) {
        setError("Query history is temporarily unavailable. Try again shortly.");
      }
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (status !== "authenticated") return;
    void loadPage(0);
  }, [status, loadPage]);

  if (status !== "authenticated") {
    return null;
  }

  return (
    <main
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        background: "var(--surface-app)",
        fontFamily: "var(--font-sans)",
      }}
    >
      <AppHeader />

      <div style={{ flex: 1, overflowY: "auto" }}>
        <div
          style={{
            maxWidth: "var(--container-page)",
            margin: "0 auto",
            padding: "28px 32px",
          }}
        >
          <div style={{ font: "var(--text-h1)", color: "var(--text-primary)", marginBottom: 4 }}>
            Query history
          </div>
          <div
            style={{ font: "var(--text-body)", color: "var(--text-tertiary)", marginBottom: 20 }}
          >
            {items.length} of {total} queries — newest first.
          </div>

          {error ? (
            <div
              role="alert"
              style={{
                padding: "10px 14px",
                background: "var(--status-error-subtle)",
                border: "1px solid var(--status-error)",
                borderRadius: "var(--radius-md)",
                font: "var(--text-small)",
                color: "var(--text-primary)",
                marginBottom: 18,
              }}
            >
              {error}
            </div>
          ) : null}

          <div
            aria-live="polite"
            aria-busy={loading}
            style={{ display: "flex", flexDirection: "column", gap: 10 }}
          >
            {!loading && !error && items.length === 0 ? (
              <div
                style={{
                  padding: "40px 20px",
                  textAlign: "center",
                  color: "var(--text-tertiary)",
                  font: "var(--text-body)",
                }}
              >
                No queries yet — ask one in the chat and it will show up here.
              </div>
            ) : null}

            {items.map((item) => (
              <QueryHistoryItem key={item.id} item={item} />
            ))}

            {loading ? (
              <div
                style={{
                  padding: "20px",
                  textAlign: "center",
                  color: "var(--text-tertiary)",
                  font: "var(--text-body)",
                }}
              >
                Loading…
              </div>
            ) : null}
          </div>

          {!loading && items.length < total ? (
            <div style={{ marginTop: 18, textAlign: "center" }}>
              <Button
                variant="secondary"
                size="md"
                onClick={() => void loadPage(nextOffsetRef.current)}
              >
                Load more
              </Button>
            </div>
          ) : null}
        </div>
      </div>
    </main>
  );
}
