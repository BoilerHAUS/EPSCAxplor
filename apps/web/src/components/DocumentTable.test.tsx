import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { CorpusDocument } from "@/lib/types";
import { DocumentTable } from "./DocumentTable";

afterEach(cleanup);

const CURRENT: CorpusDocument = {
  id: "doc-1",
  union_name: "IBEW",
  document_type: "primary_ca",
  title: "IBEW Generation 2025-2030 Collective Agreement",
  effective_date: "2025-05-01",
  expiry_date: "2030-04-30",
  is_expired: false,
  chunk_count: 412,
  ingested_at: "2026-06-02T14:03:00Z",
};

const EXPIRED_SPARSE: CorpusDocument = {
  id: "doc-2",
  union_name: "Boilermakers",
  document_type: "npa",
  title: "Boilermakers NPA 2021",
  effective_date: null,
  expiry_date: null,
  is_expired: true,
  chunk_count: null,
  ingested_at: null,
};

describe("DocumentTable", () => {
  it("renders one row per document with union, type, title, effective date, chunks, and ingested date", () => {
    render(<DocumentTable documents={[CURRENT]} />);

    const row = screen.getAllByRole("row")[1];
    expect(row.textContent).toContain("IBEW");
    expect(row.textContent).toContain("Primary CA");
    expect(row.textContent).toContain("IBEW Generation 2025-2030 Collective Agreement");
    expect(row.textContent).toContain("2025-05-01");
    expect(row.textContent).toContain("412");
    expect(row.textContent).toContain("2026-06-02");
  });

  it("labels known document types and prettifies unknown ones", () => {
    render(
      <DocumentTable
        documents={[
          CURRENT,
          { ...EXPIRED_SPARSE, id: "d3", document_type: "wage_schedule" },
          { ...EXPIRED_SPARSE, id: "d4", document_type: "letter_of_understanding" },
        ]}
      />,
    );

    expect(screen.getByText("Primary CA")).toBeDefined();
    expect(screen.getByText("Wage Schedule")).toBeDefined();
    expect(screen.getByText("Letter Of Understanding")).toBeDefined();
  });

  it("shows an expiry status pill per row", () => {
    render(<DocumentTable documents={[CURRENT, EXPIRED_SPARSE]} />);

    expect(screen.getByText("Current")).toBeDefined();
    expect(screen.getByText("Expired agreement")).toBeDefined();
  });

  it("renders em dashes for null metadata instead of placeholder text", () => {
    const { container } = render(<DocumentTable documents={[EXPIRED_SPARSE]} />);

    expect(container.textContent).not.toContain("null");
    expect(container.textContent).not.toContain("undefined");
    const row = screen.getAllByRole("row")[1];
    expect(row.textContent).toContain("—");
  });

  it("shows an empty message when no documents match", () => {
    render(<DocumentTable documents={[]} />);
    expect(screen.getByText(/No documents match/)).toBeDefined();
  });
});
