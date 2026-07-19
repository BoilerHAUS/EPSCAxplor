"use client";

/**
 * Query history (#30): paginated, tenant-scoped list of past queries
 * (newest first per GET /query-history), each expandable to its full
 * answer, citations, and disclaimer. "Load more" appends the next page.
 */
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { AppShell } from "@/components/AppShell";
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
    <AppShell>
      <div className="page">
        <div className="page__scroll">
          <div className="page__inner">
            <div className="masthead">
              <div className="u-label">Query log</div>
              <h1 className="masthead__title">Query history</h1>
              <p className="masthead__sub">
                {items.length} of {total} queries — newest first.
              </p>
            </div>

            {error ? (
              <div role="alert" className="answer-error" style={{ marginBottom: 18 }}>
                {error}
              </div>
            ) : null}

            <div aria-live="polite" aria-busy={loading} className="log">
              {!loading && !error && items.length === 0 ? (
                <div className="log__loose">
                  No queries yet — ask one in the chat and it will show up here.
                </div>
              ) : null}

              {items.map((item) => (
                <QueryHistoryItem key={item.id} item={item} />
              ))}

              {loading ? <div className="log__loose">Loading…</div> : null}
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
      </div>
    </AppShell>
  );
}
