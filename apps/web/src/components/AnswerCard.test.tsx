import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { AnswerCard } from "./AnswerCard";

afterEach(cleanup);

describe("AnswerCard — source markers", () => {
  it("renders plain answer text without markers untouched", () => {
    render(<AnswerCard answer="The provided documents do not contain information about parking." />);
    expect(
      screen.getByText(/do not contain information about parking/),
    ).toBeDefined();
    expect(screen.queryAllByLabelText(/^Source \d+$/)).toHaveLength(0);
  });

  it("renders [SOURCE N] markers as numbered source chips", () => {
    render(
      <AnswerCard answer="Overtime is paid at 1.5x [SOURCE 1] and 2x on Sundays [SOURCE 2]." />,
    );

    expect(screen.getByLabelText("Source 1").textContent).toContain("1");
    expect(screen.getByLabelText("Source 2").textContent).toContain("2");
    expect(screen.getByText(/Overtime is paid at 1\.5x/)).toBeDefined();
    // the raw marker text must not remain in the rendered output
    expect(screen.queryByText(/\[SOURCE/)).toBeNull();
  });

  it("handles extended marker forms like [SOURCE 2, Page 34]", () => {
    render(<AnswerCard answer="Shift premium applies [SOURCE 2, Page 34]." />);
    expect(screen.getByLabelText("Source 2")).toBeDefined();
    expect(screen.queryByText(/Page 34\]/)).toBeNull();
  });

  it("renders repeated markers for the same source", () => {
    render(<AnswerCard answer="Rate A [SOURCE 1]. Rate B [SOURCE 1]." />);
    expect(screen.getAllByLabelText("Source 1")).toHaveLength(2);
  });

  it("preserves multi-line answers", () => {
    render(<AnswerCard answer={"Line one [SOURCE 1]\n\nLine two"} />);
    expect(screen.getByText(/Line one/)).toBeDefined();
    expect(screen.getByText(/Line two/)).toBeDefined();
  });
});

describe("AnswerCard — Markdown rendering", () => {
  it("renders Markdown headings as heading elements", () => {
    render(<AnswerCard answer={"## Foreman Rates\n\nBody text."} />);
    expect(screen.getByRole("heading", { name: "Foreman Rates" })).toBeDefined();
    expect(screen.getByText("Body text.")).toBeDefined();
  });

  it("renders bold text as <strong>, not literal asterisks", () => {
    render(<AnswerCard answer={"Rate for **United Association** plumbers."} />);
    const strong = screen.getByText("United Association");
    expect(strong.tagName).toBe("STRONG");
    expect(screen.queryByText(/\*\*/)).toBeNull();
  });

  it("renders Markdown bullet lists as list items", () => {
    render(<AnswerCard answer={"- Local 71 Ottawa\n- Local 46 Toronto"} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("renders GFM tables", () => {
    const table = "| Local | Package |\n| --- | --- |\n| 71 | $78.24 |";
    render(<AnswerCard answer={table} />);
    expect(screen.getByRole("table")).toBeDefined();
    expect(screen.getByRole("columnheader", { name: "Local" })).toBeDefined();
    expect(screen.getByRole("cell", { name: "$78.24" })).toBeDefined();
  });

  it("does not render raw HTML embedded in the answer (XSS-safe)", () => {
    const { container } = render(
      <AnswerCard answer={'Before <img src=x onerror="alert(1)"> after'} />,
    );
    expect(container.querySelector("img")).toBeNull();

    const { container: scriptContainer } = render(
      <AnswerCard answer={"text <script>alert(1)</script> more"} />,
    );
    expect(scriptContainer.querySelector("script")).toBeNull();
  });
});

describe("AnswerCard — markers inside Markdown blocks", () => {
  it("renders [SOURCE N] markers inside list items", () => {
    render(<AnswerCard answer={"- Base rate is $57.35 [SOURCE 1]"} />);
    expect(screen.getByRole("listitem")).toBeDefined();
    expect(screen.getByLabelText("Source 1").textContent).toContain("1");
    expect(screen.queryByText(/\[SOURCE/)).toBeNull();
  });

  it("renders [SOURCE N] markers inside headings", () => {
    render(<AnswerCard answer={"## Current Rates [SOURCE 2]"} />);
    expect(screen.getByRole("heading", { name: /Current Rates/ })).toBeDefined();
    expect(screen.getByLabelText("Source 2")).toBeDefined();
    expect(screen.queryByText(/\[SOURCE/)).toBeNull();
  });
});
