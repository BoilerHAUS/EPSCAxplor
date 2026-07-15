import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { AnswerCard } from "./AnswerCard";

afterEach(cleanup);

describe("AnswerCard", () => {
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
