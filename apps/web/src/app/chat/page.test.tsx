import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiClient } from "@/lib/api-client";
import type { QueryResponse } from "@/lib/types";
import ChatPage from "./page";

const { mockReplace, mockLogout, mockUseAuth } = vi.hoisted(() => ({
  mockReplace: vi.fn(),
  mockLogout: vi.fn(),
  mockUseAuth: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
  usePathname: () => "/chat",
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
      query: vi.fn(),
      listDocuments: vi.fn(),
    },
  };
});

const mocked = vi.mocked(apiClient);

const RESPONSE: QueryResponse = {
  answer: "Overtime is paid at 1.5x the regular rate [SOURCE 1].",
  citations: [
    {
      source_number: 1,
      union_name: "Ironworkers",
      document_title: "Ironworkers 2025-2030 Collective Agreement",
      document_type: "primary_ca",
      effective_date: "2025-05-01",
      article: "Article 9",
      section: "9.02",
      article_title: "Overtime",
      page_number: 21,
      excerpt: "Overtime shall be paid at one and one-half (1.5) times the regular hourly rate.",
    },
  ],
  model_used: "claude-haiku",
  disclaimer:
    "This answer is for reference only and does not constitute legal advice. Consult qualified labour relations counsel for binding interpretations.",
  query_log_id: "log-1",
};

async function submitQuery(text: string) {
  fireEvent.change(screen.getByRole("textbox"), { target: { value: text } });
  fireEvent.click(screen.getByLabelText("Send"));
}

describe("ChatPage", () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({ status: "authenticated", login: vi.fn(), logout: mockLogout });
    mocked.listDocuments.mockResolvedValue({ documents: [], total: 0 });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("redirects to /login when unauthenticated", () => {
    mockUseAuth.mockReturnValue({ status: "unauthenticated", login: vi.fn(), logout: mockLogout });
    render(<ChatPage />);
    expect(mockReplace).toHaveBeenCalledWith("/login");
  });

  it("shows the empty state before any query", () => {
    render(<ChatPage />);
    expect(screen.getByText(/Ask a question about overtime, wages/)).toBeDefined();
  });

  it("renders the user message, then answer with citations and disclaimer", async () => {
    let resolveQuery!: (r: QueryResponse) => void;
    mocked.query.mockImplementationOnce(
      () => new Promise<QueryResponse>((resolve) => (resolveQuery = resolve)),
    );

    render(<ChatPage />);
    await submitQuery("What is the Ironworkers overtime rate?");

    // user bubble + loading state while in flight
    expect(screen.getByText("What is the Ironworkers overtime rate?")).toBeDefined();
    expect(screen.getByLabelText("Generating answer")).toBeDefined();
    expect(mocked.query).toHaveBeenCalledWith("What is the Ironworkers overtime rate?");

    resolveQuery(RESPONSE);
    await waitFor(() => {
      expect(screen.getByText(/Overtime is paid at 1\.5x the regular rate/)).toBeDefined();
    });

    expect(screen.queryByLabelText("Generating answer")).toBeNull();
    expect(screen.getByText("Ironworkers")).toBeDefined();
    expect(screen.getByText(/one and one-half/)).toBeDefined();
    expect(screen.getByRole("note").textContent).toContain("does not constitute legal advice");
  });

  it("shows a rate-limit message on 429", async () => {
    mocked.query.mockRejectedValueOnce(new ApiError(429, "monthly query limit reached"));

    render(<ChatPage />);
    await submitQuery("anything");

    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toMatch(/limit/i);
    });
  });

  it("shows an availability message on 503", async () => {
    mocked.query.mockRejectedValueOnce(new ApiError(503, "upstream error"));

    render(<ChatPage />);
    await submitQuery("anything");

    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toMatch(/unavailable|try again/i);
    });
  });

  it("shows a generic message when the request never reaches the server", async () => {
    mocked.query.mockRejectedValueOnce(new TypeError("fetch failed"));

    render(<ChatPage />);
    await submitQuery("anything");

    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toMatch(/unable to reach/i);
    });
  });

  it("does not update state when unmounted while a query is in flight", async () => {
    let resolveQuery!: (r: QueryResponse) => void;
    mocked.query.mockImplementationOnce(
      () => new Promise<QueryResponse>((resolve) => (resolveQuery = resolve)),
    );
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    const { unmount } = render(<ChatPage />);
    await submitQuery("anything");
    unmount();

    resolveQuery(RESPONSE);
    await Promise.resolve();

    expect(errorSpy).not.toHaveBeenCalled();
    errorSpy.mockRestore();
  });

  it("populates the union filter from the corpus registry", async () => {
    mocked.listDocuments.mockResolvedValue({
      documents: [
        {
          id: "1",
          union_name: "IBEW",
          document_type: "primary_ca",
          title: "IBEW CA",
          effective_date: null,
          expiry_date: null,
          is_expired: false,
          chunk_count: null,
          ingested_at: null,
        },
        {
          id: "2",
          union_name: "IBEW",
          document_type: "wage_schedule",
          title: "IBEW WS",
          effective_date: null,
          expiry_date: null,
          is_expired: false,
          chunk_count: null,
          ingested_at: null,
        },
        {
          id: "3",
          union_name: "Ironworkers",
          document_type: "primary_ca",
          title: "IW CA",
          effective_date: null,
          expiry_date: null,
          is_expired: false,
          chunk_count: null,
          ingested_at: null,
        },
      ],
      total: 3,
    });

    render(<ChatPage />);

    await waitFor(() => {
      const select = screen.getByLabelText("Union filter") as HTMLSelectElement;
      const labels = Array.from(select.options).map((o) => o.textContent);
      expect(labels).toEqual(["All unions", "IBEW", "Ironworkers"]);
    });
  });

  it("signs out via the shell button", () => {
    render(<ChatPage />);
    // the shell renders a sign-out in both the rail and the mobile top bar;
    // clicking either calls logout
    fireEvent.click(screen.getAllByRole("button", { name: "Sign out" })[0]);
    expect(mockLogout).toHaveBeenCalled();
  });
});
