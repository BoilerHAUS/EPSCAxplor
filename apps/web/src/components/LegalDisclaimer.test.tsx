import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { DEFAULT_DISCLAIMER, LegalDisclaimer } from "./LegalDisclaimer";

afterEach(cleanup);

describe("LegalDisclaimer", () => {
  it("renders the standard legal disclaimer by default", () => {
    render(<LegalDisclaimer />);
    const note = screen.getByRole("note");
    expect(note.textContent).toContain(
      "This answer is for reference only and does not constitute legal advice.",
    );
  });

  it("renders the disclaimer text provided by the API", () => {
    render(<LegalDisclaimer text="Custom disclaimer from /query." />);
    expect(screen.getByRole("note").textContent).toContain("Custom disclaimer from /query.");
  });

  it("marks the warning glyph as decorative", () => {
    const { container } = render(<LegalDisclaimer />);
    const glyph = container.querySelector('[aria-hidden="true"]');
    expect(glyph?.textContent).toBe("⚠️");
  });

  it("exports the default disclaimer for reuse", () => {
    expect(DEFAULT_DISCLAIMER).toMatch(/not constitute legal advice/);
  });
});
