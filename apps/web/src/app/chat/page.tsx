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
import { AppShell } from "@/components/AppShell";
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

// Starter prompts shown in the empty state — real domain questions, not
// fabricated stats. Clicking one submits it.
const EXAMPLE_QUERIES = [
  "What is the IBEW Generation overtime rate?",
  "Foreman-to-worker ratio at Darlington",
  "Sheet Metal shift premium for nuclear work",
];

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
    <AppShell>
      <div className="chat">
        <div ref={threadRef} className="chat__thread">
          <div role="log" aria-live="polite" className="chat__inner chat__list">
            {messages.length === 0 ? (
              <div className="console-empty">
                <div className="u-label">Reference console</div>
                <div className="console-empty__title">Ask across every EPSCA agreement</div>
                <p className="console-empty__body">
                  Ask a question about overtime, wages, foreman ratios, or nuclear project
                  provisions across any EPSCA union agreement.
                </p>
                <div className="console-empty__examples">
                  {EXAMPLE_QUERIES.map((example) => (
                    <button
                      key={example}
                      type="button"
                      className="example-chip"
                      onClick={() => void handleSubmit(example)}
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {messages.map((message) => {
              if (message.kind === "user") {
                return (
                  <div key={message.id} className="query-line">
                    <span className="query-line__marker" aria-hidden="true">
                      ▸
                    </span>
                    <span className="query-line__text">{message.text}</span>
                  </div>
                );
              }
              if (message.kind === "error") {
                return (
                  <div key={message.id} role="alert" className="answer-error">
                    {message.text}
                  </div>
                );
              }
              return (
                <div key={message.id} className="record-group">
                  <AnswerCard answer={message.response.answer} />
                  <CitationList citations={message.response.citations} />
                  <LegalDisclaimer text={message.response.disclaimer} />
                </div>
              );
            })}

            {pending ? (
              <div aria-label="Generating answer" className="retrieving">
                <span className="u-label">Retrieving</span>
                <span className="retrieving__bar epx-scan" aria-hidden="true" />
              </div>
            ) : null}
          </div>
        </div>

        <div className="chat__composer">
          <div className="chat__inner">
            <QueryInput onSubmit={handleSubmit} disabled={pending} unions={unions} />
          </div>
        </div>
      </div>
    </AppShell>
  );
}
