import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiClient } from "@/lib/api-client";
import type { CorpusDocument } from "@/lib/types";
import DocumentsPage from "./page";

const { mockReplace, mockUseAuth } = vi.hoisted(() => ({
  mockReplace: vi.fn(),
  mockUseAuth: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
  usePathname: () => "/documents",
}));

vi.mock("@/lib/auth", () => ({
  useAuth: mockUseAuth,
}));

vi.mock("@/lib/api-client", () => {
  class ApiError extends Error {
    constructor(
      public readonly status: number,
      public readonly detail: string,
    ) {
      super(`${status}: ${detail}`);
    }
  }
  return {
    ApiError,
    apiClient: {
      listDocuments: vi.fn(),
    },
  };
});

const mocked = vi.mocked(apiClient);

function doc(overrides: Partial<CorpusDocument>): CorpusDocument {
  return {
    id: "doc-1",
    union_name: "IBEW",
    document_type: "primary_ca",
    title: "IBEW CA",
    effective_date: "2025-05-01",
    expiry_date: null,
    is_expired: false,
    chunk_count: 100,
    ingested_at: "2026-06-02T14:03:00Z",
    ...overrides,
  };
}

const ALL_DOCS = [
  doc({ id: "1", union_name: "IBEW", document_type: "primary_ca", title: "IBEW CA" }),
  doc({ id: "2", union_name: "IBEW", document_type: "wage_schedule", title: "IBEW Wages" }),
  doc({
    id: "3",
    union_name: "Ironworkers",
    document_type: "npa",
    title: "Ironworkers NPA",
    is_expired: true,
  }),
];

describe("DocumentsPage", () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({ status: "authenticated", login: vi.fn(), logout: vi.fn() });
    mocked.listDocuments.mockResolvedValue({ documents: ALL_DOCS, total: 3 });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("redirects to /login when unauthenticated", () => {
    mockUseAuth.mockReturnValue({ status: "unauthenticated", login: vi.fn(), logout: vi.fn() });
    render(<DocumentsPage />);
    expect(mockReplace).toHaveBeenCalledWith("/login");
  });

  it("lists all documents with a count after the initial fetch", async () => {
    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText("IBEW CA")).toBeDefined();
    });
    expect(screen.getByText("Ironworkers NPA")).toBeDefined();
    expect(screen.getByText(/3 documents · 2 unions/)).toBeDefined();
    expect(mocked.listDocuments).toHaveBeenCalledWith({});
  });

  it("refetches server-side when a union is selected", async () => {
    render(<DocumentsPage />);
    await waitFor(() => expect(screen.getByText("IBEW CA")).toBeDefined());

    mocked.listDocuments.mockResolvedValueOnce({
      documents: ALL_DOCS.filter((d) => d.union_name === "IBEW"),
      total: 2,
    });
    fireEvent.change(screen.getByLabelText("Union filter"), { target: { value: "IBEW" } });

    await waitFor(() => {
      expect(mocked.listDocuments).toHaveBeenLastCalledWith({ union_name: "IBEW" });
      expect(screen.queryByText("Ironworkers NPA")).toBeNull();
    });
  });

  it("refetches when a document type is selected", async () => {
    render(<DocumentsPage />);
    await waitFor(() => expect(screen.getByText("IBEW CA")).toBeDefined());

    fireEvent.change(screen.getByLabelText("Document type filter"), {
      target: { value: "wage_schedule" },
    });

    await waitFor(() => {
      expect(mocked.listDocuments).toHaveBeenLastCalledWith({ document_type: "wage_schedule" });
    });
  });

  it("hides expired documents via the toggle", async () => {
    render(<DocumentsPage />);
    await waitFor(() => expect(screen.getByText("IBEW CA")).toBeDefined());

    fireEvent.click(screen.getByLabelText("Hide expired"));

    await waitFor(() => {
      expect(mocked.listDocuments).toHaveBeenLastCalledWith({ is_expired: false });
    });
  });

  it("filters client-side by search text", async () => {
    render(<DocumentsPage />);
    await waitFor(() => expect(screen.getByText("IBEW CA")).toBeDefined());

    fireEvent.change(screen.getByPlaceholderText(/Search/), {
      target: { value: "ironworkers" },
    });

    expect(screen.getByText("Ironworkers NPA")).toBeDefined();
    expect(screen.queryByText("IBEW CA")).toBeNull();
    // search is local: no extra server call
    expect(mocked.listDocuments).toHaveBeenCalledTimes(1);
  });

  it("keeps the full union list in the filter after filtering", async () => {
    render(<DocumentsPage />);
    await waitFor(() => expect(screen.getByText("IBEW CA")).toBeDefined());

    mocked.listDocuments.mockResolvedValueOnce({
      documents: ALL_DOCS.filter((d) => d.union_name === "IBEW"),
      total: 2,
    });
    fireEvent.change(screen.getByLabelText("Union filter"), { target: { value: "IBEW" } });
    await waitFor(() => expect(screen.queryByText("Ironworkers NPA")).toBeNull());

    const select = screen.getByLabelText("Union filter") as HTMLSelectElement;
    const labels = Array.from(select.options).map((o) => o.textContent);
    expect(labels).toContain("Ironworkers");
  });

  it("keeps the current rows visible while a filter refetch is in flight", async () => {
    render(<DocumentsPage />);
    await waitFor(() => expect(screen.getByText("IBEW CA")).toBeDefined());

    // never resolves during the test — refetch stays in flight
    mocked.listDocuments.mockImplementationOnce(() => new Promise(() => {}));
    fireEvent.change(screen.getByLabelText("Union filter"), { target: { value: "IBEW" } });

    expect(screen.getByText("IBEW CA")).toBeDefined();
    expect(screen.queryByText(/Loading documents/)).toBeNull();
    expect(screen.getByTestId("document-results").getAttribute("aria-busy")).toBe("true");
  });

  it("shows an error state when the fetch fails", async () => {
    mocked.listDocuments.mockRejectedValueOnce(new ApiError(503, "upstream error"));

    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toMatch(/unavailable|try again/i);
    });
  });
});
