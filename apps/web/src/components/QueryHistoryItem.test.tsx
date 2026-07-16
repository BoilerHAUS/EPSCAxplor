import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { QueryHistoryItem as HistoryItem } from "@/lib/types";
import { QueryHistoryItem } from "./QueryHistoryItem";

afterEach(cleanup);

const ITEM: HistoryItem = {
  id: "q-1",
  query_text: "What is the Ironworkers overtime rate?",
  answer: "Overtime is paid at 1.5x the regular rate [SOURCE 1].",
  model_used: "claude-haiku",
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
  created_at: "2026-07-14T18:22:00Z",
};

describe("QueryHistoryItem", () => {
  it("shows query text, timestamp, model, and citation count when collapsed", () => {
    render(<QueryHistoryItem item={ITEM} />);

    expect(screen.getByText("What is the Ironworkers overtime rate?")).toBeDefined();
    expect(screen.getByText(/2026-07-14/)).toBeDefined();
    expect(screen.getByText("claude-haiku")).toBeDefined();
    expect(screen.getByText("1 citation")).toBeDefined();
    // the answer stays hidden until expanded
    expect(screen.queryByText(/Overtime is paid at 1\.5x/)).toBeNull();
  });

  it("pluralizes the citation count", () => {
    render(
      <QueryHistoryItem
        item={{ ...ITEM, citations: [ITEM.citations[0], { ...ITEM.citations[0], source_number: 2 }] }}
      />,
    );
    expect(screen.getByText("2 citations")).toBeDefined();
  });

  it("expands to the full answer, citations, and disclaimer", () => {
    render(<QueryHistoryItem item={ITEM} />);

    const toggle = screen.getByRole("button", { expanded: false });
    fireEvent.click(toggle);

    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText(/Overtime is paid at 1\.5x/)).toBeDefined();
    // one marker inline in the answer, one in the citation card header
    expect(screen.getAllByLabelText("Source 1")).toHaveLength(2);
    expect(screen.getByText(/one and one-half/)).toBeDefined();
    expect(screen.getByRole("note").textContent).toContain("does not constitute legal advice");
  });

  it("collapses again on a second click", () => {
    render(<QueryHistoryItem item={ITEM} />);

    const toggle = screen.getByRole("button", { expanded: false });
    fireEvent.click(toggle);
    fireEvent.click(toggle);

    expect(screen.queryByText(/Overtime is paid at 1\.5x/)).toBeNull();
  });
});
