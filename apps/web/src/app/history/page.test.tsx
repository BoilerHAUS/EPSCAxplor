import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "@/lib/api-client";
import type { QueryHistoryItem, QueryHistoryResponse } from "@/lib/types";
import HistoryPage from "./page";

const { mockReplace, mockUseAuth } = vi.hoisted(() => ({
  mockReplace: vi.fn(),
  mockUseAuth: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
  usePathname: () => "/history",
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
      getQueryHistory: vi.fn(),
    },
  };
});

const mocked = vi.mocked(apiClient);

function item(id: string, text: string): QueryHistoryItem {
  return {
    id,
    query_text: text,
    answer: `Answer for ${text}`,
    model_used: "claude-haiku",
    citations: [],
    created_at: "2026-07-14T18:22:00Z",
  };
}

function page(items: QueryHistoryItem[], total: number, offset: number): QueryHistoryResponse {
  return { queries: items, total, limit: 20, offset };
}

describe("HistoryPage", () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({ status: "authenticated", login: vi.fn(), logout: vi.fn() });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("redirects to /login when unauthenticated", () => {
    mockUseAuth.mockReturnValue({ status: "unauthenticated", login: vi.fn(), logout: vi.fn() });
    render(<HistoryPage />);
    expect(mockReplace).toHaveBeenCalledWith("/login");
  });

  it("lists past queries after the initial fetch", async () => {
    mocked.getQueryHistory.mockResolvedValueOnce(
      page([item("1", "First query"), item("2", "Second query")], 2, 0),
    );

    render(<HistoryPage />);

    await waitFor(() => expect(screen.getByText("First query")).toBeDefined());
    expect(screen.getByText("Second query")).toBeDefined();
    expect(mocked.getQueryHistory).toHaveBeenCalledWith({ limit: 20, offset: 0 });
    expect(screen.getByText(/2 of 2 queries/)).toBeDefined();
  });

  it("loads the next page and appends it", async () => {
    const firstPage = Array.from({ length: 20 }, (_, i) => item(`a${i}`, `Query ${i}`));
    mocked.getQueryHistory
      .mockResolvedValueOnce(page(firstPage, 25, 0))
      .mockResolvedValueOnce(page([item("b0", "Older query")], 25, 20));

    render(<HistoryPage />);
    await waitFor(() => expect(screen.getByText("Query 0")).toBeDefined());

    fireEvent.click(screen.getByRole("button", { name: "Load more" }));

    await waitFor(() => expect(screen.getByText("Older query")).toBeDefined());
    expect(mocked.getQueryHistory).toHaveBeenLastCalledWith({ limit: 20, offset: 20 });
    // earlier items remain
    expect(screen.getByText("Query 0")).toBeDefined();
  });

  it("dedupes rows when a query drifts across the page boundary", async () => {
    // A new query logged between pages shifts the offset window so the
    // second page repeats an item already shown; it must not render twice.
    const firstPage = Array.from({ length: 20 }, (_, i) => item(`a${i}`, `Query ${i}`));
    mocked.getQueryHistory
      .mockResolvedValueOnce(page(firstPage, 26, 0))
      .mockResolvedValueOnce(page([item("a19", "Query 19"), item("b0", "Older query")], 26, 20));

    render(<HistoryPage />);
    await waitFor(() => expect(screen.getByText("Query 19")).toBeDefined());

    fireEvent.click(screen.getByRole("button", { name: "Load more" }));

    await waitFor(() => expect(screen.getByText("Older query")).toBeDefined());
    expect(screen.getAllByText("Query 19")).toHaveLength(1);
  });

  it("hides the load-more control once everything is loaded", async () => {
    mocked.getQueryHistory.mockResolvedValueOnce(page([item("1", "Only query")], 1, 0));

    render(<HistoryPage />);
    await waitFor(() => expect(screen.getByText("Only query")).toBeDefined());

    expect(screen.queryByRole("button", { name: "Load more" })).toBeNull();
  });

  it("shows an empty state when there is no history", async () => {
    mocked.getQueryHistory.mockResolvedValueOnce(page([], 0, 0));

    render(<HistoryPage />);

    await waitFor(() => expect(screen.getByText(/No queries yet/)).toBeDefined());
  });

  it("shows an error state when the fetch fails", async () => {
    mocked.getQueryHistory.mockRejectedValueOnce(new Error("network"));

    render(<HistoryPage />);

    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toMatch(/unavailable|try again/i);
    });
  });
});
