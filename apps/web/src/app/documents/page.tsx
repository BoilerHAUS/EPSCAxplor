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
import { AppShell } from "@/components/AppShell";
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

  return (
    <AppShell>
      <div className="page">
        <div className="page__scroll">
          <div className="page__inner">
            <div className="masthead">
              <div className="u-label">Corpus registry</div>
              <h1 className="masthead__title">Document library</h1>
              <p className="masthead__sub">
                {visible.length} documents · {unionCount} unions — primary agreements, nuclear
                project agreements, and wage schedules.
              </p>
            </div>

            <div className="controls">
              <input
                type="search"
                placeholder="Search by union or document…"
                aria-label="Search documents"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="field field--search"
              />
              <select
                aria-label="Union filter"
                value={union}
                onChange={(e) => setUnion(e.target.value)}
                className="field"
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
                className="field"
              >
                <option value={ALL}>All types</option>
                {typeOptions.map((value) => (
                  <option key={value} value={value}>
                    {documentTypeLabel(value)}
                  </option>
                ))}
              </select>
              <label className="checkline">
                <input
                  type="checkbox"
                  aria-label="Hide expired"
                  checked={hideExpired}
                  onChange={(e) => setHideExpired(e.target.checked)}
                />
                Hide expired
              </label>
            </div>

            {error ? (
              <div role="alert" className="answer-error" style={{ marginBottom: 18 }}>
                {error}
              </div>
            ) : null}

            <div
              data-testid="document-results"
              aria-live="polite"
              aria-busy={loading}
              style={{ opacity: loading ? 0.6 : 1, transition: "opacity 150ms var(--ease-out)" }}
            >
              {loading && documents.length === 0 ? (
                <div className="ledger-empty">Loading documents…</div>
              ) : (
                // refetches keep the current rows visible (dimmed) instead of
                // blanking the table on every filter change
                <div className="ledger-wrap">
                  <DocumentTable documents={visible} />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
