"use client";

/**
 * Corpus browser (#29): what documents are in the system, filterable by
 * union and document type, with a hide-expired toggle and local text
 * search. Layout from the design-system export's ui_kits/chat/
 * DocumentLibraryScreen. Union/type filters refetch server-side via
 * GET /documents; the search box filters the current result locally.
 */
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { DocumentTable, documentTypeLabel } from "@/components/DocumentTable";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth";
import type { CorpusDocument, DocumentFilters } from "@/lib/types";

const ALL = "";

export default function DocumentsPage() {
  const { status } = useAuth();
  const router = useRouter();
  const [documents, setDocuments] = useState<CorpusDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [union, setUnion] = useState(ALL);
  const [docType, setDocType] = useState(ALL);
  const [hideExpired, setHideExpired] = useState(false);
  const [search, setSearch] = useState("");
  // Filter options come from the unfiltered corpus so narrowing one
  // filter never removes the others' choices.
  const [unionOptions, setUnionOptions] = useState<string[]>([]);
  const [typeOptions, setTypeOptions] = useState<string[]>([]);
  const optionsLoadedRef = useRef(false);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  useEffect(() => {
    if (status !== "authenticated") return;
    let cancelled = false;
    const filters: DocumentFilters = {};
    if (union !== ALL) filters.union_name = union;
    if (docType !== ALL) filters.document_type = docType;
    if (hideExpired) filters.is_expired = false;

    setLoading(true);
    setError(null);
    apiClient
      .listDocuments(filters)
      .then(({ documents }) => {
        if (cancelled) return;
        setDocuments(documents);
        if (!optionsLoadedRef.current) {
          optionsLoadedRef.current = true;
          setUnionOptions([...new Set(documents.map((d) => d.union_name))].sort());
          setTypeOptions([...new Set(documents.map((d) => d.document_type))].sort());
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("The document registry is temporarily unavailable. Try again shortly.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [status, union, docType, hideExpired]);

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return documents;
    return documents.filter(
      (d) =>
        d.union_name.toLowerCase().includes(needle) || d.title.toLowerCase().includes(needle),
    );
  }, [documents, search]);

  // Counts reflect the rows on screen (after local search), unlike the
  // filter options above, which stay pinned to the full corpus.
  const unionCount = new Set(visible.map((d) => d.union_name)).size;

  if (status !== "authenticated") {
    return null;
  }

  const selectStyle = {
    padding: "5px 10px",
    font: "var(--text-small)",
    fontFamily: "var(--font-sans)",
    color: "var(--text-primary)",
    background: "var(--surface-card)",
    border: "1px solid var(--border-default)",
    borderRadius: "var(--radius-md)",
    outline: "none",
  } as const;

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
            Document library
          </div>
          <div
            style={{ font: "var(--text-body)", color: "var(--text-tertiary)", marginBottom: 20 }}
          >
            {visible.length} documents · {unionCount} unions — primary agreements, nuclear
            project agreements, and wage schedules.
          </div>

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: 12,
              marginBottom: 18,
            }}
          >
            <input
              type="search"
              placeholder="Search by union or document…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                ...selectStyle,
                padding: "7px 12px",
                width: 280,
                font: "var(--text-body)",
              }}
            />
            <select
              aria-label="Union filter"
              value={union}
              onChange={(e) => setUnion(e.target.value)}
              style={selectStyle}
            >
              <option value={ALL}>All unions</option>
              {unionOptions.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
            <select
              aria-label="Document type filter"
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              style={selectStyle}
            >
              <option value={ALL}>All types</option>
              {typeOptions.map((value) => (
                <option key={value} value={value}>
                  {documentTypeLabel(value)}
                </option>
              ))}
            </select>
            <label
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                font: "var(--text-small)",
                color: "var(--text-secondary)",
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                aria-label="Hide expired"
                checked={hideExpired}
                onChange={(e) => setHideExpired(e.target.checked)}
                style={{ accentColor: "var(--accent-primary)" }}
              />
              Hide expired
            </label>
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
            data-testid="document-results"
            aria-live="polite"
            aria-busy={loading}
            style={{ opacity: loading ? 0.6 : 1, transition: "opacity 150ms ease-out" }}
          >
            {loading && documents.length === 0 ? (
              <div
                style={{
                  padding: "40px 20px",
                  textAlign: "center",
                  color: "var(--text-tertiary)",
                  font: "var(--text-body)",
                }}
              >
                Loading documents…
              </div>
            ) : (
              // refetches keep the current rows visible (dimmed) instead of
              // blanking the table on every filter change
              <DocumentTable documents={visible} />
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
