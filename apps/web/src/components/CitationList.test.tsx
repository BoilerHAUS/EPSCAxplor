import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { Citation } from "@/lib/types";
import { CitationList } from "./CitationList";

afterEach(cleanup);

const FULL_CITATION: Citation = {
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
  source_url: "https://www.epsca.org/upload/request/13?file=Ironworkers.pdf&download=1",
};

const SPARSE_CITATION: Citation = {
  source_number: 2,
  union_name: "IBEW",
  document_title: "IBEW Wage Schedule 2025",
  document_type: "wage_schedule",
  effective_date: null,
  article: null,
  section: null,
  article_title: null,
  page_number: null,
  excerpt: "Foreman rate: $54.12/hr.",
  source_url: null,
};

describe("CitationList", () => {
  it("renders union, document, article, section, and excerpt for each citation", () => {
    render(<CitationList citations={[FULL_CITATION]} />);

    expect(screen.getByText("Ironworkers")).toBeDefined();
    expect(screen.getByText("Ironworkers 2025-2030 Collective Agreement")).toBeDefined();
    const meta = screen.getByText(/Article 9/);
    expect(meta.textContent).toContain("§9.02");
    expect(meta.textContent).toContain("Overtime");
    expect(meta.textContent).toContain("Effective 2025-05-01");
    expect(meta.textContent).toContain("p.21");
    expect(screen.getByText(/one and one-half/)).toBeDefined();
  });

  it("shows the source number matching the answer's [SOURCE N] marker", () => {
    render(<CitationList citations={[FULL_CITATION, SPARSE_CITATION]} />);
    expect(screen.getByLabelText("Source 1")).toBeDefined();
    expect(screen.getByLabelText("Source 2")).toBeDefined();
  });

  it("omits null metadata instead of rendering placeholder text", () => {
    const { container } = render(<CitationList citations={[SPARSE_CITATION]} />);

    expect(screen.getByText("IBEW")).toBeDefined();
    expect(screen.getByText(/\$54\.12/)).toBeDefined();
    expect(container.textContent).not.toContain("null");
    expect(container.textContent).not.toContain("undefined");
    expect(container.textContent).not.toContain("Effective");
    expect(container.textContent).not.toContain("§");
  });

  it("renders nothing for an empty citation list", () => {
    const { container } = render(<CitationList citations={[]} />);
    expect(container.textContent).toBe("");
  });

  it("links the document title to the source at the cited page, in a new tab", () => {
    render(<CitationList citations={[FULL_CITATION]} />);

    const link = screen.getByRole("link", { name: FULL_CITATION.document_title });
    expect(link.getAttribute("href")).toBe(`${FULL_CITATION.source_url}#page=21`);
    expect(link.getAttribute("target")).toBe("_blank");
    const rel = link.getAttribute("rel") ?? "";
    expect(rel).toContain("noopener");
    expect(rel).toContain("noreferrer");
    expect(rel).toContain("nofollow");
  });

  it("renders the document title as plain text when there is no source", () => {
    render(<CitationList citations={[SPARSE_CITATION]} />);

    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByText(SPARSE_CITATION.document_title)).toBeDefined();
  });

  it("does not render an unsafe source_url as a link (XSS guard)", () => {
    render(
      <CitationList
        citations={[{ ...FULL_CITATION, source_url: "javascript:alert(1)" }]}
      />,
    );

    expect(screen.queryByRole("link")).toBeNull();
  });
});
