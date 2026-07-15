"use client";

/**
 * Chat interface (#28): submit a query, render the grounded answer with
 * [SOURCE N] markers, structured citations, and the mandatory legal
 * disclaimer. Layout from the design-system export's ui_kits/chat/
 * ChatScreen. No streaming in Phase 3 — the full response is rendered
 * when it arrives.
 */
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { AnswerCard } from "@/components/AnswerCard";
import { AppHeader } from "@/components/AppHeader";
import { CitationList } from "@/components/CitationList";
import { LegalDisclaimer } from "@/components/LegalDisclaimer";
import { QueryInput } from "@/components/QueryInput";
import { ApiError, apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth";
import type { QueryResponse } from "@/lib/types";

type MessageInput =
  | { kind: "user"; text: string }
  | { kind: "answer"; response: QueryResponse }
  | { kind: "error"; text: string };

type Message = MessageInput & { id: number };

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 429) {
      return "Query limit reached — wait a moment and try again, or check your subscription tier.";
    }
    if (error.status === 503) {
      return "The answer service is temporarily unavailable. Try again shortly.";
    }
    return error.detail;
  }
  return "Unable to reach the server. Check your connection and try again.";
}

export default function ChatPage() {
  const { status } = useAuth();
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [pending, setPending] = useState(false);
  const [unions, setUnions] = useState<string[]>([]);
  const nextIdRef = useRef(0);
  const threadRef = useRef<HTMLDivElement>(null);
  // An in-flight query can outlive the page (sign-out, navigation); this
  // flag keeps its continuation from updating unmounted state — same
  // pattern as disposedRef in lib/auth.tsx.
  const mountedRef = useRef(true);

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

  // Union filter options come from the corpus registry; the filter is
  // simply hidden if the lookup fails.
  useEffect(() => {
    if (status !== "authenticated") return;
    let cancelled = false;
    apiClient
      .listDocuments()
      .then(({ documents }) => {
        if (cancelled) return;
        setUnions([...new Set(documents.map((d) => d.union_name))].sort());
      })
      .catch(() => {
        // non-blocking: chat works without the filter
      });
    return () => {
      cancelled = true;
    };
  }, [status]);

  useEffect(() => {
    const thread = threadRef.current;
    if (thread) thread.scrollTop = thread.scrollHeight;
  }, [messages, pending]);

  function push(message: MessageInput) {
    setMessages((prev) => [...prev, { ...message, id: nextIdRef.current++ }]);
  }

  async function handleSubmit(query: string) {
    push({ kind: "user", text: query });
    setPending(true);
    try {
      const response = await apiClient.query(query);
      if (mountedRef.current) push({ kind: "answer", response });
    } catch (error) {
      if (mountedRef.current) push({ kind: "error", text: errorMessage(error) });
    } finally {
      if (mountedRef.current) setPending(false);
    }
  }

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

      <div ref={threadRef} style={{ flex: 1, overflowY: "auto", padding: "24px 0" }}>
        <div
          role="log"
          aria-live="polite"
          style={{
            maxWidth: "var(--container-chat)",
            margin: "0 auto",
            display: "flex",
            flexDirection: "column",
            gap: 16,
            padding: "0 20px",
          }}
        >
          {messages.length === 0 ? (
            <div
              style={{
                textAlign: "center",
                padding: "60px 20px",
                color: "var(--text-tertiary)",
                font: "var(--text-body)",
              }}
            >
              Ask a question about overtime, wages, foreman ratios, or nuclear project
              provisions across any EPSCA union agreement.
            </div>
          ) : null}

          {messages.map((message) => {
            if (message.kind === "user") {
              return (
                <div key={message.id} style={{ display: "flex", justifyContent: "flex-end" }}>
                  <div
                    style={{
                      maxWidth: "78%",
                      background: "var(--accent-primary)",
                      color: "var(--text-on-accent)",
                      borderRadius: "var(--radius-lg)",
                      padding: "10px 14px",
                      font: "var(--text-body)",
                      lineHeight: 1.55,
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {message.text}
                  </div>
                </div>
              );
            }
            if (message.kind === "error") {
              return (
                <div
                  key={message.id}
                  role="alert"
                  style={{
                    padding: "10px 14px",
                    background: "var(--status-error-subtle)",
                    border: "1px solid var(--status-error)",
                    borderRadius: "var(--radius-md)",
                    font: "var(--text-small)",
                    color: "var(--text-primary)",
                  }}
                >
                  {message.text}
                </div>
              );
            }
            return (
              <div
                key={message.id}
                style={{ display: "flex", flexDirection: "column", gap: 12 }}
              >
                <AnswerCard answer={message.response.answer} />
                <CitationList citations={message.response.citations} />
                <LegalDisclaimer text={message.response.disclaimer} />
              </div>
            );
          })}

          {pending ? (
            <div
              aria-label="Generating answer"
              style={{
                display: "inline-flex",
                gap: 5,
                alignItems: "center",
                alignSelf: "flex-start",
                background: "var(--surface-card)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-pill)",
                padding: "10px 14px",
              }}
            >
              <style>{`@keyframes epsca-pulse{0%,60%,100%{opacity:.25}30%{opacity:1}}`}</style>
              {[0, 0.15, 0.3].map((delay) => (
                <span
                  key={delay}
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    background: "var(--text-tertiary)",
                    animation: `epsca-pulse 1.1s ease-in-out ${delay}s infinite`,
                  }}
                />
              ))}
            </div>
          ) : null}
        </div>
      </div>

      <div
        style={{
          padding: "14px 20px 22px",
          borderTop: "1px solid var(--border-subtle)",
          background: "var(--surface-app)",
        }}
      >
        <div style={{ maxWidth: "var(--container-chat)", margin: "0 auto" }}>
          <QueryInput onSubmit={handleSubmit} disabled={pending} unions={unions} />
        </div>
      </div>
    </main>
  );
}
